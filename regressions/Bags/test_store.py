"""The record, the stored views of other characters, the tooltip counts (spec 4.5,
tests 12, 13 and 14). Bags 1.0, written new 2026-11-22.
"""
import unittest
from bags_env import load, frame

REALM = "BagsStore[\"Y'Shaarj\"]"
BANKS = ("BagsStore = { [\"Y'Shaarj\"] = {"
         " Bagholder = { money = 500, bags = { [0] = { size = 16, [1] = '8928,200', [2] = '16910:92:0:0' },"
         "   [1] = { size = 20, link = '51043' }, [-1] = { size = 24, [2] = '8928,40' } } },"
         " Zed = { money = 7, bags = { [0] = { size = 16 } } } },"
         " Other = { Faraway = { money = 9, bags = {} } } }")


def tip(lua, setup):
    lua.execute(f"GameTooltip:SetOwner(UIParent); {setup}")
    return lua.eval("table.concat(GameTooltip.lines, '|')")


class Record(unittest.TestCase):
    def test_logout_writes_the_bags_and_the_money(self):
        lua = load()
        lua.execute("fire('PLAYER_LOGOUT')")
        me = f"{REALM}.Claude"
        self.assertEqual(lua.eval(f"{me}.money"), 10000)
        self.assertEqual(lua.eval(f"{me}.bags[0].size"), 16)
        self.assertEqual(lua.eval(f"{me}.bags[0][1]"), "8928,10")
        self.assertEqual(lua.eval(f"{me}.bags[0][16]"), "10753")
        self.assertEqual(lua.eval(f"{me}.bags[1].link"), "51043")
        self.assertIsNone(lua.eval(f"{me}.bags[-1]"), "no bank visit")
        self.assertIsNone(lua.eval(f"{me}.bags[2]"), "no bag in the slot")

    def test_the_bank_is_written_at_a_banker_and_again_as_it_changes(self):
        lua = load()
        lua.execute("openBank()")
        me = f"{REALM}.Claude"
        self.assertEqual(lua.eval(f"{me}.bags[-1][24]"), "15138:2619:0:0")
        self.assertEqual(lua.eval(f"{me}.bags[5][3]"), "13209,2")
        lua.execute("put(5, 4, { id = 8928, count = 5 }); fire('BAG_UPDATE', 5); fire('BAG_UPDATE_DELAYED')")
        self.assertEqual(lua.eval(f"{me}.bags[5][4]"), "8928,5")

    def test_bag_events_away_from_the_bank_write_nothing(self):
        lua = load()
        lua.execute("ToggleBackpack(); put(0, 2, { id = 8928 }); fire('BAG_UPDATE', 0); fire('BAG_UPDATE_DELAYED')")
        self.assertIsNone(lua.eval(f"{REALM}.Claude"))

    def test_odd_records_read_safely(self):
        lua = load("BagsStore = { [\"Y'Shaarj\"] = { NoBank = { money = 1 }, NoSize = { bags = { [0] = { [1] = '8928' } } },"
                   " Suffix = { bags = { [0] = { size = 16, [3] = '19019:0:1200:0,1' } } } } }")
        for name in ("NoBank", "NoSize", "Suffix"):
            lua.execute(f"ToggleBackpack(); BagsInventory:Open(nil, '{name}'); click(BagsInventory.bankButton); BagsBank:Hide(); ToggleBackpack()")
        self.assertIsNone(lua.eval("luaErrors[1]"))
        lua.execute("ToggleBackpack(); BagsInventory:Open(nil, 'Suffix')")
        self.assertEqual(lua.eval("button('inventory', 0, 3).link"), "item:19019:0:1200:0")
        self.assertEqual(tip(lua, "GameTooltip:SetHyperlink('item:8928:0:0:0')"), "NoSize has 1 (Bags)")


