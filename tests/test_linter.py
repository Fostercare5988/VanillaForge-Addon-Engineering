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
            "local text = [=[\\n"
            "if function then\\n"
            "    { [ (\\n"
            "end\\n"
            "]=]\\n"
            "--[==[\\n"
            "function fake()\\n"
            "    if true then\\n"
            "]==]\\n"
            "local function real()\\n"
            "    return text\\n"
            "end\\n"
        )
        self.assertEqual(self.scan(source), [])


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

    def test_table_getn_is_reported(self):
        errors, warnings, _ = self.audit("local count = table.getn(items)\\n")
        self.assertEqual(errors, [])
        self.assertTrue(any("Legacy table.getn" in warning for warning in warnings))

    def test_manual_wipe_is_reported(self):
        errors, warnings, _ = self.audit(
            "for k in pairs(cache) do cache[k] = nil end\\n"
        )
        self.assertEqual(errors, [])
        self.assertTrue(any("Obsolete Wipe Loop" in warning for warning in warnings))

    def test_vanillaforge_inline_suppression_works(self):
        _, warnings, _ = self.audit(
            "local count = table.getn(items) -- vanillaforge-ignore: A3\\n"
        )
        self.assertFalse(any("Legacy table.getn" in warning for warning in warnings))

    def test_legacy_octowow_suppression_remains_compatible(self):
        _, warnings, _ = self.audit(
            "local count = table.getn(items) -- octowow-ignore: A3\\n"
        )
        self.assertFalse(any("Legacy table.getn" in warning for warning in warnings))

    def test_localization_is_not_treated_as_a_defect(self):
        errors, warnings, infos = self.audit('''
if GetLocale() == "deDE" then
    PLAYER_CLASS = "KRIEGER"
end
''')
        joined = "\\n".join(errors + warnings + infos)
        self.assertNotIn("Foreign Locale", joined)
        self.assertNotIn("Foreign Localization", joined)


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

    def test_outdated_classicapi_guard_is_reported(self):
        auditor = LINTER.VanillaForgeAuditor()

        with tempfile.TemporaryDirectory() as tmp:
            addon = Path(tmp) / "GuardedAddon"
            addon.mkdir()
            (addon / "GuardedAddon.lua").write_text(
                "local MIN_CLASSIC_API = 11400\\n"
                "if not CLASSIC_API_VERSION then\\n"
                "    return\\n"
                "end\\n",
                encoding="utf-8",
            )
            (addon / "README.md").write_text("# GuardedAddon\\n", encoding="utf-8")

            result = auditor.audit_addon_dir(str(addon))
            self.assertTrue(result[1])
            self.assertTrue(any("11508" in warning for warning in result[2]), result[2])


if __name__ == "__main__":
    unittest.main(verbosity=2)
