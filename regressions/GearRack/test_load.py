"""A first login (spec 4.5 test 1): the bars where the client saved them, or
in their own spot; a new character's defaults; the saved-key sweep."""
import unittest
from gr_env import load, values

CLAUDE = '''GearRackDB = { gearBar = "ACROSS", trinketBar = "DOWN", readyAlert = true, auto = false,
    slots = { 16, 17, 18, 15, 7, 2 }, when = { mounted = "", ["form Stealth"] = "", oldRow = "PVE" },
    target = { Elemental = "Dissolvent", other = "Instant", Plaguelands = "x" }, Events = {}, ShowIcon = "ON" }'''


class FirstLogin(unittest.TestCase):
    def test_a_new_character_gets_three_slots_across_and_the_trinkets_down(self):
        lua = load()
        self.assertEqual(values(lua, "GearRackDB.slots"), [16, 17, 18])
        self.assertEqual(lua.eval("GearRackDB.gearBar"), "ACROSS")
        self.assertEqual(lua.eval("GearRackDB.trinketBar"), "DOWN")
        self.assertTrue(lua.eval("GearRackDB.readyAlert"))
        self.assertFalse(lua.eval("GearRackDB.auto"))
        # Main, off, ranged and the Sets button across; the trinkets one under the other.
        self.assertEqual(lua.eval("GearRackGearBar:GetWidth()"), 4 * 40 - 4)
        self.assertEqual(lua.eval("GearRackGearBar:GetHeight()"), 36)
        self.assertEqual(lua.eval("GearRackTrinketBar:GetHeight()"), 2 * 40 - 4)
        self.assertEqual(lua.eval("(select(4, GearRackSets:GetPoint(1)))"), 3 * 40)
        self.assertTrue(lua.eval("GearRackGearBar:IsShown()"))

    def test_the_bars_sit_where_the_client_saved_them(self):
        lua = load(CLAUDE, layout={"GearRackGearBar": (478, -535), "GearRackTrinketBar": (431, -318)})
        # The client puts a saved frame back at the first frame (KP-66); the
        # addon placed nothing of its own over it.
        self.assertEqual(lua.eval("GearRackGearBar:GetLeft()"), 478)
        self.assertEqual(lua.eval("(select(4, GearRackGearBar:GetPoint(1)))"), 478)
        self.assertEqual(lua.eval("GearRackGearBar:GetNumPoints()"), 1)
        self.assertEqual(lua.eval("GearRackTrinketBar:GetLeft()"), 431)

    def test_no_error_before_the_bars_have_a_place(self):
        lua = load(CLAUDE, layout={"GearRackGearBar": (478, -535)}, world=False)
        lua.execute('fire("VARIABLES_LOADED") fire("PLAYER_ENTERING_WORLD")')  # before the first frame
        lua.execute("step(0)")
        self.assertEqual(lua.eval("GearRackGearBar:GetLeft()"), 478)

    def test_a_bar_with_no_saved_place_sits_in_its_own_spot(self):
        lua = load()
        self.assertEqual(lua.eval("(select(3, GearRackGearBar:GetPoint(1)))"), "BOTTOMLEFT")
        self.assertEqual(lua.eval("(select(4, GearRackGearBar:GetPoint(1)))"), 478)

    def test_unknown_saved_keys_are_swept_and_kept_keys_survive(self):
        lua = load(CLAUDE, setup='player.forms = { "Stealth" }')
        self.assertIsNone(lua.eval("GearRackDB.Events"))
        self.assertIsNone(lua.eval("GearRackDB.ShowIcon"))
        self.assertIsNone(lua.eval("GearRackDB.when.oldRow"))
        self.assertIsNone(lua.eval("GearRackDB.target.Plaguelands"))
        self.assertEqual(lua.eval("GearRackDB.target.Elemental"), "Dissolvent")
        self.assertEqual(lua.eval("GearRackDB.when['form Stealth']"), "")
        self.assertEqual(values(lua, "GearRackDB.slots"), [16, 17, 18, 15, 7, 2])

    def test_a_form_key_waits_while_the_forms_are_not_known(self):
        lua = load(CLAUDE)  # GetNumShapeshiftForms() is 0
        self.assertEqual(lua.eval("GearRackDB.when['form Stealth']"), "")

    def test_without_classicapi_it_says_so(self):
        import wowkit
        from gr_env import MOCK, ROOT
        lua = wowkit.runtime()
        lua.execute(MOCK)
        lua.execute("CLASSIC_API_VERSION = nil")
        with self.assertRaises(Exception) as caught:
            wowkit.load_addon(lua, ROOT, "GearRack")
        self.assertIn("GearRack needs ClassicAPI", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
