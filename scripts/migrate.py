#!/usr/bin/env python3
"""Copy work items across configured trackers; never modify the source.

plan SOURCE DESTINATION --id ID [--mapping FILE]
apply ID | resume ID | verify ID | cutover ID | rollback ID

MCP/CLI bridges use the same canonical operations as the direct API adapter.
Missing capabilities are limitations, never silently fabricated successes.
"""
from __future__ import annotations

import argparse
import base64
import contextlib
import json
import sys
import uuid
from pathlib import Path

import integration_core as core
from integration_transport import Pending, transport
from integrations import root_path, runtime


def identity(conn):
    defaults = {"azure-devops": "https://dev.azure.com", "github": "https://api.github.com",
                "gitlab": "https://gitlab.com", "linear": "https://api.linear.app"}
    value = {k: conn.get(k) for k in ("provider", "organization", "project", "repository", "team")}
    value["base_url"] = conn.get("base_url", defaults.get(conn["provider"], "")).rstrip("/").lower()
    if conn["provider"] == "github" and value["repository"]:
        value["repository"] = value["repository"].lower()
    return value


def plan_hash(manifest):
    return core.digest({k: v for k, v in manifest.items() if k != "status"})


def migration_dir(root, mid):
    return Path(root) / "project/backlog/migrations" / core.safe_id(mid)


@contextlib.contextmanager
def locked(root, mid):
    import fcntl
    directory = runtime(root) / "locks"
    directory.mkdir(exist_ok=True)
    with (directory / (core.safe_id(mid) + ".lock")).open("a") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError("another process is operating on this migration") from None
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def state(root, mid):
    directory = migration_dir(root, mid)
    manifest = core.load(directory / "manifest.json")
    if not manifest:
        raise ValueError("migration plan does not exist")
    private = runtime(root) / "migrations" / core.safe_id(mid)
    sources = core.load(private / "source.json")
    if sources is None or core.digest(sources) != manifest["archive_sha256"]:
        raise ValueError("private source archive missing or modified")
    _, connections, _ = core.configuration(root)
    for side in ("source", "destination"):
        name = manifest[side]
        if name not in connections or identity(connections[name]) != manifest[side + "_identity"]:
            raise ValueError("configured migration endpoint changed; make a new plan")
    return directory, manifest, private, sources, connections


def client_for(root, manifest, connections, side, writing=False, phase="apply"):
    name = manifest[side]
    return transport(name, connections[name], runtime(root) / "migrations" / manifest["id"] / "bridge" / phase / side,
                     writing=writing, locked=manifest[side + "_transport"])


def user_key(user):
    if isinstance(user, dict):
        return str(user.get("accountId", user.get("login", user.get("id", user.get("uniqueName", user.get("email", ""))))))
    return str(user) if user else ""


def user_matches(user, expected):
    if isinstance(user, dict):
        return str(expected) in {str(user[k]) for k in ("accountId", "id", "login", "uniqueName", "email") if user.get(k)}
    return user_key(user) == str(expected)


def label_names(labels):
    if isinstance(labels, dict):
        labels = labels.get("nodes", [])
    return [l.get("name", "") if isinstance(l, dict) else str(l) for l in (labels or [])]


