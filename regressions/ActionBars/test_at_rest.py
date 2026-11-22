"""At rest the addon listens only to the bars' slot events, runs no OnUpdate
and no timer, and leaves only its own names (spec test 15; Tweaks
spec 4.2 "Events at rest" and 4.7 "All")."""
import re
import unittest
import wowkit
from fb_env import load, GLOBALS, MOCK, BARS, ROOT

# The slot buttons' events (Slots.lua) and the bars' own (Bars.lua), from login on.
AT_REST = sorted([
    "ACTIONBAR_SLOT_CHANGED", "ACTION_USABLE_CHANGED", "ACTION_RANGE_CHECK_UPDATE",
    "ACTIONBAR_UPDATE_COOLDOWN", "ACTIONBAR_UPDATE_STATE", "BAG_UPDATE_DELAYED", "UPDATE_BONUS_ACTIONBAR",
    "ACTIONBAR_PAGE_CHANGED", "UPDATE_MACROS", "PLAYER_ENTER_COMBAT", "PLAYER_LEAVE_COMBAT",
    "START_AUTOREPEAT_SPELL", "STOP_AUTOREPEAT_SPELL", "TRADE_SKILL_SHOW", "TRADE_SKILL_CLOSE",
    "CRAFT_SHOW", "CRAFT_CLOSE", "UNIT_INVENTORY_CHANGED", "PLAYER_EQUIPMENT_CHANGED",
    "PLAYER_ENTERING_WORLD", "UPDATE_BINDINGS", "CURSOR_CHANGED", "LOSS_OF_CONTROL_UPDATE",
])


class AtRest(unittest.TestCase):
    def test_only_the_slot_events_at_rest_and_no_onupdate(self):
        lua = load('ActionBarsDB = { profiles = { PVP = { actions = {} } } }')
        self.assertEqual(lua.eval("allEvents()").split(","), AT_REST)
        self.assertEqual(lua.eval("busyFrames()"), "")
        self.assertEqual(lua.eval("timerCount()"), 0)
        lua.execute("ActionBars.LoadProfile('PVP')")
        self.assertEqual(lua.eval("busyFrames()"), "", "a load with nothing to wait for listens to nothing")

    def test_the_stock_buttons_stop_listening(self):
        lua = load()
        self.assertIsNone(lua.eval("next(ActionButton1.events)"))
        self.assertIsNone(lua.eval("next(MultiBarRightButton12.events)"))

    def test_only_the_listed_globals(self):
        lua = wowkit.runtime()
        lua.execute(MOCK)
        lua.execute(BARS)
        lua.execute("before = {} for k in pairs(_G) do before[k] = true end")
        wowkit.load_addon(lua, ROOT, "ActionBars")
        lua.execute('fire("VARIABLES_LOADED") fire("PLAYER_ENTERING_WORLD")')
        new = lua.eval('''(function()
            local out = {}
            for k in pairs(_G) do if not before[k] and k ~= '__addon_ns' then out[#out + 1] = k end end
            table.sort(out)
            return table.concat(out, ',')
        end)()''').split(",")
        # event and arg1... are the kit's (fire() sets them); hookedTimer is the mock's.
        own = [n for n in new if n not in GLOBALS and not re.fullmatch(r"event|arg\d|hookedTimer", n)]
        for name in own:
            self.assertTrue(re.fullmatch(r"ActionBars_\w+|BINDING_HEADER_ACTIONBARS"
                                         r"|BINDING_NAME_ACTIONBARS_EXTRA\d+_\d+", name), name)
        self.assertEqual(sorted(set(GLOBALS) & set(new)), sorted(GLOBALS))
        popups = lua.eval("(function() local o = {} for k in pairs(StaticPopupDialogs) do o[#o + 1] = k end "
                          "table.sort(o) return table.concat(o, ',') end)()")
        self.assertEqual(popups, "ACTIONBARS_DELETE,ACTIONBARS_NEW")

    def test_a_first_login_makes_an_empty_table(self):
        lua = load()
        self.assertEqual(lua.eval("next(ActionBarsDB.profiles)"), None)
        self.assertEqual(lua.eval("ActionBarsDB.extraBars"), 1)

    def test_without_classicapi_it_stops_with_one_message(self):
        lua = wowkit.runtime()
        lua.execute(MOCK)
        lua.execute("CLASSIC_API_VERSION = nil")
        with self.assertRaises(Exception) as raised:
            wowkit.load_addon(lua, ROOT, "ActionBars")
        self.assertIn("ActionBars needs ClassicAPI.", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
