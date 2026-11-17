"""The page in ClassicAPI's Settings window and /al (spec 4.2, 4.3; tests 1, 13):
eleven rows in play order, the defaults are Claude's settings, the roll
choices hang on Auto-roll, Defaults puts each back, the old keys are swept.
Also what listens at rest and which globals the addon makes.
"""
import unittest
from al_env import load

PAGE = "settingsWindow.find('AutoLazy')"
DEFAULTS = {"roll": True, "rollSand": "PASS", "rollBijous": "NEED", "rollCoins": "NEED",
            "rollScarabs": "MANUAL", "rollScraps": "MANUAL", "confirmBind": True, "hideRollChat": True,
            "shiftQuests": True, "tray": True, "hideRadioLfg": True}


def rows(lua):
    return lua.eval(f'''(function()
        local out = {{}}
        for _, r in ipairs({PAGE}.layout.rows) do out[#out + 1] = r:GetName() end
        return table.concat(out, '|')
    end)()''')


class Page(unittest.TestCase):
    def test_the_rows_in_play_order(self):
        self.assertEqual(rows(load()), "Loot|Auto-roll farm items|Corrupted Sand|Bijous|Coins|Scarabs|"
                         "Wartorn Scraps|Accept bind-on-pickup|Hide roll spam|Quests|Shift turn-ins|"
                         "Minimap|Minimap tray|Hide Pirate Radio and Group Finder")

    def test_the_defaults_are_claudes_settings(self):
        lua = load()
        for key, value in DEFAULTS.items():
            self.assertEqual(lua.eval(f"AutoLazyDB.{key}"), value, key)
            self.assertEqual(lua.eval(f"Settings.GetSetting('AutoLazy_{key}'):GetDefaultValue()"), value, key)

    def test_the_roll_choices_and_their_parent(self):
        lua = load()
        lua.execute(f"row = settingsWindow.row({PAGE}, 'Scarabs')")
        self.assertEqual(lua.eval("(function() local o = {} for _, c in ipairs(settingsWindow.choices(row)) do"
                                  " o[#o + 1] = c.value .. '=' .. c.label end return table.concat(o, ',') end)()"),
                         "MANUAL=Manual,NEED=Need,GREED=Greed,PASS=Pass")
        self.assertTrue(lua.eval("settingsWindow.enabled(row)"))
        lua.execute("settingsWindow.use('AutoLazy_roll', false)")
        self.assertFalse(lua.eval("settingsWindow.enabled(row)"))

    def test_the_old_keys_are_swept_and_a_set_value_is_kept(self):
        lua = load("AutoLazyDB = { Enabled = true, ItemRules = {}, KeepOnMinimap = {}, ButtonPos = { 1, 2 },"
                   " rollScarabs = 'NEED', tray = false }")
        self.assertIsNone(lua.eval("AutoLazyDB.Enabled"))
        self.assertIsNone(lua.eval("AutoLazyDB.ItemRules"))
        self.assertIsNone(lua.eval("AutoLazyDB.KeepOnMinimap"))
        self.assertIsNone(lua.eval("AutoLazyDB.ButtonPos"))
        self.assertEqual(lua.eval("AutoLazyDB.rollScarabs"), "NEED")
        self.assertIs(lua.eval("AutoLazyDB.tray"), False)

    def test_defaults_put_it_back(self):
        lua = load("AutoLazyDB = { rollSand = 'NEED', tray = false, shiftQuests = false }")
        lua.execute(f"settingsWindow.defaults({PAGE})")
        for key, value in DEFAULTS.items():
            self.assertEqual(lua.eval(f"AutoLazyDB.{key}"), value, key)
        self.assertTrue(lua.eval("AutoLazyButton:IsShown()"))

    def test_al_and_a_right_click_open_the_page(self):
        lua = load()
        self.assertEqual(lua.eval("SLASH_AUTOLAZY1"), "/al")
        lua.execute("SlashCmdList.AUTOLAZY('')")
        self.assertEqual(lua.eval("settingsWindow.opened:GetName()"), "AutoLazy")
        lua.execute("settingsWindow.opened = nil; click(AutoLazyButton, 'RightButton')")
        self.assertEqual(lua.eval("settingsWindow.opened:GetName()"), "AutoLazy")
        self.assertFalse(lua.eval("AutoLazyTray:IsShown()"))


class AtRest(unittest.TestCase):
    def test_what_listens_and_no_timer(self):
        lua = load()
        lua.execute('fire("ZONE_CHANGED_NEW_AREA") fire("PLAYER_ENTERING_WORLD") step(1) step(1)')
        self.assertEqual(lua.eval("listening()"),
                         "CONFIRM_LOOT_ROLL,GOSSIP_SHOW,LOOT_BIND_CONFIRM,LOOT_CLOSED,QUEST_COMPLETE,"
                         "QUEST_DATA_LOAD_RESULT,QUEST_DETAIL,QUEST_GREETING,QUEST_PROGRESS,QUEST_TURNED_IN,"
                         "START_LOOT_ROLL")
        self.assertEqual(lua.eval("liveTimers()"), 0)

    def test_the_only_globals(self):
        import wowkit
        from al_env import MOCK, ROOT, BEFORE
        lua = wowkit.runtime()
        lua.execute(MOCK)
        lua.execute(BEFORE)
        lua.execute("before = { __addon_ns = true, event = true }; for k in pairs(_G) do before[k] = true end")
        wowkit.load_addon(lua, ROOT, "AutoLazy")
        lua.execute('fire("VARIABLES_LOADED") fire("PLAYER_LOGIN") fire("PLAYER_ENTERING_WORLD")')
        made = lua.eval("(function() local out = {} for k in pairs(_G) do if not before[k] then out[#out + 1] = k end end"
                        " table.sort(out) return table.concat(out, ',') end)()")
        self.assertEqual(made, "AutoLazyButton,AutoLazyDB,AutoLazyTray,SLASH_AUTOLAZY1")

    def test_without_classicapi_one_error_and_nothing_else(self):
        import wowkit
        from al_env import MOCK, ROOT
        lua = wowkit.runtime()
        lua.execute(MOCK)
        lua.execute("CLASSIC_API_VERSION = nil")
        with self.assertRaises(Exception) as caught:
            wowkit.load_addon(lua, ROOT, "AutoLazy")
        self.assertIn("AutoLazy needs ClassicAPI.", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
