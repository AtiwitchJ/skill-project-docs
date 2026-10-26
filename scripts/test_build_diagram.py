#!/usr/bin/env python3
"""Tests for build_diagram.py and the gate's diagram check (check_docs.check_diagrams).

Run from a project folder, because layout.py finds the project from the current directory:
  python3 ~/.agents/skills/project-docs/scripts/test_build_diagram.py

Nothing is written into the project: every output goes to a temporary folder. Standard library only.
"""
from __future__ import annotations

import contextlib
import copy
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build_diagram as bd  # noqa: E402
import check_docs  # noqa: E402

TEMPLATE = HERE.parent / "templates" / "diagram-spec.example.json"


def template() -> dict:
    return json.loads(TEMPLATE.read_text(encoding="utf-8"))


def spec_with_blocks(*blocks) -> dict:
    s = template()
    s["blocks"] = list(blocks)
    return s


def problems_of(spec: dict) -> list[str]:
    elements, drawing, problems = bd.build(spec)
    return problems + bd.check(drawing)


class BuildTests(unittest.TestCase):
    def test_template_builds_without_problems(self):
        self.assertEqual(problems_of(template()), [])

    def test_same_spec_gives_the_same_elements(self):
        first, _, _ = bd.build(template())
        second, _, _ = bd.build(template())
        self.assertEqual(json.dumps(first, sort_keys=True), json.dumps(second, sort_keys=True))

    def test_two_nodes_in_one_cell_are_refused(self):
        s = template()
        s["blocks"][0]["nodes"].append({"id": "twin", "lane": "client", "row": "A", "text": "Twin"})
        self.assertTrue(any("same lane and row" in p for p in problems_of(s)))

    def test_crossing_arrows_are_refused(self):
        block = {
            "id": "x", "title": "x", "row_by": "variant",
            "lanes": [{"id": "a", "label": "A"}, {"id": "b", "label": "B"}],
            "nodes": [
                {"id": "a0", "lane": "a", "row": "A", "text": "A0"},
                {"id": "a1", "lane": "a", "row": "B", "text": "A1"},
                {"id": "b0", "lane": "b", "row": "A", "text": "B0"},
                {"id": "b1", "lane": "b", "row": "B", "text": "B1"},
            ],
            "edges": [{"from": "a0", "to": "b1"}, {"from": "a1", "to": "b0"}],
        }
        self.assertTrue(any("arrows cross" in p for p in problems_of(spec_with_blocks(block))))

    def test_arrow_through_a_box_is_refused(self):
        block = {
            "id": "p", "title": "p", "row_by": "variant",
            "lanes": [{"id": "a", "label": "A"}, {"id": "b", "label": "B"}, {"id": "c", "label": "C"}],
            "nodes": [
                {"id": "p1", "lane": "a", "row": "A", "text": "P1"},
                {"id": "p2", "lane": "b", "row": "A", "text": "P2"},
                {"id": "p3", "lane": "c", "row": "A", "text": "P3"},
            ],
            "edges": [{"from": "p1", "to": "p3"}],
        }
        self.assertTrue(any("passes through box 'p2'" in p for p in problems_of(spec_with_blocks(block))))

    def test_text_that_does_not_fit_is_refused(self):
        s = template()
        s["blocks"][1]["nodes"][1]["text"] = "ขอคำค้นย่อยที่ยาวเกินกว่าจะอยู่ในกล่องเดียวได้เลยจริงๆ"
        self.assertTrue(any("does not fit" in p for p in problems_of(s)))

    def test_emoji_and_circled_digits_are_refused(self):
        s = template()
        s["blocks"][1]["nodes"][1]["text"] = "🚀 ขอคำค้น ① ย่อย"
        self.assertTrue(any("emoji or a circled digit" in p for p in problems_of(s)))

    def test_unknown_tag_is_refused(self):
        s = template()
        s["blocks"][0]["edges"][0]["tag"] = {"auth": "nope"}
        self.assertTrue(any("not defined under 'tags'" in p for p in problems_of(s)))

    def test_stale_value_is_refused(self):
        s = template()
        s["blocks"][1]["nodes"][2]["text"] = "ค้นได้ zzz-old"
        stale = Path(tempfile.mkdtemp()) / "stale-patterns.json"
        stale.write_text(json.dumps({"patterns": [{"regex": "zzz-old", "why": "test value"}]}), encoding="utf-8")
        with mock.patch.object(bd, "STALE_FILE", stale):
            self.assertTrue(any("stale value" in p for p in problems_of(s)))

    def test_unknown_style_is_refused(self):
        s = template()
        s["blocks"][0]["nodes"][0]["style"] = "neon"
        self.assertTrue(any("unknown style 'neon'" in p for p in problems_of(s)))


