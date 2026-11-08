"""Reproductions for the 2026-11-08 EasyPoisons audit (.private/audit-EasyPoisons-2026-11-08.md).

Mocks only: the Poisons window's skill line name ("Poisons"), how the
profession UI's filters hide ranks, and when BAG_UPDATE_DELAYED fires stay
in-game checks.
"""
import unittest
from ep_env import load

INSTANT_VI = '{ item = 8928, name = "Instant Poison VI", reagents = { {8924, 4}, {8925, 1} } }'
INSTANT_IV = '{ item = 8926, name = "Instant Poison IV", reagents = { {8924, 2}, {8925, 1} } }'
WINDOW = """tradeskills = {
    { item = 8928, name = "Instant Poison VI", reagents = { {8924, 4}, {8925, 1} } },
    { item = 8926, name = "Instant Poison IV", reagents = { {8924, 2}, {8925, 1} } },
    { item = 8985, name = "Deadly Poison IV", reagents = { {5173, 5}, {8925, 1} } },
    { item = 3776, name = "Crippling Poison II", reagents = { {8923, 3}, {8925, 1} } },
}"""


def garbage(lua, code, times=20):
    return lua.eval('''(function()
        collectgarbage("collect"); collectgarbage("stop")
        local before = collectgarbage("count")
        for _ = 1, %d do %s end
        local after = collectgarbage("count")
        collectgarbage("restart")
        return after - before
    end)()''' % (times, code))


class PoisonsWindow(unittest.TestCase):
    def test_p2_first_read_keeps_the_rank_a_filtered_window_hides(self):
        """P2: the first read of Instant Poison VI (the table's rank) was not saved, so a
        later window with VI hidden (collapsed or filtered) moved the row down to IV."""
        lua = load("poisonVendor()")
        lua.execute('tradeskills = { %s }; fire("TRADE_SKILL_SHOW"); advance(0)' % INSTANT_VI)
        lua.execute('tradeskills = { %s }; fire("TRADE_SKILL_UPDATE"); advance(0)' % INSTANT_IV)
        lua.execute("openVendor()")
        self.assertIn("Instant Poison VI", lua.eval("allText()"))
        self.assertNotIn("Instant Poison IV", lua.eval("allText()"))

    def test_p3_other_profession_windows_are_not_read(self):
        """P3: every Alchemy, Cooking or First Aid window update walked its recipes by name."""
        lua = load("poisonVendor()")
        lua.execute('tradeskillLine = "Alchemy"; ' + WINDOW + '; calls = {}; fire("TRADE_SKILL_SHOW"); '
                    'fire("TRADE_SKILL_UPDATE"); advance(0)')
        self.assertEqual(lua.eval("calls.recipeName or 0"), 0)
        self.assertIsNone(lua.eval("EasyPoisonsDB.Recipes[8928]"))

    def test_p3_opening_the_window_reads_it_once(self):
        """P3: TRADE_SKILL_SHOW and TRADE_SKILL_UPDATE arrive together on opening; both read it."""
        lua = load("poisonVendor()")
        lua.execute(WINDOW + '; calls = {}; fire("TRADE_SKILL_SHOW"); fire("TRADE_SKILL_UPDATE"); advance(0)')
        self.assertEqual(lua.eval("calls.recipeName or 0"), 4)

    def test_p3_unchanged_window_reads_no_names_and_makes_no_tables(self):
        """P3: each craft's TRADE_SKILL_UPDATE split every name and built a table per poison."""
        lua = load("poisonVendor()")
        lua.execute(WINDOW + '; fire("TRADE_SKILL_SHOW"); advance(0); calls = {}')
        lua.execute('fire("TRADE_SKILL_UPDATE"); advance(0)')
        self.assertEqual(lua.eval("calls.recipeName or 0"), 0)
        baseline = garbage(lua, 'C_Timer.After(0, function() end); advance(0)')
        delta = garbage(lua, 'fire("TRADE_SKILL_UPDATE"); advance(0)')
        self.assertLess(delta - baseline, 2)

    def test_recipes_and_ranks_still_learned(self):
        """The moved path: the window's ranks and recipes are saved as before."""
        lua = load("poisonVendor()")
        lua.execute(WINDOW + '; fire("TRADE_SKILL_SHOW"); advance(0)')
        self.assertEqual(lua.eval("EasyPoisonsDB.Recipes[8928][8924]"), 4)
        self.assertEqual(lua.eval("EasyPoisonsDB.Recipes[8985][5173]"), 5)
        self.assertIsNone(lua.eval("EasyPoisonsDB.Recipes[8926]"), "a lower rank's recipe is not saved")
        self.assertEqual(lua.eval("EasyPoisonsDB.Ranks[\"Claude-Y'Shaarj\"][8928].rank"), 6)

    def test_changed_recipe_replaces_the_saved_one(self):
        lua = load("poisonVendor()")
        lua.execute(WINDOW + '; fire("TRADE_SKILL_SHOW"); advance(0)')
        lua.execute('tradeskills[3].reagents = { {5173, 6}, {8925, 1}, {8924, 1} }; fire("TRADE_SKILL_UPDATE"); advance(0)')
        self.assertEqual(lua.eval("EasyPoisonsDB.Recipes[8985][5173]"), 6)
        self.assertEqual(lua.eval("EasyPoisonsDB.Recipes[8985][8924]"), 1)
        lua.execute('tradeskills[3].reagents = { {5173, 6}, {8925, 1} }; fire("TRADE_SKILL_UPDATE"); advance(0)')
        self.assertIsNone(lua.eval("EasyPoisonsDB.Recipes[8985][8924]"), "a dropped reagent goes")


