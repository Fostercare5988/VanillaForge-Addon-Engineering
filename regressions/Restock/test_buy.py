"""Buying at a vendor (spec K1-K5, tests 3 to 7): the plan pools the reagents over the
poisons below target and takes off what is carried; a poison whose reagents the vendor does
not all sell is skipped; room, money and stock are checked before anything is bought; one
purchase at a time, at most one stack, the plan made again from the bags after each; a
lost purchase is sent again, three in a row stop; Flash Powder is a target in the same
queue. First login: empty bags, a vendor that sells nothing for us, a rogue who has not
opened the Poisons window yet.
"""
import unittest
from rs_env import load, CLAUDE

DUST, ANGUISH, VIAL, ESSENCE, DEATHWEED, FLASH = 8924, 2931, 8925, 8923, 5173, 5140


def claude(setup="poisonVendor(); sells(5140)", saved=CLAUDE):
    return load(saved, setup)


class Plan(unittest.TestCase):
    def test_claudes_order_is_pooled_bought_and_named_in_one_line(self):
        lua = claude()
        lua.execute("openVendor()")
        self.assertEqual(lua.eval("#chat"), 1)
        self.assertEqual(lua.eval("said()"), "|cffff9e38Restock:|r buying 80 Dust A, 50 Vial, 30 Essence, 100 Deathweed,"
                         " 20 Flash Powder (70s).")
        lua.execute("finish()")
        for item, n in ((DUST, 80), (VIAL, 50), (ESSENCE, 30), (DEATHWEED, 100), (FLASH, 20), (ANGUISH, 0)):
            self.assertEqual(lua.eval(f"bought({item})"), n, item)
        self.assertEqual(lua.eval("#chat"), 1)
        self.assertEqual(lua.eval("largest()"), 20)

    def test_what_is_carried_is_taken_off(self):
        # 3 Instant Poisons carried: 17 to make. 30 Dust and 5 Vials in the bags.
        lua = claude()
        lua.execute("put(0, 1, 8928, 3); put(0, 2, 8924, 30); put(0, 3, 8925, 5); put(0, 4, 5140, 20)")
        lua.execute("openVendor(); finish()")
        self.assertEqual(lua.eval("bought(8924)"), 17 * 4 - 30)
        self.assertEqual(lua.eval("bought(8925)"), 17 + 10 + 20 - 5)
        self.assertEqual(lua.eval("bought(5140)"), 0)

    def test_a_poison_is_bought_for_only_where_all_its_reagents_are_sold(self):
        lua = claude("sells(8924); sells(8925)")  # Dust and Vials: Instant only
        lua.execute("openVendor(); finish()")
        self.assertEqual(lua.eval("bought(8924)"), 80)
        self.assertEqual(lua.eval("bought(8925)"), 20)

    def test_vials_alone_buy_nothing_and_say_nothing(self):
        lua = claude("sells(8925); sells(3372)")
        lua.execute("openVendor()")
        self.assertEqual(lua.eval("#purchases"), 0)
        self.assertEqual(lua.eval("#chat"), 0)
        self.assertEqual(lua.eval("listening()"), "MERCHANT_CLOSED,MERCHANT_SHOW,TRADE_SKILL_SHOW")

    def test_targets_met_buy_nothing_and_say_nothing(self):
        lua = claude()
        lua.execute("put(0, 1, 8928, 20); put(0, 2, 3776, 10); put(0, 3, 8985, 20); put(0, 4, 5140, 20)")
        lua.execute("openVendor()")
        self.assertEqual(lua.eval("#purchases"), 0)
        self.assertEqual(lua.eval("#chat"), 0)

    def test_a_vendor_that_sells_nothing_and_a_repair_bot_with_flash_powder(self):
        lua = claude("")
        lua.execute("openVendor()")
        self.assertEqual(lua.eval("#chat + #purchases"), 0)
        lua = claude("sells(5140)")
        lua.execute("openVendor(); finish()")
        self.assertEqual(lua.eval("bought(5140)"), 20)
        self.assertEqual(lua.eval("#purchases"), 1)

    def test_a_flash_powder_target_of_zero_buys_none(self):
        lua = claude(saved=CLAUDE.replace("RestockDB = {", "RestockDB = { keepFlashPowder = 0,"))
        lua.execute("poisonVendor(); sells(5140); openVendor(); finish()")
        self.assertEqual(lua.eval("bought(5140)"), 0)
        self.assertEqual(lua.eval("bought(8924)"), 80)

    def test_a_poison_with_a_target_and_no_recipe_is_named_once(self):
        lua = load("", "sells(8925)")  # first login: the Poisons window never opened
        lua.execute("openVendor(); closeVendor(); openVendor()")
        self.assertEqual(lua.eval("#chat"), 1)
        self.assertEqual(lua.eval("said()"), "|cffff9e38Restock:|r open your Poisons window once to learn"
                         " Instant Poison, Crippling Poison, Deadly Poison.")
        self.assertEqual(lua.eval("#purchases"), 0)

    def test_flash_powder_alone_needs_no_recipe_and_is_bought_with_the_note(self):
        lua = load("", "sells(5140)")
        lua.execute("openVendor(); finish()")
        self.assertEqual(lua.eval("bought(5140)"), 20)
        self.assertEqual(lua.eval("#chat"), 2)


