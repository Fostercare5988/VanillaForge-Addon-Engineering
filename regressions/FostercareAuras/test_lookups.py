"""Lookups answered by NamPower or the addon's own event-driven caches.

Real FostercareConditions.lua bodies under Lua 5.1 with mock APIs. 1.1.0-local
rescanned the pet's auras on every stack check and walked both spellbooks for a
spell NamPower had already reported missing, so both tests fail on it.
"""
from pathlib import Path
import os
import unittest
from lupa.lua51 import LuaRuntime

ADDON = Path(os.environ["VANILLAFORGE_ADDON_ROOT"])
SOURCE = (ADDON / "Modules/FostercareConditions.lua").read_text("utf-8-sig")


def stacks_runtime():
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(r'''
        auraScans = 0
        function UnitBuff() auraScans = auraScans + 1 end
        function UnitDebuff() auraScans = auraScans + 1 end
        function _NP_SpellNameAndTexture() return nil end
        auraSnapshot = {}
        FostercarePlayerAuras, FostercareTargetAuras = {}, {}
        petStacks = { ["Frenzy"] = 3 }
        FostercarePetAuras = {
            GetStacks = function(name, wantDebuff, sid, bySid) return petStacks[name] end,
        }
    ''')
    body = SOURCE[SOURCE.index('_GetAuraStacksOnUnit = function('):
                  SOURCE.index('-- Fast check: does unit have ANY of the named buffs?')]
    lua.execute('local _GetAuraStacksOnUnit\n' + body +
                '\nfunction stacks(...) return _GetAuraStacksOnUnit(...) end')
    return lua


def spellbook_runtime():
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(r'''
        BOOKTYPE_SPELL, BOOKTYPE_PET = "spell", "pet"
        book = {}
        for i = 1, 150 do book[i] = "Spell " .. i end
        bookReads = 0
        function GetSpellName(i) bookReads = bookReads + 1; return book[i] end
        function GetSpellSlotTypeIdForName(name)
            for i = 1, 150 do if book[i] == name then return i, "spell", 1000 + i end end
            return 0, "unknown", 0
        end
    ''')
    start = SOURCE.index('-- Spell index cache (must be defined before any usage)')
    body = SOURCE[start:SOURCE.index('-- Dirty flags used by the central update loop')]
    lua.execute(body + '\nfunction index(n) return _GetSpellIndexByName(n) end')
    return lua


class LookupTests(unittest.TestCase):
    def test_pet_stacks_come_from_the_pet_aura_cache(self):
        lua = stacks_runtime()
        self.assertEqual(lua.eval('stacks("pet", "Frenzy", false, 0, false)'), 3)
        self.assertIsNone(lua.eval('stacks("pet", "Bestial Wrath", false, 0, false)'))
        self.assertEqual(lua.eval('auraScans'), 0, 'pet auras were rescanned')

    def test_spell_missing_from_the_book_does_not_walk_the_spellbook(self):
        lua = spellbook_runtime()
        self.assertEqual(lua.eval('index("Spell 42")'), 42)
        self.assertIsNone(lua.eval('index("Not Learned")'))
        self.assertEqual(lua.eval('bookReads'), 0, 'spellbook walked after NamPower answered')


if __name__ == '__main__':
    unittest.main()
