"""The bank header counts its free slots, 2026-11-02.

C_Container.GetContainerNumFreeSlots answers 0 for the bank and its bags (ClassicAPI
documents backpack and bags 1..4 only), so an open bank with room showed "0 / 122 Free"
and a red 0 on every row of the tooltip. The bank's bags are now counted slot by slot.

In game: open the bank with empty slots; the header and the tooltip rows show them.
"""
import unittest
from bgn_env import load

FRAME = '''
    Bagnon_SetAtBank(true)
    frame = widget("Banknon"); frame.player = "Tester"
    widget("BanknonFreeSlots"); widget("BanknonTitle"); widget("BanknonSortButton"); widget("BanknonCloseButton"); widget("BanknonDropDown")
    bagSlots[-1] = 24; bagSlots[5] = 16; bagSlots[6] = 16
    for b = 7, 10 do bagSlots[b] = 0 end
    -- bank: 20 of 24 used; bag 5: 3 of 16 used; bag 6: full
    used = { [-1] = 20, [5] = 3, [6] = 16 }
    function GetContainerItemInfo(bag, slot) if slot <= (used[bag] or 0) then return "tex", 1 end end
    bagLinks[6] = "|cff9d9d9d|Hitem:4496:0:0:0|h[Small Brown Pouch]|h|r"
    bagLinks[7] = bagLinks[6]
'''


class BankFree(unittest.TestCase):
    def test_header_counts_empty_bank_slots(self):
        lua = load("localization", "utility", "frame")
        lua.execute(FRAME + "BagnonFrame_UpdateFreeSlots(frame)")
        # 4 + 13 + 0 free of 24 + 16 + 16
        self.assertEqual(lua.eval("BanknonFreeSlots.text"), "17 / 56 Free")

    def test_a_full_bank_reads_zero(self):
        lua = load("localization", "utility", "frame")
        lua.execute(FRAME + "used = { [-1] = 24, [5] = 16, [6] = 16 }; BagnonFrame_UpdateFreeSlots(frame)")
        self.assertEqual(lua.eval("BanknonFreeSlots.text"), "0 / 56 Free")


if __name__ == "__main__":
    unittest.main()