def plan(root, source, destination, mid, mappings=None, factory=None):
    """Gather immutable source records + bytes before any destination write."""
    cfg, connections, _ = core.configuration(root)
    if source == destination:
        raise ValueError("source and destination must differ")
    for name in (source, destination):
        if connections[name]["provider"] not in core.TRACKERS:
            raise ValueError("only tracker work items may be migrated")
    if identity(connections[source]) == identity(connections[destination]):
        raise ValueError("source and destination identify the same tracker project")
    directory = migration_dir(root, mid)
    if (directory / "manifest.json").exists():
        raise ValueError("migration ID already exists; use resume or a new ID")
    private = runtime(root) / "migrations" / core.safe_id(mid)
    make = factory or (lambda name, side: transport(name, connections[name], private / "bridge" / "plan" / side))
    src, dest = make(source, "source"), make(destination, "destination")
    doctor = dest.call("doctor")
    capabilities = doctor.get("capabilities", [])
    schema = dest.call("schema")
    snap = src.call("list", full=True)
    snap = core.normalize(source, connections[source], snap)
    if snap["coverage"] != "complete":
        raise ValueError("migration requires a complete source inventory, not a partial snapshot")
    sources = [item for item in snap["items"] if item["kind"] == "work_item"]
    if any(not i.get("full") for i in sources):
        raise ValueError("full source records with paginated comments/attachments required")
    rules = mappings or {}
    limitations, operations, entries = [], [], []

    def limit(code, message):
        reason = rules.get("accept", {}).get(code)
        limitations.append({"code": code, "message": message, "accepted_reason": reason if isinstance(reason, str) and reason.strip() else None})

    for needed in ("create", "configure", "find", "get"):
        if needed not in capabilities:
            raise ValueError(f"destination lacks required capability: {needed}")
    ids = {str(i["id"]) for i in sources}
    if len(ids) != len(sources):
        raise ValueError("duplicate source item IDs")
    local_mapping = core.mapping(root)
    refs = [ref for entry in local_mapping["tasks"].values() for ref in entry.get("refs", [])]
    refs += [ref for phase_refs in local_mapping.get("phases", {}).values() for ref in phase_refs]
    missing_refs = {str(ref["id"]) for ref in refs if ref["connection"] == source and
                    ref.get("kind", "work_item") == "work_item" and str(ref["id"]) not in ids}
    for external in sorted(missing_refs):
        limit("mapping."+external, "local mapping refers to an item absent from the complete source inventory")
    ordered, pending = [], list(sources)
    while pending:
        ready = [i for i in pending if not i.get("parent") or str(i["parent"]) not in ids or str(i["parent"]) in {str(o["id"]) for o in ordered}]
        if not ready:
            raise ValueError("source parent relationships contain a cycle")
        ordered.extend(ready)
        pending = [i for i in pending if i not in ready]
    sources = ordered
    for item in sources:
        external = str(item["id"])
        key = core.digest([identity(connections[source]), external, identity(connections[destination])])[:24]
        typ = rules.get("types", {}).get(item["type"], item["type"])
        state_name = rules.get("states", {}).get(item["raw_state"], item["raw_state"])
        for field, value, choices in (("type", typ, schema.get("types", [])), ("state", state_name, schema.get("states", []))):
            if value not in choices:
                # Required fields cannot be waived; a valid mapping is needed.
                raise ValueError(f"{external}: map {field} {value!r} to a supported destination value")
        labels = [rules.get("labels", {}).get(l, l) for l in label_names(item.get("labels"))]
        if not schema.get("free_labels"):
            for label in list(labels):
                if label not in schema.get("labels", []):
                    limit(external+".label."+label, "label not available at destination: " + label)
                    labels.remove(label)
        original_user = user_key(item.get("assignee"))
        assignee = rules.get("users", {}).get(original_user)
        if original_user and not assignee:
            limit(external+".assignee", "assignee needs an explicit identity mapping; original preserved in archive")
        if assignee and schema.get("users") and assignee not in schema["users"]:
            raise ValueError(f"{external}: mapped assignee not available at destination")
        description = item["description"] + "\n\nOriginal source: " + item.get("url", "") + "\nOriginal identity: " + source + ":" + external
        description += "\nOriginal assignee: " + (original_user or "unassigned")
        description += "\nMigration: " + mid + "; original system metadata retained in the source archive."
        target = {"title": item["title"], "description": description, "type": typ,
                  "raw_state": state_name, "labels": labels, "assignee": assignee}
        if typ in schema.get("parent_types", []) and (not item.get("parent") or str(item["parent"]) not in ids):
            raise ValueError(f"{external}: destination type requires a parent in the migration scope")
        entries.append({"source_id": external, "key": key, "target": target})
        operations.extend([{"key": key+":create", "kind": "create", "source_id": external, "item": target,
                            "parent_source_id": str(item["parent"]) if typ in schema.get("parent_types", []) else None},
                           {"key": key+":configure", "kind": "configure", "source_id": external, "item": target}])
        for comment in item.get("comments", []):
            if "comment" not in capabilities:
                limit(external+".comment."+str(comment["id"]), "destination cannot create comment; original archived")
                continue
            comment_key = key+":comment:"+core.digest(str(comment["id"]))[:16]
            body = comment["body"] + "\n\nOriginal author: " + json.dumps(comment.get("author"), ensure_ascii=False) + "\nOriginal time: " + str(comment.get("created", "unknown"))
            operations.append({"key": comment_key, "kind": "comment", "source_id": external, "body": body})
        for index, attachment in enumerate(item.get("attachments", [])):
            file_key = key+":attachment:"+core.digest(str(attachment.get("id", index)))[:16]
            name = Path(attachment.get("name", attachment.get("filename", "attachment"))).name
            url = attachment.get("url", attachment.get("content"))
            if not url:
                raise ValueError("attachment has no downloadable URL")
            # Always archive source bytes, even when the destination cannot upload them.
            downloaded = src.call("download", url=url)
            content = base64.b64decode(downloaded["base64"], validate=True)
            checksum = core.digest(content)
            if downloaded.get("sha256") and downloaded["sha256"] != checksum:
                raise ValueError("source attachment checksum mismatch")
            cache = private / "attachments" / core.digest(file_key)
            cache.parent.mkdir(parents=True, exist_ok=True); cache.write_bytes(content)
            if "attach" not in capabilities:
                limit(external+".attachment."+str(attachment.get("id", index)), "attachment upload unavailable; source bytes archived")
                continue
            operations.append({"key": file_key, "kind": "attach", "source_id": external, "name": name,
                               "sha256": checksum, "cache": str(cache.relative_to(private)), "source_url": url,
                               "source_link": attachment.get("source_link", url)})
        parent = item.get("parent")
        if parent:
            if str(parent) not in ids or "parent" not in capabilities:
                limit(external+".parent", "parent is outside migration inventory or destination hierarchy is unsupported")
            else:
                # Parent operations are reordered after all creates.
                operations.append({"key": key+":parent", "kind": "parent", "source_id": external, "parent_source_id": str(parent)})
    # All items must exist before comments, files or parent relationships are copied.
    operations.sort(key=lambda op: {"create": 0, "attach": 1, "configure": 2, "comment": 3, "parent": 4}[op["kind"]])
    if len({op["key"] for op in operations}) != len(operations):
        raise ValueError("source inventory contains duplicate comment or attachment IDs")
    core.save(private / "source.json", sources)
    manifest = {"version": 1, "id": mid, "source": source, "destination": destination,
                "source_identity": identity(connections[source]), "destination_identity": identity(connections[destination]),
                "source_transport": src.mode, "destination_transport": dest.mode, "created": core.now(),
                "archive_sha256": core.digest(sources), "entries": entries, "operations": operations,
                "limitations": limitations, "status": "planned", "fetched": snap["fetched"]}
    core.save(directory / "manifest.json", manifest)
    core.save(directory / "journal.json", {"operations": {}, "items": {}})
    # Backup only local configuration/mapping. No external cleanup or source write.
    core.save(directory / "before.json", {"config": cfg, "mapping": core.load(core.mapping_path(root))})
    return manifest


