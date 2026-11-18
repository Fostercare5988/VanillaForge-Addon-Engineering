"""A bar button (spec 4.5 test 3): icon, rarity edge, the slot's own texture
when empty, one slot redrawn per change, the cooldown, the key text, use and
link, and a tooltip filled again only while it counts."""
import unittest
from gr_env import load


class Buttons(unittest.TestCase):
    def test_icon_edge_and_empty_texture(self):
        lua = load()
        self.assertEqual(lua.eval("GearRackGear16Icon.texture"), "icon:The Ripper")
        self.assertEqual(lua.eval("GearRackGear16.edge.border[1]"), 0.3)  # rare
        lua.execute("worn[18] = nil fire('PLAYER_EQUIPMENT_CHANGED', 18)")
        self.assertEqual(lua.eval("GearRackGear18Icon.texture"), "slotTex:RangedSlot")
        self.assertEqual(lua.eval("GearRackGear18.edge.border[1]"), 0)

    def test_one_slot_is_redrawn_per_change(self):
        lua = load()
        lua.execute('GearRackGear16Icon.texture = "old" GearRackGear17Icon.texture = "old"')
        lua.execute("worn[16] = '0xD' fire('PLAYER_EQUIPMENT_CHANGED', 16, 1)")
        self.assertEqual(lua.eval("GearRackGear16Icon.texture"), "icon:Satyr Claw")
        self.assertEqual(lua.eval("GearRackGear17Icon.texture"), "old")

    def test_the_cooldown_is_set_and_cleared(self):
        lua = load()
        lua.execute("cooldowns['0x11'] = { 100, 120 } fire('BAG_UPDATE_COOLDOWN')")
        self.assertEqual(lua.eval("GearRackTrinket13.cooldown.cd"), "100+120")
        lua.execute("cooldowns['0x11'] = nil fire('BAG_UPDATE_COOLDOWN')")
        self.assertIsNone(lua.eval("GearRackTrinket13.cooldown.cd"))

    def test_the_trinket_keys_follow_the_bindings(self):
        lua = load(setup="keys.GEARRACK_USE_TOP_TRINKET_ITEM = 'ALT-1'")
        self.assertEqual(lua.eval("GearRackTrinket13HotKey.text"), "kALT-1")
        self.assertEqual(lua.eval("GearRackTrinket14HotKey.text"), "")
        lua.execute("keys.GEARRACK_USE_BOTTOM_TRINKET_ITEM = 'ALT-2' fire('UPDATE_BINDINGS')")
        self.assertEqual(lua.eval("GearRackTrinket14HotKey.text"), "kALT-2")

    def test_the_two_keys_use_the_trinkets(self):
        from pathlib import Path
        from gr_env import ROOT
        text = (Path(ROOT) / "Bindings.xml").read_text("utf-8")
        self.assertIn('name="GEARRACK_USE_TOP_TRINKET_ITEM" header="GEARRACK">UseInventoryItem(13)', text)
        self.assertIn('name="GEARRACK_USE_BOTTOM_TRINKET_ITEM">UseInventoryItem(14)', text)

    def test_click_uses_and_shift_click_links_only_with_the_edit_box(self):
        lua = load()
        lua.execute("click(GearRackTrinket14)")
        self.assertEqual(lua.eval("used[1]"), 14)
        lua.execute("press('lshift') click(GearRackGear16)")
        self.assertIsNone(lua.eval("inserted[1]"))
        lua.execute("ChatFrameEditBox:Show() click(GearRackGear16)")
        self.assertIn("[The Ripper]", lua.eval("inserted[1]"))
        self.assertIsNone(lua.eval("used[2]"))

    def test_the_tooltip_refills_only_while_it_counts(self):
        lua = load()
        lua.execute("hover(GearRackGear16)")
        self.assertEqual(lua.eval("tickers()"), 0)
        lua.execute("leave(GearRackGear16) cooldowns['0x11'] = { 100, 120 } hover(GearRackTrinket13)")
        self.assertEqual(lua.eval("tickers()"), 1)
        fills = lua.eval("tipFills")
        lua.execute("step(1)")
        self.assertEqual(lua.eval("tipFills"), fills + 1)
        lua.execute("leave(GearRackTrinket13)")
        self.assertEqual(lua.eval("tickers()"), 0)

    def test_the_sets_button_shows_the_worn_set(self):
        lua = load(setup='makeSet("Weapons", "INV_W", { [16] = "0xA", [17] = "0xB" })'
                         ' makeSet("Other", "INV_O", { [16] = "0xD", [17] = "ignored" })')
        for s in range(1, 20):
            if s not in (16, 17):
                lua.execute(f'sets[1].slots[{s}] = "ignored" sets[2].slots[{s}] = "ignored"')
        lua.execute("fire('EQUIPMENT_SETS_CHANGED') step(0)")
        self.assertEqual(lua.eval("GearRackSetsIcon.texture"), "Interface\\Icons\\INV_W")
        lua.execute("C_Item.EquipItemByName('0xD', 16) step(0)")
        self.assertEqual(lua.eval("GearRackSetsIcon.texture"), "Interface\\Icons\\INV_O")


if __name__ == "__main__":
    unittest.main()
