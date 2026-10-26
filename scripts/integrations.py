#!/usr/bin/env python3
"""Configured integrations: doctor, fetch, import, check, upgrade, evidence.

Normal commands never write to external services. MCP requests are completed by
an agent using real tools; see integrations/providers.md for the JSON contract.
"""
from __future__ import annotations

import argparse
import base64
import io
import json
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree

import integration_core as core
from integration_transport import Pending, availability, transport


def runtime(root):
    p = Path(root) / ".project-docs/runtime"
    p.mkdir(parents=True, exist_ok=True)
    (p / ".gitignore").write_text("*\n", encoding="utf-8")
    return p


def root_path(value):
    if value:
        return Path(value).expanduser().resolve()
    from layout import REPO
    return REPO


def doctor(root, name=None):
    _, connections, primary = core.configuration(root)
    report = []
    for key in ([name] if name else connections):
        conn = connections[key]
        row = {"connection": key, "provider": conn["provider"], "primary": key == primary,
               "available": availability(conn)}
        try:
            client = transport(key, conn, runtime(root))
            row["transport"] = client.mode
            row.update(client.call("doctor"))
            caps = row.get("capabilities", [])
            row["missing_read_capabilities"] = [c for c in ("list", "get", "schema") if c not in caps]
            row["missing_migration_capabilities"] = [c for c in ("create", "configure", "find", "comment", "attach", "parent") if c not in caps]
        except (ValueError, RuntimeError, OSError) as exc:
            row["ready"] = False
            row["error"] = str(exc)
        else:
            row["ready"] = row.get("read_access") is True and not row["missing_read_capabilities"]
        report.append(row)
    return report


def record_evidence(root, uid, name, artifact_id, expected_sha, member, attempt=None):
    _, connections, _ = core.configuration(root)
    if connections[name]["provider"] not in {"github", "github-actions"}:
        raise ValueError("Actions evidence requires a GitHub connection")
    if uid not in {t["uid"] for t in core.tasks(root)}:
        raise ValueError("unknown Task UID")
    client = transport(name, connections[name], runtime(root))
    artifact = client.call("artifact", id=artifact_id, attempt=attempt)
    if not artifact.get("attempt_verified"):
        raise ValueError("artifact attempt attribution was not verified by the provider adapter")
    if artifact.get("expired") or artifact.get("conclusion") != "success" or artifact.get("commit_sha") != expected_sha:
        raise ValueError("artifact is expired, workflow failed, or commit does not match")
    downloaded = client.call("download", url=artifact["download_url"])
    content = base64.b64decode(downloaded["base64"], validate=True)
    if downloaded.get("sha256") and core.digest(content) != downloaded["sha256"]:
        raise ValueError("download checksum mismatch")
    member_path = Path(member)
    if member_path.is_absolute() or ".." in member_path.parts:
        raise ValueError("unsafe archive member")
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        info = archive.getinfo(member)
        if info.file_size > 20 * 1024 * 1024 or info.external_attr >> 16 & 0o170000 == 0o120000:
            raise ValueError("oversized result file or symlink")
        result = archive.read(info)
    if member.endswith(".xml"):
        doc = ElementTree.fromstring(result)
        cases = doc.findall(".//testcase")
        if doc.tag == "testcase":
            cases.append(doc)
        passed = bool(cases) and not any(c.find("failure") is not None or c.find("error") is not None for c in cases)
        passed = passed and any(c.find("skipped") is None for c in cases)
        passed = passed and not any(int(s.get("failures", "0")) or int(s.get("errors", "0")) for s in doc.iter() if s.tag in {"testsuite", "testsuites"})
    elif member.endswith(".json"):
        data = json.loads(result)
        # Explicit supported contract; arbitrary metrics or a successful download are not test results.
        passed = data.get("status") == "passed" and data.get("tests", 0) > 0 and data.get("failures") == 0 and data.get("errors") == 0
    else:
        raise ValueError("use JUnit XML or JSON {status, tests, failures, errors}")
    destination = Path(root) / "project/results/evidence" / core.safe_id(name) / core.safe_id(str(artifact_id)) / member_path
    if not destination.resolve().is_relative_to(Path(root).resolve()):
        raise ValueError("result destination escapes the project through a symlink")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(result)
    evidence = {k: artifact[k] for k in ("artifact_id", "run_id", "attempt", "commit_sha", "conclusion", "expired", "attempt_verified")}
    evidence.update(connection=name, expected_commit_sha=expected_sha, archive_sha256=core.digest(content),
                    sha256=core.digest(result), path=str(destination.relative_to(root)),
                    test_result="passed" if passed else "failed", recorded=core.now())
    data = core.mapping(root)
    entry = data["tasks"].setdefault(uid, {"refs": [], "evidence": []})
    entry["evidence"] = [e for e in entry.get("evidence", []) if (e.get("connection"), str(e.get("artifact_id"))) != (name, str(artifact_id))] + [evidence]
    core.save(core.mapping_path(root), data)
    return evidence


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", help="documented project root; default: discover from cwd")
    sub = ap.add_subparsers(dest="command", required=True)
    p = sub.add_parser("doctor"); p.add_argument("--connection"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("import"); p.add_argument("connection"); p.add_argument("file"); p.add_argument("--coverage", choices=["partial", "complete"], default="partial")
    p = sub.add_parser("fetch"); p.add_argument("connection"); p.add_argument("--full", action="store_true")
    p = sub.add_parser("check"); p.add_argument("--connection"); p.add_argument("--json", action="store_true")
    sub.add_parser("upgrade")
    p = sub.add_parser("evidence"); p.add_argument("connection"); p.add_argument("artifact_id"); p.add_argument("--uid", required=True); p.add_argument("--commit", required=True); p.add_argument("--member", required=True); p.add_argument("--attempt", type=int)
    args = ap.parse_args(argv)
    try:
        root = root_path(args.root)
        _, connections, _ = core.configuration(root)
        if args.command == "doctor":
            result = doctor(root, args.connection)
            code = int(any(not r["ready"] for r in result))
        elif args.command == "check":
            result = core.check(root, args.connection); code = int(bool(result))
        elif args.command == "upgrade":
            result = core.upgrade(root); code = 0
        elif args.command == "evidence":
            result = record_evidence(root, args.uid, args.connection, args.artifact_id, args.commit, args.member, args.attempt)
            code = int(result["test_result"] != "passed")
        else:
            name = args.connection; conn = connections[name]
            if args.command == "fetch":
                raw = transport(name, conn, runtime(root)).call("list", full=args.full)
            else:
                raw = core.load(args.file)
            result = core.normalize(name, conn, raw, coverage=getattr(args, "coverage", "partial"))
            core.save(core.snapshot_path(root, name), result); code = 0
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return code
    except (ValueError, KeyError, RuntimeError, OSError, zipfile.BadZipFile, ElementTree.ParseError) as exc:
        print(f"integration: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
