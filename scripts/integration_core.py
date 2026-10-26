"""Provider-independent records, project configuration and offline checks.

No import-time project lookup or network access. Python standard library only.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import uuid
from html.parser import HTMLParser
from datetime import datetime, timezone
from pathlib import Path

TRACKERS = {"azure-devops", "github", "jira", "linear", "gitlab"}
PROVIDERS = TRACKERS | {"github-actions"}
UID_RE = re.compile(r"^\*\*Task UID:\*\*\s*(\S+)\s*$", re.M)
HEADER_RE = re.compile(r"^###\s+\[([ x/!])\]\s+(.+)$", re.M)


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(value):
    if not isinstance(value, bytes):
        value = json.dumps(value, sort_keys=True, ensure_ascii=False).encode()
    return hashlib.sha256(value).hexdigest()


def load(path, default=None):
    p = Path(path)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default


def save(path, value):
    """Atomic JSON replacement, including after an interrupted migration."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".write-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
    finally:
        if Path(tmp).exists():
            Path(tmp).unlink()


def safe_id(value):
    if not isinstance(value, str) or not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]*", value) or value in {".", ".."}:
        raise ValueError("IDs must contain only letters, digits, dots, underscores or hyphens")
    return value


def configuration(root):
    cfg = load(Path(root) / ".project-docs/config.json", {})
    integrations = cfg.get("integrations", {})
    connections = integrations.get("connections", {})
    primary = integrations.get("primary")
    for name, conn in connections.items():
        safe_id(name)
        if conn.get("provider") not in PROVIDERS:
            raise ValueError(f"{name}: unknown provider")
        if conn.get("transport", "auto") not in {"auto", "mcp", "cli", "api"}:
            raise ValueError(f"{name}: unknown transport")
        if any(k in conn for k in ("token", "password", "api_key", "authorization")):
            raise ValueError(f"{name}: use environment variable references, not credentials in config")
    if primary and (primary not in connections or connections[primary]["provider"] not in TRACKERS):
        raise ValueError("primary must name a configured tracker connection")
    return cfg, connections, primary


def snapshot_path(root, connection):
    return Path(root) / "project/backlog" / (safe_id(connection) + "-snapshot.json")


def mapping_path(root):
    return Path(root) / ".project-docs/work-items.json"


def mapping(root):
    data = load(mapping_path(root), {"version": 1, "tasks": {}, "phases": {}})
    if data.get("version") != 1 or not isinstance(data.get("tasks"), dict):
        raise ValueError("invalid work-items mapping")
    return data


def tasks(root):
    result = []
    seen = set()
    for path in sorted((Path(root) / "project/phases").glob("phase-*/tasks.md")):
        text = path.read_text(encoding="utf-8")
        headers = list(HEADER_RE.finditer(text))
        for i, head in enumerate(headers):
            body = text[head.end(): headers[i+1].start() if i+1 < len(headers) else len(text)]
            matches = UID_RE.findall(body)
            if len(matches) > 1:
                raise ValueError(f"{path}: multiple Task UIDs")
            uid = matches[0] if matches else None
            if uid and uid in seen:
                raise ValueError(f"duplicate Task UID: {uid}")
            if uid:
                seen.add(uid)
            result.append({"uid": uid, "mark": head[1], "title": head[2], "body": body,
                           "phase": path.parent.name, "path": str(path.relative_to(root))})
    return result


