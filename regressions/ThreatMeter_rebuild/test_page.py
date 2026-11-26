"""ThreatMeter 1.0: the page, the switch and the saved settings (spec 4.5, tests 1, 2, 14).

The page in ClassicAPI's Settings window holds five rows in play order; the four kept
keys carry over by name and every other old key is swept at load (KNOWN_PATTERNS KP-64).
Off means off: no event, no question, no window. The window and the badge are named
frames the client places from layout-cache.txt at the first frame (KP-66).
"""
import unittest

from tm_env import CLAUDE, FIGHT, fight, load


class Page(unittest.TestCase):
    def test_five_rows_in_play_order(self):
        lua = load()
        got = [lua.eval("page().layout.rows[%d].data.name" % i) for i in range(1, 6)]
        self.assertEqual(got, ["Show ThreatMeter", "Players shown", "Width", "Bar height", "Preview"])
        self.assertIsNone(lua.eval("page().layout.rows[6]"))

    def test_the_rows_under_the_switch_grey_out_with_it(self):
        lua = load()
        lua.execute('settingsWindow.use("ThreatMeter_enabled", false)')
        for name in ("Players shown", "Width", "Bar height", "Preview"):
            self.assertFalse(lua.eval('settingsWindow.enabled(settingsWindow.row(page(), "%s"))' % name), name)
        lua.execute('settingsWindow.use("ThreatMeter_enabled", true)')
        self.assertTrue(lua.eval('settingsWindow.enabled(settingsWindow.row(page(), "Width"))'))

    def test_defaults_are_claudes_sizes_and_on(self):
        lua = load("ThreatMeterDB = { enabled = false, rows = 5, width = 300, rowHeight = 14 }")
        lua.execute("settingsWindow.defaults(page())")
        self.assertEqual([lua.eval("ThreatMeterDB.%s" % k) for k in ("enabled", "rows", "width", "rowHeight")],
                         [True, 14, 220, 25])

    def test_slash_tm_opens_the_page(self):
        lua = load()
        lua.execute("SlashCmdList.THREATMETER('')")
        self.assertEqual(lua.eval("settingsWindow.opened.name"), "ThreatMeter")

    def test_a_right_click_on_the_title_opens_the_page_and_a_left_drag_moves(self):
        lua = load()
        head = "(function() for _, w in ipairs(widgets) do if w.parent == ThreatMeter_Window and w.kind == 'Frame' then return w end end end)()"
        lua.execute("run(%s, 'OnMouseDown', 'RightButton')" % head)
        self.assertEqual(lua.eval("settingsWindow.opened and settingsWindow.opened.name"), "ThreatMeter")
        self.assertFalse(lua.eval("ThreatMeter_Window.moving"))
        lua.execute("run(%s, 'OnMouseDown', 'LeftButton')" % head)
        self.assertTrue(lua.eval("ThreatMeter_Window.moving"))
        lua.execute("run(%s, 'OnMouseUp', 'LeftButton')" % head)
        self.assertFalse(lua.eval("ThreatMeter_Window.moving"))


class Saved(unittest.TestCase):
    def test_claudes_file_keeps_four_keys_and_loses_the_rest(self):
        lua = load(CLAUDE)
        keys = sorted(lua.eval("(function() local t = {} for k in pairs(ThreatMeterDB) do t[#t + 1] = k end "
                               "table.sort(t) return table.concat(t, ',') end)()").split(","))
        self.assertEqual(keys, ["enabled", "rowHeight", "rows", "width"])
        self.assertEqual([lua.eval("ThreatMeterDB.%s" % k) for k in ("enabled", "rows", "width", "rowHeight")],
                         [False, 14, 220, 25])

    def test_a_first_login_with_no_file_starts_on(self):
        lua = load()
        self.assertTrue(lua.eval("ThreatMeterDB.enabled"))
        self.assertTrue(lua.eval("ThreatMeter_Window:IsShown()"))

    def test_a_key_of_the_wrong_kind_takes_the_default(self):
        lua = load('ThreatMeterDB = { rows = "many", enabled = 1 }')
        self.assertEqual(lua.eval("ThreatMeterDB.rows"), 14)
        self.assertTrue(lua.eval("ThreatMeterDB.enabled"))


