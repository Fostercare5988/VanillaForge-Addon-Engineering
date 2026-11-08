"""The bank header counts its free slots, 2026-11-02; through ClassicAPI, 2026-11-07.

C_Container.GetContainerNumFreeSlots used to answer 0 for the bank and its bags, so an
open bank with room showed "0 / 122 Free" and Bagnon counted the bank slot by slot.
ClassicAPI 1.19.3 counts the main bank (-1) and the bank bags (5..10) while the bank
is open, the only time the bank frame is live, so every live bag asks it and no slot is
walked.

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
    -- bank: 4 of 24 free; bag 5: 13 of 16; bag 6: full
    bagFree[-1], bagFree[5], bagFree[6] = 4, 13, 0
    slotReads = 0
    function GetContainerItemInfo() slotReads = slotReads + 1 end
    bagLinks[6] = "|cff9d9d9d|Hitem:4496:0:0:0|h[Small Brown Pouch]|h|r"
    bagLinks[7] = bagLinks[6]
'''


class BankFree(unittest.TestCase):
    def test_header_counts_empty_bank_slots(self):
        lua = load("utility", "frame")
        lua.execute(FRAME + "BagnonFrame_UpdateFreeSlots(frame)")
        # 4 + 13 + 0 free of 24 + 16 + 16
        self.assertEqual(lua.eval("BanknonFreeSlots.text"), "17 / 56 Free")
        self.assertEqual(lua.eval("slotReads"), 0)

    def test_a_full_bank_reads_zero(self):
        lua = load("utility", "frame")
        lua.execute(FRAME + "bagFree[-1], bagFree[5] = 0, 0; BagnonFrame_UpdateFreeSlots(frame)")
        self.assertEqual(lua.eval("BanknonFreeSlots.text"), "0 / 56 Free")


if __name__ == "__main__":
    unittest.main()
