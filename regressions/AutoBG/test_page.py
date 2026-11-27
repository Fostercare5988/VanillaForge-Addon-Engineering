"""The three pages, the saved table and /abg (spec 4.4 test 1). AutoBG 1.0, written
new 2026-11-22; a first login with no saved file unless a test gives one."""
import unittest
from abg_env import load

MAIN, BARS, FRAMES, SPY = ("settingsWindow.find('AutoBG')", "settingsWindow.find('Timer bars')",
                           "settingsWindow.find('Enemy frames')", "settingsWindow.find('Spy')")


def rows(lua, page):
    return lua.eval(f'''(function()
        local out = {{}}
        for _, r in ipairs({page}.layout.rows) do out[#out + 1] = r:GetName() end
        return table.concat(out, '|')
    end)()''')


class Pages(unittest.TestCase):
    def test_the_rows_in_play_order(self):
        lua = load()
        # 2026-11-23, the player: the page was too long, the match switches below the fold
        # and Release spirit under "After the match". 15 rows to 11.
        # 2026-11-24, the player: the arena queue was missing; its row after Alterac.
        self.assertEqual(rows(lua, MAIN), "Queue|Warsong Gulch|Arathi Basin|Alterac Valley|Arena|Queue at login|Leave queues|"
                         "Sound and flash when it pops|The match|Release spirit when you die|Leave when it ends|"
                         "Queue again after leaving")
        self.assertEqual(rows(lua, BARS), "Width|Height|Preview frames")
        # 2026-11-23, the player: the racial switches on a page of their own did not
        # say what they change; they sit in Enemy frames, one switch each.
        self.assertEqual(rows(lua, FRAMES), "Preview frames|Layout|Size|Show|Hide realm names|Distance in yards|"
                         "Width|Height|Text size|Racial cooldowns|Perception (Human)|Stoneform (Dwarf)|"
                         "Shadowmeld (Night Elf)|Escape Artist (Gnome)|Blood Fury (Orc)|"
                         "Will of the Forsaken (Undead)|War Stomp (Tauren)|Berserking (Troll)")
        self.assertIsNone(lua.eval("settingsWindow.find('Enemy racials')"))
        self.assertEqual(rows(lua, SPY), "Spy list|Rows shown|Warning sounds|Stealth card|Sap on click")

    def test_claudes_choices_are_the_defaults_and_defaults_puts_them_back(self):
        lua = load()
        expect = {"queueWSG": False, "queueAB": False, "queueAV": True, "teamsWSG": "fa", "teamsAB": "fa",
                  "queueArena": False, "arenaType": "skirmish", "queueOnLogin": True, "popAlert": True, "leave": True, "rejoin": True, "release": True,
                  "barWidth": 200, "barHeight": 22, "spy": True, "spyRows": 10, "spySounds": True}
        for key, value in expect.items():
            self.assertEqual(lua.eval(f"AutoBGDB.{key}"), value, key)
        lua.execute("settingsWindow.use('AutoBG_queueWSG', true); settingsWindow.use('AutoBG_teamsWSG', 'xf');"
                    " settingsWindow.use('AutoBG_spyRows', 4); settingsWindow.use('AutoBG_barWidth', 300)")
        self.assertEqual(lua.eval("AutoBGDB.teamsWSG"), "xf")
        lua.execute(f"settingsWindow.defaults()")
        for key, value in expect.items():
            self.assertEqual(lua.eval(f"AutoBGDB.{key}"), value, key)

    def test_each_battleground_and_its_teams_share_a_row_and_queue_now_rides_the_login_switch(self):
        # The window greys a checkbox-dropdown row's dropdown while its box is off
        # (Blizzard_SettingControls.lua, SettingsCheckboxDropdownControlMixin:EvaluateState).
        lua = load()
        wsg = f"{MAIN}.layout.rows[2]"
        self.assertEqual(lua.eval(f"{wsg}.template"), "SettingsCheckboxDropdownControlTemplate")
        self.assertEqual(lua.eval(f"{wsg}.data.cbSetting:GetVariable()"), "AutoBG_queueWSG")
        self.assertEqual(lua.eval(f"{wsg}.data.dropdownSetting:GetVariable()"), "AutoBG_teamsWSG")
        self.assertEqual(lua.eval(f"#{wsg}.data.dropdownOptions()"), 3)
        arena = f"{MAIN}.layout.rows[5]"
        self.assertEqual(lua.eval(f"{arena}.data.dropdownSetting:GetVariable()"), "AutoBG_arenaType")
        self.assertEqual(lua.eval(f"#{arena}.data.dropdownOptions()"), 4)
        login = f"{MAIN}.layout.rows[6]"
        self.assertEqual(lua.eval(f"{login}.data.setting:GetVariable()"), "AutoBG_queueOnLogin")
        lua.execute(f"settingsWindow.click({login})")
        self.assertTrue(lua.eval("said('^request:Alterac$')"))  # Alterac is ticked by default

    def test_the_size_dropdown_edits_only_that_size(self):
        lua = load()
        lua.execute("settingsWindow.use('AutoBG_size', '15'); settingsWindow.use('AutoBG_size_width', 222);"
                    " settingsWindow.use('AutoBG_size_show', false)")
        self.assertEqual(lua.eval("AutoBGDB.sizes[15].width"), 222)
        self.assertFalse(lua.eval("AutoBGDB.sizes[15].show"))
        self.assertEqual(lua.eval("AutoBGDB.sizes[10].width"), 195)
        self.assertFalse(lua.eval(f"settingsWindow.enabled({FRAMES}.layout.rows[8])"))
        lua.execute(f"settingsWindow.use('AutoBG_size', '15'); settingsWindow.defaults({FRAMES})")
        self.assertEqual(lua.eval("AutoBGDB.sizes[10].width"), 195)

    def test_old_keys_are_swept_and_the_learned_numbers_kept(self):
        lua = load("AutoBGDB = { AutoAccept = true, Positions = {}, spyRows = 'x', ticks = { [3] = { gain = 10, every = 5, n = 1 } },"
                   " spots = { [529] = { Farm = { x = 1, y = 2, n = 3 } } }, sizes = { [10] = { width = 180 }, arena = 5 } }")
        self.assertIsNone(lua.eval("AutoBGDB.AutoAccept"))
        self.assertIsNone(lua.eval("AutoBGDB.Positions"))
        self.assertEqual(lua.eval("AutoBGDB.spyRows"), 10)
        self.assertEqual(lua.eval("AutoBGDB.ticks[3].every"), 5)
        self.assertEqual(lua.eval("AutoBGDB.spots[529].Farm.n"), 3)
        self.assertEqual(lua.eval("AutoBGDB.sizes[10].width"), 180)
        self.assertEqual(lua.eval("AutoBGDB.sizes[10].height"), 25)
        self.assertIsNone(lua.eval("AutoBGDB.sizes.arena"))  # the arena's frame moved to AutoArena

    def test_the_old_table_is_not_read(self):
        lua = load("AutoBG_Settings = { AutoQueue_WSG = true, ObjectiveWidth = 150 }")
        self.assertFalse(lua.eval("AutoBGDB.queueWSG"))
        self.assertEqual(lua.eval("AutoBGDB.barWidth"), 200)

    def test_slash_opens_the_page_and_keeps_three_words(self):
        lua = load()
        self.assertEqual(lua.eval("SLASH_AUTOBG1"), "/abg")
        self.assertIsNone(lua.eval("SLASH_AUTOBG2"))
        lua.execute("SlashCmdList.AUTOBG('')")
        self.assertEqual(lua.eval("settingsWindow.opened:GetName()"), "AutoBG")
        lua.execute("SlashCmdList.AUTOBG('q xx')")
        self.assertTrue(lua.eval("heard('Queue words')") is not None)

    def test_bar_size_changes_the_rows_at_once(self):
        lua = load()
        lua.execute("enter('Arathi Basin'); line('Grom claims the Stables! If left unchallenged, the Horde will control it in 1 minute!')")
        lua.execute("settingsWindow.use('AutoBG_barHeight', 30)")
        self.assertEqual(lua.eval("AutoBG_NodeFrame.rows[1]:GetHeight()"), 30)


if __name__ == "__main__":
    unittest.main()
