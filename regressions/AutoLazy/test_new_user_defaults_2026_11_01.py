"""A new AutoLazy user starts with the author's settings, 2026-11-01.

Loot rules, quiet roll chat and the radio/LFG icon tweaks follow the author's own
choices; the author's button position is used only when the screen can hold it.
Existing saved settings are not replaced. Everything here is the shipped default
table; how it feels in game stays a game check.
"""
import unittest

from wowlua import LuaRuntime

from test_audit_2026_10_26 import CORE, CORE_MOCKS


def load(width, height, saved=None):
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(CORE_MOCKS)
    lua.execute("function GetScreenWidth() return %d end; function GetScreenHeight() return %d end" % (width, height))
    if saved:
        lua.execute("AutoLazyDB = " + saved)
    lua.execute(CORE)
    lua.execute("AutoLazy.UpdateActionButton = function() end; AutoLazy.ApplySystemIconToggles = function() end")
    lua.execute('fire("ADDON_LOADED", "AutoLazy")')
    return lua


class NewUser(unittest.TestCase):
    def test_options_follow_the_authors_choices(self):
        lua = load(1920, 1080)
        self.assertFalse(lua.eval("AutoLazyDB.CleanRollChat"))
        self.assertTrue(lua.eval("AutoLazyDB.Tweaks.HideRadio"))
        self.assertTrue(lua.eval("AutoLazyDB.Tweaks.HideLfg"))
        self.assertTrue(lua.eval("AutoLazyDB.AutoConfirmBop"))

    def test_loot_rules_follow_the_authors_choices(self):
        lua = load(1920, 1080)
        rules = lua.eval("AutoLazyDB.ItemRules")
        self.assertEqual(rules["zg coins"], "NEED")
        self.assertEqual(rules["zg bijous"], "NEED")
        self.assertEqual(rules["corrupted sand"], "PASS")
        for key in ("aq20 scarabs", "aq20 idols", "wartorn cloth scrap", "wartorn leather scrap",
                    "wartorn chain scrap", "wartorn plate scrap"):
            self.assertEqual(rules[key], "MANUAL", key)

    def test_the_button_position_is_used_when_the_screen_can_hold_it(self):
        lua = load(1920, 1080)
        self.assertAlmostEqual(lua.eval("AutoLazyDB.ButtonPos.x"), 1417.11, places=2)
        self.assertAlmostEqual(lua.eval("AutoLazyDB.ButtonPos.y"), 928.56, places=2)

    def test_a_smaller_screen_gets_the_default_top_right_button(self):
        lua = load(1366, 768)
        self.assertIsNone(lua.eval("AutoLazyDB.ButtonPos.x"))


class ExistingUser(unittest.TestCase):
    def test_saved_choices_are_kept(self):
        lua = load(1920, 1080, '{ Enabled = true, CleanRollChat = true, ButtonPos = {}, Tweaks = { HideRadio = false, HideLfg = false, CollapseAddons = true, KeepOnMinimap = {} } }')
        self.assertTrue(lua.eval("AutoLazyDB.CleanRollChat"))
        self.assertFalse(lua.eval("AutoLazyDB.Tweaks.HideRadio"))
        self.assertIsNone(lua.eval("AutoLazyDB.ButtonPos.x"))     # an unmoved button stays unmoved


if __name__ == "__main__":
    unittest.main()