class SavedData(unittest.TestCase):
    def test_p3_recipes_nothing_reads_are_cleared(self):
        """P3: older versions saved every rank's recipe (Deadly Poison III 8984 and five
        more on Claude); only the rows' ranks are read."""
        lua = load("""poisonVendor()
            EasyPoisonsDB.Recipes[8984] = { [5173] = 3, [8925] = 1 }
            EasyPoisonsDB.Recipes[8926] = { [8924] = 2, [8925] = 1 }
            EasyPoisonsDB.Ranks = { ["Alt-Y'Shaarj"] = { [8928] = { itemID = 8926, name = "Instant Poison IV", rank = 4 } } }""")
        self.assertIsNone(lua.eval("EasyPoisonsDB.Recipes[8984]"))
        self.assertEqual(lua.eval("EasyPoisonsDB.Recipes[8926][8924]"), 2, "an alt's rank keeps its recipe")
        self.assertEqual(lua.eval("EasyPoisonsDB.Recipes[8985][5173]"), 7, "a row's recipe stays")


class Bags(unittest.TestCase):
    def test_p3_landed_purchase_sends_the_next_in_the_same_frame(self):
        """P3: BAG_UPDATE was coalesced by hand into a refresh one frame later;
        ClassicAPI's BAG_UPDATE_DELAYED is already once per frame."""
        lua = load("poisonVendor()")
        lua.execute("openVendor(); setQty(POISON.Deadly, 10); buy()")
        self.assertEqual(lua.eval("#purchases"), 1)
        lua.execute("addItem(purchases[1].id, purchases[1].items); delivered = 1; bagUpdate()")
        self.assertEqual(lua.eval("#purchases"), 2)

    def test_bag_update_alone_does_nothing(self):
        lua = load("poisonVendor()")
        lua.execute('openVendor(); setQty(POISON.Deadly, 1); calls = {}; fire("BAG_UPDATE", 0); advance(0)')
        self.assertEqual(lua.eval("calls.bagRead or 0"), 0)


class Vendor(unittest.TestCase):
    def test_p3_hidden_window_skips_vendor_updates(self):
        """P3: every MERCHANT_UPDATE (each item sold) rescanned the vendor with the window closed."""
        lua = load("poisonVendor(); sells(999, 5)")
        lua.execute('openVendor(); window():Hide(); calls = {}; fire("MERCHANT_UPDATE"); advance(0)')
        self.assertEqual(lua.eval("calls.merchantRead or 0"), 0)

    def test_slash_command_sees_stock_changed_while_closed(self):
        """The moved path: /ep at the vendor reads the stock as it is now."""
        lua = load("sells(8925, 25); sells(5173, 25, 1, 50)")
        lua.execute('openVendor(); window():Hide(); merchant.items[2].stock = 3; fire("MERCHANT_UPDATE"); advance(0)')
        lua.execute('SlashCmdList.EASYPOISONS(""); advance(0); setQty(POISON.Deadly, 1)')
        self.assertIn("too few Deathweed", lua.eval("allText()"))


class Window(unittest.TestCase):
    def status(self, lua):
        return lua.eval("(function() for _, f in ipairs(fonts) do if f.text == statusText then "
                        "return f.color[1] .. ',' .. f.color[2] end end end)()")

    def test_p3_information_is_not_shown_as_an_error(self):
        """P3: "You have all the reagents." and "Buying..." were red like a problem."""
        lua = load("poisonVendor(); addItem(5173, 20); addItem(8925, 5)")
        lua.execute("openVendor(); setQty(POISON.Deadly, 1); statusText = 'You have all the reagents.'")
        self.assertNotEqual(self.status(lua), "1,0.35")
        lua.execute("money = 0; setQty(POISON.Deadly, 9); statusText = 'Not enough money.'")
        self.assertEqual(self.status(lua), "1,0.35")

    def test_p3_tab_moves_to_the_next_count(self):
        """P3: Tab did nothing in a count box; typing a batch meant clicking every box."""
        lua = load("poisonVendor()")
        lua.execute("openVendor(); run(EasyPoisons_Row1Count, 'OnTabPressed')")
        self.assertTrue(lua.eval("focused == EasyPoisons_Row2Count"))
        lua.execute("shiftDown = true; run(EasyPoisons_Row1Count, 'OnTabPressed')")
        self.assertTrue(lua.eval("focused == EasyPoisons_Row8Count"), "Shift-Tab goes back, wrapping")


class Globals(unittest.TestCase):
    def test_p3_no_global_table(self):
        """P3: a global EasyPoisons table held the addon's own functions; nothing outside used it."""
        lua = load("poisonVendor()")
        self.assertTrue(lua.eval("EasyPoisons == nil"))


if __name__ == "__main__":
    unittest.main()
