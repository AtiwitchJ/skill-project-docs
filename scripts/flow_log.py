#!/usr/bin/env python3
"""Measure %C&A (percent complete and accurate) for docs tasks.

A docs task counts as complete-and-accurate when the FIRST gate run after the
edits has no ERROR and nobody later reports a defect that sends it back (rework).

  python3 flow_log.py start B "Task 1.2 closed"   # before editing: records the baseline, prints an id
  python3 flow_log.py finish <id>                  # after editing: runs the gate; the first finish counts
  python3 flow_log.py rework <id> "wiki still showed old number"   # a defect found after handover
  python3 flow_log.py report                       # %C&A and the task list

Change types are the change-router letters (A results, B task status, C close phase,
D issue, E presentation, F wiki, G md/html pair, H diagram/chart, I rename/cut,
J Azure DevOps drift, K Diataxis split, L skill self-check, M memory-bank counts). Log: .project-docs/flow-log.jsonl next to
the documented project. Standard library only.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_docs  # noqa: E402

from docs_lib import REPO  # noqa: E402
from layout import FLOW_LOG  # noqa: E402

LOG = FLOW_LOG
TYPES = {"A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M"}


def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def gate() -> dict:
    results = check_docs.run()
    return {k.lower(): sum(1 for r in results if r[0] == k) for k in ("ERROR", "WARN", "ACK")}


def load() -> list[dict]:
    if not LOG.exists():
        return []
    return [json.loads(line) for line in LOG.read_text(encoding="utf-8").splitlines() if line.strip()]


def save(entries: list[dict]) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    LOG.write_text("".join(json.dumps(e, ensure_ascii=False) + "\n" for e in entries), encoding="utf-8")


def find(entries: list[dict], task_id: str) -> dict:
    for e in entries:
        if e["id"] == task_id:
            return e
    raise SystemExit(f"no task with id {task_id} in {LOG}")


def cmd_start(args) -> None:
    if args.type not in TYPES:
        raise SystemExit(f"type must be one of {sorted(TYPES)} (change-router letters)")
    entries = load()
    task_id = datetime.now().strftime("%Y%m%d-%H%M%S")
    entries.append({"id": task_id, "type": args.type, "note": args.note, "started": now(),
                    "baseline": gate(), "first_gate": None, "gate_runs": 0, "rework": []})
    save(entries)
    print(task_id)


def cmd_finish(args) -> None:
    entries = load()
    e = find(entries, args.id)
    g = gate()
    e["gate_runs"] += 1
    if e["first_gate"] is None:
        e["first_gate"] = g
        e["finished"] = now()
    e["last_gate"] = g
    save(entries)
    status = "PASS" if g["error"] == 0 else "FAIL (Andon: fix, then run finish again; first-pass result is already recorded)"
    print(f"{args.id}: gate {status} · errors {g['error']} · warnings {g['warn']} · accepted {g['ack']}")
    raise SystemExit(0 if g["error"] == 0 else 1)


def cmd_rework(args) -> None:
    entries = load()
    e = find(entries, args.id)
    e["rework"].append({"at": now(), "note": args.note})
    save(entries)
    print(f"{args.id}: rework recorded ({len(e['rework'])} total)")


def cmd_report(_args) -> None:
    done = [e for e in load() if e.get("first_gate") is not None]
    if not done:
        print("no finished docs tasks logged yet")
        return
    ok = [e for e in done if e["first_gate"]["error"] == 0 and not e["rework"]]
    print(f"%C&A = {len(ok)}/{len(done)} = {100 * len(ok) / len(done):.0f}%  (first gate without ERROR and no rework)")
    for e in done:
        mark = "C&A" if e in ok else "   "
        print(f"  {mark} {e['id']} [{e['type']}] first-gate errors={e['first_gate']['error']} "
              f"runs={e['gate_runs']} rework={len(e['rework'])} · {e['note']}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("start"); s.add_argument("type"); s.add_argument("note"); s.set_defaults(fn=cmd_start)
    f = sub.add_parser("finish"); f.add_argument("id"); f.set_defaults(fn=cmd_finish)
    r = sub.add_parser("rework"); r.add_argument("id"); r.add_argument("note"); r.set_defaults(fn=cmd_rework)
    p = sub.add_parser("report"); p.set_defaults(fn=cmd_report)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
