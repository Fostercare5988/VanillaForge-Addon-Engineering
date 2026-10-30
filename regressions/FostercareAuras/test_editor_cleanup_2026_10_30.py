"""FostercareAuras_Edit refactor (2026-10-30): the editor calls the client's own functions.

The editor guarded and pcall-wrapped UIDropDownMenu functions that FrameXML always
defines (a failure there was silenced instead of reaching !ErrorLog), kept three copies
of the check enable/disable helper (one behind a test that was always false) and
tested main-addon functions that are always loaded before it. The one guard that
stays is the check helper's `cb.Enable`: a dropdown frame has no :Enable().
"""
import os
import re
import unittest
from pathlib import Path

ADDON = Path(os.environ["VANILLAFORGE_ADDON_ROOT"])
EDIT = (ADDON.parent / "FostercareAuras_Edit" / "FostercareEdit.lua").read_text("utf-8-sig")


class EditorCleanup(unittest.TestCase):
    def test_no_guard_or_pcall_around_stock_dropdown_functions(self):
        self.assertNotRegex(EDIT, r"pcall\(\s*UIDropDownMenu_")
        self.assertNotRegex(EDIT, r"if UIDropDownMenu_\w+ then")
        self.assertNotIn("pcall(commitFunc", EDIT)

    def test_main_addon_functions_are_called_not_tested(self):
        for name in ("FostercareAuras_RefreshList", "FostercareAuras_RefreshIcons", "FostercareConditions_RequestEvaluate"):
            self.assertNotRegex(EDIT, r"if %s then" % name)

    def test_one_enable_and_one_disable_helper_for_checks(self):
        for gone in ("_enCheck", "_disCheck", "_SetAuraCheckEnabled", "_WhiteifyDDText"):
            self.assertNotIn(gone, EDIT, gone)
        self.assertEqual(len(re.findall(r"local function FostercareEdit_EnableCheck", EDIT)), 1)
        self.assertEqual(len(re.findall(r"local function FostercareEdit_DisableCheck", EDIT)), 1)

    def test_dropdown_frames_are_not_asked_to_enable(self):
        """cond_item_enchant is a dropdown; the shared helper must tolerate it."""
        self.assertRegex(EDIT, r"if cb\.Enable then\s+cb:Enable\(\)")
        self.assertRegex(EDIT, r"if cb\.Disable then\s+cb:Disable\(\)")

    def test_dropdown_color_helpers_are_not_globals(self):
        for name in ("_GoldifyDD", "_GreyifyDD"):
            self.assertRegex(EDIT, r"local function %s\(" % name)
            self.assertNotRegex(EDIT, r"(?m)^function %s\(" % name)


if __name__ == "__main__":
    unittest.main()
