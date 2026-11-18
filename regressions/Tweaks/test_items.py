"""Items (spec T1-T4, 4.7 "Tweaks"): the sell price times the stack, once,
also where there is no GUID (loot, quests, auctions); Shift compares a frame
later and a hidden tooltip cancels; borders per quality on the character slots
while they show and on inspect (the inspected unit); none on bags and bank,
which Bagnon draws (review 2026-11-18); Sell Junk calls SellAllJunkItems and
is hidden with no junk.
"""
import unittest
from ftr_env import load

ITEMS = "items[10] = { price = 25, quality = 1 }; items[20] = { price = 1000, quality = 4 }; items[30] = { quality = 0 }"


def items():
    lua = load(setup=ITEMS)
    return lua


class Prices(unittest.TestCase):
    def test_a_bag_stack_is_priced_by_its_guid(self):
        lua = items()
        lua.execute("stacks.g1 = 13; showItem(GameTooltip, 10, 'g1')")
        self.assertEqual(lua.eval("GameTooltip.money"), 25 * 13)
        self.assertEqual(lua.eval("count('SetTooltipMoney')"), 1)

    def test_a_link_without_guid_is_one_item(self):
        lua = items()
        lua.execute("showItem(ItemRefTooltip, 20)")
        self.assertEqual(lua.eval("ItemRefTooltip.money"), 1000)

    def test_no_price_for_an_item_the_vendor_does_not_buy(self):
        lua = items()
        lua.execute("showItem(GameTooltip, 30)")
        self.assertIsNone(lua.eval("GameTooltip.money"))

    def test_at_a_merchant_the_game_prices_your_own_items(self):
        lua = items()
        lua.execute("MerchantFrame:Show(); stacks.g1 = 2; showItem(GameTooltip, 10, 'g1')")
        self.assertIsNone(lua.eval("GameTooltip.money"))

    def test_an_auction_counts_its_stack(self):
        lua = items()
        lua.execute("auctions[1] = { id = 10, count = 20 }; GameTooltip:SetAuctionItem('list', 1)")
        self.assertEqual(lua.eval("GameTooltip.money"), 500)
        self.assertEqual(lua.eval("count('SetTooltipMoney')"), 1, "one money line")

    def test_a_loot_stack_and_a_quest_reward_count_too(self):
        # Review 2026-11-18: 1.0 priced one item of a looted stack, 1.22 the stack.
        lua = items()
        lua.execute("loot[1] = { id = 10, count = 12 }; GameTooltip:SetLootItem(1)")
        self.assertEqual(lua.eval("GameTooltip.money"), 25 * 12)
        lua.execute("quests.choice[2] = { id = 20, count = 3 }; GameTooltip:SetQuestLogItem('choice', 2)")
        self.assertEqual(lua.eval("GameTooltip.money"), 3000)
        lua.execute("quests.reward[1] = { id = 10, count = 1 }; GameTooltip:SetQuestLogItem('reward', 1)")
        self.assertEqual(lua.eval("GameTooltip.money"), 25)


class Compare(unittest.TestCase):
    def test_shift_compares_a_frame_later(self):
        lua = items()
        lua.execute("shift = true; showItem(GameTooltip, 20)")
        self.assertEqual(lua.eval("count('compare')"), 0, "not inside OnTooltipSetItem")
        lua.execute("step(0)")
        self.assertEqual(lua.eval("last('compare')"), "GameTooltip")

    def test_a_hidden_tooltip_cancels(self):
        lua = items()
        lua.execute("shift = true; showItem(GameTooltip, 20); GameTooltip:Hide(); step(0)")
        self.assertEqual(lua.eval("count('compare')"), 0)

    def test_without_shift_nothing(self):
        lua = items()
        lua.execute("showItem(GameTooltip, 20); step(0)")
        self.assertEqual(lua.eval("count('compare')"), 0)

    def test_pressing_shift_compares_the_hovered_tooltip_and_letting_go_hides(self):
        lua = items()
        lua.execute("showItem(ItemRefTooltip, 10); showItem(GameTooltip, 20); press(true, false); step(0)")
        self.assertEqual(lua.eval("last('compare')"), "GameTooltip")
        lua.execute("press(false, false)")
        self.assertFalse(lua.eval("ShoppingTooltip1:IsShown()"))

    def test_an_open_link_under_the_cursor_wins(self):
        lua = items()
        lua.execute("showItem(ItemRefTooltip, 10); showItem(GameTooltip, 20); ItemRefTooltip.hovered = true;"
                    "press(true, false); step(0)")
        self.assertEqual(lua.eval("last('compare')"), "ItemRefTooltip")


