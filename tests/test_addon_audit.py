"""Load closure, read-only defaults and evidence boundaries for source audits."""
import contextlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from unittest import mock
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

    def test_comparison_reports_changed_added_removed_and_unchanged_modules(self):
        self.write("Addon.toc", "core.lua\nold.lua\n")
        self.write("old.lua", "local old = true\n")
        previous = AUDIT.audit(self.addon)
        self.write("Addon.toc", "core.lua\nnew.lua\n")
        self.write("new.lua", "local new = true\n")
        current = AUDIT.audit(self.addon)
        difference = AUDIT.compare_reports(current, previous)
        self.assertEqual(difference["unchanged_modules"], ["core.lua"])
        self.assertEqual(difference["changed_modules"], ["Addon.toc"])
        self.assertEqual(difference["added_modules"], ["new.lua"])
        self.assertEqual(difference["removed_modules"], ["old.lua"])
        self.assertTrue(difference["load_graph_changed"])
        self.assertEqual(difference["status"], "changed")
        self.assertEqual(current["review"]["status"], "pending")

    def test_byte_change_invalidates_reuse_even_when_load_graph_is_unchanged(self):
        previous = AUDIT.audit(self.addon)
        self.write("core.lua", "local value = 2\n")
        difference = AUDIT.compare_reports(AUDIT.audit(self.addon), previous)
        self.assertEqual(difference["changed_modules"], ["core.lua"])
        self.assertFalse(difference["load_graph_changed"])

    def test_matching_source_does_not_promote_previous_review_or_runtime_claims(self):
        previous = AUDIT.audit(self.addon)
        previous["review"]["status"] = "complete"
        previous["addon"] = "retired-client/Addon"
        current = AUDIT.audit(self.addon)
        difference = AUDIT.compare_reports(current, previous)
        self.assertEqual(difference["status"], "unchanged")
        self.assertEqual(current["review"]["status"], "pending")
        self.assertIn("native runtime", difference["limitations"])

    def test_comparison_rejects_missing_hash_and_duplicate_module(self):
        current = AUDIT.audit(self.addon)
        for mutate in (lambda d: d["modules"][0].pop("sha256"),
                       lambda d: d["modules"].append(d["modules"][0])):
            previous = AUDIT.audit(self.addon)
            mutate(previous)
            with self.assertRaises(ValueError):
                AUDIT.compare_reports(current, previous)

    def test_comparison_cli_preserves_its_input(self):
        previous = self.root / "before.json"
        previous.write_text(json.dumps(AUDIT.audit(self.addon)), encoding="utf-8")
        original = previous.read_bytes()
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(AUDIT.main([str(self.addon), "--compare", str(previous),
                                         "--output", str(previous)]), 2)
        self.assertEqual(previous.read_bytes(), original)

    def test_external_regression_receives_the_selected_source_root(self):
        start = self.root / "external-tests"
        start.mkdir()
        (start / "test_source.py").write_text(
            "import os, unittest\nfrom pathlib import Path\n"
            "class SourceTest(unittest.TestCase):\n"
            " def test_source(self):\n"
            "  root = Path(os.environ['VANILLAFORGE_ADDON_ROOT'])\n"
            "  self.assertEqual((root / 'core.lua').read_text(), 'local value = 1\\n')\n",
            encoding="utf-8")
        result = AUDIT.run_tests(start, "test*.py", 10, self.addon)
        self.assertEqual(result["status"], "passed", result)
        self.assertEqual(result["tests_run"], 1)
        self.assertEqual(result["source_root"], str(self.addon))

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
            self.assertEqual(report["tests"]["source_verification"]["status"], "unchanged")
            self.assertNotIn("__pycache__", {p.name for p in start.iterdir()})

    def run_source_mutation(self, body):
        start = self.root / "mutation-tests"
        start.mkdir(exist_ok=True)
        (start / "test_mutation.py").write_text(
            "import os, unittest\nfrom pathlib import Path\n"
            "class MutationTest(unittest.TestCase):\n"
            " def test_source(self):\n"
            "  root = Path(os.environ['VANILLAFORGE_ADDON_ROOT'])\n" +
            "".join("  " + line + "\n" for line in body.splitlines()), encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()) as output:
            code = AUDIT.main([str(self.addon), "--run-tests", "--test-start", str(start)])
        return code, json.loads(output.getvalue())

    def test_successful_runner_cannot_validate_changed_same_size_source(self):
        before = AUDIT.audit(self.addon)
        code, report = self.run_source_mutation("(root / 'core.lua').write_text('local value = 2\\n')")
        self.assertEqual(code, 1)
        self.assertEqual(report["tests"]["status"], "invalidated")
        self.assertEqual(report["tests"]["runner_status"], "passed")
        self.assertEqual(report["tests"]["tests_run"], 1)
        self.assertEqual(report["modules"], before["modules"])
        self.assertEqual(report["review"]["status"], "pending")
        difference = report["tests"]["source_verification"]
        self.assertEqual(difference["changed_modules"], ["core.lua"])
        self.assertFalse(difference["load_graph_changed"])

    def test_source_verification_detects_changed_load_graph_and_new_root_toc(self):
        for manifest in ("Addon.toc", "New.toc"):
            with self.subTest(manifest=manifest):
                self.write("Addon.toc", "## Interface: 11200\ncore.lua\n")
                (self.addon / "New.toc").unlink(missing_ok=True)
                code, report = self.run_source_mutation(
                    "(root / 'new.lua').write_text('local new = true\\n')\n" +
                    f"(root / '{manifest}').write_text('core.lua\\nnew.lua\\n')")
                self.assertEqual(code, 1)
                self.assertEqual(report["tests"]["status"], "invalidated")
                difference = report["tests"]["source_verification"]
                self.assertTrue(difference["load_graph_changed"])
                self.assertIn("new.lua", difference["added_modules"])

    def test_deleted_source_or_manifest_cannot_leave_passing_test_evidence(self):
        for name in ("core.lua", "Addon.toc"):
            with self.subTest(deleted=name):
                self.write("Addon.toc", "core.lua\n")
                self.write("core.lua", "local value = 1\n")
                code, report = self.run_source_mutation(f"(root / '{name}').unlink()")
                self.assertEqual(code, 1)
                self.assertEqual(report["tests"]["status"], "invalidated")
                self.assertEqual(report["tests"]["runner_status"], "passed")
                self.assertIn(report["tests"]["source_verification"]["status"], {"changed", "failed"})

    def test_invalidated_source_retains_a_failed_runner_and_its_diagnostics(self):
        code, report = self.run_source_mutation(
            "(root / 'core.lua').write_text('local value = 2\\n')\nself.fail('original failure')")
        self.assertEqual(code, 1)
        self.assertEqual(report["tests"]["status"], "invalidated")
        self.assertEqual(report["tests"]["runner_status"], "failed")
        self.assertIn("original failure", report["tests"]["output_tail"])

    def test_unloaded_scratch_file_does_not_invalidate_source_evidence(self):
        code, report = self.run_source_mutation("(root / 'scratch.txt').write_text('temporary')")
        self.assertEqual(code, 0)
        self.assertEqual(report["tests"]["status"], "passed")
        self.assertEqual(report["tests"]["source_verification"]["status"], "unchanged")

    def test_post_test_snapshot_keeps_closure_and_errors_without_repeating_review_scans(self):
        self.write("Addon.toc", "ui.xml\n")
        self.write("ui.xml", '<Ui><Script file="core.lua"/><Include file="missing.xml"/></Ui>')
        self.write("Bindings.xml", '<Bindings><Binding name="B">RunAction()</Binding></Bindings>')
        before = AUDIT.audit(self.addon)
        with mock.patch.object(AUDIT, "source_sites", side_effect=AssertionError("repeated site scan")), \
             mock.patch.object(AUDIT.VanillaForgeAuditor, "audit_file", side_effect=AssertionError("repeated lint")), \
             mock.patch.object(AUDIT.VanillaForgeAuditor, "audit_toc_file", side_effect=AssertionError("repeated TOC lint")):
            after = AUDIT.audit(self.addon, source_only=True)
        self.assertEqual(AUDIT.compare_reports(after, before)["status"], "unchanged")
        self.assertEqual(after["graph_errors"], before["graph_errors"])
        self.assertEqual({m["path"] for m in after["modules"]}, {"Addon.toc", "ui.xml", "core.lua", "Bindings.xml"})
        self.assertTrue(all("lint" not in m and "sites" not in m for m in after["modules"]))


if __name__ == "__main__":
    unittest.main()