def rewrite(text, source_id, manifest, journal):
    for op in manifest["operations"]:
        if op["kind"] == "attach" and op["source_id"] == source_id:
            result = journal["operations"].get(op["key"], {}).get("result", {})
            if result.get("url"):
                text = text.replace(op["source_url"], result["url"])
                text = text.replace(op.get("source_link", op["source_url"]), result["url"])
    return text


def resolved_item(entry, manifest, journal):
    value = dict(entry["target"])
    value["description"] = rewrite(value["description"], entry["source_id"], manifest, journal)
    value["description"] += "\n\nproject-docs-migration:" + entry["key"] + ":create"
    return value


def apply(root, mid, factory=None):
    directory, manifest, private, _, connections = state(root, mid)
    if manifest["status"] in {"cutover", "rolled-back"}:
        raise ValueError("migration already cut over or rolled back; create a new plan instead")
    if any(not l["accepted_reason"] for l in manifest["limitations"]):
        raise ValueError("unaccepted limitations; create a new plan with explicit accept reasons")
    client = factory or client_for(root, manifest, connections, "destination", writing=True)
    journal = core.load(directory / "journal.json")
    for op in manifest["operations"]:
        key = op["key"]
        previous = journal["operations"].get(key, {})
        if previous.get("status") == "done":
            continue
        marker = "project-docs-migration:" + key
        external = journal["items"].get(op["source_id"])
        generation = previous.get("reconcile_generation", 0)
        try:
            result = None
            if op["kind"] in {"create", "comment", "attach"}:
                kind = {"create": "item", "comment": "comment", "attach": "attachment"}[op["kind"]]
                marker = "pd-" + core.digest(key)[:24] if op["kind"] == "attach" else marker
                # A new read context on every resume avoids reusing an old 'not found' MCP response.
                if hasattr(client, "runtime"):
                    if previous.get("status") == "uncertain":
                        generation += 1
                    journal["operations"][key] = {"status": "reconciling", "reconcile_generation": generation}
                    core.save(directory / "journal.json", journal)
                    client.runtime = private / "bridge" / "reconcile" / str(generation)
                found = client.call("find", marker=marker, kind=kind, item_id=external)
                if not isinstance(found, list) or len(found) > 1:
                    raise ValueError("remote operation reconciliation is ambiguous")
                if found:
                    result = found[0]
            if result is None:
                journal["operations"][key] = {"status": "running", "at": core.now(), "reconcile_generation": generation}
                core.save(directory / "journal.json", journal)
                if op["kind"] == "create":
                    target = dict(op["item"])
                    if op.get("parent_source_id"):
                        target["parent_id"] = journal["items"][op["parent_source_id"]]
                    result = client.call("create", item=target, marker=marker)
                elif op["kind"] == "configure":
                    entry = next(e for e in manifest["entries"] if e["source_id"] == op["source_id"])
                    result = client.call("configure", id=external, item=resolved_item(entry, manifest, journal))
                elif op["kind"] == "comment":
                    result = client.call("comment", id=external, body=rewrite(op["body"], op["source_id"], manifest, journal), marker=marker)
                elif op["kind"] == "attach":
                    content = (private / op["cache"]).read_bytes()
                    if core.digest(content) != op["sha256"]:
                        raise ValueError("cached attachment was modified")
                    result = client.call("attach", id=external, name=op["name"], base64_data=base64.b64encode(content).decode(), marker=marker)
                else:
                    result = client.call("parent", id=external, parent_id=journal["items"][op["parent_source_id"]])
            if not isinstance(result, dict) or not result.get("id"):
                raise ValueError("write/reconciliation response has no record ID")
            if op["kind"] == "create":
                journal["items"][op["source_id"]] = str(result["id"])
            journal["operations"][key] = {"status": "done", "result": result, "at": core.now()}
            core.save(directory / "journal.json", journal)
        except Pending:
            # Pending is not a failure; do not invalidate a response awaiting an agent.
            core.save(directory / "journal.json", journal)
            raise
        except Exception:
            journal["operations"][key] = {"status": "uncertain", "at": core.now(),
                                           "reconcile_generation": generation}
            core.save(directory / "journal.json", journal)
            raise RuntimeError(f"operation {key} uncertain; resume will reconcile before retry") from None
    manifest["status"] = "applied"
    core.save(directory / "manifest.json", manifest)
    return journal


