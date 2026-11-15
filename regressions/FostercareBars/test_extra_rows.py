"""FostercareTweaks' Extra Rows 2-7 go with the profile (spec K7; test 10)."""
import unittest
from fb_env import load

SAVED = '''FostercareBarsDB = { profiles = { PVP = {
    actions = { [1] = { kind = 'spell', id = 10 } },
    extra = { version = 1, rows = { [3] = { [2] = { kind = 'spell', id = 7 } } } },
} } }'''


class ExtraRows(unittest.TestCase):
    def test_saved_through_the_interface(self):
        lua = load(setup="tweaksOn()")
        lua.execute("StaticPopup_Show('FOSTERCAREBARS_NEW') accept('PVP')")
        self.assertEqual(lua.eval("FostercareBarsDB.profiles.PVP.extra.rows[2][1].id"), 5)

    def test_a_failed_read_saves_nothing(self):
        lua = load(SAVED, "tweaksOn() FostercareTweaks.ExtraActions.failGet = 'Bars are not ready.'")
        lua.execute("bars[1] = { kind = 'spell', id = 99 } StaticPopup_Show('FOSTERCAREBARS_NEW') accept('PVP')")
        self.assertEqual(lua.eval("FostercareBarsDB.profiles.PVP.actions[1].id"), 10, "the old profile stays")
        self.assertIn("Not saved: Bars are not ready.", lua.eval("chatText()"))

    def test_checked_before_any_slot_changes_and_applied_after(self):
        lua = load(SAVED, "tweaksOn() learn(10)")
        self.assertTrue(lua.eval("FostercareBars.LoadProfile('PVP')"))
        log = list(lua.eval("FostercareTweaks.ExtraActions.log").values())
        self.assertEqual(log, ["validate after 0 changes", "apply after 1 changes"])
        self.assertEqual(lua.eval("FostercareTweaks.ExtraActions.applied.rows[3][2].id"), 7)
        self.assertIn("1 button changed, extra rows too.", lua.eval("chatText()"))

    def test_a_refused_check_changes_nothing(self):
        lua = load(SAVED, "tweaksOn() learn(10) FostercareTweaks.ExtraActions.failValidate = 'Release the keys.'")
        self.assertFalse(lua.eval("FostercareBars.LoadProfile('PVP')"))
        self.assertEqual(lua.eval("changes()"), 0)
        self.assertIn("Not loaded: Release the keys.", lua.eval("chatText()"))

    def test_a_failed_apply_is_said_and_the_buttons_stay_loaded(self):
        lua = load(SAVED, "tweaksOn() learn(10) FostercareTweaks.ExtraActions.failApply = 'Refresh failed.'")
        self.assertTrue(lua.eval("FostercareBars.LoadProfile('PVP')"))
        self.assertEqual(lua.eval("bars[1].id"), 10)
        text = lua.eval("chatText()")
        self.assertIn("Extra rows not loaded: Refresh failed.", text)
        self.assertIn("1 button changed.", text)

    def test_a_profile_with_extra_rows_needs_fostercaretweaks(self):
        lua = load(SAVED, "learn(10)")
        self.assertFalse(lua.eval("FostercareBars.LoadProfile('PVP')"))
        self.assertEqual(lua.eval("changes()"), 0)
        self.assertIn("turn FostercareTweaks on", lua.eval("chatText()"))

    def test_saving_without_it_keeps_the_rows_the_profile_had(self):
        lua = load(SAVED)
        lua.execute("bars[1] = { kind = 'spell', id = 99 } StaticPopup_Show('FOSTERCAREBARS_NEW') accept('PVP')")
        self.assertEqual(lua.eval("FostercareBarsDB.profiles.PVP.actions[1].id"), 99)
        self.assertEqual(lua.eval("FostercareBarsDB.profiles.PVP.extra.rows[3][2].id"), 7)

    def test_another_interface_version_is_not_used(self):
        lua = load(setup="tweaksOn() FostercareTweaks.ExtraActions.ProfileVersion = 2")
        lua.execute("StaticPopup_Show('FOSTERCAREBARS_NEW') accept('PVP')")
        self.assertIsNone(lua.eval("FostercareBarsDB.profiles.PVP.extra"))


if __name__ == "__main__":
    unittest.main()
