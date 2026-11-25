"""The poison on each weapon (after the third play, 2026-11-18): its icon and
time or charges on the bar and in menus, the time counted down by a
ClassicAPI text binding (review, 2026-11-25: no timer of ours), and a poison
in hand applied by clicking the weapon on the bar."""
import unittest
from gr_env import load

# Instant Poison (enchant 625, icon from its spell) on the main hand, 28 min left.
POISONED = 'poisons["0xA"] = { ["until"] = now + 28 * 60 - 10, charges = 60, enchant = 625 }'


class Poison(unittest.TestCase):
    def test_the_weapon_shows_its_poison_and_time(self):
        lua = load(setup=POISONED)
        self.assertTrue(lua.eval("GearRackGear16.poison:IsShown()"))
        self.assertEqual(lua.eval("GearRackGear16.poison.icon.texture"), "Interface\Icons\Ability_Poisons")
        self.assertEqual(lua.eval("clock(GearRackGear16.poison.text)"), "28m")
        self.assertIsNone(lua.eval("GearRackGear17.poison"), "the off hand has none")

    def test_the_time_counts_down_with_no_timer_of_ours(self):
        lua = load(setup=POISONED)
        self.assertEqual(lua.eval("timerCount()"), 0, "the /lag cost of 2026-11-25: one timer per label change")
        lua.execute("step(49)")
        self.assertEqual(lua.eval("clock(GearRackGear16.poison.text)"), "28m")
        lua.execute("step(1.1)")
        self.assertEqual(lua.eval("clock(GearRackGear16.poison.text)"), "27m")
        lua.execute("step(1519)")
        self.assertEqual(lua.eval("clock(GearRackGear16.poison.text)"), "|cffff3333%dm|r" % 2, "red under two minutes")
        lua.execute("step(56)")
        self.assertEqual(lua.eval("clock(GearRackGear16.poison.text)"), "|cffff3333%ds|r" % 45)
        self.assertEqual(lua.eval("timerCount()"), 0)

    def test_few_charges_show_the_charges(self):
        lua = load(setup=POISONED)
        lua.execute('poisons["0xA"].charges = 4 fire("WEAPON_ENCHANT_CHANGED")')
        self.assertEqual(lua.eval("clock(GearRackGear16.poison.text)"), "4c")
        lua.execute('poisons["0xA"] = nil fire("WEAPON_ENCHANT_CHANGED")')
        self.assertFalse(lua.eval("GearRackGear16.poison:IsShown()"))
        self.assertEqual(lua.eval("timerCount()"), 0, "no poison, no timer")

    def test_an_enchant_with_no_spell_icon_gets_the_poison_icon(self):
        lua = load(setup='poisons["0xB"] = { ["until"] = now + 600, charges = 0, enchant = 2640 }')
        self.assertEqual(lua.eval("GearRackGear17.poison.icon.texture"), "Interface\Icons\Ability_Poisons")

    def test_crippling_poison_shows_the_classic_purple_sting(self):
        lua = load(setup='poisons["0xB"] = { ["until"] = now + 600, charges = 0, enchant = 603 }'
                   ' local get = C_Item.GetEnchantInfo function C_Item.GetEnchantInfo(id)'
                   ' if id == 603 then return { enchantID = 603, name = "Crippling Poison II", spellID = 11202 } end'
                   ' return get(id) end')
        self.assertEqual(lua.eval("GearRackGear17.poison.icon.texture"), "Interface\\Icons\\Ability_PoisonSting")

    def test_a_bag_weapon_in_the_menu_shows_its_poison(self):
        lua = load(setup='poisons["0xD"] = { ["until"] = now + 3000, charges = 30, enchant = 625 }')
        lua.execute("hover(GearRackGear16)")
        lua.execute("b = nil for i = 1, 10 do local m = menuButton(i) if m and m.entry.guid == '0xD' then b = m end end")
        self.assertTrue(lua.eval("b.poison:IsShown()"))
        self.assertEqual(lua.eval("clock(b.poison.text)"), "50m")
        lua.execute("leave(GearRackGear16)")
        self.assertFalse(lua.eval("bindings[b.poison.text].on"), "a closed menu's time stops counting")

    def test_a_poison_in_hand_is_applied_by_clicking_the_weapon(self):
        lua = load()
        lua.execute("targeting = true click(GearRackGear17)")
        self.assertEqual(lua.eval("cursor"), "0xB", "the stock pickup applies the poison to that slot")
        self.assertIsNone(lua.eval("used[1]"), "the weapon is not used")
        lua.execute("cursor = nil worn[17] = '0xB' targeting = false click(GearRackGear17)")
        self.assertEqual(lua.eval("used[1]"), 17)


if __name__ == "__main__":
    unittest.main()
