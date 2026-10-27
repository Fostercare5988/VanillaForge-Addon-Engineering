"""Weapon-slot state, the only item state since the 2026-10-27 rogue pass.

The real _GetInventorySlotState body runs under Lua 5.1 with mock NamPower and
item APIs. Trinket on-use detection (C_Item.GetItemSpell) left with the trinket
trackers. Live item data remains an in-game check.
"""
from pathlib import Path
import os
import unittest
from lupa.lua51 import LuaRuntime

ADDON = Path(os.environ["VANILLAFORGE_ADDON_ROOT"])
SOURCE = (ADDON / "Modules/FostercareConditions.lua").read_text("utf-8-sig")


def runtime():
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(r'''
        FOSTERCARE_ITEM_CD_IGNORE = 5.0
        function GetTime() return 100 end
        equipped, cooldowns = {}, {}
        function GetEquippedItem(unit, slot) return equipped[slot] end
        function GetInventoryItemCooldown(unit, slot)
            local cd = cooldowns[slot]
            if cd then return cd[1], cd[2], 1 end
            return 0, 0, 1
        end
    ''')
    body = SOURCE[SOURCE.index('-- Is a weapon in this slot, and is it on cooldown (an on-use weapon)?'):
                  SOURCE.index('-- Core item state used by both condition checks')]
    lua.execute(body + '\nState = _GetInventorySlotState\n')
    return lua


class WeaponSlotTests(unittest.TestCase):
    def test_empty_hand_has_no_item(self):
        lua = runtime()
        self.assertEqual(tuple(lua.eval('{State(17)}').values()), (False, False, 0, 0))

    def test_equipped_weapon_off_cooldown(self):
        lua = runtime()
        lua.execute('equipped[16] = { itemId = 12345 }')
        has, on_cd, rem, dur = lua.eval('State(16)')
        self.assertTrue(has)
        self.assertFalse(on_cd)
        self.assertEqual(rem, 0)

    def test_on_use_weapon_cooldown_counts_but_a_global_cooldown_does_not(self):
        lua = runtime()
        lua.execute('equipped[16] = { itemId = 12345 }; cooldowns[16] = { 90, 30 }')
        has, on_cd, rem, dur = lua.eval('State(16)')
        self.assertTrue(on_cd)
        self.assertEqual(rem, 20)
        lua.execute('cooldowns[16] = { 99, 1.5 }')
        self.assertFalse(lua.eval('State(16)')[1])


if __name__ == '__main__':
    unittest.main()
