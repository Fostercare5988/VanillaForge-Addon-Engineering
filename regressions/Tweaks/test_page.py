"""The page in ClassicAPI's Settings window and /ft (spec 4.1, 4.7 "Every
addon"): a checkbox per kept switch, on by default; a slider per number the
player changed, at the player's value; using a row applies at once; Defaults
puts it back. Also what listens at rest and which globals the addon makes.
"""
import unittest
from ftr_env import load

PAGE = "settingsWindow.find('Tweaks')"
SWITCHES = ("arrowKeys", "history", "timestamps", "classColors", "blueShaman", "minimapSquare",
            "minimapClock", "minimapTidy")


def rows(lua):
    return lua.eval(f'''(function()
        local out = {{}}
        for _, r in ipairs({PAGE}.layout.rows) do out[#out + 1] = r:GetName() end
        return table.concat(out, '|')
    end)()''')


class Page(unittest.TestCase):
    def test_the_rows_in_play_order(self):
        # A rogue: no Auto Stance row, since it would do nothing (review 2026-11-18).
        rogue = ("Chat|Arrow keys without Alt|Chat history|Timestamps|"
                 "Names in class colours|Blue shamans|Minimap|Minimap size|Square minimap|Clock|"
                 "Tidy minimap|World map|Map window size")
        self.assertEqual(rows(load()), rogue)
        self.assertEqual(rows(load(cls="DRUID")), rogue + "|Gameplay|Auto Stance")

    def test_every_switch_is_on_by_default_and_the_numbers_are_the_players(self):
        lua = load()
        for key in SWITCHES:
            self.assertIs(lua.eval(f"TweaksDB.{key}"), True, key)
            self.assertIs(lua.eval(f"Settings.GetSetting('Tweaks_{key}'):GetDefaultValue()"), True, key)
        self.assertEqual(lua.eval("TweaksDB.minimapScale"), 1.6)
        self.assertEqual(lua.eval("TweaksDB.mapScale"), 1.65)
        warrior = load(cls="WARRIOR")
        self.assertIs(warrior.eval("Settings.GetSetting('Tweaks_autoStance'):GetDefaultValue()"), True)

    def test_a_saved_choice_is_kept(self):
        lua = load("TweaksDB = { timestamps = false, minimapScale = 1.1 }")
        self.assertIs(lua.eval("TweaksDB.timestamps"), False)
        self.assertEqual(lua.eval("Minimap:GetScale()"), 1.1)

    def test_a_row_applies_at_once_and_defaults_put_it_back(self):
        lua = load()
        lua.execute("settingsWindow.use('Tweaks_minimapScale', 1.0)")
        self.assertEqual(lua.eval("Minimap:GetScale()"), 1.0)
        lua.execute("settingsWindow.use('Tweaks_arrowKeys', false)")
        self.assertIs(lua.eval("ChatFrameEditBox.altArrows"), True)
        lua.execute(f"settingsWindow.defaults({PAGE})")
        self.assertEqual(lua.eval("Minimap:GetScale()"), 1.6)
        self.assertIs(lua.eval("ChatFrameEditBox.altArrows"), False)

    def test_ft_opens_the_page(self):
        lua = load()
        lua.execute("SlashCmdList.TWEAKS('')")
        self.assertEqual(lua.eval("settingsWindow.opened:GetName()"), "Tweaks")
        self.assertEqual(lua.eval("SLASH_TWEAKS1"), "/ft")


class AtRest(unittest.TestCase):
    def test_what_listens_while_nothing_happens(self):
        # A rogue: no Auto Stance. Chat at logout, the modifier keys, and the two
        # load-on-demand addons it waits for (Inspect, the battleground map);
        # nothing ticks but the clock, once a minute.
        lua = load()
        self.assertEqual(lua.eval("listening()"), "ADDON_LOADED,MODIFIER_STATE_CHANGED,PLAYER_LOGOUT")
        self.assertEqual(lua.eval("liveTimers()"), 1)

    def test_a_warrior_also_hears_the_error_text(self):
        self.assertIn("UI_ERROR_MESSAGE", load(cls="WARRIOR").eval("listening()"))

    def test_the_only_globals(self):
        import wowkit
        from ftr_env import MOCK, ROOT, GLOBALS
        lua = wowkit.runtime()
        lua.execute(MOCK)
        lua.execute("before = { __addon_ns = true, event = true }; for k in pairs(_G) do before[k] = true end")  # the kit's
        wowkit.load_addon(lua, ROOT, "Tweaks")
        lua.execute('fire("VARIABLES_LOADED") fire("PLAYER_ENTERING_WORLD")')
        made = lua.eval("(function() local out = {} for k in pairs(_G) do if not before[k] then out[#out + 1] = k end end"
                        " table.sort(out) return table.concat(out, ',') end)()")
        # SetItemRef is the client's, wrapped; the popup is an entry in StaticPopupDialogs.
        self.assertEqual(made, ",".join(sorted(g for g in GLOBALS if g != "SetItemRef")))

    def test_without_classicapi_one_error_and_nothing_else(self):
        import wowkit
        from ftr_env import MOCK, ROOT
        lua = wowkit.runtime()
        lua.execute(MOCK)
        lua.execute("CLASSIC_API_VERSION = nil")
        with self.assertRaises(Exception) as caught:
            wowkit.load_addon(lua, ROOT, "Tweaks")
        self.assertIn("Tweaks needs ClassicAPI.", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
