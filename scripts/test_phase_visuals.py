"""Phase flow/chart correctness and paired-output regression tests; no network."""
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET

import phase_visuals as visuals
import presentation_charts as charts

SCRIPTS = Path(__file__).resolve().parent


class VisualTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root/".project-docs/presentations").mkdir(parents=True)
        (self.root/".project-docs/config.json").write_text('{"language":"English"}')
        self.source = self.root/"results.json"
        self.data = {"bars":[{"method":"A","value":10},{"method":"B","value":20}],
                     "trend":[{"x":1,"y":8},{"x":2,"y":5},{"x":3,"y":7}],
                     "parts":[{"name":"A","done":3,"left":2},{"name":"B","done":1,"left":4}],
                     "matrix":[{"x":"A","y":"small","value":1},{"x":"B","y":"small","value":3},{"x":"A","y":"large","value":2}]}
        self.source.write_text(json.dumps(self.data))
        self.items = [{"id":"1.1","uid":"first","title":"Prepare","mark":"x"},
                      {"id":"1.2","uid":"second","title":"Copy","mark":"/"},
                      {"id":"1.3","uid":"third","title":"Verify","mark":"!"},
                      {"id":"1.4","uid":"fourth","title":"Hand over","mark":" "}]

    def spec(self, intent="comparison", pointer="/bars", **fields):
        return {"id":"example","title":"A sourced question","question":"What differs?","intent":intent,
                "source":{"path":"results.json","pointer":pointer},"x":"method","y":"value",
                "unit":"ms","limitations":"Fixture only; no real measurement.",**fields}

    def configure(self, spec):
        (self.root/".project-docs/presentations/phase-1.json").write_text(json.dumps(spec))

    def test_every_task_appears_and_all_active_steps_remain_visible(self):
        model = visuals.model(self.root,1,self.items)
        self.assertEqual([s["mark"] for s in model["steps"]],["x","/","!"," "])
        self.assertEqual((model["done"],model["total"]),(1,4))
        generated = visuals.outputs(self.root,1,self.items)
        self.assertIn("Copy · Verify",generated["html_flow"])
        self.assertIn("1/4",generated["md_flow"])
        ET.fromstring(generated["assets"][self.root/"project/phases/phase-1/phase-flow.svg"])

    def test_grouped_steps_derive_status_and_counts_without_stored_status(self):
        self.configure({"flow":{"steps":[{"id":"work","label":"Work","tasks":["first","second"]},{"id":"review","label":"Review","tasks":["third","fourth"]}]}})
        model=visuals.model(self.root,1,self.items)
        self.assertEqual([s["mark"] for s in model["steps"]],["/","!"])
        self.assertEqual(model["steps"][0]["done"],1)
        moved=[{**t,"id":"9."+str(i)} for i,t in enumerate(self.items)]
        self.assertEqual(visuals.model(self.root,1,moved)["steps"],model["steps"])

    def test_invalid_or_incomplete_grouping_is_rejected(self):
        for refs in (["missing"],["first","first"],["first"]):
            self.configure({"flow":{"steps":[{"id":"only","label":"Only","tasks":refs}]}})
            with self.assertRaises(ValueError): visuals.model(self.root,1,self.items)

    def test_empty_phase_does_not_claim_completion(self):
        generated=visuals.outputs(self.root,1,[])
        self.assertIn("No tasks defined",next(iter(generated["assets"].values())))
        self.assertNotIn("All steps verified",generated["html_flow"])
        self.assertNotIn("<progress",generated["html_flow"])

    def test_auto_selection_renders_all_five_chart_families(self):
        specs=[self.spec(),self.spec("trend","/trend",x="x",y="y"),
               self.spec("relationship","/trend",x="x",y="y"),
               self.spec("composition","/parts",x="name",series=[{"field":"done"},{"field":"left"}]),
               self.spec("matrix","/matrix",x="x",y="y",value="value")]
        for spec in specs:
            with self.subTest(intent=spec["intent"]):
                result=charts.render(self.root,spec)
                self.assertEqual(result["type"],charts.CHOICES[spec["intent"]])
                ET.fromstring(result["svg"])
                self.assertTrue(result["rows"])
                self.assertEqual(result["sha256"],hashlib.sha256(self.source.read_bytes()).hexdigest())

    def test_missing_nonfinite_and_boolean_measurements_are_not_zero(self):
        for value in (None,float("nan"),True):
            self.data["bars"][0]["value"]=value;self.source.write_text(json.dumps(self.data))
            with self.assertRaises(ValueError): charts.render(self.root,self.spec())

    def test_line_chart_rejects_category_order_and_duplicate_x(self):
        for data in ([{"x":"B","y":1},{"x":"A","y":2}],[{"x":1,"y":1},{"x":1,"y":2}]):
            self.data["trend"]=data;self.source.write_text(json.dumps(self.data))
            with self.assertRaises(ValueError): charts.render(self.root,self.spec("trend","/trend",x="x",y="y"))

    def test_duplicate_heatmap_cells_and_negative_parts_rejected(self):
        self.data["matrix"].append(dict(self.data["matrix"][0]));self.source.write_text(json.dumps(self.data))
        with self.assertRaises(ValueError): charts.render(self.root,self.spec("matrix","/matrix",x="x",y="y",value="value"))
        self.data["parts"][0]["done"]=-1;self.source.write_text(json.dumps(self.data))
        with self.assertRaises(ValueError): charts.render(self.root,self.spec("composition","/parts",x="name",series=[{"field":"done"}]))

    def test_no_results_do_not_invent_a_chart(self):
        generated=visuals.outputs(self.root,1,self.items)
        self.assertIn("No measured results yet",generated["md_charts"])
        self.assertEqual(len(generated["assets"]),1)

    def test_source_pointer_and_paths_are_validated(self):
        for source in ({"path":"../outside.json"},{"path":"results.json","pointer":"bars"},{"path":"results.json","pointer":"/missing"}):
            with self.assertRaises((ValueError,KeyError,FileNotFoundError)):
                charts.render(self.root,{**self.spec(),"source":source})

    def custom(self, extra=""):
        generator=self.root/"generator.py";generator.write_text("# immutable fixture generator\n")
        checksum=hashlib.sha256(self.source.read_bytes()).hexdigest()
        genhash=hashlib.sha256(generator.read_bytes()).hexdigest()
        asset=self.root/"custom.svg"
        asset.write_text(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><title id="label">Custom fixture</title><metadata id="project-docs-source-sha256">{checksum}</metadata><metadata id="project-docs-generator-sha256">{genhash}</metadata><circle cx="50" cy="50" r="20"/>{extra}</svg>')
        return {**self.spec(),"type":"custom","fields":["method","value"],"asset":"custom.svg","generator":"generator.py","reason":"Preserve paired observations."}

    def test_custom_svg_is_namespaced_and_source_and_generator_checked(self):
        spec=self.custom();result=charts.render(self.root,spec)
        self.assertIn('id="example-label"',result["svg"])
        self.assertNotIn("project-docs-source-sha256",result["svg"])
        (self.root/"generator.py").write_text("# changed\n")
        with self.assertRaisesRegex(ValueError,"generator checksum"): charts.render(self.root,spec)

    def test_custom_svg_rejects_active_content_and_stale_source(self):
        for extra in ('<script>alert(1)</script>','<image href="https://example.test/image.png"/>','<circle onload="alert(1)"/>'):
            spec=self.custom(extra)
            with self.assertRaises(ValueError): charts.render(self.root,spec)
        spec=self.custom();self.source.write_text(self.source.read_text()+" ")
        with self.assertRaisesRegex(ValueError,"source checksum"): charts.render(self.root,spec)

    def test_labels_are_escaped_and_table_retains_original_values(self):
        self.data["bars"][0]["method"]='<script>example</script>';self.source.write_text(json.dumps(self.data))
        chart=charts.render(self.root,self.spec())
        self.assertNotIn('<script>',chart["svg"])
        self.assertEqual(chart["rows"][0],["<script>example</script>",10])


class SyncTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        (self.root/".project-docs").mkdir();(self.root/".project-docs/config.json").write_text('{"language":"English"}')
        self.phase=self.root/"project/phases/phase-1";self.phase.mkdir(parents=True)
        self.tasks=self.phase/"tasks.md"
        self.tasks.write_text('# PHASE 1: Fixture\n\n> **Period:** Fixture only\n\n### [x] 1.1 First\n\n**Task UID:** first\n- [x] Checked\n\n### [/] 1.2 Second\n\n**Task UID:** second\n- [ ] Pending\n')

    def run_script(self,*args):
        return subprocess.run([sys.executable,str(SCRIPTS/"sync_presentation.py"),*args],cwd=self.root,text=True,capture_output=True)

    def test_new_sync_both_formats_and_check_is_read_only(self):
        result=self.run_script("1","--new");self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertIn("AUTO:phase-flow",self.tasks.read_text())
        self.assertLess(self.tasks.read_text().index("AUTO:phase-flow"),self.tasks.read_text().index("### [x]"))
        self.assertTrue((self.phase/"phase-flow.svg").is_file())
        before={p:(p.read_bytes(),p.stat().st_mtime_ns) for p in self.root.rglob('*') if p.is_file()}
        self.assertEqual(self.run_script("1","--check").returncode,0)
        self.assertEqual(before,{p:(p.read_bytes(),p.stat().st_mtime_ns) for p in before})
        self.assertEqual(self.run_script("--all","--check").returncode,0)

    def test_task_edit_makes_both_flow_outputs_stale_and_sync_repairs(self):
        self.assertEqual(self.run_script("1","--new").returncode,0)
        self.tasks.write_text(self.tasks.read_text().replace("### [/] 1.2","### [!] 1.2"))
        self.assertEqual(self.run_script("1","--check").returncode,1)
        self.assertEqual(self.run_script("1").returncode,0)
        self.assertEqual(self.run_script("1","--check").returncode,0)
        self.assertIn("Blocked",self.tasks.read_text())

    def test_legacy_presentation_upgrade_keeps_narrative(self):
        html='<html><head><title>Legacy</title></head><body>'
        for n in range(6):
            html+=f'<section class="slide"><h2>KEEP narrative {n}</h2>'
            if n==0: html+='<!-- AUTO:summary --><!-- /AUTO:summary -->'
            if n==2: html+='<table><!-- AUTO:status-rows --><!-- /AUTO:status-rows --></table>'
            html+='</section>'
        html+='</body></html>'
        (self.phase/"presentation.html").write_text(html)
        self.assertEqual(self.run_script("1").returncode,0)
        output=(self.phase/"presentation.html").read_text()
        for n in range(6):self.assertIn(f'KEEP narrative {n}',output)
        self.assertEqual(self.run_script("1","--check").returncode,0)

    def test_generated_svg_hand_edit_is_detected(self):
        self.assertEqual(self.run_script("1","--new").returncode,0)
        path=self.phase/"phase-flow.svg";path.write_text(path.read_text().replace('First','Hand edited'))
        self.assertEqual(self.run_script("1","--check").returncode,1)

    def test_new_and_check_cannot_write_a_presentation(self):
        self.assertEqual(self.run_script("1","--new","--check").returncode,2)
        self.assertFalse((self.phase/"presentation.html").exists())


if __name__ == "__main__": unittest.main()
