"""Form condition checks from the real FostercareConditions.lua bodies.

The talent checks lived in the extra aura-condition list, retired in the
2026-10-27 rogue pass with their tests. The form condition is the rogue's
Stealth or no Stealth; the Warrior, Druid, Priest and Paladin forms were removed.
"""
from pathlib import Path
import os
import unittest
from lupa.lua51 import LuaRuntime

ADDON = Path(os.environ["VANILLAFORGE_ADDON_ROOT"])
SOURCE = (ADDON / "Modules/FostercareConditions.lua").read_text("utf-8-sig")


def form_runtime(cls, active):
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(r'''
        str_gsub = string.gsub
        FostercareConditions = {}
        forms, buffs = {}, {}
        function UnitClass() return playerClass, playerClass end
        function GetNumShapeshiftForms() return table.getn(forms) end
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
    body = SOURCE[SOURCE.index('local function _Stealthed()'):
                  SOURCE.index('function FostercareConditions_PassesFormRequirement(formStr)')]
    lua.execute(body + '\nfunction passes(s) return _PassesFormRequirement(s) end')
    return lua


class FormConditionTests(unittest.TestCase):
    def test_stealth_and_no_stealth(self):
        lua = form_runtime("ROGUE", [("Stealth", True)])
        self.assertTrue(lua.eval('passes("1. Stealth")'))
        self.assertFalse(lua.eval('passes("0. No Stealth")'))
        lua.execute('forms[1].active = false')
        self.assertFalse(lua.eval('passes("1. Stealth")'))
        self.assertTrue(lua.eval('passes("0. No Stealth")'))

    def test_all_forms_and_retired_labels_never_hide(self):
        lua = form_runtime("ROGUE", [("Stealth", False)])
        for label in ("All", "All forms", "", "1. Bear", "No Aura", "1. Battle"):
            self.assertTrue(lua.eval('passes("%s")' % label), label)


if __name__ == '__main__':
    unittest.main()