def verify(root, mid, factory=None):
    directory, manifest, private, _, connections = state(root, mid)
    session_file = private / "verify-session.json"
    session = core.load(session_file, {})
    if session.get("status") != "pending":
        session = {"id": uuid.uuid4().hex, "status": "pending"}
        core.save(session_file, session)
    client = factory or client_for(root, manifest, connections, "destination", phase="verify-"+session["id"])
    journal = core.load(directory / "journal.json")
    missing, failed, checked = [], [], []
    observed = []
    for entry in manifest["entries"]:
        source_id = entry["source_id"]
        external = journal["items"].get(source_id)
        if external is None:
            missing.append(source_id); continue
        try:
            actual = client.call("get", id=external)
            if not isinstance(actual, dict) or str(actual.get("id")) != str(external) or not actual.get("full"):
                raise ValueError("readback must return the requested full record")
            observed.append(actual)
            target = resolved_item(entry, manifest, journal)
            for field in ("title", "raw_state", "type"):
                if actual.get(field) != target[field]:
                    failed.append({"source_id": source_id, "field": field})
            if target["description"] not in actual.get("description", ""):
                failed.append({"source_id": source_id, "field": "description"})
            if sorted(label_names(actual.get("labels"))) != sorted(target["labels"]):
                failed.append({"source_id": source_id, "field": "labels"})
            if target.get("assignee") and not user_matches(actual.get("assignee"), target["assignee"]):
                failed.append({"source_id": source_id, "field": "assignee"})
            for op in (o for o in manifest["operations"] if o["source_id"] == source_id):
                if journal["operations"].get(op["key"], {}).get("status") != "done":
                    failed.append({"source_id": source_id, "operation": op["key"], "field": "unfinished"})
                if op["kind"] == "comment":
                    marker = "project-docs-migration:" + op["key"]
                    matches = [c for c in actual.get("comments", []) if marker in c["body"]]
                    if len(matches) != 1 or rewrite(op["body"], source_id, manifest, journal) not in matches[0]["body"]:
                        failed.append({"source_id": source_id, "field": "comment", "operation": op["key"]})
                elif op["kind"] == "attach":
                    marker = "pd-" + core.digest(op["key"])[:24]
                    matches = [a for a in actual.get("attachments", []) if marker in a.get("name", a.get("filename", ""))]
                    if len(matches) != 1:
                        failed.append({"source_id": source_id, "field": "attachment", "operation": op["key"]})
                    else:
                        attachment = matches[0]
                        content = client.call("download", url=attachment.get("url", attachment.get("content")))
                        if core.digest(base64.b64decode(content["base64"], validate=True)) != op["sha256"]:
                            failed.append({"source_id": source_id, "field": "attachment-checksum", "operation": op["key"]})
                elif op["kind"] == "parent" and str(actual.get("parent")) != journal["items"][op["parent_source_id"]]:
                    failed.append({"source_id": source_id, "field": "parent"})
            checked.append(source_id)
        except Pending:
            raise
        except (RuntimeError, ValueError, KeyError, OSError):
            failed.append({"source_id": source_id, "field": "readback"})
    unsupported = manifest["limitations"]
    success = (not missing and not failed and not any(not l["accepted_reason"] for l in unsupported)
               and manifest["status"] in {"applied", "verified", "cutover"})
    report = {"verified": core.now(), "success": success, "missing": missing, "failed": failed,
              "unsupported": unsupported, "checked": checked, "journal_sha256": core.digest(journal), "plan_sha256": plan_hash(manifest)}
    core.save(directory / "verification.json", report)
    core.save(private / "verified-items.json", observed)
    session["status"] = "complete"
    core.save(session_file, session)
    if success and manifest["status"] != "cutover":
        manifest["status"] = "verified"
        core.save(directory / "manifest.json", manifest)
    return report


