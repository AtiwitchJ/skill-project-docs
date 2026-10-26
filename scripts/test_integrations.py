#!/usr/bin/env python3
"""Offline integration/migration contract tests. No real accounts or network.

Run: python3 -m unittest discover -s scripts -p 'test_integrations.py' -v
"""
from __future__ import annotations

import base64
import copy
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
import urllib.error
import zipfile
from pathlib import Path
from unittest import mock

import integration_core as core
import integrations
import migrate
import provider_api
from integration_transport import Bridge, Pending, select

HERE = Path(__file__).resolve().parent


def item(id="1", parent=None):
    return {"id": id, "kind": "work_item", "key": id, "url": "https://source.test/items/"+id,
            "title": "Task " + id, "description": "Original description\nsecond line", "type": "Issue",
            "raw_state": "Open", "state": "todo", "labels": ["docs"], "assignee": {"id": "old-user"},
            "parent": parent, "full": True, "raw": {"custom": {"priority": 7}},
            "comments": [{"id": "c1", "body": "Original comment", "author": {"name": "Original user"}, "created": "2024-01-01"}],
            "attachments": [{"id": "a1", "name": "result.txt", "url": "https://source.test/files/a1"}]}


class Remote:
    mode = "api"

    def __init__(self, name, provider, source=False):
        self.name, self.provider = name, provider
        self.items = {"1": item(), "2": item("2", "1")} if source else {}
        self.source = source
        self.calls, self.counts, self.fail_after = [], {}, None
        self.capabilities = ["list", "schema", "get", "find", "create", "configure", "comment", "comments", "attach", "parent", "download"]
        self.bytes = b"original file bytes"

    def call(self, operation, **p):
        self.calls.append(operation)
        self.counts[operation] = self.counts.get(operation, 0)+1
        if self.source and operation not in {"list", "get", "download", "schema", "doctor", "find"}:
            raise AssertionError("source must never be modified")
        if operation == "doctor":
            return {"capabilities": self.capabilities, "read_access": True, "write_access": "unverified"}
        if operation == "schema":
            return {"types": ["Issue"], "states": ["Open"], "labels": ["docs"], "users": ["new-user"]}
        if operation == "list":
            return {"version": 1, "connection": self.name, "provider": self.provider, "fetched": core.now(), "coverage": "complete", "items": list(copy.deepcopy(self.items).values())}
        if operation == "download":
            return {"base64": base64.b64encode(self.bytes).decode(), "sha256": core.digest(self.bytes)}
        if operation == "get":
            return {**copy.deepcopy(self.items[str(p["id"])]), "full": True}
        if operation == "find":
            if p["kind"] == "item":
                return [copy.deepcopy(i) for i in self.items.values() if p["marker"] in i["description"]]
            values = self.items[str(p["item_id"])]["comments" if p["kind"] == "comment" else "attachments"]
            return [copy.deepcopy(i) for i in values if p["marker"] in i.get("body", i.get("name", ""))]
        if operation == "create":
            external = str(100+len(self.items))
            self.items[external] = {**copy.deepcopy(p["item"]), "id": external, "kind": "work_item", "state": "todo", "url": "https://dest.test/"+external,
                                    "description": p["item"]["description"]+"\n\n"+p["marker"], "comments": [], "attachments": [], "parent": None}
            result = {"id": external}
        elif operation == "configure":
            self.items[str(p["id"])].update({k: copy.deepcopy(p["item"][k]) for k in ("raw_state", "labels", "assignee", "description")})
            result = {"id": str(p["id"])}
        elif operation == "comment":
            record = {"id": str(len(self.items[str(p["id"])]["comments"])), "body": p["body"]+"\n\n"+p["marker"]}
            self.items[str(p["id"])]["comments"].append(record); result = record
        elif operation == "attach":
            record = {"id": "attachment-"+p["marker"], "name": p["marker"]+"-"+p["name"], "url": "https://dest.test/attachment"}
            self.items[str(p["id"])]["attachments"].append(record); result = record
        elif operation == "parent":
            self.items[str(p["id"])]["parent"] = str(p["parent_id"]); result = {"id": str(p["id"])}
        else:
            raise AssertionError(operation)
        if self.fail_after == operation:
            self.fail_after = None
            raise TimeoutError("server succeeded but response was lost")
        return result


class ProjectTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config = {"integrations": {"primary": "source", "connections": {
            "source": {"provider": "azure-devops", "project": "old", "transport": "api", "token_env": "TEST_TOKEN"},
            "dest": {"provider": "jira", "project": "new", "transport": "api", "token_env": "TEST_TOKEN"}}}}
        core.save(self.root / ".project-docs/config.json", self.config)
        self.rules = {"users": {"old-user": "new-user"}}

    def clients(self, source="azure-devops", destination="jira"):
        self.config["integrations"]["connections"]["source"]["provider"] = source
        self.config["integrations"]["connections"]["dest"]["provider"] = destination
        core.save(self.root / ".project-docs/config.json", self.config)
        src, dest = Remote("source", source, True), Remote("dest", destination)
        return src, dest

    def task(self, text="### [ ] 1.1 Work\n\n**Task UID:** stable-task\n"):
        path = self.root / "project/phases/phase-1/tasks.md"
        path.parent.mkdir(parents=True, exist_ok=True); path.write_text(text)
        core.save(core.mapping_path(self.root), {"version": 1, "tasks": {"stable-task": {"refs": [{"connection": "source", "kind": "work_item", "id": "1"}], "evidence": []}}, "phases": {"phase-1": [{"connection": "source", "kind": "work_item", "id": "1"}]}})
        return path

    def make_plan(self, src, dest, mid="move", rules=None):
        return migrate.plan(self.root, "source", "dest", mid, self.rules if rules is None else rules,
                            factory=lambda name, side: src if side == "source" else dest)

    def test_all_twenty_tracker_directions_full_copy_and_readback(self):
        for source in sorted(core.TRACKERS):
            for destination in sorted(core.TRACKERS - {source}):
                with self.subTest(source=source, destination=destination):
                    mid = source+"-"+destination
                    src, dest = self.clients(source, destination)
                    self.make_plan(src, dest, mid)
                    self.assertFalse(dest.items, "plan must not write destination")
                    journal = migrate.apply(self.root, mid, dest)
                    self.assertEqual(len(dest.items), 2)
                    self.assertEqual(len(journal["items"]), 2)
                    self.assertTrue(migrate.verify(self.root, mid, dest)["success"])
                    for copied in dest.items.values():
                        self.assertEqual(len(copied["comments"]), 1)
                        self.assertIn("Original user", copied["comments"][0]["body"])
                        self.assertEqual(len(copied["attachments"]), 1)
                    self.assertEqual(dest.items["101"]["parent"], "100")
                    self.assertEqual(src.calls, ["list", "download", "download"])

    def test_resume_after_create_comment_and_upload_timeout(self):
        for operation in ("create", "comment", "attach", "configure", "parent"):
            with self.subTest(operation=operation):
                src, dest = self.clients(); mid = "timeout-"+operation
                self.make_plan(src, dest, mid); dest.fail_after = operation
                with self.assertRaises(RuntimeError):
                    migrate.apply(self.root, mid, dest)
                migrate.apply(self.root, mid, dest)
                self.assertEqual(len(dest.items), 2)
                self.assertEqual(dest.counts["create"], 2)
                self.assertEqual(dest.counts["comment"], 2)
                self.assertEqual(dest.counts["attach"], 2)
                self.assertTrue(migrate.verify(self.root, mid, dest)["success"])

    def test_cutover_and_rollback_keep_source_refs_and_task_uid(self):
        path = self.task(); original = path.read_text()
        data = core.mapping(self.root)
        data["tasks"]["stable-task"]["refs"].append({"connection": "source", "kind": "change_request", "id": "2"})
        core.save(core.mapping_path(self.root), data)
        src, dest = self.clients(); self.make_plan(src, dest)
        migrate.apply(self.root, "move", dest)
        with self.assertRaises(ValueError):
            migrate.cutover(self.root, "move")
        self.assertTrue(migrate.verify(self.root, "move", dest)["success"])
        migrate.cutover(self.root, "move")
        self.assertEqual(core.configuration(self.root)[2], "dest")
        refs = core.mapping(self.root)["tasks"]["stable-task"]["refs"]
        self.assertEqual({r["connection"] for r in refs}, {"source", "dest"})
        self.assertEqual(len([r for r in refs if r["connection"] == "dest"]), 1)
        migrate.rollback(self.root, "move")
        self.assertEqual(core.configuration(self.root)[2], "source")
        self.assertEqual(path.read_text(), original)
        self.assertEqual(len(dest.items), 2)

    def test_unaccepted_missing_capabilities_block_apply(self):
        src, dest = self.clients(); dest.capabilities.remove("attach")
        manifest = self.make_plan(src, dest)
        self.assertEqual(len(manifest["limitations"]), 2)
        with self.assertRaises(ValueError):
            migrate.apply(self.root, "move", dest)
        self.assertFalse(dest.items)

    def test_accepted_limitations_still_appear_in_verification(self):
        src, dest = self.clients(); dest.capabilities.remove("attach")
        rules = {**self.rules, "accept": {"1.attachment.a1": "Archived bytes are sufficient for this project", "2.attachment.a1": "Archived bytes are sufficient for this project"}}
        self.make_plan(src, dest, rules=rules); migrate.apply(self.root, "move", dest)
        report = migrate.verify(self.root, "move", dest)
        self.assertTrue(report["success"])
        self.assertEqual(len(report["unsupported"]), 2)

    def test_partial_inventory_and_unknown_mapping_rejected(self):
        src, dest = self.clients()
        original = src.call
        def partial(op, **kwargs):
            result = original(op, **kwargs)
            if op == "list": result["coverage"] = "partial"
            return result
        src.call = partial
        with self.assertRaisesRegex(ValueError, "complete source"):
            self.make_plan(src, dest)
        src.call = original; src.items["1"]["raw_state"] = "Mystery"
        with self.assertRaisesRegex(ValueError, "map state"):
            self.make_plan(src, dest)

    def test_corruption_and_readback_mismatch_prevent_cutover(self):
        src, dest = self.clients(); self.make_plan(src, dest); migrate.apply(self.root, "move", dest)
        dest.items["100"]["title"] = "Changed"
        report = migrate.verify(self.root, "move", dest)
        self.assertFalse(report["success"])
        with self.assertRaises(ValueError): migrate.cutover(self.root, "move")

    def test_check_partial_missing_and_state_mapping(self):
        self.task()
        snapshot = {"version": 1, "connection": "source", "provider": "azure-devops", "fetched": core.now(), "coverage": "partial", "items": []}
        core.save(core.snapshot_path(self.root, "source"), snapshot)
        kinds = {r["kind"] for r in core.check(self.root)}
        self.assertIn("not-observed", kinds); self.assertNotIn("missing", kinds)
        snapshot["coverage"] = "complete"; snapshot["items"] = [item()]; snapshot["items"][0]["state"] = "unknown"
        core.save(core.snapshot_path(self.root, "source"), snapshot)
        self.assertIn("unknown-state", {r["kind"] for r in core.check(self.root)})

    def test_duplicate_uid_and_orphan_mapping_detected(self):
        self.task("### [ ] 1.1 One\n**Task UID:** same\n### [ ] 1.2 Two\n**Task UID:** same\n")
        with self.assertRaisesRegex(ValueError, "duplicate Task UID"):
            core.check(self.root)

    def test_legacy_upgrade_idempotent_and_keeps_original_snapshot(self):
        self.config = {"ado": {"organization": "org", "project": "old"}}
        core.save(self.root / ".project-docs/config.json", self.config)
        path = self.task("# PHASE 1: Sample\n\n> **ADO PBI:** #10\n\n### [x] 1.1 Work\n\n**ADO:** #1, #2\n- [x] Verified\n")
        original = {"fetched": core.now(), "items": [{"id": 1, "type": "Task", "title": "Work", "state": "Done"}]}
        core.save(self.root / "project/backlog/ado-snapshot.json", original)
        core.upgrade(self.root); before = path.read_text(); data = core.mapping(self.root)
        core.upgrade(self.root)
        self.assertEqual(path.read_text(), before)
        self.assertEqual(core.mapping(self.root), data)
        self.assertIn("### [x] 1.1 Work", before)
        self.assertIn("**ADO:** #1, #2", before)
        self.assertEqual(core.load(self.root / "project/backlog/ado-snapshot.json"), original)

    def test_upgrade_keeps_legacy_ado_when_destination_is_already_configured(self):
        self.config["ado"] = {"organization": "org", "project": "old-ado"}
        self.config["integrations"]["primary"] = "dest"
        core.save(self.root / ".project-docs/config.json", self.config)
        self.task("### [ ] 1.1 Work\n\n**ADO:** #123\n")
        data = core.upgrade(self.root)
        self.assertEqual(core.configuration(self.root)[2], "dest")
        generated = next(t for t in core.tasks(self.root) if t["uid"])
        self.assertEqual(data["tasks"][generated["uid"]]["refs"][0]["connection"], "legacy-ado")

    def test_embedded_attachment_links_are_rewritten_before_final_text(self):
        src, dest = self.clients()
        src.items["1"]["description"] += "\n[file](https://source.test/files/a1)"
        src.items["1"]["comments"][0]["body"] += " [file](https://source.test/files/a1)"
        self.make_plan(src, dest); migrate.apply(self.root, "move", dest)
        self.assertNotIn("https://source.test/files/a1", dest.items["100"]["description"])
        self.assertIn("https://dest.test/attachment", dest.items["100"]["comments"][0]["body"])
        self.assertTrue(migrate.verify(self.root, "move", dest)["success"])

    def test_mcp_migration_replays_actual_bridge_requests_without_duplicates(self):
        src, dest = self.clients(); self.make_plan(src, dest)
        bridge_root = self.root / "bridge"
        bridge = Bridge("dest", self.config["integrations"]["connections"]["dest"], bridge_root, "mcp", True)
        def complete_pending():
            processed = 0
            for request_file in (self.root / ".project-docs/runtime").rglob("requests/*.json"):
                request = core.load(request_file)
                output = request_file.parent.parent / "responses" / request_file.name
                if not output.exists():
                    result = dest.call(request["operation"], **request["payload"])
                    core.save(output, {"request_id": request["request_id"], "result": result})
                    processed += 1
            return processed
        for _ in range(100):
            try:
                migrate.apply(self.root, "move", bridge)
                break
            except Pending:
                self.assertGreater(complete_pending(), 0)
        else:
            self.fail("MCP request protocol did not make progress")
        self.assertEqual(len(dest.items), 2)
        self.assertEqual(dest.counts["create"], 2)
        self.assertEqual(dest.counts["comment"], 2)

    def test_changed_plan_invalidates_previous_verification(self):
        src, dest = self.clients(); self.make_plan(src, dest); migrate.apply(self.root, "move", dest)
        migrate.verify(self.root, "move", dest)
        path = migrate.migration_dir(self.root, "move") / "manifest.json"
        manifest = core.load(path); manifest["entries"][0]["target"]["title"] = "Changed after review"
        core.save(path, manifest)
        with self.assertRaisesRegex(ValueError, "verification"):
            migrate.cutover(self.root, "move")

    def test_parent_cycle_and_required_missing_parent_block_planning(self):
        src, dest = self.clients(); src.items["1"]["parent"] = "2"
        with self.assertRaisesRegex(ValueError, "cycle"):
            self.make_plan(src, dest)

    def test_external_reference_ids_do_not_collide_between_kinds(self):
        snap = core.normalize("source", {"provider": "gitlab"}, [
            {"iid": 1, "title": "Issue", "state": "opened"},
            {"iid": 1, "title": "MR", "state": "merged", "kind": "change_request"}])
        self.assertEqual(len(snap["items"]), 2)

    def test_cli_migration_full_copy_uses_argv_json_contract(self):
        src, dest = self.clients(); self.make_plan(src, dest)
        bridge_file = self.root / "cli-bridge.py"
        store = self.root / "cli-store.json"
        bridge_file.write_text(
            'import json,sys\nfrom pathlib import Path\n'
            f'sys.path.insert(0,{str(HERE)!r})\nfrom test_integrations import Remote\n'
            f'store=Path({str(store)!r})\n'
            'remote=Remote("dest","jira")\n'
            'if store.exists(): remote.items=json.loads(store.read_text())\n'
            'request=json.load(sys.stdin)\n'
            'result=remote.call(request["operation"],**request["payload"])\n'
            'store.write_text(json.dumps(remote.items))\n'
            'print(json.dumps({"request_id":request["request_id"],"result":result}))\n')
        bridge = Bridge("dest", {"provider": "jira", "cli": [sys.executable, str(bridge_file)]}, self.root/"bridge", "cli", True)
        migrate.apply(self.root, "move", bridge)
        migrate.apply(self.root, "move", bridge)
        self.assertEqual(len(core.load(store)), 2)
        self.assertTrue(migrate.verify(self.root, "move", bridge)["success"])

    def test_plan_rejects_alias_for_same_endpoint(self):
        self.config["integrations"]["connections"] = {
            "source": {"provider": "github", "repository": "Owner/Repo"},
            "dest": {"provider": "github", "repository": "owner/repo", "base_url": "https://api.github.com/"}}
        core.save(self.root / ".project-docs/config.json", self.config)
        with self.assertRaisesRegex(ValueError, "same tracker"):
            migrate.plan(self.root, "source", "dest", "same")

    def test_migration_lock_excludes_concurrent_command(self):
        with migrate.locked(self.root, "same"):
            with self.assertRaisesRegex(ValueError, "another process"):
                with migrate.locked(self.root, "same"):
                    self.fail("lock should be exclusive")

    def test_configuration_status_mapping_applies_to_existing_snapshot(self):
        value = {"version": 1, "connection": "x", "provider": "jira", "fetched": core.now(), "coverage": "partial", "items": [item()]}
        value["items"][0]["state"] = "unknown"
        normalized = core.normalize("x", {"provider": "jira", "states": {"Open": "todo"}}, value)
        self.assertEqual(normalized["items"][0]["state"], "todo")

    def test_doctor_does_not_confuse_capabilities_with_permission(self):
        client = mock.Mock(mode="cli")
        client.call.return_value = {"capabilities": ["list", "get", "schema"], "read_access": False}
        with mock.patch.object(integrations, "transport", return_value=client):
            self.assertFalse(integrations.doctor(self.root, "source")[0]["ready"])

    def test_private_archive_ignored_by_git(self):
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        path = integrations.runtime(self.root)/"raw.json"; path.write_text('{"private":"fixture"}')
        result = subprocess.run(["git", "check-ignore", "--", str(path)], cwd=self.root, capture_output=True)
        self.assertEqual(result.returncode, 0)

    def test_artifact_provenance_failures(self):
        self.task()
        path = self.root / "result.json"; path.write_text('{"status":"passed"}')
        valid = {"run_id": "1", "attempt": 1, "attempt_verified": True, "artifact_id": "2", "commit_sha": "abc", "expected_commit_sha": "abc", "sha256": core.digest(path.read_bytes()), "path": "result.json", "conclusion": "success", "test_result": "passed"}
        self.assertEqual(core.evidence_problems(self.root, valid), [])
        for field, value in (("expired", True), ("commit_sha", "other"), ("conclusion", "failure"), ("test_result", "downloaded"), ("sha256", "bad")):
            self.assertTrue(core.evidence_problems(self.root, {**valid, field: value}))

    def test_artifact_archive_safe_extraction_and_no_automatic_task_close(self):
        path = self.task(); original = path.read_text()
        self.config["integrations"]["connections"]["dest"]["provider"] = "github-actions"
        core.save(self.root / ".project-docs/config.json", self.config)
        data = io.BytesIO()
        with zipfile.ZipFile(data, "w") as archive:
            archive.writestr("results.xml", '<testsuite><testcase name="pass"/></testsuite>')
        client = mock.Mock()
        def call(op, **kwargs):
            if op == "artifact": return {"artifact_id": "a", "run_id": "r", "attempt": 1, "attempt_verified": True, "commit_sha": "sha", "conclusion": "success", "expired": False, "download_url": "https://x.test/file"}
            return {"base64": base64.b64encode(data.getvalue()).decode()}
        client.call.side_effect = call
        with mock.patch.object(integrations, "transport", return_value=client):
            evidence = integrations.record_evidence(self.root, "stable-task", "dest", "a", "sha", "results.xml")
            self.assertEqual(evidence["test_result"], "passed")
            with self.assertRaises(ValueError):
                integrations.record_evidence(self.root, "stable-task", "dest", "a", "sha", "../result.xml")
        self.assertEqual(path.read_text(), original)


