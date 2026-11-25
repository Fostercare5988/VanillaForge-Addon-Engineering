"""The page, a first login over the old file, Move text areas and the combat log
filter (spec BattleText.md 4.5, tests 1, 2, 12 and 13). BattleText 1.0, written
new 2026-11-22. Every test logs in fresh (no /reload).
"""
import unittest
from pathlib import Path
from bt_env import load, CLAUDE_243

PAGE = "settingsWindow.find('BattleText')"
DEFAULTS = {"manaGains": True, "alertWindfury": True, "alertLowHealth": False, "alertLowMana": True,
            "alertClearcasting": True, "alertReady": True}
REAL = Path.home() / "Desktop" / "OctoWoW" / "WTF" / "Account" / "NIKORULES" / "SavedVariables" / "BattleText.lua"


def rows(lua):
    """The names of the rows a player sees, in order."""
    return lua.eval(f'''(function()
        local out = {{}}
        for _, r in ipairs({PAGE}.layout.rows) do
            if settingsWindow.visible(r) then out[#out + 1] = r:GetName() end
        end
        return table.concat(out, '|')
    end)()''')


class Page(unittest.TestCase):
    def test_a_rogue_who_knows_riposte(self):
        lua = load(setup="known.Riposte = 'Interface\\\\Icons\\\\Ability_Warrior_Challange'")
        self.assertEqual(rows(lua), "Text|Move text areas|Alerts|Windfury!|Low Health!|Ready alerts")
        for key, value in DEFAULTS.items():
            self.assertEqual(lua.eval(f"BattleTextDB.{key}"), value, key)
            self.assertEqual(lua.eval(f"Settings.GetSetting('BattleText_{key}'):GetDefaultValue()"), value, key)

    def test_a_mage_has_the_mana_rows_and_clearcasting(self):
        lua = load(setup="playerClass = 'MAGE'")
        self.assertEqual(rows(lua), "Text|Move text areas|Mana|All mana gains|Alerts|Windfury!|Low Health!|"
                         "Low Mana!|Clearcasting!")

    def test_defaults_put_each_back_and_leave_the_places(self):
        lua = load(setup="playerClass = 'MAGE'")
        lua.execute("BattleTextDB.areas = { Incoming = { x = 1, y = 2 } }")
        for key, value in DEFAULTS.items():
            lua.execute(f"settingsWindow.use('BattleText_{key}', {'false' if value else 'true'})")
        lua.execute(f"settingsWindow.defaults({PAGE})")
        for key, value in DEFAULTS.items():
            self.assertEqual(lua.eval(f"BattleTextDB.{key}"), value, key)
        self.assertEqual(lua.eval("BattleTextDB.areas.Incoming.x"), 1)

    def test_bt_opens_the_page(self):
        lua = load()
        self.assertEqual(lua.eval("SLASH_BATTLETEXT1"), "/bt")
        self.assertIsNone(lua.eval("SLASH_BATTLETEXT2"))
        lua.execute("SlashCmdList.BATTLETEXT('')")
        self.assertEqual(lua.eval("settingsWindow.opened:GetName()"), "BattleText")


class FirstLogin(unittest.TestCase):
    def test_the_old_file_is_swept_and_the_defaults_filled(self):
        lua = load(CLAUDE_243)
        self.assertIsNone(lua.eval("BattleTextDB.UserDisabled"))
        self.assertIsNone(lua.eval("BattleTextDB.Profiles"))
        for key, value in DEFAULTS.items():
            self.assertEqual(lua.eval(f"BattleTextDB.{key}"), value, key)

    @unittest.skipUnless(REAL.exists(), "no client")
    def test_claudes_real_243_file(self):
        lua = load(REAL.read_bytes().decode("utf-8", errors="replace"))
        keys = lua.eval("(function() local t = {} for k in pairs(BattleTextDB) do t[#t + 1] = k end "
                        "table.sort(t) return table.concat(t, ',') end)()")
        self.assertEqual(keys, ",".join(sorted(DEFAULTS)))

    def test_an_empty_file(self):
        lua = load("BattleTextDB = {}")
        for key, value in DEFAULTS.items():
            self.assertEqual(lua.eval(f"BattleTextDB.{key}"), value, key)

    def test_a_stray_area_goes_and_a_saved_place_is_used(self):
        lua = load("BattleTextDB = { areas = { Pet = { x = 1, y = 1 }, Outgoing = { x = 40, y = 50 },"
                   " Incoming = { x = 'a' } } }", world=False)
        self.assertIsNone(lua.eval("BattleTextDB.areas.Pet"))
        self.assertIsNone(lua.eval("BattleTextDB.areas.Incoming"))
        self.assertEqual(list(lua.eval("{__addon_ns.areas.Outgoing.frame:GetPoint(1)}").values())[2:], ["CENTER", 40, 50])
        self.assertTrue(lua.eval("select(2, __addon_ns.areas.Outgoing.frame:GetPoint(1)) == UIParent"))

    def test_the_areas_stand_before_the_first_frame_and_nothing_is_cached(self):
        lua = load(world=False)
        for name, x, y in (("Incoming", -159, -46), ("Outgoing", 153, -43), ("Notification", -5, 169)):
            point = list(lua.eval(f"{{__addon_ns.areas.{name}.frame:GetPoint(1)}}").values())
            self.assertEqual(point[0], "BOTTOM")
            self.assertEqual(point[2:], ["CENTER", x, y], name)
            self.assertIsNone(lua.eval(f"__addon_ns.areas.{name}.frame:GetName()"))
        self.assertEqual(lua.eval("#restoring"), 0)


