#!/usr/bin/env python3
"""
Regression tests for the VanillaForge linter.

These tests exercise high-confidence framework behavior instead of snapshotting
every heuristic warning.
"""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LINTER_PATH = ROOT / "tools" / "vanillaforge_linter.py"


def load_linter():
    if not LINTER_PATH.is_file():
        raise FileNotFoundError(f"Expected VanillaForge linter at: {LINTER_PATH}")

    spec = importlib.util.spec_from_file_location("vanillaforge_linter", LINTER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load vanillaforge_linter.py")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


LINTER = load_linter()


class StructuralScannerTests(unittest.TestCase):
    def scan(self, source: str):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "Test.lua"
            path.write_text(source, encoding="utf-8")
            return LINTER.HeuristicStructuralScanner.check_structure(str(path))

    def test_valid_lua_structure_passes(self):
        errors = self.scan('''
local function demo(value)
    if value then
        for i = 1, 3 do
            print(i)
        end
    end
end
''')
        self.assertEqual(errors, [])

    def test_unclosed_function_is_detected(self):
        errors = self.scan('''
local function broken()
    print("missing end")
''')
        self.assertTrue(any("Unclosed block 'function'" in error for error in errors))

    def test_long_bracket_content_does_not_confuse_scanner(self):
        source = (
            "local text = [=[\n"
            "if function then\n"
            "    { [ (\n"
            "end\n"
            "]=]\n"
            "--[==[\n"
            "function fake()\n"
            "    if true then\n"
            "]==]\n"
            "local function real()\n"
            "    return text\n"
            "end\n"
        )
        self.assertEqual(self.scan(source), [])

    def test_mask_lua_preserves_lines_and_offsets(self):
        source = (
            "local x = 1 -- comment with math.mod(1, 2)\n"
            'local s = "for k in pairs(t) do t[k] = nil" -- wipe string\n'
            "--[[\n"
            "multi-line\n"
            "]]\n"
            "return x\n"
        )
        c_lines, nc_lines = LINTER.HeuristicStructuralScanner.mask_lua(source)
        raw_lines = source.splitlines(keepends=True)
        self.assertEqual(len(c_lines), len(raw_lines))
        self.assertEqual(len(nc_lines), len(raw_lines))
        for r, c, nc in zip(raw_lines, c_lines, nc_lines):
            self.assertEqual(len(r), len(c))
            self.assertEqual(len(r), len(nc))
        self.assertNotIn("math.mod", c_lines[0])
        self.assertNotIn("pairs", c_lines[1])
        self.assertIn("for k in pairs(t) do t[k] = nil", nc_lines[1])

    def test_mask_xml_preserves_lines_and_offsets(self):
        source = (
            "<Ui>\n"
            '  <!-- <Button name="CommentedButton"> -->\n'
            '  <Frame name="RealFrame"/>\n'
            "</Ui>\n"
        )
        c_lines, nc_lines = LINTER.HeuristicStructuralScanner.mask_xml(source)
        raw_lines = source.splitlines(keepends=True)
        self.assertEqual(len(c_lines), len(raw_lines))
        self.assertEqual(len(nc_lines), len(raw_lines))
        for r, c, nc in zip(raw_lines, c_lines, nc_lines):
            self.assertEqual(len(r), len(c))
        self.assertNotIn("CommentedButton", nc_lines[1])
        self.assertIn("RealFrame", nc_lines[2])


class AuditorRuleTests(unittest.TestCase):
    def setUp(self):
        self.auditor = LINTER.VanillaForgeAuditor()

    def audit(self, source: str, suffix: str = ".lua"):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / f"Test{suffix}"
            path.write_text(source, encoding="utf-8")
            return self.auditor.audit_file(str(path))

    def test_modern_classicapi_event_signature_is_not_an_error(self):
        errors, warnings, infos = self.audit('''
local frame = CreateFrame("Frame")
frame:SetScript("OnEvent", function(self, event, ...)
    print(event)
end)
''')
        joined = "\\n".join(errors + warnings + infos)
        self.assertNotIn("Event Parameter Shadowing", joined)
        self.assertEqual(errors, [])

    def test_stored_table_length_contract_is_not_flagged_as_obsolete(self):
        errors, warnings, _ = self.audit('''
local cache = setmetatable({}, { __mode = "v" })
table.insert(cache, {})
local count = table.getn(cache)
table.setn(cache, count)
''')
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_explicit_count_and_nil_append_are_not_flagged_as_obsolete(self):
        errors, warnings, _ = self.audit('''
local args = { n = 3 }
table.setn(args, 3)
local count = table.getn(args)
table.insert(args, nil)
''')
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_manual_wipe_is_reported(self):
        errors, warnings, _ = self.audit(
            "for k in pairs(cache) do cache[k] = nil end\\n"
        )
        self.assertEqual(errors, [])
        self.assertTrue(any("Obsolete Wipe Loop" in warning for warning in warnings))

    def test_vanillaforge_inline_suppression_works(self):
        _, warnings, _ = self.audit(
            "local remainder = math.mod(5, 2) -- vanillaforge-ignore: A4\n"
        )
        self.assertFalse(any("Legacy math.mod" in warning for warning in warnings))

    def test_legacy_octowow_suppression_remains_compatible(self):
        _, warnings, _ = self.audit(
            "local remainder = math.mod(5, 2) -- octowow-ignore: A4\n"
        )
        self.assertFalse(any("Legacy math.mod" in warning for warning in warnings))

    def test_unsuppressed_math_mod_is_still_reported(self):
        _, warnings, _ = self.audit("local remainder = math.mod(5, 2)\n")
        self.assertTrue(any("Legacy math.mod" in warning for warning in warnings))

    def test_localization_is_not_treated_as_a_defect(self):
        errors, warnings, infos = self.audit('''
if GetLocale() == "deDE" then
    PLAYER_CLASS = "KRIEGER"
end
''')
        joined = "\\n".join(errors + warnings + infos)
        self.assertNotIn("Foreign Locale", joined)
        self.assertNotIn("Foreign Localization", joined)

    def test_manual_wipe_in_comment_or_string_does_not_trigger_b10(self):
        errors, warnings, _ = self.audit(
            '-- for k in pairs(cache) do cache[k] = nil end\n'
            'local doc = "for k in pairs(cache) do cache[k] = nil end"\n'
        )
        self.assertEqual(errors, [])
        self.assertFalse(any("Obsolete Wipe Loop" in w for w in warnings))

    def test_legacy_library_in_comment_or_string_does_not_trigger_b0(self):
        errors, warnings, _ = self.audit(
            '-- migrated from AceLibrary\n'
            'local note = "Using AceLibrary for fallback"\n'
        )
        self.assertEqual(errors, [])
        self.assertFalse(any("Obsolete Library Bloat" in w for w in warnings))

    def test_legacy_library_in_code_triggers_b0(self):
        errors, warnings, _ = self.audit(
            'local AceEvent = AceLibrary("AceEvent-2.0")\n'
        )
        self.assertEqual(errors, [])
        self.assertTrue(any("Obsolete Library Bloat" in w for w in warnings))

    def test_math_mod_in_comment_or_string_does_not_trigger_a4(self):
        errors, warnings, _ = self.audit(
            '-- use % instead of math.mod(a, b)\n'
            'local s = "math.mod(5, 2)"\n'
        )
        self.assertEqual(errors, [])
        self.assertFalse(any("Legacy math.mod" in w for w in warnings))

    def test_bare_colon_in_comment_or_string_does_not_trigger_a1(self):
        errors, warnings, _ = self.audit(
            '-- example: f:GetScript and f:GetScript()\n'
            'local s = "f:GetScript and f:GetScript()"\n'
        )
        self.assertEqual(errors, [])
        self.assertFalse(any("Fatal Colon Method" in e for e in errors))

    def test_marketing_superlative_in_ui_string_triggers_c14_and_14b(self):
        errors, warnings, _ = self.audit(
            'DEFAULT_CHAT_FRAME:AddMessage("Loaded enterprise-grade addon")\n'
        )
        self.assertTrue(any("Marketing Superlative in UI" in w for w in warnings))
        self.assertTrue(any("§14b" in w for w in warnings))

    def test_marketing_superlative_in_comment_does_not_trigger_c14(self):
        errors, warnings, _ = self.audit(
            '-- This is an enterprise-grade optimization\n'
            'local x = 1\n'
        )
        self.assertFalse(any("Marketing Superlative" in w for w in warnings))

    def test_developer_meta_jargon_in_comment_does_not_trigger_c14(self):
        errors, warnings, _ = self.audit(
            '-- Implemented via C++ engine coroutine\n'
            'local x = 1\n'
        )
        self.assertFalse(any("Developer Meta-Jargon in UI" in w for w in warnings))


class AddonDirectoryPolicyTests(unittest.TestCase):
    def test_missing_dependency_guard_is_not_an_error(self):
        auditor = LINTER.VanillaForgeAuditor()

        with tempfile.TemporaryDirectory() as tmp:
            addon = Path(tmp) / "MinimalAddon"
            addon.mkdir()
            (addon / "MinimalAddon.lua").write_text(
                'local addonName = "MinimalAddon"\\n', encoding="utf-8"
            )
            (addon / "README.md").write_text("# MinimalAddon\\n", encoding="utf-8")

            result = auditor.audit_addon_dir(str(addon))
            has_guard = result[1]
            readme_warnings = result[2]
            structure_warnings = result[3]
            total_errors = result[4]

            self.assertFalse(has_guard)
            self.assertEqual(total_errors, 0)
            self.assertEqual(readme_warnings, [])
            self.assertEqual(structure_warnings, [])

    def test_addon_minimum_is_not_forced_to_framework_baseline(self):
        auditor = LINTER.VanillaForgeAuditor()

        with tempfile.TemporaryDirectory() as tmp:
            addon = Path(tmp) / "GuardedAddon"
            addon.mkdir()
            (addon / "README.md").write_text("# GuardedAddon\n", encoding="utf-8")
            for minimum in (11400, 11510, 11511, 11512, 11513, 11514):
                with self.subTest(minimum=minimum):
                    (addon / "GuardedAddon.lua").write_text(
                        f"local MIN_CLASSIC_API = {minimum}\n"
                        "if not CLASSIC_API_VERSION or CLASSIC_API_VERSION < MIN_CLASSIC_API then\n"
                        "    return\n"
                        "end\n",
                        encoding="utf-8",
                    )
                    result = auditor.audit_addon_dir(str(addon))
                    self.assertTrue(result[1])
                    self.assertEqual(result[2], [])
                    self.assertEqual(result[4], 0)

    def test_readme_marketing_superlatives_trigger_rule_h9(self):
        auditor = LINTER.VanillaForgeAuditor()

        with tempfile.TemporaryDirectory() as tmp:
            addon = Path(tmp) / "HypeAddon"
            addon.mkdir()
            (addon / "HypeAddon.lua").write_text('local addonName = "HypeAddon"\n', encoding="utf-8")
            (addon / "README.md").write_text(
                "# HypeAddon\n"
                "An ultra-optimized military-grade addon featuring zero-latency processing.\n",
                encoding="utf-8",
            )

            result = auditor.audit_addon_dir(str(addon))
            readme_warnings = result[2]
            self.assertTrue(any("Rule H9 / §14b - Marketing Superlative" in w for w in readme_warnings))


class TocManifestTests(unittest.TestCase):
    def setUp(self):
        self.auditor = LINTER.VanillaForgeAuditor()

    @staticmethod
    def make_addon(tmp, name="ManifestAddon"):
        addon = Path(tmp) / name
        addon.mkdir()
        return addon

    def test_valid_toc_runtime_entries_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            addon = self.make_addon(tmp)
            (addon / "Core.lua").write_text('local addon = "ok"\n', encoding="utf-8")
            (addon / "UI.xml").write_text("<Ui></Ui>\n", encoding="utf-8")
            toc = addon / "ManifestAddon.toc"
            toc.write_text(
                "## Interface: 11200\n## Title: ManifestAddon\nCore.lua\nUI.xml\n",
                encoding="utf-8",
            )
            errors, warnings, _, _ = self.auditor.audit_toc_file(str(toc), str(addon))
            self.assertEqual(errors, [])
            self.assertEqual(warnings, [])

    def test_missing_declared_lua_is_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            addon = self.make_addon(tmp)
            toc = addon / "ManifestAddon.toc"
            toc.write_text("Missing.lua\n", encoding="utf-8")
            errors, _, _, _ = self.auditor.audit_toc_file(str(toc), str(addon))
            self.assertTrue(any("Declared runtime file does not exist" in e for e in errors))

    def test_missing_declared_xml_is_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            addon = self.make_addon(tmp)
            toc = addon / "ManifestAddon.toc"
            toc.write_text("Missing.xml\n", encoding="utf-8")
            errors, _, _, _ = self.auditor.audit_toc_file(str(toc), str(addon))
            self.assertTrue(any("Declared runtime file does not exist" in e for e in errors))

    def test_metadata_and_comments_are_not_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            addon = self.make_addon(tmp)
            toc = addon / "ManifestAddon.toc"
            toc.write_text(
                "## Interface: 11200\n"
                "## Notes: metadata.lua is text, not a runtime path\n"
                "# Disabled.lua\n",
                encoding="utf-8",
            )
            errors, _, _, declared = self.auditor.audit_toc_file(str(toc), str(addon))
            self.assertEqual(errors, [])
            self.assertEqual(declared, set())

    def test_backslash_nested_path_resolves(self):
        with tempfile.TemporaryDirectory() as tmp:
            addon = self.make_addon(tmp)
            modules = addon / "Modules"
            modules.mkdir()
            (modules / "Feature.lua").write_text("return\n", encoding="utf-8")
            toc = addon / "ManifestAddon.toc"
            toc.write_text("Modules\\Feature.lua\n", encoding="utf-8")
            errors, _, _, _ = self.auditor.audit_toc_file(str(toc), str(addon))
            self.assertEqual(errors, [])

    def test_dxvk_in_dependency_metadata_warns(self):
        with tempfile.TemporaryDirectory() as tmp:
            addon = self.make_addon(tmp)
            toc = addon / "ManifestAddon.toc"
            toc.write_text("## Dependencies: DXVK\n", encoding="utf-8")
            errors, warnings, _, _ = self.auditor.audit_toc_file(str(toc), str(addon))
            self.assertEqual(errors, [])
            self.assertTrue(any("Invalid Addon Dependency" in w for w in warnings))

    def test_tests_lua_is_not_reported_as_orphan(self):
        with tempfile.TemporaryDirectory() as tmp:
            addon = self.make_addon(tmp)
            (addon / "Core.lua").write_text("return\n", encoding="utf-8")
            test_dir = addon / "tests"
            test_dir.mkdir()
            (test_dir / "fixture.lua").write_text("return\n", encoding="utf-8")
            (addon / "ManifestAddon.toc").write_text("Core.lua\n", encoding="utf-8")
            result = self.auditor.audit_addon_dir(str(addon))
            self.assertFalse(any("fixture.lua" in w for w in result[3]))

    def test_unlisted_root_lua_is_advisory_not_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            addon = self.make_addon(tmp)
            (addon / "Core.lua").write_text("return\n", encoding="utf-8")
            (addon / "Bootstrap.lua").write_text("return\n", encoding="utf-8")
            (addon / "ManifestAddon.toc").write_text("Core.lua\n", encoding="utf-8")
            result = self.auditor.audit_addon_dir(str(addon))
            self.assertEqual(result[4], 0)
            self.assertTrue(any("Bootstrap.lua" in w for w in result[3]))

    def test_root_bindings_xml_is_not_reported_as_orphan(self):
        with tempfile.TemporaryDirectory() as tmp:
            addon = self.make_addon(tmp)
            (addon / "Core.lua").write_text("return\n", encoding="utf-8")
            (addon / "Bindings.xml").write_text(
                '<Bindings><Binding name="TEST_ACTION">TestAction()</Binding></Bindings>\n',
                encoding="utf-8",
            )
            (addon / "ManifestAddon.toc").write_text("Core.lua\n", encoding="utf-8")
            result = self.auditor.audit_addon_dir(str(addon))
            self.assertFalse(any("Bindings.xml" in w for w in result[3]), result[3])

    def test_unlisted_root_lua_still_reports_orphan(self):
        with tempfile.TemporaryDirectory() as tmp:
            addon = self.make_addon(tmp)
            (addon / "Core.lua").write_text("return\n", encoding="utf-8")
            (addon / "Dormant.lua").write_text("return\n", encoding="utf-8")
            (addon / "ManifestAddon.toc").write_text("Core.lua\n", encoding="utf-8")
            result = self.auditor.audit_addon_dir(str(addon))
            self.assertTrue(any("Dormant.lua" in w for w in result[3]), result[3])

    def test_unlisted_nested_bindings_xml_still_reports_orphan(self):
        with tempfile.TemporaryDirectory() as tmp:
            addon = self.make_addon(tmp)
            (addon / "Core.lua").write_text("return\n", encoding="utf-8")
            sub = addon / "Sub"
            sub.mkdir()
            (sub / "Bindings.xml").write_text("<Bindings></Bindings>\n", encoding="utf-8")
            (addon / "ManifestAddon.toc").write_text("Core.lua\n", encoding="utf-8")
            result = self.auditor.audit_addon_dir(str(addon))
            self.assertTrue(any("Bindings.xml" in w for w in result[3]), result[3])


if __name__ == "__main__":
    unittest.main(verbosity=2)
