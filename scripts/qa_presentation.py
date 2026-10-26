#!/usr/bin/env python3
"""Render-check phase presentations in a real browser (desktop 1280px, mobile 390px).

  python3 qa_presentation.py 2                 # one phase
  python3 qa_presentation.py --all             # every phase
  python3 qa_presentation.py 2 --shots DIR     # also save full-page screenshots to DIR (outside the repo)

Checks per viewport: no page-level horizontal overflow, no raw backtick in visible text,
status pill count equals the task count in phase-N/tasks.md, Mermaid blocks rendered or
fell back to source. Tables that scroll inside their own overflow container are reported,
not failed. Exit 1 on any FAIL, 2 when Playwright is missing.

Needs Playwright for Python (`pip install playwright`, then `playwright install chromium`,
or an installed Google Chrome). Serves the repo over a local HTTP server because browsers
may block file: URLs. Read-only: never edits files.
"""
from __future__ import annotations

import argparse
import functools
import http.server
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from docs_lib import REPO, parse_tasks, phases_present, presentation_path, tasks_path  # noqa: E402

VIEWPORTS = (("desktop", 1280, 900), ("mobile", 390, 844))
PROBE = """() => {
  const doc = document.documentElement;
  const diagrams = [...document.querySelectorAll('.diagram')];
  return {
    pageOverflow: doc.scrollWidth > doc.clientWidth,
    slides: document.querySelectorAll('section.slide').length,
    rawBacktick: document.body.innerText.includes('`'),
    pills: document.querySelectorAll('.pill.done, .pill.doing, .pill.block, .pill.todo').length,
    scrollingTables: [...document.querySelectorAll('.tbl, .table-wrap')].filter(t => t.scrollWidth > t.clientWidth).length,
    diagrams: diagrams.length,
    diagramsEmpty: diagrams.filter(d => !d.querySelector('svg, pre')).length,
  };
}"""


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):  # keep the report readable
        pass


def serve() -> tuple[http.server.ThreadingHTTPServer, int]:
    handler = functools.partial(QuietHandler, directory=str(REPO))
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, srv.server_address[1]


def launch(p):
    try:
        return p.chromium.launch(headless=True)
    except Exception:
        return p.chromium.launch(channel="chrome", headless=True)  # fall back to installed Chrome


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("phase", type=int, nargs="?")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--shots", help="directory for screenshots (keep it outside the repo)")
    args = ap.parse_args()
    phases = phases_present() if args.all else [args.phase] if args.phase is not None else None
    if not phases:
        ap.error("give a phase number or --all")
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Playwright for Python is not installed: pip install playwright && playwright install chromium")
        print("Without it, check desktop/mobile by hand and say so in the report.")
        return 2

    srv, port = serve()
    fails = 0
    try:
        with sync_playwright() as p:
            browser = launch(p)
            for n in phases:
                path = presentation_path(n)
                if not path.exists():
                    print(f"FAIL  phase {n}: {path} missing"); fails += 1; continue
                tasks = len(parse_tasks(tasks_path(n))) if tasks_path(n).exists() else None
                url = f"http://127.0.0.1:{port}/{path.relative_to(REPO).as_posix()}"
                for name, w, h in VIEWPORTS:
                    page = browser.new_page(viewport={"width": w, "height": h})
                    page.goto(url, wait_until="load")
                    page.wait_for_timeout(800)  # let Mermaid render
                    r = page.evaluate(PROBE)
                    problems = []
                    if r["pageOverflow"]: problems.append("page scrolls horizontally")
                    if r["rawBacktick"]: problems.append("raw backtick visible")
                    if tasks is not None and r["pills"] != tasks: problems.append(f"{r['pills']} status pills but {tasks} tasks in TASKS")
                    if r["diagramsEmpty"]: problems.append(f"{r['diagramsEmpty']} Mermaid block(s) rendered nothing")
                    level = "FAIL" if problems else "OK"
                    fails += bool(problems)
                    note = f" · {r['scrollingTables']} table(s) scroll inside their container" if r["scrollingTables"] else ""
                    print(f"{level:4}  phase {n} {name:7} slides={r['slides']} pills={r['pills']}{note}"
                          + (f" · {'; '.join(problems)}" if problems else ""))
                    if args.shots:
                        out = Path(args.shots); out.mkdir(parents=True, exist_ok=True)
                        page.screenshot(path=str(out / f"phase{n}_{name}.png"), full_page=True)
                    page.close()
            browser.close()
    finally:
        srv.shutdown()
    print(f"\n{fails} failing view(s). Screens were checked by script only; look at them yourself before saying 'verified visually'.")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