class Move(unittest.TestCase):
    def handles(self, lua):
        return lua.eval('''(function()
            local out = {}
            for _, w in ipairs(widgets) do
                if w.kind == "Button" and w.parent == BattleTextMover and w.scripts.OnDragStart then out[#out + 1] = w end
            end
            return out
        end)()''')

    def test_the_button_shows_three_handles_a_drag_saves_a_right_click_restores(self):
        lua = load()
        lua.execute(f"settingsWindow.click(settingsWindow.row({PAGE}, 'Move text areas'))")
        self.assertTrue(lua.eval("BattleTextMover:IsShown()"))
        self.assertEqual(len(self.handles(lua)), 3)
        # The Outgoing handle dragged: its centre 100 right of and 20 above the screen's.
        lua.execute('''for _, w in ipairs(widgets) do
            if w.kind == "Button" and w.parent == BattleTextMover and w.scripts.OnDragStart then
                local _, _, _, x = w:GetPoint(1)
                if x == 153 then dragged = w end
            end
        end
        run(dragged, "OnDragStart")
        dragged.left, dragged.top = 512 + 100 - 60, 384 + 20 + 12
        run(dragged, "OnDragStop")''')
        self.assertEqual((lua.eval("BattleTextDB.areas.Outgoing.x"), lua.eval("BattleTextDB.areas.Outgoing.y")), (100, 20))
        self.assertEqual(list(lua.eval("{__addon_ns.areas.Outgoing.frame:GetPoint(1)}").values())[3:], [100, 20])
        lua.execute('run(dragged, "OnClick", "RightButton")')
        self.assertIsNone(lua.eval("BattleTextDB.areas.Outgoing"))
        self.assertEqual(list(lua.eval("{__addon_ns.areas.Outgoing.frame:GetPoint(1)}").values())[3:], [153, -43])

    def test_escape_hides_them(self):
        lua = load()
        lua.execute("__addon_ns.Move()")
        names = lua.eval("(function() local t = {} for _, n in ipairs(UISpecialFrames) do t[#t + 1] = n end "
                         "return table.concat(t, ',') end)()")
        self.assertIn("BattleTextMover", names.split(","))
        lua.execute("__addon_ns.Move()")
        self.assertEqual(names.count("BattleTextMover"), 1)


class Filter(unittest.TestCase):
    def test_reset_and_set_to_you_once_with_no_pet_filter(self):
        lua = load()
        self.assertEqual(lua.eval("filters.resets"), 1)
        self.assertEqual(lua.eval("#filters"), 2)
        self.assertEqual((lua.eval("filters[1].source"), lua.eval("filters[1].dest")), (0x511, None))
        self.assertEqual((lua.eval("filters[2].source"), lua.eval("filters[2].dest")), (None, 0x511))
        events = lua.eval("filters[1].events").split(",")
        self.assertIn("SWING_DAMAGE", events)
        self.assertIn("PARTY_KILL", events)
        self.assertEqual(lua.eval("filters[1].events"), lua.eval("filters[2].events"))
        lua.execute('fire("PLAYER_ENTERING_WORLD")')
        self.assertEqual(lua.eval("filters.resets"), 1)
        self.assertIn(",COMBAT_LOG_EVENT,", lua.eval("listening()"))
        self.assertNotIn("COMBAT_LOG_EVENT_UNFILTERED", lua.eval("listening()"))


if __name__ == "__main__":
    unittest.main()
