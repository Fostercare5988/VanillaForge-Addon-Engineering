"""On-use detection for equipped slots comes from C_Item.GetItemSpell (ClassicAPI).

The real _GetInventorySlotState body runs under Lua 5.1 with mock item APIs.
1.1.0-local guessed at NamPower item fields it does not return, called an
undocumented GetItemSpell global and parsed the English slot tooltip, so all
three tests fail on it. Live item data remains an in-game check.
"""
from pathlib import Path
import os
import unittest
from lupa.lua51 import LuaRuntime

ADDON = Path(os.environ["VANILLAFORGE_ADDON_ROOT"])
SOURCE = (ADDON / "Modules/FostercareConditions.lua").read_text("utf-8-sig")
TRINKET, PASSIVE = 11111, 22222


def runtime():
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(r'''
        str_find = string.find
        FOSTERCARE_ITEM_CD_IGNORE = 5.0
        FostercareConditions = {}
        function GetTime() return 100 end
        equipped = {}
        function _GetPlayerItemSnapshot() return { eq = equipped } end
        function GetInventoryItemLink() return nil end
        function GetInventoryItemCooldown() return 0, 0, 1 end
        cached, spellCalls = {}, 0
        C_Item = {}
        function C_Item.GetItemSpell(itemId)
            spellCalls = spellCalls + 1
            if not cached[itemId] then return nil end
            if itemId == %d then return "Earthstrike", 25891 end
            return nil
        end
        -- The tooltip a passive trinket shows; reading it is the old behaviour.
        tooltipReads, tooltipText = 0, nil
        _CondTipLeft = { { GetText = function() tooltipReads = tooltipReads + 1
            return tooltipText end } }
        FostercareConditionsTooltip = { SetInventoryItem = function() end, ClearLines = function() end }
        function _EnsureTooltip() end
    ''' % TRINKET)
    body = SOURCE[SOURCE.index('local function _GetInventorySlotState(slot)'):
                  SOURCE.index('-- Core item state used by both condition checks')]
    lua.execute(body + r'''
        function isUse(slot) local _, _, _, _, u = _GetInventorySlotState(slot); return u end
    ''')
    return lua


class ItemUseTests(unittest.TestCase):
    def test_on_use_trinket_is_detected_from_its_item_spell(self):
        runtime().execute('''
            equipped[13] = { itemId = %d }; cached[%d] = true
            assert(isUse(13) == true, 'on-use trinket not detected')
        ''' % (TRINKET, TRINKET))

    def test_passive_trinket_is_not_use_and_its_tooltip_is_not_read(self):
        runtime().execute('''
            equipped[14] = { itemId = %d }; cached[%d] = true
            tooltipText = 'Equip: Chance on hit to use 50 mana.'
            assert(isUse(14) == false, 'passive trinket counted as on-use')
            assert(tooltipReads == 0, 'slot tooltip was parsed')
        ''' % (PASSIVE, PASSIVE))

    def test_item_cache_miss_is_retried_and_a_hit_is_kept(self):
        runtime().execute('''
            equipped[13] = { itemId = %d }
            assert(isUse(13) == false)
            cached[%d] = true
            assert(isUse(13) == true, 'a cache miss was remembered as not on-use')
            local calls = spellCalls
            assert(isUse(13) == true and spellCalls == calls, 'a positive answer was not cached')
        ''' % (TRINKET, TRINKET))


if __name__ == '__main__':
    unittest.main()
