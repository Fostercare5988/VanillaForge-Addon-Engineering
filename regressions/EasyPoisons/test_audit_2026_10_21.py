"""Reproductions for the 2026-10-21 EasyPoisons audit (chat audit, A to E).

Mocks only: whether the OctoWoW server accepts a purchase over one stack, how
many items a vendor purchase gives, and the real Dissolvent/Corrosive recipes
stay in-game checks.
"""
import unittest
from ep_env import load


class Buying(unittest.TestCase):
    def test_a1_big_order_is_split_into_one_stack_purchases(self):
        """A1: 70 Deathweed went out as one purchase; the stock vendor window caps one at a stack."""
        lua = load("poisonVendor()")
        lua.execute("openVendor(); setQty(POISON.Deadly, 10); buy(); settle()")
        self.assertEqual(lua.eval("bought(5173)"), 70)
        self.assertLessEqual(lua.eval("largestPurchase(5173)"), 20)

    def test_a2_second_click_before_delivery_buys_nothing(self):
        """A2: clicking Buy twice before the items arrived bought the order twice."""
        lua = load("poisonVendor()")
        lua.execute("openVendor(); setQty(POISON.Deadly, 2); buy(); buy()")
        self.assertEqual(lua.eval("bought(5173)"), 14)

    def test_lost_purchase_is_bought_again(self):
        """2026-10-21 in game: 80 Instant Poison VI gave 60 of 80 vials; a purchase in the burst was lost."""
        lua = load("poisonVendor(); bags[1] = { size = 16, family = 0, slots = {} }")
        lua.execute("drop[3] = true; openVendor(); setQty(POISON.Instant, 80); buy(); settle()")
        self.assertGreaterEqual(lua.eval("C_Item.GetItemCount(8925)"), 80)
        self.assertGreaterEqual(lua.eval("C_Item.GetItemCount(8924)"), 320)

    def test_purchases_go_out_one_at_a_time(self):
        """Each purchase waits until the previous one is in the bags."""
        lua = load("poisonVendor()")
        lua.execute("openVendor(); setQty(POISON.Deadly, 10); buy()")
        self.assertEqual(lua.eval("#purchases"), 1)

    def test_purchase_that_never_arrives_gives_up(self):
        """A vendor that refuses every purchase ends the order with a message."""
        lua = load("poisonVendor()")
        lua.execute("for i = 1, 50 do drop[i] = true end; openVendor(); setQty(POISON.Deadly, 1); buy(); settle(20)")
        self.assertLessEqual(lua.eval("#purchases"), 3)
        self.assertIn("did not sell", lua.eval("table.concat(messages, '\\n')"))

    def test_a2_order_frees_the_button_once_delivered(self):
        """A2: after delivery the plan is met and a stale timeout must not touch a newer order."""
        lua = load("poisonVendor()")
        lua.execute("openVendor(); setQty(POISON.Deadly, 1); buy(); settle()")
        self.assertIn("You have all the reagents.", lua.eval("allText()"))
        lua.execute("setQty(POISON.Deadly, 3); buy(); buy()")
        self.assertEqual(lua.eval("#purchases"), 3, "second click while buying adds nothing")
        lua.execute("settle()")
        self.assertEqual(lua.eval("bought(5173)"), 21)

    def test_a3_reagent_the_vendor_lacks_blocks_the_order(self):
        """A3: a reagent the vendor did not sell was priced 0 and silently skipped."""
        lua = load("for _, id in ipairs({8924, 8925, 8923, 5173}) do sells(id, 25) end")
        lua.execute("openVendor(); setQty(POISON.Dissolvent, 1); buy()")
        self.assertEqual(lua.eval("#purchases"), 0)
        self.assertIn("Maiden's Anguish", lua.eval("allText()"))

    def test_a3_no_purchase_or_success_message_away_from_a_vendor(self):
        """A3: /ep away from a vendor, then Buy, printed "Purchase complete!"."""
        lua = load("poisonVendor()")
        lua.execute('SlashCmdList.EASYPOISONS(""); advance(0); setQty(POISON.Deadly, 1); buy()')
        self.assertEqual(lua.eval("#purchases"), 0)
        self.assertNotIn("complete", lua.eval("table.concat(messages, '\\n')"))

    def test_a4_quiver_slots_are_not_bag_space(self):
        """A4: empty quiver slots counted as room for herbs and vials."""
        lua = load('''
            poisonVendor()
            for s = 1, 16 do bags[0].slots[s] = { id = 999, count = 1 } end
            bags[1] = { size = 16, family = 1, slots = {} }
        ''')
        lua.execute("openVendor(); setQty(POISON.Deadly, 1); buy()")
        self.assertEqual(lua.eval("#purchases"), 0)
        self.assertIn("Not enough bag space.", lua.eval("allText()"))

    def test_a8_limited_stock_blocks_the_order(self):
        """A8: a vendor with too few left was asked for more than it had."""
        lua = load("sells(8925, 25); sells(5173, 25, 1, 3)")
        lua.execute("openVendor(); setQty(POISON.Deadly, 1); buy()")
        self.assertEqual(lua.eval("#purchases"), 0)
        self.assertIn("too few Deathweed", lua.eval("allText()"))