class Characters(unittest.TestCase):
    def test_the_menu_only_with_two_or_more_on_this_realm(self):
        lua = load()
        lua.execute("ToggleBackpack()")
        self.assertFalse(lua.eval("BagsInventory.menu:IsShown()"))
        lua = load(BANKS)
        lua.execute("ToggleBackpack()")
        self.assertTrue(lua.eval("BagsInventory.menu:IsShown()"))
        entries = lua.eval("(function() local o = {} for _, e in ipairs(menuEntries(BagsInventory)) do"
                           " o[#o + 1] = e.text .. (e.picked and '*' or '') end return table.concat(o, ',') end)()")
        self.assertEqual(entries, "Claude*,Bagholder,Zed", "you first, no other realm")

    def test_choosing_one_shows_its_bags_read_only_with_its_money(self):
        lua = load(BANKS)
        lua.execute("ToggleBackpack(); menuEntries(BagsInventory)[2].pick()")
        self.assertEqual(lua.eval("BagsInventory.title:GetText()"), "Bagholder's Inventory")
        self.assertFalse(lua.eval("BagsInventory:Live()"))
        self.assertEqual(lua.eval("button('inventory', 0, 1).count"), 200)
        self.assertEqual(lua.eval("button('inventory', 0, 2).link"), "item:16910:92:0:0")
        self.assertEqual(lua.eval("shownButtons('inventory')"), 36)
        self.assertEqual(lua.eval("BagsInventoryMoney.shownMoney"), 500)
        lua.execute("forget(); click(button('inventory', 0, 1)); fire('BAG_UPDATE', 0); fire('BAG_UPDATE_DELAYED')")
        self.assertIsNone(lua.eval("calls.click"), "no moves")
        self.assertEqual(lua.eval("count('GetContainerItemInfo')"), 0)

    def test_shift_links_and_ctrl_tries_on_a_stored_item(self):
        lua = load(BANKS)
        lua.execute("items[16910] = { name = 'Sneaky Cloak', quality = 3, icon = 'c' }")
        lua.execute("ToggleBackpack(); BagsInventory:Open(nil, 'Bagholder'); ChatFrameEditBox:Show()")
        lua.execute("shift = 1; click(button('inventory', 0, 2)); shift = nil")
        self.assertEqual(lua.eval("calls.inserted"), "|cff0070dd|Hitem:16910:92:0:0|h[Sneaky Cloak]|h|r")
        lua.execute("ctrl = 1; click(button('inventory', 0, 2))")
        self.assertEqual(lua.eval("calls.dressUp"), "item:16910:92:0:0")

    def test_a_stored_item_shows_when_its_data_arrives(self):
        lua = load(BANKS)
        lua.execute("ToggleBackpack(); BagsInventory:Open(nil, 'Bagholder')")
        self.assertTrue(lua.eval("receives(BagsInventory, 'GET_ITEM_INFO_RECEIVED')"))
        lua.execute("items[16910] = { name = 'Sneaky Cloak', quality = 3, icon = 'c' }; fire('GET_ITEM_INFO_RECEIVED', 16910, true)")
        frame(lua)
        self.assertEqual(lua.eval("button('inventory', 0, 2).icon:GetTexture()"), "c")

    def test_forget_removes_it_and_returns_to_you(self):
        lua = load(BANKS)
        lua.execute("ToggleBackpack(); BagsInventory:Open(nil, 'Bagholder')")
        entries = lua.eval("menuEntries(BagsInventory)")
        self.assertEqual(entries[len(entries)].text, "Forget Bagholder")
        entries[len(entries)].pick()
        self.assertIsNone(lua.eval(f"{REALM}.Bagholder"))
        self.assertTrue(lua.eval("BagsInventory:Live()"))
        self.assertEqual(lua.eval("BagsInventory.title:GetText()"), "Claude's Inventory")

    def test_you_cannot_forget_yourself(self):
        lua = load(BANKS)
        lua.execute("ToggleBackpack()")
        self.assertNotIn("Forget", lua.eval("menuEntries(BagsInventory)[#menuEntries(BagsInventory)].text"))

    def test_another_characters_stored_bank(self):
        lua = load(BANKS)
        lua.execute("ToggleBackpack(); BagsInventory:Open(nil, 'Bagholder'); click(BagsInventory.bankButton)")
        self.assertEqual(lua.eval("BagsBank.title:GetText()"), "Bagholder's Bank")
        self.assertEqual(lua.eval("button('bank', -1, 2).count"), 40)


class Counts(unittest.TestCase):
    def test_other_characters_counts_in_the_old_wording(self):
        lua = load(BANKS)
        self.assertEqual(tip(lua, "GameTooltip:SetHyperlink('item:8928:0:0:0')"), "Bagholder has 200 (Bags) 40 (Bank)")
        self.assertEqual(tip(lua, "GameTooltip:SetHyperlink('item:16910:0:0:0')"), "Bagholder has 1 (Bags)")

    def test_your_own_bank_after_a_visit(self):
        lua = load()
        self.assertEqual(tip(lua, "GameTooltip:SetHyperlink('item:13209:0:0:0')"), "", "nothing with no bank visit")
        lua.execute("openBank(); closeBank()")
        self.assertEqual(tip(lua, "GameTooltip:SetHyperlink('item:13209:0:0:0')"), "Bank: 2")
        self.assertEqual(tip(lua, "GameTooltip:SetHyperlink('item:8928:0:0:0')"), "", "your bags are in front of you")

    def test_a_tooltip_set_twice_gets_its_lines_once(self):
        lua = load(BANKS)
        lines = tip(lua, "GameTooltip:SetHyperlink('item:8928:0:0:0'); run(GameTooltip, 'OnTooltipSetItem')")
        self.assertEqual(lines, "Bagholder has 200 (Bags) 40 (Bank)")
        lua.execute("GameTooltip:Hide()")
        self.assertEqual(tip(lua, "GameTooltip:SetHyperlink('item:8928:0:0:0')"), "Bagholder has 200 (Bags) 40 (Bank)")

    def test_the_item_reference_tooltip_too(self):
        lua = load(BANKS)
        lua.execute("ItemRefTooltip:SetOwner(UIParent); ItemRefTooltip:SetHyperlink('item:8928:0:0:0')")
        self.assertEqual(lua.eval("ItemRefTooltip.lines[1]"), "Bagholder has 200 (Bags) 40 (Bank)")


if __name__ == "__main__":
    unittest.main()