def upgrade(root):
    """Explicit, repeatable legacy upgrade. Keep all headings, marks and ADO lines."""
    cfg, connections, primary = configuration(root)
    ado = cfg.get("ado", {})
    ado_connection = None
    if ado:
        ado_connection = next((name for name, conn in connections.items() if conn["provider"] == "azure-devops" and
                               all(conn.get(k) == ado.get(k) for k in ("organization", "project"))), None)
        if ado_connection is None:
            if "legacy-ado" in connections:
                raise ValueError("legacy-ado already identifies a different project; rename that connection before upgrade")
            ado_connection = "legacy-ado"
            connections[ado_connection] = {"provider": "azure-devops", "transport": "auto", **ado}
        primary = primary or ado_connection
        cfg["integrations"] = {**cfg.get("integrations", {}), "primary": primary, "connections": connections}
    elif primary and connections[primary]["provider"] == "azure-devops":
        ado_connection = primary
    # Preflight duplicate IDs before changing any task file.
    tasks(root)
    data = mapping(root)
    for path in sorted((Path(root) / "project/phases").glob("phase-*/tasks.md")):
        text = path.read_text(encoding="utf-8")
        parts = []
        cursor = 0
        headers = list(HEADER_RE.finditer(text))
        for i, head in enumerate(headers):
            end = headers[i+1].start() if i+1 < len(headers) else len(text)
            body = text[head.end():end]
            m = UID_RE.search(body)
            uid = m[1] if m else "task-" + uuid.uuid4().hex
            if not m:
                body = "\n\n**Task UID:** " + uid + body
            parts.extend([text[cursor:head.end()], body])
            cursor = end
            entry = data["tasks"].setdefault(uid, {"refs": [], "evidence": []})
            old = re.search(r"\*\*ADO:\*\*\s*([#\d, ]+)", body)
            if old and ado_connection:
                for external in re.findall(r"\d+", old[1]):
                    ref = {"connection": ado_connection, "kind": "work_item", "id": external}
                    if ref not in entry["refs"]:
                        entry["refs"].append(ref)
        if headers:
            parts.append(text[cursor:])
            updated = "".join(parts)
            if updated != text:
                path.write_text(updated, encoding="utf-8")
        pbi = re.search(r"ADO\s*PBI:\*\*.*?#(\d+)", "\n".join(text.splitlines()[:10]))
        if pbi and ado_connection:
            refs = data["phases"].setdefault(path.parent.name, [])
            ref = {"connection": ado_connection, "kind": "work_item", "id": pbi[1]}
            if ref not in refs:
                refs.append(ref)
    save(mapping_path(root), data)
    save(Path(root) / ".project-docs/config.json", cfg)
    old_snapshot = load(Path(root) / "project/backlog/ado-snapshot.json")
    if old_snapshot and ado_connection:
        # Do not replace a newer imported snapshot during a repeated upgrade.
        if not snapshot_path(root, ado_connection).exists():
            save(snapshot_path(root, ado_connection), normalize(ado_connection, connections[ado_connection], old_snapshot,
                                                        fetched=old_snapshot.get("fetched")))
    return data


def rich_text(value):
    if isinstance(value, str):
        return value
    if not value:
        return ""
    if isinstance(value, list):
        return "\n".join(rich_text(v) for v in value)
    if isinstance(value, dict):
        if value.get("type") == "text":
            text = value.get("text", "")
            for mark in value.get("marks", []):
                if mark.get("type") == "link":
                    text = "["+text+"]("+mark.get("attrs", {}).get("href", "")+")"
            return text
        if value.get("type") == "hardBreak":
            return "\n"
        if value.get("type") in {"paragraph", "heading"}:
            return "".join(rich_text(v) for v in value.get("content", []))
        return rich_text(value.get("content", []))
    return str(value)


def html_text(value):
    class Text(HTMLParser):
        def __init__(self):
            super().__init__(); self.parts = []
        def handle_data(self, text):
            self.parts.append(text)
        def handle_starttag(self, tag, attrs):
            if tag == "br": self.parts.append("\n")
            if tag == "a":
                self.parts.append(dict(attrs).get("href", "") + " ")
            if tag == "img":
                self.parts.append("![image](" + dict(attrs).get("src", "") + ")")
        def handle_endtag(self, tag):
            if tag in {"div", "p", "li", "tr"}: self.parts.append("\n")
    if not re.search(r"</?[a-zA-Z][^>]*>", value):
        return value
    parser = Text(); parser.feed(value)
    return "".join(parser.parts).rstrip("\n")