class Checks(unittest.TestCase):
    def test_too_little_money_buys_nothing_and_says_why(self):
        lua = claude("money = 6999; poisonVendor(); sells(5140)")
        lua.execute("openVendor()")
        self.assertEqual(lua.eval("#purchases"), 0)
        self.assertEqual(lua.eval("said()"), "|cffff9e38Restock:|r cannot buy: not enough money (70s).")

    def test_too_little_stock_buys_nothing_and_says_why(self):
        lua = claude("sells(8924, 25, 1, 5); sells(8925); sells(8923); sells(5173); sells(5140)")
        lua.execute("openVendor()")
        self.assertEqual(lua.eval("#purchases"), 0)
        self.assertEqual(lua.eval("said()"), "|cffff9e38Restock:|r cannot buy: the vendor has only 5 Dust A.")

    def test_no_free_slot_buys_nothing_and_says_why(self):
        lua = claude("poisonVendor(); sells(5140); fillBags()")
        lua.execute("openVendor()")
        self.assertEqual(lua.eval("#purchases"), 0)
        self.assertEqual(lua.eval("said()"), "|cffff9e38Restock:|r cannot buy: not enough bag space.")

    def test_partial_stacks_are_filled_before_free_slots_are_counted(self):
        # Only Flash Powder wanted; the bags are full but one stack holds 10 of 20.
        saved = "RestockDB = { keepInstant = 0, keepCrippling = 0, keepDeadly = 0 }"
        lua = load(saved, "sells(5140); fillBags()")
        lua.execute("put(0, 5, 5140, 10); openVendor(); finish()")
        self.assertEqual(lua.eval("bought(5140)"), 10)

    def test_the_partial_room_of_two_stacks_counts_and_one_free_slot_is_enough_for_one_stack_more(self):
        saved = "RestockDB = { keepInstant = 0, keepCrippling = 0, keepDeadly = 0, keepFlashPowder = 50 }"
        lua = load(saved, "sells(5140); fillBags()")
        lua.execute("put(0, 5, 5140, 5); put(0, 6, 5140, 5); bags[0].slots[7] = nil; openVendor(); finish()")
        # 40 wanted: the two stacks take 30, the other 10 need the one free slot.
        self.assertEqual(lua.eval("bought(5140)"), 40)

    def test_general_bag_slots_only_an_ammo_bag_does_not_help(self):
        lua = claude("poisonVendor(); sells(5140); fillBags(); bags[1] = { size = 8, family = 1, slots = {} }")
        lua.execute("openVendor()")
        self.assertEqual(lua.eval("#purchases"), 0)
        self.assertEqual(lua.eval("said()"), "|cffff9e38Restock:|r cannot buy: not enough bag space.")

    def test_a_full_pack_still_buys_what_a_partial_stack_holds(self):
        lua = claude("sells(5140); fillBags()")
        lua.execute("put(0, 1, 5140, 19); openVendor(); finish()")
        self.assertEqual(lua.eval("bought(5140)"), 1)