def refresh_local(root):
    """Only regenerate the existing derived phase table; never change task marks."""
    import subprocess
    if (Path(root) / "project/README.md").exists():
        result = subprocess.run([sys.executable, str(Path(__file__).parent / "sync_project_readme.py")], cwd=root, capture_output=True, text=True)
        if result.returncode:
            raise RuntimeError("local phase table regeneration failed; rollback or fix markers before retry")


def cutover(root, mid):
    directory, manifest, private, _, _ = state(root, mid)
    verified = core.load(directory / "verification.json", {})
    journal = core.load(directory / "journal.json")
    if not verified.get("success") or verified.get("journal_sha256") != core.digest(journal) or verified.get("plan_sha256") != plan_hash(manifest) or manifest["status"] not in {"verified", "cutover"}:
        raise ValueError("successful verification of the current journal is required")
    cfg, _, primary = core.configuration(root)
    if primary not in {manifest["source"], manifest["destination"]}:
        raise ValueError("primary tracker changed since the plan")
    data = core.mapping(root)
    actual = core.load(private / "verified-items.json", [])
    by_id = {str(i["id"]): i for i in actual}
    for entry in list(data["tasks"].values()) + [{"refs": refs} for refs in data.get("phases", {}).values()]:
        for ref in list(entry.get("refs", [])):
            if ref["connection"] != manifest["source"] or ref.get("kind", "work_item") != "work_item":
                continue
            external = journal["items"].get(str(ref["id"]))
            if not external and not any(l["code"] == "mapping."+str(ref["id"]) and l["accepted_reason"] for l in manifest["limitations"]):
                raise ValueError("local source mapping has no verified destination; make a new plan")
            if external:
                new = {"connection": manifest["destination"], "kind": "work_item", "id": external,
                       "url": by_id.get(external, {}).get("url", ""), "migration": mid}
                if new not in entry["refs"]:
                    entry["refs"].append(new)
    # Preserve original configuration immediately before cutover as well as plan-time backup.
    before_cutover = directory / "before-cutover.json"
    if not before_cutover.exists():
        core.save(before_cutover, {"config": cfg, "mapping": core.load(core.mapping_path(root))})
    core.save(core.mapping_path(root), data)
    cfg["integrations"]["primary"] = manifest["destination"]
    core.save(Path(root) / ".project-docs/config.json", cfg)
    snap = {"version": 1, "connection": manifest["destination"], "provider": manifest["destination_identity"]["provider"],
            "coverage": "partial", "fetched": verified["verified"], "items": actual}
    core.save(core.snapshot_path(root, manifest["destination"]), snap)
    refresh_local(root)
    manifest["status"] = "cutover"
    core.save(directory / "manifest.json", manifest)
    return {"primary": manifest["destination"], "source_retained": True}


