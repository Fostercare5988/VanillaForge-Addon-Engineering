"""Bagnon audit repros (2026-10-30). Fail on 1.1.0.

1. The free-space header counted every bag slot as space but only the plain bags'
   free slots, because ClassicAPI's CalculateTotalNumberOfFreeBagSlots leaves out
   quivers, soul bags and profession bags. 8 free of 46 showed as 3 / 46.
2. Every item slot looked its bag up by name text (two GetItemInfo calls and a
   link parse per slot) to colour the slot border; ClassicAPI gives the bag's
   family from one native call.
"""
import unittest
from bgn_env import load

FRAME = '''
    frame = widget("Bagnon")
    frame.size = 46; frame.player = "Tester"
    widget("BagnonFreeSlots"); widget("BagnonTitle"); widget("BagnonSortButton")
'''


class FreeSlots(unittest.TestCase):
    def test_header_counts_the_free_slots_of_every_bag(self):
        lua = load("localization", "utility", "frame")
        lua.execute(FRAME + "BagnonFrame_UpdateFreeSlots(frame)")
        # bag 0: 3 free of 16, bag 1: 0 of 16, soul bag 5 of 8, herb bag 2 of 6
        self.assertEqual(lua.eval("BagnonFreeSlots.text"), "10 / 46 Free")

    def test_header_agrees_with_the_tooltip_rows(self):
        lua = load("localization", "utility", "frame")
        lua.execute(FRAME + """
            rows = 0
            GameTooltip = widget("GameTooltip")
            function GameTooltip:AddDoubleLine(_, right) rows = rows + tonumber(string.match(string.gsub(right, "|c%x%x%x%x%x%x%x%x", ""), "^(%d+) /")) end
            local button = widget("BagnonFreeSlotsTip"); button.parent = frame; button.freeSlots, button.totalSlots = 0, 0
            BagnonFrameFreeSlots_OnEnter(button)
            BagnonFrame_UpdateFreeSlots(frame)
        """)
        self.assertEqual(lua.eval("rows"), lua.eval("BagnonFreeSlots.freeSlots"))


class BorderColour(unittest.TestCase):
    ITEM = '''
        function item(bag, slot)
            local parent = widget(nil, bag); local button = widget("Slot" .. bag .. "_" .. slot, slot)
            button.parent = parent; parent.parent = widget("Bagnon")
            button.border = widget(nil); button.qualityBorder = widget(nil); button.normalTexture = widget(nil)
            return button
        end
    '''

    def colours(self, bag, slots=16):
        lua = load("localization", "utility", "frame", "item")
        lua.execute(self.ITEM)
        lua.execute("calls = {}; b = {}; for s = 1, %d do b[s] = item(%d, s); BagnonItem_UpdateBorder(b[s], 1) end" % (slots, bag))
        return lua

    def test_soul_bag_slots_are_yellow_and_herb_bag_slots_green(self):
        lua = self.colours(2)
        self.assertEqual(list(lua.eval("b[1].normalTexture.color").values()), [1, 1, 0])
        lua = self.colours(3)
        self.assertEqual(list(lua.eval("b[1].normalTexture.color").values()), [0, 1, 0])

    def test_plain_bag_and_keyring_keep_their_colours(self):
        lua = self.colours(1)
        self.assertEqual(list(lua.eval("b[1].normalTexture.color").values()), [1, 1, 1])
        lua = self.colours(-2)
        self.assertEqual(list(lua.eval("b[1].normalTexture.color").values()), [1, 0.7, 0])

    def test_one_bag_costs_no_item_name_lookups(self):
        lua = self.colours(2)
        self.assertEqual(lua.eval("calls.GetItemInfo or 0"), 0)


class CachedViews(unittest.TestCase):
    """Another character's saved bags: free slots and bag families read the saved strings only."""

    def test_saved_free_slots(self):
        lua = load("localization", "database", "utility")
        self.assertEqual(list(lua.eval('{BagnonDB.GetFreeSlots("Alt", 0)}').values()), [14, 16])
        self.assertEqual(list(lua.eval('{BagnonDB.GetFreeSlots("Alt", 2)}').values()), [7, 8])
        self.assertEqual(list(lua.eval('{BagnonDB.GetFreeSlots("Alt", 4)}').values()), [0, 0])
        self.assertEqual(lua.eval("calls.GetItemInfo or 0"), 0)

    def test_saved_bag_family_comes_from_the_saved_link(self):
        lua = load("localization", "database", "utility")
        self.assertEqual(lua.eval('Bagnon_BagFamily(2, "Alt")'), 4)
        self.assertEqual(lua.eval('Bagnon_BagFamily(0, "Alt")'), 0)
        self.assertEqual(lua.eval('Bagnon_BagFamily(1, "Alt")'), 0)


if __name__ == "__main__":
    unittest.main()