class CommandTests(unittest.TestCase):
    def run_cli(self, spec: dict, *flags: str) -> tuple[int, str]:
        folder = Path(tempfile.mkdtemp())
        spec_path = folder / "spec.json"
        spec_path.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = bd.main([str(spec_path), *flags])
        return code, out.getvalue()

    def test_bad_file_name_is_refused_before_writing(self):
        s = template()
        s["file"] = "docs/explanation/Untitled-1.excalidraw"
        code, out = self.run_cli(s, "--check")
        self.assertEqual(code, 1)
        self.assertIn("must be lower-case", out)

    def test_write_is_deterministic_and_keeps_editor_settings(self):
        folder = Path(tempfile.mkdtemp())
        s = template()
        s["file"] = str(folder / "out.excalidraw")  # absolute path: REPO / abs keeps abs
        spec_path = folder / "spec.json"
        spec_path.write_text(json.dumps(s, ensure_ascii=False), encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(bd.main([str(spec_path)]), 0)
        first = (folder / "out.excalidraw").read_bytes()
        (folder / "out.excalidraw").write_text(
            json.dumps({"type": "excalidraw", "appState": {"zoom": 2}, "elements": []}), encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()):
            bd.main([str(spec_path)])
        second = json.loads((folder / "out.excalidraw").read_text(encoding="utf-8"))
        self.assertEqual(second["appState"], {"zoom": 2})  # appState from the editor is kept
        self.assertEqual(second["elements"], json.loads(first)["elements"])


class GateTests(unittest.TestCase):
    """check_docs.check_diagrams: the picture on disk must be exactly what its spec builds."""

    def setUp(self):
        self.folder = Path(tempfile.mkdtemp())
        self.specs = self.folder / "diagrams"
        self.specs.mkdir()
        self.spec_path = self.specs / "flow.json"
        s = template()
        s["file"] = str(self.folder / "flow.excalidraw")
        self.spec_path.write_text(json.dumps(s, ensure_ascii=False), encoding="utf-8")
        self.patch = mock.patch.object(check_docs, "DIAGRAMS", self.specs)
        self.patch.start()
        check_docs.findings.clear()

    def tearDown(self):
        self.patch.stop()

    def errors(self) -> list[str]:
        return [msg for level, _, msg in check_docs.findings if level == "ERROR"]

    def test_no_diagram_folder_means_nothing_to_check(self):
        with mock.patch.object(check_docs, "DIAGRAMS", self.folder / "absent"):
            check_docs.check_diagrams()
        self.assertEqual(self.errors(), [])

    def test_missing_picture_is_an_error(self):
        check_docs.check_diagrams()
        self.assertTrue(any("is missing" in e for e in self.errors()))

    def test_picture_built_from_the_spec_passes(self):
        with contextlib.redirect_stdout(io.StringIO()):
            bd.main([str(self.spec_path)])
        check_docs.check_diagrams()
        self.assertEqual(self.errors(), [])

    def test_hand_edited_picture_is_an_error(self):
        with contextlib.redirect_stdout(io.StringIO()):
            bd.main([str(self.spec_path)])
        target = self.folder / "flow.excalidraw"
        data = json.loads(target.read_text(encoding="utf-8"))
        text_el = next(e for e in data["elements"] if e["type"] == "text")
        text_el["text"] = text_el["text"] + " (edited)"
        target.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        check_docs.check_diagrams()
        self.assertTrue(any("is not what this spec builds" in e for e in self.errors()))

    def test_broken_spec_is_an_error_even_with_a_picture(self):
        broken = copy.deepcopy(template())
        broken["file"] = str(self.folder / "flow.excalidraw")
        broken["blocks"][0]["nodes"].append({"id": "twin", "lane": "client", "row": "A", "text": "Twin"})
        self.spec_path.write_text(json.dumps(broken, ensure_ascii=False), encoding="utf-8")
        check_docs.check_diagrams()
        self.assertTrue(any("same lane and row" in e for e in self.errors()))


if __name__ == "__main__":
    unittest.main()