def rollback(root, mid):
    directory, manifest, _, _, _ = state(root, mid)
    backup = core.load(directory / "before-cutover.json")
    if backup is None:
        raise ValueError("no cutover to roll back; destination items are retained")
    core.save(Path(root) / ".project-docs/config.json", backup["config"])
    if backup["mapping"] is None:
        core.mapping_path(root).unlink(missing_ok=True)
    else:
        core.save(core.mapping_path(root), backup["mapping"])
    refresh_local(root)
    manifest["status"] = "rolled-back"
    core.save(directory / "manifest.json", manifest)
    return {"rolled_back": True, "external_items_deleted": False}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root")
    sub = ap.add_subparsers(dest="command", required=True)
    p = sub.add_parser("plan"); p.add_argument("source"); p.add_argument("destination"); p.add_argument("--id", required=True); p.add_argument("--mapping")
    for command in ("apply", "resume", "verify", "cutover", "rollback"):
        p = sub.add_parser(command); p.add_argument("id")
    args = ap.parse_args(argv)
    try:
        root = root_path(args.root)
        with locked(root, args.id):
            if args.command == "plan":
                result = plan(root, args.source, args.destination, args.id, core.load(args.mapping, {}) if args.mapping else {})
            else:
                fn = apply if args.command in {"apply", "resume"} else globals()[args.command]
                result = fn(root, args.id)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1 if result.get("success") is False else 0
    except (ValueError, KeyError, RuntimeError, OSError) as exc:
        print(f"migration: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
