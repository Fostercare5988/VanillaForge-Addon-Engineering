"""The window's controls: free space, search, sort, the bag bar, money (spec 4.5,
tests 7, 8, 9, 15 and 16). Bags 1.0, written new 2026-11-22.
"""
import unittest
from bags_env import load, frame

OTHERS = ("BagsStore = { [\"Y'Shaarj\"] = { Bagholder = { money = 500, bags = { [0] = { size = 16, [1] = '8928,200' },"
          " [-1] = { size = 24, [2] = '8928,40' } } } } }")


def opened(saved=None, setup=""):
    lua = load(saved, setup)
    lua.execute("ToggleBackpack()")
    return lua


class FreeSpace(unittest.TestCase):
    def test_the_count_and_each_bag_in_the_tooltip(self):
        lua = opened(setup="for s = 1, 20 do put(1, s, { id = 8928 }) end; for s = 3, 16 do put(0, s, { id = 8928 }) end")
        self.assertEqual(lua.eval("BagsInventory.free:GetText()"), "1 / 36 Free")
        lua.execute("run(BagsInventory.free:GetParent(), 'OnEnter')")
        lines = lua.eval("table.concat(GameTooltip.lines, '|')")
        self.assertEqual(lines, "Free space|Backpack=1 / 16|Bag 1=0 / 20")
        self.assertEqual(lua.eval("GameTooltip.colors['Bag 1'][2]"), 0.1, "full: red")
        self.assertEqual(lua.eval("GameTooltip.colors['Backpack'][2]"), 0.82, "two or fewer: yellow")

    def test_the_bank_counts_only_while_open_and_a_stored_view_its_stored_slots(self):
        lua = load()
        lua.execute("openBank()")
        self.assertEqual(lua.eval("BagsBank.free:GetText()"), "38 / 40 Free")
        lua.execute("closeBank(); ToggleBackpack(); click(BagsInventory.bankButton)")
        self.assertEqual(lua.eval("BagsBank.free:GetText()"), "38 / 40 Free")


class Search(unittest.TestCase):
    def test_typing_sets_the_search_and_dims_what_does_not_match(self):
        lua = opened()
        lua.execute("bags[0].slots[16].filtered = true; BagsInventory.search:SetText('poison')")
        self.assertEqual(lua.eval("search"), "poison")
        frame(lua)
        self.assertTrue(lua.eval("button('inventory', 0, 16).icon.desaturated"))
        self.assertEqual(lua.eval("button('inventory', 0, 16).edge.alpha"), 0.25)
        self.assertIsNone(lua.eval("button('inventory', 0, 1).icon.desaturated"))

    def test_one_search_for_both_windows(self):
        lua = load()
        lua.execute("openBank(); BagsInventory.search:SetText('cloak')")
        self.assertEqual(lua.eval("BagsBank.search:GetText()"), "cloak")

    def test_escape_and_closing_clear_it(self):
        lua = opened()
        lua.execute("BagsInventory.search:SetText('poison'); run(BagsInventory.search, 'OnEscapePressed')")
        self.assertEqual(lua.eval("search"), "")
        lua.execute("BagsInventory.search:SetText('poison'); ToggleBackpack()")
        self.assertEqual(lua.eval("search"), "")

    def test_a_search_left_from_a_reload_is_cleared_at_login(self):
        lua = load(setup="search = 'left over'")
        self.assertEqual(lua.eval("search"), "")

    def test_a_stored_view_cannot_be_searched(self):
        lua = load(OTHERS)
        lua.execute("ToggleBackpack(); BagsInventory:Open(nil, 'Bagholder')")
        self.assertFalse(lua.eval("BagsInventory.search:IsMouseEnabled()"))
        self.assertFalse(lua.eval("receives(BagsInventory, 'INVENTORY_SEARCH_UPDATE')"))


class Sort(unittest.TestCase):
    def test_a_click_sorts_the_bags_and_at_a_banker_the_bank(self):
        lua = load()
        lua.execute("ToggleBackpack(); click(BagsInventory.sort)")
        self.assertEqual(lua.eval("count('SortBags')"), 1)
        lua.execute("openBank(); click(BagsBank.sort)")
        self.assertEqual(lua.eval("count('SortBankBags')"), 1)

    def test_a_right_click_flips_the_direction(self):
        lua = opened()
        lua.execute("click(BagsInventory.sort, 'RightButton')")
        self.assertTrue(lua.eval("rightToLeft"))
        self.assertEqual(lua.eval("count('SortBags')"), 0)
        lua.execute("click(BagsInventory.sort, 'RightButton')")
        self.assertFalse(lua.eval("rightToLeft"))

    def test_disabled_in_a_stored_view_and_for_the_bank_away_from_a_banker(self):
        lua = load(OTHERS)
        lua.execute("ToggleBackpack(); BagsInventory:Open(nil, 'Bagholder')")
        self.assertFalse(lua.eval("BagsInventory.sort:IsEnabled()"))
        lua.execute("BagsInventory:Open(nil, 'Claude')")
        self.assertTrue(lua.eval("BagsInventory.sort:IsEnabled()"))