def normalize(connection, conn, raw, coverage="partial", fetched=None):
    """Convert provider API/export records, retaining the complete original payload."""
    provider = conn["provider"]
    if coverage not in {"partial", "complete"}:
        raise ValueError("coverage must be partial or complete")
    if isinstance(raw, dict) and raw.get("version") == 1 and "items" in raw:
        if raw.get("connection") != connection or raw.get("provider") != provider:
            raise ValueError("snapshot connection/provider mismatch")
        if raw.get("coverage") not in {"partial", "complete"} or not raw.get("fetched"):
            raise ValueError("snapshot needs coverage and fetched")
        result = json.loads(json.dumps(raw))
    else:
        values = raw
        if isinstance(raw, dict):
            values = raw.get("items", raw.get("issues", raw.get("results", raw.get("value", raw.get("artifacts")))))
            if provider == "linear":
                values = raw.get("data", raw).get("issues", {}).get("nodes", values)
        if not isinstance(values, list):
            raise ValueError("expected an item list or provider response containing items")
        items = []
        for original in values:
            if not isinstance(original, dict):
                raise ValueError("items must be objects")
            f = original.get("fields", original)
            if not isinstance(f, dict):
                raise ValueError("item fields must be an object")
            lower = {k.lower(): v for k, v in f.items()}
            ext = original.get("id", original.get("iid"))
            if provider in {"github", "gitlab"}:
                ext = original.get("number", original.get("iid", ext))
            if ext is None:
                raise ValueError("item has no external ID")
            state = f.get("status", original.get("state", lower.get("system.state", "")))
            if isinstance(state, dict):
                state = state.get("name", "")
            kind = "work_item"
            if original.get("pull_request") or original.get("merge_request") or original.get("kind") == "change_request":
                kind = "change_request"
            if provider == "github-actions":
                kind = "evidence"
            typ = f.get("issuetype", lower.get("system.workitemtype", original.get("type", "Issue")))
            if isinstance(typ, dict):
                typ = typ.get("name", "Issue")
            title = f.get("summary", original.get("title", original.get("name", lower.get("system.title", ""))))
            body = f.get("description", original.get("body", lower.get("system.description", "")))
            if provider == "azure-devops":
                body = html_text(str(body or ""))
            url = original.get("html_url", original.get("web_url", original.get("url", "")))
            if provider == "jira":
                url = conn.get("base_url", "").rstrip("/") + "/browse/" + original.get("key", str(ext))
            if provider == "azure-devops":
                url = f"{conn.get('base_url', 'https://dev.azure.com').rstrip('/')}/{conn.get('organization', '')}/{conn.get('project', '')}/_workitems/edit/{ext}"
            if provider == "azure-devops" and original.get("type") and "fields" not in original:
                state, title, body = original.get("state", ""), original.get("title", ""), original.get("description", "")
            default_states = {
                "github": {"open": "todo", "closed": "done"},
                "gitlab": {"opened": "todo", "closed": "done"},
                "linear": {"Backlog": "todo", "Todo": "todo", "In Progress": "doing", "Done": "done"},
                "azure-devops": {
                    **{s: "todo" for s in ("new", "approved", "committed", "to do", "proposed", "open", "ready")},
                    **{s: "doing" for s in ("active", "in progress", "doing", "started", "resolved in build")},
                    **{s: "blocked" for s in ("blocked", "impediment")},
                    **{s: "done" for s in ("done", "closed", "resolved", "completed")}},
            }
            defaults = default_states.get(provider, {})
            category = conn.get("states", {}).get(state, defaults.get(state, {k.lower(): v for k, v in defaults.items()}.get(str(state).lower(), "unknown")))
            if original.get("state_reason") == "not_planned":
                category = "unknown"
            parent = original.get("parent", f.get("parent", lower.get("system.parent")))
            if isinstance(parent, dict):
                parent = parent.get("id")
            comments = original.get("comments", f.get("comment", {}).get("comments", []))
            if not isinstance(comments, list):
                comments = []  # API enrichment fetches paginated comments separately.
            labels = original.get("labels", f.get("labels", []))
            assignee = original.get("assignee", f.get("assignee"))
            if provider == "azure-devops":
                labels = [s.strip() for s in lower.get("system.tags", "").split(";") if s.strip()] or labels
                assignee = lower.get("system.assignedto", assignee)
            items.append({"id": str(ext), "key": original.get("key", original.get("identifier", str(ext))),
                          "kind": kind, "url": url, "title": title or "", "description": rich_text(body),
                          "type": typ, "raw_state": state, "state": category, "parent": str(parent) if parent else None,
                          "labels": labels, "assignee": assignee,
                          "comments": comments, "attachments": original.get("attachments", f.get("attachment", [])),
                          "raw": original})
        result = {"version": 1, "connection": connection, "provider": provider,
                  "coverage": coverage, "fetched": fetched or now(), "items": items}
    seen = set()
    for item in result["items"]:
        if not isinstance(item, dict) or not item.get("id") or item.get("kind") not in {"work_item", "change_request", "evidence"}:
            raise ValueError("invalid normalized item")
        key = item["kind"], str(item["id"])
        if key in seen:
            raise ValueError(f"duplicate external record: {key}")
        seen.add(key)
        if item.get("raw_state") in conn.get("states", {}):
            item["state"] = conn["states"][item["raw_state"]]
        if item.get("kind") == "work_item" and item.get("state") not in {"todo", "doing", "blocked", "done", "unknown"}:
            raise ValueError("normalized work item needs a valid state or 'unknown'")
    datetime.fromisoformat(result["fetched"].replace("Z", "+00:00"))
    return result