class GameData(unittest.TestCase):
    def test_a5_item_8928_is_instant_poison_vi(self):
        """A5: octowow.st/db?item=8928 is Instant Poison VI, not IV."""
        lua = load("poisonVendor()")
        lua.execute("openVendor()")
        text = lua.eval("allText()")
        self.assertIn("Instant Poison VI", text)
        self.assertNotIn("Instant Poison IV", text)

    def test_c_purchase_size_comes_from_the_vendor(self):
        """C: vials were assumed to come in fives; the vendor reports one per purchase here."""
        lua = load("for _, id in ipairs({8924, 2931, 8925, 8923, 5173}) do sells(id, 25, 1) end")
        lua.execute("openVendor(); setQty(POISON.Deadly, 3); buy(); settle()")
        self.assertEqual(lua.eval("bought(8925)"), 3)

    def test_c_recipes_are_learned_from_the_poisons_window(self):
        """C: recipes read from the Poisons window replace the unverified defaults."""
        lua = load("poisonVendor()")
        lua.execute('''
            tradeskills = { { item = 47409, reagents = { {8924, 2}, {5173, 5}, {8925, 1} } } }
            fire("TRADE_SKILL_SHOW"); advance(0)
            openVendor(); setQty(POISON.Corrosive, 1); buy(); settle()
        ''')
        self.assertEqual(lua.eval("EasyPoisonsDB.Recipes[47409][5173]"), 5)
        self.assertEqual(lua.eval("bought(5173)"), 5)
        self.assertEqual(lua.eval("bought(8924)"), 2)


class Behaviour(unittest.TestCase):
    def test_a6_window_stays_closed_for_other_classes(self):
        """A6: a warrior at a herb vendor got the poison window."""
        lua = load('playerClass = "WARRIOR"; poisonVendor()')
        lua.execute("openVendor()")
        self.assertFalse(lua.eval("window() ~= nil and window():IsShown()"))

    def test_kept_window_opens_at_vendor_and_resets_on_close(self):
        """Kept: the window opens at a reagent vendor and leaving clears the plan."""
        lua = load("poisonVendor()")
        lua.execute("openVendor(); setQty(POISON.Deadly, 4)")
        self.assertTrue(lua.eval("window():IsShown()"))
        lua.execute("closeVendor(); openVendor(); buy()")
        self.assertEqual(lua.eval("#purchases"), 0)

    def test_d_hidden_window_skips_bag_work(self):
        """D: bag events while the window is closed must not walk the bags."""
        lua = load("poisonVendor()")
        lua.execute('openVendor(); closeVendor(); calls = {}; fire("BAG_UPDATE", 0); advance(0)')
        self.assertEqual(lua.eval("calls.bagRead or 0"), 0)


if __name__ == "__main__":
    unittest.main()
