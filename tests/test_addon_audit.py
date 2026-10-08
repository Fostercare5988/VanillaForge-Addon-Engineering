"""Load closure, read-only defaults and evidence boundaries for source audits."""
import contextlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))
SPEC = importlib.util.spec_from_file_location("audit_addon", TOOLS / "audit_addon.py")
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


class AddonAuditTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.addon = self.root / "Addon"
        self.addon.mkdir()
        self.write("Addon.toc", "## Interface: 11200\ncore.lua\n")
        self.write("core.lua", "local value = 1\n")

    def write(self, name, content):
        path = self.addon / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def test_nested_xml_closure_and_client_managed_bindings(self):
        self.write("Addon.toc", "ui/main.xml\n")
        self.write("ui/main.xml", '<Ui><Include file="nested/child.xml"/></Ui>')
        self.write("ui/nested/child.xml", '<Ui><Script file="../../core.lua"/></Ui>')
        self.write("Bindings.xml", '<Bindings><Binding name="B">RunAction()</Binding></Bindings>')
        self.write("tests/unused.lua", 'invalid : text')
        report = AUDIT.audit(self.addon)
        self.assertEqual(report["graph_errors"], [])
        self.assertEqual({m["path"] for m in report["modules"]},
                         {"Addon.toc", "ui/main.xml", "ui/nested/child.xml", "core.lua", "Bindings.xml"})
        self.assertEqual(report["review"]["pending_modules"], 5)
        self.assertTrue(all(len(m["sha256"]) == 64 and m["review_status"] == "pending" for m in report["modules"]))
        self.assertEqual(report, AUDIT.audit(self.addon))

    def test_cycle_duplicate_and_missing_reference(self):
        self.write("Addon.toc", "a.xml\na.xml\nmissing.lua\n")
        self.write("a.xml", '<Ui><Include file="b.xml"/></Ui>')
        self.write("b.xml", '<Ui><Include file="a.xml"/></Ui>')
        report = AUDIT.audit(self.addon)
        self.assertEqual(len(report["modules"]), 3)
        self.assertTrue(any("load cycle" in error for error in report["graph_errors"]))
        self.assertTrue(any("missing file" in error for error in report["graph_errors"]))
        self.assertEqual(report["status"], "source_checks_failed")

    def test_path_escape_and_windows_absolute_are_rejected(self):
        self.write("Addon.toc", "../outside.lua\nC:\\outside.lua\n")
        (self.root / "outside.lua").write_text("local outside = true", encoding="utf-8")
        report = AUDIT.audit(self.addon)
        self.assertEqual(len(report["modules"]), 1)
        self.assertEqual(len(report["graph_errors"]), 2)

    def test_xml_entity_and_malformed_xml_rejected(self):
        for xml in ('<!DOCTYPE Ui [<!ENTITY a "hi">]><Ui/>', '<Ui><Script></Ui>'):
            self.write("Addon.toc", "bad.xml\n")
            self.write("bad.xml", xml)
            self.assertTrue(AUDIT.audit(self.addon)["graph_errors"])

    def test_resolved_symlink_cannot_escape_addon(self):
        outside = self.root / "private"
        outside.mkdir()
        (outside / "foreign.lua").write_text("local private = true", encoding="utf-8")
        try:
            (self.addon / "link").symlink_to(outside, target_is_directory=True)
        except OSError as error:
            self.skipTest(f"Native symlink creation unavailable: {error}")
        self.write("Addon.toc", "link/foreign.lua\n")
        report = AUDIT.audit(self.addon)
        self.assertEqual(len(report["modules"]), 1)
        self.assertTrue(any("escapes addon" in error for error in report["graph_errors"]))

    def test_comment_string_masking_and_dynamic_callbacks(self):
        text = ('-- NotifyInspect("target")\nlocal text = "SetText(what)"\n'
                '--[=[ RegisterEvent("LOOT_OPENED") ]=]\n'
                'f:RegisterEvent("BAG_UPDATE")\nf:RegisterEvent(eventName)\n'
                'f:SetScript("OnUpdate", handler)\nf:SetScript(scriptName, handler)\n'
                'C_Timer.After(1, handler)\nf:SetText(value)\n'
                'f:RegisterEvent("BAG_" .. suffix)\n')
        sites = AUDIT.source_sites(text, ".lua")
        self.assertEqual(len(sites), 8)
        self.assertEqual([s["line"] for s in sites], [4, 5, 6, 7, 8, 8, 9, 10])
        self.assertEqual(sites[0]["argument"], "BAG_UPDATE")
        self.assertTrue(sites[1]["dynamic_argument"])
        self.assertEqual(sites[2]["kind"], "on_update")
        self.assertTrue(sites[3]["dynamic_argument"])
        self.assertTrue(sites[-1]["dynamic_argument"])

    def test_enhanced_namespace_and_unitxp_queries_are_masked_candidates(self):
        text = ('-- C_Inventory.Lookup(1)\nlocal s = "UnitXP(query)"\n'
                'C_Inventory.Lookup(1)\nUnitXP("distanceBetween", "player", "target")\n'
                'UnitXP(query, "player")\nC_UnitAuras.GetAuraDataByIndex("player", 1)\n')
        sites = [s for s in AUDIT.source_sites(text, ".lua") if s["kind"] == "enhanced_api_sites"]
        self.assertEqual([(s["api"], s["line"]) for s in sites],
                         [("C_Inventory.Lookup", 3), ("UnitXP", 4), ("UnitXP", 5),
                          ("C_UnitAuras.GetAuraDataByIndex", 6)])
        self.assertEqual(sites[1]["argument"], "distanceBetween")
        self.assertTrue(sites[2]["dynamic_argument"])

    def test_xml_handlers_scan_lua_but_ignore_comments_and_strings(self):
        text = ('<Ui><!-- <OnUpdate>GetItemInfo(1)</OnUpdate> -->\n'
                '<OnUpdate>\nlocal s = "NotifyInspect(thing)"\nf:SetText(value)\n</OnUpdate></Ui>')
        sites = AUDIT.source_sites(text, ".xml")
        self.assertEqual([(s["api"], s["line"]) for s in sites], [("OnUpdate", 2), ("SetText", 4)])

    def test_default_cli_is_deterministic_and_does_not_execute_tests_or_write(self):
        self.write("tests/test_side_effect.py", 'raise RuntimeError("must not import")')
        before = {p.relative_to(self.addon): p.read_bytes() for p in self.addon.rglob("*") if p.is_file()}
        outputs = []
        for _ in range(2):
            with contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(AUDIT.main([str(self.addon)]), 0)
            outputs.append(output.getvalue())
        self.assertEqual(outputs[0], outputs[1])
        self.assertEqual(json.loads(outputs[0])["tests"]["status"], "not_run")
        self.assertEqual(before, {p.relative_to(self.addon): p.read_bytes() for p in self.addon.rglob("*") if p.is_file()})

    def test_output_inside_addon_rejected_before_tests_run(self):
        marker = self.write("tests/test_side_effect.py", 'raise RuntimeError("must not import")')
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(AUDIT.main([str(self.addon), "--output", str(self.addon / "result.json"), "--run-tests"]), 2)
        self.assertFalse((self.addon / "result.json").exists())
        self.assertTrue(marker.is_file())

    def test_external_output_and_scoped_lint(self):
        destination = self.root / "report.json"
        self.write("core.lua", "local broken = )\n")
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(AUDIT.main([str(self.addon), "--output", str(destination)]), 1)
        report = json.loads(destination.read_text("utf-8"))
        self.assertGreater(next(m for m in report["modules"] if m["path"] == "core.lua")["lint"]["errors"]["count"], 0)

    def test_explicit_unittest_success_failure_and_zero_tests(self):
        start = self.addon / "tests"
        start.mkdir()
        self.assertEqual(AUDIT.run_tests(start, "test*.py", 10)["status"], "failed")
        self.write("tests/test_local.py", 'import unittest\nclass T(unittest.TestCase):\n def test_ok(self): self.assertTrue(True)\n')
        result = AUDIT.run_tests(start, "test*.py", 10)
        self.assertEqual((result["status"], result["tests_run"]), ("passed", 1))
        self.write("tests/test_local.py", 'import unittest\nclass T(unittest.TestCase):\n def test_bad(self): self.fail("expected")\n')
        self.assertEqual(AUDIT.run_tests(start, "test*.py", 10)["status"], "failed")
        self.assertEqual(AUDIT.run_tests(start, "test*.py", 0.0001)["status"], "timeout")

    def test_explicit_cli_tests_have_separate_status_from_source_review(self):
        start = self.root / "private-tests"
        start.mkdir()
        fixture = start / "test_local.py"
        for assertion, status, code in (("self.assertTrue(True)", "passed", 0),
                                        ("self.fail('expected')", "failed", 1)):
            fixture.write_text("import unittest\nclass T(unittest.TestCase):\n def test_local(self): " + assertion + "\n", encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(AUDIT.main([str(self.addon), "--run-tests", "--test-start", str(start)]), code)
            report = json.loads(output.getvalue())
            self.assertEqual(report["status"], "human_review_pending")
            self.assertEqual(report["tests"]["status"], status)
            self.assertEqual(report["tests"]["tests_run"], 1)
            self.assertNotIn("__pycache__", {p.name for p in start.iterdir()})


if __name__ == "__main__":
    unittest.main()