class BagBar(unittest.TestCase):
    def test_keys_show_on_shift_click_or_the_key_button_and_are_no_free_space(self):
        lua = opened(setup="bags[-2] = { size = 4, slots = {} }; put(-2, 1, { id = 8928 })")
        self.assertEqual(lua.eval("BagsInventory.free:GetText()"), "32 / 36 Free")
        self.assertEqual(lua.eval("BagsInventory.holders[-2].size"), 0, "hidden on a first login")
        lua.execute("shift = true; click(BagsInventory.barButton); shift = nil")
        self.assertTrue(lua.eval("BagsDB.keys"))
        self.assertFalse(lua.eval("BagsDB.bagBar.inventory"), "the shift-click leaves the bag icons alone")
        self.assertEqual(lua.eval("BagsInventory.holders[-2].size"), 4)
        self.assertEqual(lua.eval("BagsInventory.free:GetText()"), "32 / 36 Free", "keys are not space")
        lua.execute("ToggleKeyRing()")
        self.assertEqual(lua.eval("BagsInventory.holders[-2].size"), 0)
        self.assertTrue(lua.eval("BagsInventory:IsShown()"))

    def test_the_toggle_is_kept_per_window(self):
        lua = opened()
        self.assertIsNone(lua.eval("BagsInventory.bar"), "hidden on a first login, made on first need")
        lua.execute("click(BagsInventory.barButton)")
        self.assertTrue(lua.eval("BagsDB.bagBar.inventory"))
        self.assertTrue(lua.eval("BagsInventory.bar:IsShown()"))
        self.assertEqual(lua.eval("(select(5, button('inventory', 0, 1):GetPoint(1)))"), -64)
        self.assertTrue(lua.eval("BagsDB.bagBar.bank"))

    def test_icons_put_and_take_bags_and_light_up_their_slots(self):
        lua = opened("BagsDB = { bagBar = { inventory = true, bank = true } }")
        icon = "BagsInventory.icons[1]"
        self.assertEqual(lua.eval(f"{icon}:GetID()"), 1)
        self.assertEqual(lua.eval(f"{icon}.texture:GetTexture()"), "Interface\\Icons\\INV_Misc_Bag_08")
        self.assertEqual(lua.eval("BagsInventory.icons[2].texture:GetTexture()"), "Interface\\PaperDoll\\UI-PaperDoll-Slot-Bag")
        lua.execute(f"click({icon}); run({icon}, 'OnDragStart')")
        self.assertEqual(lua.eval("calls.PutItemInBag"), 20)
        self.assertEqual(lua.eval("calls.PickupBagFromSlot"), 20)
        lua.execute(f"enter({icon})")
        self.assertTrue(lua.eval("button('inventory', 1, 20).highlit"))
        lua.execute(f"run({icon}, 'OnLeave')")
        self.assertIsNone(lua.eval("button('inventory', 1, 20).highlit"))

    def test_the_bank_slot_purchase_uses_the_stock_dialog(self):
        lua = load()
        lua.execute("openBank()")
        self.assertTrue(lua.eval("BagsBank.buy:IsShown()"))
        self.assertEqual(lua.eval("BagsBank.icons[3].texture.color[2]"), 0.1, "a slot not bought is red")
        lua.execute("click(BagsBank.buy)")
        self.assertEqual(lua.eval("BankFrame.nextSlotCost"), 3000)
        self.assertEqual(lua.eval("calls.popup"), "CONFIRM_BUY_BANK_SLOT")
        lua.execute("bankFull = 1; bankSlots = 6; fire('PLAYERBANKBAGSLOTS_CHANGED')")
        frame(lua)
        self.assertFalse(lua.eval("BagsBank.buy:IsShown()"))


class Money(unittest.TestCase):
    def test_the_live_money_can_be_picked_up_a_stored_one_cannot(self):
        lua = load(OTHERS)
        lua.execute("ToggleBackpack()")
        self.assertEqual(lua.eval("BagsInventoryMoney.shownMoney"), 10000)
        self.assertEqual(lua.eval("BagsInventoryMoney.moneyType"), "PLAYER")
        lua.execute("BagsInventory:Open(nil, 'Bagholder')")
        self.assertEqual(lua.eval("BagsInventoryMoney.shownMoney"), 500)
        self.assertEqual(lua.eval("BagsInventoryMoney.moneyType"), "STATIC")

    def test_the_realm_total_only_with_two_characters(self):
        lua = opened()
        lua.execute("run(BagsInventoryMoney, 'OnEnter')")
        self.assertIsNone(lua.eval("GameTooltip.money"))
        lua = opened(OTHERS)
        lua.execute("run(BagsInventoryMoneyGoldButton, 'OnEnter')")
        self.assertEqual(lua.eval("GameTooltip.money"), 10500)


if __name__ == "__main__":
    unittest.main()