class Borders(unittest.TestCase):
    def test_character_slots_while_they_show(self):
        lua = items()
        lua.execute("PaperDollFrame:Show(); worn[1] = 20; this = slotButton('CharacterHeadSlot', 1);"
                    "PaperDollItemSlotButton_Update()")
        self.assertEqual(lua.eval("borderOf(CharacterHeadSlot)[1]"), 0.4)
        lua.execute("this = slotButton('CharacterNeckSlot', 2); PaperDollItemSlotButton_Update()")
        self.assertEqual(lua.eval("borderOf(CharacterNeckSlot)[1]"), 0.5, "empty: grey")

    def test_a_closed_window_is_drawn_when_it_opens(self):
        # Review 2026-11-18: the game redraws every slot at each gear change, the
        # window closed too; 1.0 read each slot's item link then.
        lua = items()
        lua.execute("worn[1] = 20; this = slotButton('CharacterHeadSlot', 1); PaperDollItemSlotButton_Update()")
        self.assertIsNone(lua.eval("CharacterHeadSlot.ftBorder"))
        lua.execute("PaperDollFrame:Show()")
        self.assertEqual(lua.eval("borderOf(CharacterHeadSlot)[1]"), 0.4)

    def test_a_border_is_written_only_when_the_quality_changes(self):
        lua = items()
        lua.execute("PaperDollFrame:Show(); worn[1] = 20; this = slotButton('CharacterHeadSlot', 1);"
                    "PaperDollItemSlotButton_Update(); CharacterHeadSlot.ftBorder.border = nil;"
                    "PaperDollItemSlotButton_Update()")
        self.assertIsNone(lua.eval("borderOf(CharacterHeadSlot)"))

    def test_inspect_reads_the_inspected_member_and_waits_for_items(self):
        lua = items()
        lua.execute("loadInspect(); InspectFrame:Show(); inspectWorn[1] = 99;"
                    "InspectPaperDollItemSlotButton_Update(slotButton('InspectHeadSlot', 1))")
        self.assertEqual(lua.eval("borderOf(InspectHeadSlot)[1]"), 0.5, "not cached yet")
        lua.execute("items[99] = { quality = 3 }; fire('GET_ITEM_INFO_RECEIVED', 99)")
        self.assertEqual(lua.eval("borderOf(InspectHeadSlot)[1]"), 0.3)
        lua.execute("InspectFrame:Hide()")
        self.assertNotIn("GET_ITEM_INFO_RECEIVED", lua.eval("listening()"))


class SellJunk(unittest.TestCase):
    def junk(self):
        lua = items()
        lua.execute("button = nil; for _, w in ipairs(widgets) do if w.parent == MerchantFrame and w.kind == 'Button' "
                    "then button = w end end")
        return lua

    def test_shown_with_junk_and_sells_once(self):
        lua = self.junk()
        lua.execute("junkCount = 3; MerchantFrame:Show(); MerchantFrame_Update()")
        self.assertTrue(lua.eval("button:IsShown()"))
        lua.execute("run(button, 'OnClick')")
        self.assertEqual(lua.eval("count('SellAllJunkItems')"), 1)
        lua.execute("junkCount = 0; fire('BAG_UPDATE_DELAYED')")
        self.assertFalse(lua.eval("button:IsShown()"))

    def test_hidden_with_no_junk_and_on_the_buyback_tab(self):
        lua = self.junk()
        lua.execute("MerchantFrame:Show(); MerchantFrame_Update()")
        self.assertFalse(lua.eval("button:IsShown()"))
        lua.execute("junkCount = 2; MerchantFrame.selectedTab = 2; MerchantFrame_Update()")
        self.assertFalse(lua.eval("button:IsShown()"))

    def test_bag_updates_only_while_the_merchant_is_open(self):
        lua = self.junk()
        lua.execute("MerchantFrame:Show()")
        self.assertIn("BAG_UPDATE_DELAYED", lua.eval("listening()"))
        lua.execute("MerchantFrame:Hide()")
        self.assertNotIn("BAG_UPDATE_DELAYED", lua.eval("listening()"))


if __name__ == "__main__":
    unittest.main()