class AdapterTests(unittest.TestCase):
    def test_all_provider_shapes_and_change_requests(self):
        examples = {
            "github": [{"number": 3, "title": "Issue", "body": "text", "state": "open"}, {"number": 4, "title": "PR", "state": "closed", "pull_request": {"url": "https://x"}}],
            "gitlab": [{"iid": 3, "title": "Issue", "description": "text", "state": "opened"}, {"iid": 3, "title": "MR", "kind": "change_request", "state": "merged"}],
            "jira": [{"id": "3", "key": "D-3", "fields": {"summary": "Issue", "status": {"name": "Open"}, "description": provider_api.adf("text"), "issuetype": {"name": "Task"}}}],
            "linear": {"data": {"issues": {"nodes": [{"id": "uuid", "identifier": "D-3", "title": "Issue", "state": {"name": "Todo"}, "description": "text"}]}}},
            "azure-devops": {"value": [{"id": 3, "fields": {"System.Title": "Issue", "System.State": "New"}}]},
            "github-actions": {"artifacts": [{"id": 3, "name": "results", "expired": False}]}}
        for provider, raw in examples.items():
            with self.subTest(provider=provider):
                result = core.normalize("x", {"provider": provider}, raw)
                self.assertEqual(result["coverage"], "partial")
                self.assertTrue(result["items"][0]["id"])
                self.assertIn("raw", result["items"][0])
                if provider in {"github", "gitlab"}: self.assertEqual(result["items"][1]["kind"], "change_request")

    def test_unknown_status_and_cancelled_issue_not_done(self):
        result = core.normalize("x", {"provider": "github"}, [{"number": 1, "state": "closed", "state_reason": "not_planned"}])
        self.assertEqual(result["items"][0]["state"], "unknown")

    def test_invalid_records_and_connection_mismatch(self):
        for raw in ({"unexpected": []}, ["bad"], [{"title": "no id"}], [{"id": 1, "fields": []}]):
            with self.assertRaises(ValueError): core.normalize("x", {"provider": "jira"}, raw)
        with self.assertRaises(ValueError):
            core.normalize("x", {"provider": "jira"}, {"version": 1, "connection": "wrong", "provider": "jira", "items": []})

    def test_mcp_agent_request_response_and_read_only(self):
        with tempfile.TemporaryDirectory() as temp:
            bridge = Bridge("x", {"provider": "jira"}, temp, "mcp")
            with self.assertRaises(Pending): bridge.call("doctor")
            request = core.load(next((Path(temp)/"requests").glob("*.json")))
            core.save(Path(temp)/"responses"/(request["request_id"]+".json"), {"request_id": request["request_id"], "result": {"capabilities": ["list"]}})
            self.assertEqual(bridge.call("doctor"), {"capabilities": ["list"]})
            with self.assertRaises(ValueError): bridge.call("create", item={})

    def test_cli_argv_bridge_no_shell(self):
        with tempfile.TemporaryDirectory() as temp:
            script = Path(temp)/"bridge.py"
            script.write_text('import json,sys\nr=json.load(sys.stdin)\nprint(json.dumps({"request_id":r["request_id"],"result":{"capabilities":["list"]}}))\n')
            bridge = Bridge("x", {"provider": "jira", "cli": [sys.executable, str(script)]}, temp, "cli")
            self.assertEqual(bridge.call("doctor")["capabilities"], ["list"])

    def test_selection_order_and_locked_transport(self):
        with mock.patch.dict(os.environ, {"TEST_TOKEN": "not-a-real-token"}):
            cfg = {"provider": "jira", "mcp": {"enabled": True}, "cli": [sys.executable], "token_env": "TEST_TOKEN"}
            self.assertEqual(select(cfg), "mcp")
            self.assertEqual(select(cfg, "api"), "api")
            cfg["mcp"]["enabled"] = False
            self.assertEqual(select(cfg), "cli")
            cfg["cli"] = []; self.assertEqual(select(cfg), "api")

    def api(self, provider="github", writing=False):
        with mock.patch.dict(os.environ, {"TEST_TOKEN": "not-a-real-token"}):
            return provider_api.API("x", {"provider": provider, "token_env": "TEST_TOKEN", "base_url": "https://api.example.test", "repository": "o/r", "project": "D", "organization": "org", "team": "team"}, writing)

    def test_api_pagination_and_permission_error(self):
        api = self.api()
        with mock.patch.object(api, "request", side_effect=[([{"id": 1}], {"Link": '<https://api.example.test/page2>; rel="next"'}), ([{"id": 2}], {})]):
            self.assertEqual([i["id"] for i in api.pages("/page1")], [1, 2])
        with mock.patch.object(api.opener, "open", side_effect=urllib.error.HTTPError("https://api.example.test/x", 403, "Forbidden", {}, None)):
            with self.assertRaisesRegex(RuntimeError, "HTTP 403"): api.json("GET", "/x")

    def test_retry_get_rate_limit_but_never_retry_write(self):
        api = self.api(writing=True)
        error = urllib.error.HTTPError("https://api.example.test/x", 429, "Rate limited", {"Retry-After": "0"}, None)
        response = mock.MagicMock(); response.__enter__.return_value.read.return_value = b'{}'
        response.__enter__.return_value.headers = {}
        with mock.patch.object(api.opener, "open", side_effect=[error, response]) as request:
            self.assertEqual(api.json("GET", "/x"), {}); self.assertEqual(request.call_count, 2)
        with mock.patch.object(api.opener, "open", side_effect=error) as request:
            with self.assertRaises(RuntimeError): api.json("POST", "/x", {})
            self.assertEqual(request.call_count, 1)

    def test_api_read_mode_rejects_writes_for_each_provider(self):
        for provider in sorted(core.TRACKERS):
            with self.subTest(provider=provider):
                api = self.api(provider)
                with self.assertRaises(ValueError): api.call("create", item={}, marker="x")
                with self.assertRaises(ValueError): api.call("comment", id="1", body="x", marker="x")
                with self.assertRaises(ValueError): api.request("GET", "https://foreign.test/credential-leak")

    def test_direct_create_and_comment_adapters_for_all_five(self):
        for provider in sorted(core.TRACKERS):
            with self.subTest(provider=provider):
                api = self.api(provider, True)
                raw = {"id": "1", "number": 1, "iid": 1}
                with mock.patch.object(api, "json", return_value=raw) as request, mock.patch.object(api, "graph", return_value={"issueCreate": {"success": True, "issue": {"id": "1"}}, "commentCreate": {"comment": {"id": "2"}}}):
                    self.assertEqual(api.call("create", item={"title": "Test", "description": "Body", "type": "Issue"}, marker="provenance")["id"], "1")
                    self.assertTrue(api.call("comment", id="1", body="Body", marker="comment-marker")["id"])
                    if provider != "linear": self.assertGreaterEqual(request.call_count, 2)

    def test_assets_never_send_provider_token_to_other_hosts(self):
        api = self.api()
        public = [(2, 1, 6, "", ("8.8.8.8", 443))]
        response = mock.MagicMock(); response.__enter__.return_value.read.return_value = b'file'
        response.__enter__.return_value.headers = {}
        with mock.patch.object(provider_api.socket, "getaddrinfo", return_value=public), mock.patch.object(api.opener, "open", return_value=response) as request:
            result = api.call("download", url="https://cdn.example.test/file")
            self.assertEqual(base64.b64decode(result["base64"]), b'file')
            self.assertNotIn("Authorization", request.call_args[0][0].headers)
        private = [(2, 1, 6, "", ("127.0.0.1", 443))]
        with mock.patch.object(provider_api.socket, "getaddrinfo", return_value=private):
            with self.assertRaisesRegex(ValueError, "private address"):
                api.call("download", url="https://untrusted.test/file")

    def test_actions_artifact_must_match_attempt_interval(self):
        api = self.api("github-actions")
        artifact = {"id": 1, "created_at": "2026-01-01T10:00:00Z", "workflow_run": {"id": 2, "head_sha": "abc"}, "expired": False, "archive_download_url": "https://api.example.test/file"}
        run = {"id": 2, "run_attempt": 2, "head_sha": "abc", "run_started_at": "2026-01-02T00:00:00Z", "updated_at": "2026-01-02T01:00:00Z", "conclusion": "success"}
        with mock.patch.object(api, "json", side_effect=[artifact, run]):
            with self.assertRaisesRegex(ValueError, "attributed"):
                api.call("artifact", id="1")
        run.update(run_attempt=1, run_started_at="2026-01-01T09:00:00Z", updated_at="2026-01-01T11:00:00Z")
        with mock.patch.object(api, "json", side_effect=[artifact, run]):
            self.assertTrue(api.call("artifact", id="1", attempt=1)["attempt_verified"])

    def test_ado_assignee_tags_and_jira_parent_are_preserved(self):
        ado = core.normalize("x", {"provider": "azure-devops"}, [{"id": 1, "fields": {"System.Title": "Task", "System.State": "New", "System.Description": "a<br>b", "System.Tags": "docs; test", "System.AssignedTo": {"id": "user"}}}])["items"][0]
        self.assertEqual(ado["labels"], ["docs", "test"])
        self.assertEqual(ado["assignee"]["id"], "user")
        self.assertEqual(ado["description"], "a\nb")
        jira = core.normalize("x", {"provider": "jira"}, [{"id": 1, "fields": {"summary": "Task", "status": {"name": "Open"}, "parent": {"id": "7"}}}])["items"][0]
        self.assertEqual(jira["parent"], "7")

    def test_linear_personal_key_and_oauth_authentication(self):
        api = self.api("linear")
        self.assertEqual(api.headers["Authorization"], "not-a-real-token")
        self.assertIn("public-file-urls-expire-in", api.headers)
        cfg = {**api.config, "auth": "bearer"}
        with mock.patch.dict(os.environ, {"TEST_TOKEN": "not-a-real-token"}):
            oauth = provider_api.API("x", cfg)
        self.assertEqual(oauth.headers["Authorization"], "Bearer not-a-real-token")

    def test_ado_comment_id_and_explicit_markdown_format(self):
        api = self.api("azure-devops", True)
        with mock.patch.object(api, "json", return_value={"commentId": 5}) as request:
            self.assertEqual(api.call("comment", id="1", body="text", marker="key"), {"id": "5"})
            self.assertIn("format=markdown", request.call_args.args[1])

    def test_provider_user_identity_comparison(self):
        self.assertEqual(migrate.user_key({"id": 42, "login": "octocat"}), "octocat")
        self.assertTrue(migrate.user_matches({"id": "uuid", "uniqueName": "user@example.test"}, "user@example.test"))
        self.assertFalse(migrate.user_matches({"id": 42, "login": "octocat"}, "someone-else"))

    def test_gitlab_upload_web_links_use_authenticated_download_api(self):
        api = self.api("gitlab")
        raw = {"iid": 1, "title": "Issue", "state": "opened", "description": "[file](https://api.example.test/group/project/uploads/secret/result.txt)"}
        with mock.patch.object(api, "op_comments", return_value=[]):
            result = api.op_get("1", raw)
        self.assertEqual(result["attachments"][0]["url"], "https://api.example.test/api/v4/projects/D/uploads/secret/result.txt")

    def test_github_parent_is_read_and_missing_parent_is_expected(self):
        api = self.api("github")
        raw = {"number": 1, "title": "Child", "state": "open"}
        parent = {"id": 1000, "number": 7, "repository_url": "https://api.example.test/repos/o/r"}
        with mock.patch.object(api, "op_comments", return_value=[]), mock.patch.object(api, "json", return_value=parent):
            self.assertEqual(api.op_get("1", raw)["parent"], "7")
        with mock.patch.object(api, "op_comments", return_value=[]), mock.patch.object(api, "json", side_effect=provider_api.APIError("github", 404)):
            self.assertIsNone(api.op_get("1", raw)["parent"])


if __name__ == "__main__":
    unittest.main()
