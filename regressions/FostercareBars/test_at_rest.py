"""At rest the addon does nothing and leaves only its own names (spec test 15)."""
import unittest
import wowkit
from fb_env import load, GLOBALS, MOCK, ROOT


class AtRest(unittest.TestCase):
    def test_no_event_and_no_onupdate_at_rest(self):
        lua = load('FostercareBarsDB = { profiles = { PVP = { actions = {} } } }')
        self.assertEqual(lua.eval("busyFrames()"), "")
        lua.execute("FostercareBars.LoadProfile('PVP')")
        self.assertEqual(lua.eval("busyFrames()"), "", "a load with nothing to wait for listens to nothing")

    def test_only_the_listed_globals(self):
        lua = wowkit.runtime()
        lua.execute(MOCK)
        lua.execute("before = {} for k in pairs(_G) do before[k] = true end")
        wowkit.load_addon(lua, ROOT, "FostercareBars")
        new = lua.eval('''(function()
            local out = {}
            for k in pairs(_G) do if not before[k] and k ~= '__addon_ns' then out[#out + 1] = k end end
            table.sort(out)
            return table.concat(out, ',')
        end)()''')
        self.assertEqual(new.split(","), sorted(GLOBALS))
        popups = lua.eval("(function() local o = {} for k in pairs(StaticPopupDialogs) do o[#o + 1] = k end "
                          "table.sort(o) return table.concat(o, ',') end)()")
        self.assertEqual(popups, "FOSTERCAREBARS_DELETE,FOSTERCAREBARS_NEW")

    def test_a_first_login_makes_an_empty_table(self):
        lua = load()
        self.assertEqual(lua.eval("next(FostercareBarsDB.profiles)"), None)

    def test_without_classicapi_it_stops_with_one_message(self):
        lua = wowkit.runtime()
        lua.execute(MOCK)
        lua.execute("CLASSIC_API_VERSION = nil")
        with self.assertRaises(Exception) as raised:
            wowkit.load_addon(lua, ROOT, "FostercareBars")
        self.assertIn("FostercareBars needs ClassicAPI.", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
