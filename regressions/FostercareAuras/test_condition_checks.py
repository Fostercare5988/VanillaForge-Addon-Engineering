"""Talent and form condition checks from the real FostercareConditions.lua bodies.

The talent-mode cache in 1.1.0-local was a fresh table on every call (it read a
global that is never set), so test_talent_mode_is_normalized_once fails on it.
The form tests pass on both versions: they pin results while the form name lists
move into tables built once.
"""
from pathlib import Path
import os
import unittest
from lupa.lua51 import LuaRuntime

ADDON = Path(os.environ["VANILLAFORGE_ADDON_ROOT"])
SOURCE = (ADDON / "Modules/FostercareConditions.lua").read_text("utf-8-sig")


def talent_runtime():
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(r'''
        str_gsub = string.gsub
        FostercareConditions = {}
        talents = { { name = "Improved Rend", rank = 2 }, { name = "Deep Wounds", rank = 0 } }
        function GetNumTalentTabs() return 1 end
        function GetNumTalents() return table.getn(talents) end
        function GetTalentInfo(tab, i) local t = talents[i]; return t.name, nil, nil, nil, t.rank end
        lowerCalls = 0
        local realLower = string.lower
        string.lower = function(s) lowerCalls = lowerCalls + 1; return realLower(s) end
    ''')
    body = SOURCE[SOURCE.index('local function _TalentIsKnownByName('):
                  SOURCE.index('local function _EvaluateAuraConditionsList(')]
    lua.execute(body + r'''
        function check(name, mode) return _AuraConditions_CheckEntry({ buffType = "TALENT", name = name, mode = mode }) end
    ''')
    return lua


def form_runtime(cls, active):
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(r'''
        str_gsub = string.gsub
        FostercareConditions = {}
        forms, buffs = {}, {}
        function UnitClass() return playerClass, playerClass end
        function GetShapeshiftFormInfo(i)
            local f = forms[i]
            if not f then return nil end
            return "tex", f.name, f.active and 1 or nil
        end
        FostercarePlayerAuras = { HasBuff = function(name) return buffs[name] == true end }
    ''')
    lua.execute('playerClass = "%s"' % cls)
    for i, (name, on) in enumerate(active):
        lua.execute('forms[%d] = { name = "%s", active = %s }' % (i + 1, name, 'true' if on else 'false'))
    body = SOURCE[SOURCE.index('local function _ActiveFormMap()'):
                  SOURCE.index('function FostercareConditions_PassesFormRequirement(formStr)')]
    lua.execute(body + '\nfunction passes(s) return _PassesFormRequirement(s) end')
    return lua


PALADIN = ["Devotion Aura", "Retribution Aura", "Concentration Aura", "Shadow Resistance Aura",
           "Frost Resistance Aura", "Fire Resistance Aura", "Sanctity Aura"]


class TalentConditionTests(unittest.TestCase):
    def test_talent_known_and_not_known(self):
        lua = talent_runtime()
        self.assertTrue(lua.eval('check("Improved Rend", "Known")'))
        self.assertFalse(lua.eval('check("Deep Wounds", "Known")'))
        self.assertTrue(lua.eval('check("Deep Wounds", "Not known")'))

    def test_talent_mode_is_normalized_once(self):
        lua = talent_runtime()
        lua.execute('for i = 1, 50 do check("Improved Rend", "Not known") end')
        self.assertEqual(lua.eval('lowerCalls'), 1, 'talent mode re-normalized on every check')


class FormConditionTests(unittest.TestCase):
    def test_paladin_multis_match_any_listed_aura(self):
        lua = form_runtime("PALADIN", [(n, n == "Frost Resistance Aura") for n in PALADIN])
        self.assertTrue(lua.eval('passes("Multi: 2+4+5+6")'))
        self.assertTrue(lua.eval('passes("Multi: 4+5+6+7")'))
        self.assertFalse(lua.eval('passes("Multi: 1+2")'))
        self.assertFalse(lua.eval('passes("No Aura")'))
        self.assertTrue(lua.eval('passes("5. Frost Resistance")'))

    def test_paladin_no_aura(self):
        lua = form_runtime("PALADIN", [(n, False) for n in PALADIN])
        self.assertTrue(lua.eval('passes("No Aura")'))
        self.assertFalse(lua.eval('passes("Multi: 1+2+3+4+5+6")'))

    def test_druid_forms_and_multis(self):
        lua = form_runtime("DRUID", [("Dire Bear Form", True), ("Cat Form", False),
                                     ("Travel Form", False), ("Moonkin Form", False)])
        self.assertTrue(lua.eval('passes("1. Bear")'))
        self.assertTrue(lua.eval('passes("Multi: 1+3+8")'))
        self.assertFalse(lua.eval('passes("0. No form")'))
        self.assertFalse(lua.eval('passes("Multi: 0+5+6")'))
        lua.execute('forms[1].active = false')
        self.assertTrue(lua.eval('passes("0. No forms")'))
        self.assertTrue(lua.eval('passes("Multi: 0+5+6")'))
        self.assertFalse(lua.eval('passes("4. Travel")'))


if __name__ == '__main__':
    unittest.main()