class OffMeansOff(unittest.TestCase):
    def test_off_registers_nothing_sends_nothing_and_shows_nothing(self):
        lua = load(CLAUDE)
        self.assertEqual(lua.eval("listening()"), "")
        lua.execute("fight()")
        self.assertEqual(lua.eval("#sent"), 0)
        self.assertFalse(lua.eval("ThreatMeter_Window:IsShown()"))

    def test_turned_on_on_the_page_it_listens_and_asks(self):
        lua = load(CLAUDE)
        lua.execute('playerCombat = true; settingsWindow.use("ThreatMeter_enabled", true)')
        self.assertTrue(lua.eval("ThreatMeter_Window:IsShown()"))
        self.assertEqual(lua.eval("#sent"), 1, "in a fight already: it asks at once")
        self.assertIn("PLAYER_IN_COMBAT_CHANGED", lua.eval("listening()"))

    def test_turned_off_in_a_fight_it_stops_asking_and_hides(self):
        lua = fight()
        lua.execute('answer("%s"); settingsWindow.use("ThreatMeter_enabled", false); step(0.2); step(1); step(1)' % FIGHT)
        self.assertEqual(lua.eval("#sent"), 1)
        self.assertEqual(lua.eval("listening()"), "")
        self.assertFalse(lua.eval("ThreatMeter_Window:IsShown()"))
        self.assertFalse(lua.eval("ThreatMeter_Badge:IsShown()"))

    def test_the_x_turns_it_off_and_says_how_to_turn_it_on(self):
        lua = load()
        lua.execute("run(closeButton(), 'OnClick')")
        self.assertFalse(lua.eval("ThreatMeterDB.enabled"))
        self.assertFalse(lua.eval("ThreatMeter_Window:IsShown()"))
        self.assertIn("/tm on", lua.eval("chat[#chat]"))
        self.assertFalse(lua.eval('Settings.GetValue("ThreatMeter_enabled")'), "the page shows it off too")


class SlashWords(unittest.TestCase):
    """The player's order, 2026-11-26: "/tm on and /tm off ... those toggles are essential"."""

    def test_tm_off_stops_it_and_tm_on_starts_it_again(self):
        lua = fight()
        lua.execute('answer("%s"); SlashCmdList.THREATMETER("off"); step(0.2); step(1)' % FIGHT)
        self.assertFalse(lua.eval("ThreatMeterDB.enabled"))
        self.assertEqual(lua.eval("listening()"), "")
        self.assertFalse(lua.eval("ThreatMeter_Window:IsShown()"))
        self.assertEqual(lua.eval("#sent"), 1, "nothing asked while off")
        self.assertIn("is off. Type /tm on", lua.eval("chat[#chat]"))
        lua.execute('SlashCmdList.THREATMETER("on")')
        self.assertTrue(lua.eval("ThreatMeterDB.enabled"))
        self.assertTrue(lua.eval("ThreatMeter_Window:IsShown()"))
        self.assertEqual(lua.eval("#sent"), 2, "still in the fight: it asks at once")
        self.assertIn("is on", lua.eval("chat[#chat]"))
        self.assertIsNone(lua.eval("settingsWindow.opened"), "the words do not open the page")

    def test_the_words_ignore_case_and_spaces(self):
        lua = load()
        lua.execute('SlashCmdList.THREATMETER(" OFF ")')
        self.assertFalse(lua.eval('Settings.GetValue("ThreatMeter_enabled")'))
        lua.execute('SlashCmdList.THREATMETER("On")')
        self.assertTrue(lua.eval('Settings.GetValue("ThreatMeter_enabled")'))

    def test_any_other_word_opens_the_page(self):
        lua = load()
        lua.execute('SlashCmdList.THREATMETER("help")')
        self.assertEqual(lua.eval("settingsWindow.opened.name"), "ThreatMeter")
        self.assertTrue(lua.eval("ThreatMeterDB.enabled"))


class Places(unittest.TestCase):
    def test_a_first_login_puts_both_frames_where_the_client_saved_them(self):
        lua = load(layout={"ThreatMeter_Window": (947, -353), "ThreatMeter_Badge": (732, -466)})
        self.assertEqual(lua.eval("ThreatMeter_Window:GetLeft()"), 947)
        self.assertEqual(lua.eval("ThreatMeter_Badge:GetLeft()"), 732)
        self.assertTrue(lua.eval("ThreatMeter_Window:IsUserPlaced()"))

    def test_with_no_saved_place_they_stand_at_their_defaults(self):
        lua = load()
        self.assertEqual(list(lua.eval("{ThreatMeter_Window:GetPoint()}").values())[:1], ["TOPLEFT"])
        self.assertEqual(list(lua.eval("{ThreatMeter_Badge:GetPoint()}").values())[:1], ["CENTER"])
        self.assertFalse(lua.eval("ThreatMeter_Window:IsUserPlaced()"))

    def test_the_badge_is_dragged_by_itself(self):
        lua = load()
        lua.execute("run(ThreatMeter_Badge, 'OnMouseDown', 'LeftButton')")
        self.assertTrue(lua.eval("ThreatMeter_Badge.moving"))
        lua.execute("run(ThreatMeter_Badge, 'OnMouseUp', 'LeftButton')")
        self.assertFalse(lua.eval("ThreatMeter_Badge.moving"))


if __name__ == "__main__":
    unittest.main()
