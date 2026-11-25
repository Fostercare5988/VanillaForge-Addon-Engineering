"""The three pages (spec 4.5 test 2): every row, Defaults, /gr, the bar
dropdowns act at once, the K14 rows grey while the switch is off, and the
rows follow the class."""
import unittest
from gr_env import load

SETS = 'makeSet("PVE", "INV_A", {}) makeSet("Instant", "INV_B", {})'


def names(lua, page):
    rows = lua.eval(f'settingsWindow.find("{page}").layout.rows')
    return [rows[i].data.name for i in range(1, len(rows) + 1)]


class Pages(unittest.TestCase):
    def test_the_gearrack_page(self):
        lua = load()
        self.assertEqual(names(lua, "GearRack"), ["Bars", "Gear bar", "Trinket bar", "Key 41", "Key 42", "Key 43",
                                                  "Alerts", "Ready alert", "Windows", "Gear sets", "Trinkets",
                                                  "Minimap buttons"])

    def test_slash_gr_opens_the_page_and_the_buttons_open_the_windows(self):
        lua = load()
        lua.execute("SlashCmdList.GEARRACK('')")
        self.assertEqual(lua.eval("settingsWindow.opened.name"), "GearRack")
        lua.execute('settingsWindow.click(settingsWindow.row(settingsWindow.find("GearRack"), "Gear sets"))')
        self.assertTrue(lua.eval("GearRackSetsWindow:IsVisible()"))
        lua.execute('settingsWindow.click(settingsWindow.row(settingsWindow.find("GearRack"), "Trinkets"))')
        self.assertTrue(lua.eval("GearRackTrinkets:IsVisible()"))
        lua.execute("SlashCmdList.GEARRACK('sets') SlashCmdList.GEARRACK('trinkets')")
        self.assertFalse(lua.eval("GearRackSetsWindow:IsShown()"))
        self.assertFalse(lua.eval("GearRackTrinkets:IsShown()"))

    def test_the_minimap_switch_hides_and_shows_both_buttons(self):
        lua = load()
        self.assertTrue(lua.eval("GearRackMinimapGear:IsShown() and GearRackMinimapTrinkets:IsShown()"))
        lua.execute('settingsWindow.use("GearRack_minimap", false)')
        self.assertFalse(lua.eval("GearRackMinimapGear:IsShown() or GearRackMinimapTrinkets:IsShown()"))
        lua.execute("settingsWindow.defaults()")
        self.assertTrue(lua.eval("GearRackMinimapGear:IsShown()"))

    def test_a_bar_dropdown_acts_at_once(self):
        lua = load()
        lua.execute('settingsWindow.use("GearRack_gearBar", "DOWN")')
        self.assertEqual(lua.eval("GearRackGearBar:GetWidth()"), 36)
        self.assertEqual(lua.eval("GearRackGearBar:GetHeight()"), 5 * 40 - 4)
        lua.execute('settingsWindow.use("GearRack_trinketBar", "OFF")')
        self.assertFalse(lua.eval("GearRackTrinketBar:IsShown()"))
        lua.execute('settingsWindow.use("GearRack_trinketBar", "ACROSS")')
        self.assertTrue(lua.eval("GearRackTrinketBar:IsShown()"))
        self.assertEqual(lua.eval("GearRackTrinketBar:GetWidth()"), 2 * 40 - 4)

    def test_defaults_puts_every_row_back(self):
        lua = load(setup=SETS)
        lua.execute('''settingsWindow.use("GearRack_gearBar", "OFF") settingsWindow.use("GearRack_readyAlert", false)
            settingsWindow.use("GearRack_auto", true) settingsWindow.use("GearRack_when_mounted", "PVE")
            settingsWindow.use("GearRack_target_Undead", "Instant")''')
        lua.execute("settingsWindow.defaults()")
        self.assertEqual(lua.eval("GearRackDB.gearBar"), "ACROSS")
        self.assertTrue(lua.eval("GearRackGearBar:IsShown()"))
        self.assertTrue(lua.eval("GearRackDB.readyAlert"))
        self.assertFalse(lua.eval("GearRackDB.auto"))
        self.assertEqual(lua.eval("GearRackDB.when.mounted"), "")
        self.assertEqual(lua.eval("GearRackDB.target.Undead"), "")

    def test_a_set_dropdown_lists_off_and_the_sets_by_name(self):
        lua = load(setup=SETS)
        lua.execute('row = settingsWindow.row(settingsWindow.find("Sets by target"), "Undead")')
        choices = lua.eval("settingsWindow.choices(row)")
        self.assertEqual([choices[i].label for i in range(1, len(choices) + 1)], ["Off", "Instant", "PVE"])
        lua.execute('GearRackDB.target.Undead = "Gone"')
        choices = lua.eval("settingsWindow.choices(row)")
        self.assertEqual(choices[len(choices)].label, "Gone (deleted)")

    def test_the_situation_rows_grey_while_the_switch_is_off(self):
        lua = load(setup=SETS)
        lua.execute('auto = settingsWindow.find("Automatic sets") target = settingsWindow.find("Sets by target")')
        self.assertFalse(lua.eval('settingsWindow.enabled(settingsWindow.row(auto, "Mounted"))'))
        self.assertFalse(lua.eval('settingsWindow.enabled(settingsWindow.row(target, "Beast"))'))
        lua.execute('settingsWindow.use("GearRack_auto", true)')
        self.assertTrue(lua.eval('settingsWindow.enabled(settingsWindow.row(auto, "Mounted"))'))
        self.assertFalse(lua.eval('settingsWindow.enabled(settingsWindow.row(target, "Beast"))'),
                         "Sets by target has its own switch, at the top of its page")
        self.assertEqual(names(lua, "Sets by target")[0], "Sets by target")
        lua.execute('settingsWindow.use("GearRack_byTarget", true)')
        self.assertTrue(lua.eval('settingsWindow.enabled(settingsWindow.row(target, "Any other enemy"))'))

    def test_a_rogue_sees_stealth_and_no_mana_row(self):
        lua = load(setup='player.forms = { "Stealth" }')
        self.assertEqual(names(lua, "Automatic sets"), ["Automatic sets", "While", "Mounted", "Under water",
                                                        "Stealth", "Eating or drinking", "Where", "City or inn",
                                                        "Battleground", "Raid", "Dungeon"])

    def test_a_mage_sees_evocation_and_low_on_mana(self):
        lua = load(setup='player.class = "MAGE" player.power = 0 player.maxMana = 100')
        rows = names(lua, "Automatic sets")
        self.assertIn("Evocation", rows)
        self.assertIn("Low on mana", rows)
        self.assertNotIn("Spirit Tap", rows)

    def test_a_warrior_sees_three_stances(self):
        lua = load(setup='player.class = "WARRIOR" player.power = 1 '
                         'player.forms = { "Battle Stance", "Defensive Stance", "Berserker Stance" }')
        rows = names(lua, "Automatic sets")
        self.assertEqual(rows[4:7], ["Battle Stance", "Defensive Stance", "Berserker Stance"])
        self.assertNotIn("Low on mana", rows)

    def test_sets_by_target_has_its_switch_and_the_nine_types(self):
        lua = load()
        self.assertEqual(names(lua, "Sets by target"), ["Sets by target", "Beast", "Demon", "Dragonkin", "Elemental", "Giant",
                                                        "Humanoid", "Mechanical", "Undead", "Any other enemy"])


if __name__ == "__main__":
    unittest.main()
