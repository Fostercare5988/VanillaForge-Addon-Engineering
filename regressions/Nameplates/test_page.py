"""The page, the plate size, what runs at rest and logout (spec 4.6, tests 1, 2, 12
and 13). Nameplates 1.0, written new 2026-11-22. First login (no saved file), then
a /reload (the game keeps our size, so GetNamePlateSize gives ours).
"""
import unittest
from np_env import load, ENEMY_ROGUE, ENEMY_NPC

PAGE = "settingsWindow.find('Nameplates')"
DEFAULTS = {"size": 90, "followUI": True, "classColors": True, "health": True, "glow": True,
            "targeting": True, "combo": True, "marks": True, "markSize": 30, "markPlace": "ABOVE",
            "auras": True, "casts": True, "cooldowns": True}


def rows(lua):
    return lua.eval(f'''(function()
        local out = {{}}
        for _, r in ipairs({PAGE}.layout.rows) do out[#out + 1] = r:GetName() end
        return table.concat(out, '|')
    end)()''')


class Page(unittest.TestCase):
    def test_the_rows_in_play_order_with_claudes_defaults(self):
        lua = load()
        self.assertEqual(rows(lua), "Plates|Plate size|Follow UI scale|Class colours|Health text|Target|"
                         "Target glow|Targeting you|Combo points|Raid marks|Move raid marks|Mark size|"
                         "Mark place|Auras and casts|Auras|Cast bars|Enemy cooldowns")
        for key, value in DEFAULTS.items():
            self.assertEqual(lua.eval(f"NameplatesDB.{key}"), value, key)
            self.assertEqual(lua.eval(f"Settings.GetSetting('Nameplates_{key}'):GetDefaultValue()"), value, key)

    def test_a_warrior_has_no_combo_row(self):
        lua = load(setup="playerClass = 'WARRIOR'")
        self.assertNotIn("Combo points", rows(lua))
        self.assertNotIn("PLAYER_COMBO_POINTS", lua.eval("listening()"))

    def test_defaults_put_each_back(self):
        lua = load()
        lua.execute("settingsWindow.use('Nameplates_size', 150); settingsWindow.use('Nameplates_glow', false);"
                    " settingsWindow.use('Nameplates_markPlace', 'LEFT')")
        self.assertEqual(lua.eval("NameplatesDB.size"), 150)
        lua.execute(f"settingsWindow.defaults({PAGE})")
        for key, value in DEFAULTS.items():
            self.assertEqual(lua.eval(f"NameplatesDB.{key}"), value, key)

    def test_mark_rows_follow_the_switch(self):
        lua = load()
        size = f"settingsWindow.row({PAGE}, 'Mark size')"
        self.assertTrue(lua.eval(f"settingsWindow.enabled({size})"))
        lua.execute("settingsWindow.use('Nameplates_marks', false)")
        self.assertFalse(lua.eval(f"settingsWindow.enabled({size})"))

    def test_the_slash_command_opens_the_page(self):
        lua = load()
        self.assertEqual(lua.eval("SLASH_NAMEPLATES1"), "/fnp")
        self.assertIsNone(lua.eval("SLASH_NAMEPLATES2"))
        lua.execute("SlashCmdList.NAMEPLATES('')")
        self.assertEqual(lua.eval("settingsWindow.opened:GetName()"), "Nameplates")

    def test_stray_keys_are_swept_the_base_size_kept_and_the_old_file_not_read(self):
        lua = load("NameplatesDB = { overwrites = {}, targetSize = 1.1, baseWidth = 120, baseHeight = 15,"
                   " size = 80 } Nameplates_Config = { overwrites = { plateSize = 0.5 } }")
        self.assertIsNone(lua.eval("NameplatesDB.overwrites"))
        self.assertIsNone(lua.eval("NameplatesDB.targetSize"))
        self.assertEqual(lua.eval("NameplatesDB.baseWidth"), 120)
        self.assertEqual(lua.eval("NameplatesDB.size"), 80)
        self.assertEqual(lua.eval("count('GetNamePlateSize')"), 0)


