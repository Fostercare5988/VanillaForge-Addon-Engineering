"""GearRack finds free bank slots through ClassicAPI (1.19.3), 2026-11-07.

FindSpaceInBag walked the slots with C_Container.HasContainerItem, which answers
only for bags 0 to 4 (ClassicAPI docs/API.md). Every bank slot looked empty, so
the first unclaimed bank slot came back even when full, SendBankItem refused it
(the destination holds an item) and putting a set in the bank stopped there.
ClassicAPI 1.19.3's GetContainerNumFreeSlots and GetContainerFreeSlots answer
the free slots and the bag family of the bank while it is open, so every bag is
read the same way and ValidBag (the bank bags' item-family lookup) is gone. The
occupied-bank test fails on the old code; real bank moves stay an in-game check.
"""
from pathlib import Path
import os
import unittest
from wowlua import LuaRuntime

ROOT = Path(os.environ["VANILLAFORGE_ADDON_ROOT"])
EQUIPMENT = (ROOT / "src/Equipment.lua").read_text("utf-8").replace("\r\n", "\n")


def between(text, start, end):
    return text[text.index(start):text.index(end)]


def engine(bags):
    """bags: Lua table source, bagID -> { family = n, items = { [slot] = true }, size = n }."""
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute("BAGS = " + bags + r'''
        freeListCalls = 0
        local function free(bag)
            local b = BAGS[bag]
            if not b then return end
            local list = {}
            for slot = 1, b.size do if not b.items[slot] then list[#list + 1] = slot end end
            return list
        end
        C_Container = {
            GetContainerNumFreeSlots = function(bag)
                local list = free(bag)
                if not list then return 0 end
                return #list, BAGS[bag].family
            end,
            GetContainerFreeSlots = function(bag) freeListCalls = freeListCalls + 1; return free(bag) end,
            -- ClassicAPI: bags 0 to 4 only.
            HasContainerItem = function(bag, slot)
                local b = bag >= 0 and bag <= 4 and BAGS[bag]
                return b and b.items[slot] == true or false
            end,
        }
        function GetContainerNumSlots(bag) return BAGS[bag] and BAGS[bag].size or 0 end
        function GetInventoryItemLink() end
        function ContainerIDToInventoryID(b) return b + 63 end
        C_Item = { GetItemFamily = function() return 0 end }
        GearRackUI = { BankIsOpen = true, BankSlots = { -1, 5, 6, 7, 8, 9, 10 } }
        GearRackEngine = { LockList = {} }
        for i = -2, 10 do GearRackEngine.LockList[i] = {} end
    ''')
    lua.execute(between(EQUIPMENT, "-- The first empty slot of a general-purpose bag",
                        "-- clears locks on all bag slots"))
    return lua


class BankSpace(unittest.TestCase):
    def test_a_full_bank_slot_is_never_chosen(self):
        lua = engine('{ [-1] = { family = 0, size = 4, items = { [1] = true, [2] = true } } }')
        bag, slot = lua.eval('GearRackEngine.FindSpace(1)')
        self.assertEqual((bag, slot), (-1, 3))

    def test_a_claimed_slot_is_skipped(self):
        lua = engine('{ [-1] = { family = 0, size = 4, items = {} } }')
        lua.execute('GearRackEngine.FindSpace(1)')
        self.assertEqual(lua.eval('select(2, GearRackEngine.FindSpace(1))'), 2)

    def test_a_specialty_bank_bag_is_skipped(self):
        lua = engine('''{ [-1] = { family = 0, size = 1, items = { [1] = true } },
            [5] = { family = 32, size = 8, items = {} }, [6] = { family = 0, size = 8, items = { [1] = true } } }''')
        bag, slot = lua.eval('GearRackEngine.FindSpace(1)')
        self.assertEqual((bag, slot), (6, 2))

    def test_a_full_bag_builds_no_free_list(self):
        lua = engine('{ [-1] = { family = 0, size = 2, items = { [1] = true, [2] = true } } }')
        self.assertIsNone(lua.eval('GearRackEngine.FindSpace(1)'))
        self.assertEqual(lua.eval('freeListCalls'), 0)

    def test_carried_bags_fill_from_the_last_bag(self):
        lua = engine('''{ [0] = { family = 0, size = 16, items = {} },
            [4] = { family = 0, size = 10, items = { [1] = true } }, [3] = { family = 1, size = 10, items = {} } }''')
        bag, slot = lua.eval('GearRackEngine.FindSpace()')
        self.assertEqual((bag, slot), (4, 2))

    def test_no_item_family_lookup_and_no_valid_bag(self):
        self.assertNotIn("ValidBag", EQUIPMENT)
        self.assertNotIn("HasContainerItem", EQUIPMENT)


if __name__ == "__main__":
    unittest.main()