def evidence_problems(root, evidence):
    problems = []
    required = ("run_id", "attempt", "commit_sha", "artifact_id", "sha256", "path", "expected_commit_sha")
    if any(not evidence.get(k) for k in required):
        problems.append("incomplete artifact provenance")
    if evidence.get("expired"):
        problems.append("artifact expired")
    if evidence.get("conclusion") != "success":
        problems.append("workflow did not succeed")
    if not evidence.get("attempt_verified"):
        problems.append("artifact attempt attribution is unverified")
    if evidence.get("commit_sha") != evidence.get("expected_commit_sha"):
        problems.append("artifact belongs to another commit")
    if evidence.get("test_result") != "passed":
        problems.append("download is not a passing test result")
    if evidence.get("path"):
        p = (Path(root) / evidence["path"]).resolve()
        if not p.is_relative_to(Path(root).resolve()) or not p.is_file():
            problems.append("result file missing or outside project")
        elif digest(p.read_bytes()) != evidence.get("sha256"):
            problems.append("result checksum mismatch")
    return problems


def check(root, connection=None):
    _, connections, primary = configuration(root)
    data = mapping(root)
    local = {t["uid"]: t for t in tasks(root) if t["uid"]}
    findings = []
    selected = [connection] if connection else ([primary] if primary else [])
    for name in selected:
        if name not in connections:
            raise ValueError(f"unknown connection: {name}")
        snap = load(snapshot_path(root, name))
        if not snap:
            findings.append({"kind": "missing-snapshot", "connection": name})
            continue
        snap = normalize(name, connections[name], snap)
        stamp = datetime.fromisoformat(snap["fetched"].replace("Z", "+00:00"))
        age = (datetime.now(timezone.utc) - stamp.replace(tzinfo=stamp.tzinfo or timezone.utc)).total_seconds() / 86400
        if age > connections[name].get("stale_days", 7):
            findings.append({"kind": "stale-snapshot", "connection": name, "age_days": int(age)})
        external = {(i["kind"], str(i["id"])): i for i in snap["items"]}
        referenced = set()
        for uid, task in local.items():
            entry = data["tasks"].get(uid, {})
            refs = [r for r in entry.get("refs", []) if r["connection"] == name]
            if not refs:
                findings.append({"kind": "unmapped-task", "uid": uid, "connection": name})
            for ref in refs:
                key = ref.get("kind", "work_item"), str(ref["id"])
                referenced.add(key)
                item = external.get(key)
                if item is None:
                    findings.append({"kind": "missing" if snap["coverage"] == "complete" else "not-observed", "uid": uid, "ref": ref})
                elif item["kind"] == "work_item":
                    marks = {"todo": {" "}, "doing": {"/", "!"}, "blocked": {"!"}, "done": {"x"}}
                    if item.get("state") not in marks:
                        findings.append({"kind": "unknown-state", "uid": uid, "ref": ref, "state": item.get("raw_state")})
                    elif task["mark"] not in marks[item["state"]]:
                        findings.append({"kind": "state-mismatch", "uid": uid, "ref": ref})
            if task["mark"] == "x" and not entry.get("evidence") and not re.search(r"\*\*Evidence:\*\*\s*\S", task["body"]):
                findings.append({"kind": "evidence-required", "uid": uid})
        for key, item in external.items():
            if item["kind"] == "work_item" and key not in referenced:
                findings.append({"kind": "unmapped-external", "connection": name, "id": item["id"]})
    for uid in data["tasks"]:
        if uid not in local:
            findings.append({"kind": "orphan-mapping", "uid": uid})
        for ev in data["tasks"][uid].get("evidence", []):
            for message in evidence_problems(root, ev):
                findings.append({"kind": "invalid-evidence", "uid": uid, "message": message})
        for ref in data["tasks"][uid].get("refs", []):
            if ref.get("connection") not in connections or ref.get("kind") not in {"work_item", "change_request", "evidence"} or not ref.get("id"):
                findings.append({"kind": "invalid-reference", "uid": uid, "ref": ref})
    for task in tasks(root):
        if primary and not task["uid"]:
            findings.append({"kind": "missing-task-uid", "where": task["path"], "task": task["title"]})
    return findings