class Size(unittest.TestCase):
    def test_a_first_login_reads_the_default_once_and_saves_it(self):
        lua = load(setup="UIParent:SetScale(0.8)")
        self.assertEqual(lua.eval("count('GetNamePlateSize')"), 1)
        self.assertEqual((lua.eval("NameplatesDB.baseWidth"), lua.eval("NameplatesDB.baseHeight")), (110, 14))
        self.assertAlmostEqual(lua.eval("plateSize[1]"), 110 * 0.9 * 0.8)
        self.assertAlmostEqual(lua.eval("plateSize[2]"), 14 * 0.9 * 0.8)

    def test_a_reload_takes_the_saved_base_not_the_games_size_now(self):
        lua = load("NameplatesDB = { baseWidth = 110, baseHeight = 14 }", "plateSize = { 79.2, 10.08 }")
        self.assertEqual(lua.eval("count('GetNamePlateSize')"), 0)
        self.assertAlmostEqual(lua.eval("plateSize[1]"), 99)

    def test_the_slider_and_follow_resize(self):
        lua = load(setup="UIParent:SetScale(0.8)")
        lua.execute("settingsWindow.use('Nameplates_size', 100)")
        self.assertAlmostEqual(lua.eval("plateSize[1]"), 88)
        lua.execute("settingsWindow.use('Nameplates_followUI', false)")
        self.assertAlmostEqual(lua.eval("plateSize[1]"), 110)

    def test_ui_scale_resizes_only_with_follow_on(self):
        lua = load()
        lua.execute("UIParent:SetScale(0.5); fire('UI_SCALE_CHANGED')")
        self.assertAlmostEqual(lua.eval("plateSize[1]"), 110 * 0.9 * 0.5)
        lua.execute("settingsWindow.use('Nameplates_followUI', false); forget()")
        self.assertNotIn("UI_SCALE_CHANGED", lua.eval("listening()"))

    def test_our_parts_scale_and_no_native_region_is_moved_sized_or_refonted(self):
        lua = load()
        lua.execute(f"show('nameplate1', {ENEMY_ROGUE}); show('nameplate2', {ENEMY_NPC}); target('nameplate1')")
        lua.execute("settingsWindow.use('Nameplates_size', 150); settingsWindow.use('Nameplates_marks', false)")
        lua.execute("UNIT = nil; fire('RAID_TARGET_UPDATE')")
        self.assertEqual(lua.eval("table.concat(touched, ',')"), "SetAlpha,SetAlpha,SetAlpha,SetAlpha")
        self.assertAlmostEqual(lua.eval("__addon_ns.byToken.nameplate1.cast.height"), 15)


class Rest(unittest.TestCase):
    def test_no_onupdate_and_no_timer_at_rest(self):
        lua = load()
        lua.execute(f"show('nameplate1', {ENEMY_ROGUE}); target('nameplate1'); target(nil);"
                    " fire('PLAYER_ENTERING_WORLD'); step(1)")
        self.assertNotIn("OnUpdate", lua.eval("listening()"))
        self.assertEqual(lua.eval("liveTimers()"), 0)

    def test_switched_off_features_listen_to_nothing(self):
        lua = load()
        for key in DEFAULTS:
            if DEFAULTS[key] is True and key != "followUI":
                lua.execute(f"settingsWindow.use('Nameplates_{key}', false)")
        lua.execute("settingsWindow.use('Nameplates_followUI', false)")
        self.assertEqual(lua.eval("listening()"),
                         "NAME_PLATE_UNIT_ADDED,NAME_PLATE_UNIT_REMOVED,PLAYER_ENTERING_WORLD,UNIT_FACTION")

    def test_logout_touches_no_plate(self):
        lua = load()
        lua.execute(f"show('nameplate1', {ENEMY_ROGUE}); forget(); touched = {{}}; fire('PLAYER_LOGOUT')")
        self.assertEqual(lua.eval("#touched"), 0)
        self.assertEqual(lua.eval("next(calls)"), None)


if __name__ == "__main__":
    unittest.main()