class Buying(unittest.TestCase):
    def test_one_purchase_at_a_time_and_the_next_after_the_last_is_in(self):
        lua = claude()
        lua.execute("openVendor()")
        self.assertEqual(lua.eval("#purchases"), 1)
        lua.execute("step(1)")
        self.assertEqual(lua.eval("#purchases"), 1)
        lua.execute("deliver()")
        self.assertEqual(lua.eval("#purchases"), 2)
        self.assertEqual(lua.eval("purchases[1].items + purchases[2].items"), 40)

    def test_a_bundle_is_bought_whole_and_a_stack_at_a_time(self):
        lua = load("RestockDB = { keepInstant = 0, keepCrippling = 0, keepDeadly = 0, keepFlashPowder = 30 }",
                   "sells(5140, 100, 5)")
        lua.execute("openVendor(); finish()")
        self.assertEqual(lua.eval("purchases[1].n .. ',' .. purchases[2].n"), "4,2")
        self.assertEqual(lua.eval("bought(5140)"), 30)
        self.assertEqual(lua.eval("money"), 1000000 - 600)

    def test_the_plan_is_made_again_from_the_bags_after_each_purchase(self):
        lua = claude()
        lua.execute("openVendor(); put(0, 9, 5173, 20); put(0, 10, 5173, 20); put(0, 11, 5173, 10); finish()")
        self.assertEqual(lua.eval("bought(5173)"), 50)
        self.assertEqual(lua.eval("bought(8924)"), 80)

    def test_a_lost_purchase_is_sent_again_after_two_seconds(self):
        lua = claude()
        lua.execute("openVendor(); lose(); step(1.9)")
        self.assertEqual(lua.eval("#purchases"), 1)
        lua.execute("step(0.2)")
        self.assertEqual(lua.eval("#purchases"), 2)
        lua.execute("finish()")
        self.assertEqual(lua.eval("bought(8924)"), 100)  # the first twenty were lost

    def test_three_misses_in_a_row_stop_with_a_line(self):
        lua = claude()
        lua.execute("openVendor(); lose(); step(2); lose(); step(2); lose(); step(2)")
        self.assertEqual(lua.eval("#purchases"), 3)
        self.assertEqual(lua.eval("said()"), "|cffff9e38Restock:|r stopped, the vendor did not deliver Dust A.")
        self.assertEqual(lua.eval("listening()"), "MERCHANT_CLOSED,MERCHANT_SHOW,TRADE_SKILL_SHOW")
        lua.execute("step(10); deliver()")
        self.assertEqual(lua.eval("#purchases"), 3)

    def test_an_arrival_resets_the_misses(self):
        lua = claude()
        lua.execute("openVendor(); lose(); step(2); lose(); step(2); deliver(); lose(); step(2); lose(); step(2)")
        self.assertNotIn("stopped", lua.eval("allSaid()"))

    def test_the_late_timer_of_a_landed_purchase_does_nothing(self):
        lua = claude()
        lua.execute("openVendor(); step(1); deliver()")
        self.assertEqual(lua.eval("#purchases"), 2)
        lua.execute("step(1.5)")  # the first timer is due, the second is not
        self.assertEqual(lua.eval("#purchases"), 2)

    def test_closing_the_vendor_stops_the_order(self):
        lua = claude()
        lua.execute("openVendor()")
        self.assertIn("BAG_UPDATE_DELAYED", lua.eval("listening()"))
        lua.execute("closeVendor(); deliver(); step(5)")
        self.assertEqual(lua.eval("#purchases"), 1)
        self.assertNotIn("BAG_UPDATE_DELAYED", lua.eval("listening()"))
        self.assertEqual(lua.eval("#chat"), 1)

    def test_the_bag_event_is_listened_to_only_while_buying(self):
        lua = claude()
        self.assertNotIn("BAG_UPDATE_DELAYED", lua.eval("listening()"))
        lua.execute("openVendor()")
        self.assertIn("BAG_UPDATE_DELAYED", lua.eval("listening()"))
        lua.execute("finish(); step(3)")
        self.assertNotIn("BAG_UPDATE_DELAYED", lua.eval("listening()"))

    def test_nothing_runs_after_an_order_ends(self):
        lua = claude()
        lua.execute("openVendor(); finish(); step(3)")
        self.assertEqual(lua.eval("liveTimers()"), 0)
        self.assertEqual(lua.eval("listening()"), "MERCHANT_CLOSED,MERCHANT_SHOW,TRADE_SKILL_SHOW")

    def test_a_vendor_with_nothing_to_buy_sets_no_timer(self):
        lua = claude("sells(8925)")
        lua.execute("openVendor()")
        self.assertEqual(lua.eval("liveTimers()"), 0)

    def test_money_gone_midway_stops_with_the_reason(self):
        lua = claude()
        lua.execute("openVendor(); money = 100; finish()")
        self.assertIn("not enough money", lua.eval("said()"))
        self.assertEqual(lua.eval("#purchases"), 1)


if __name__ == "__main__":
    unittest.main()
