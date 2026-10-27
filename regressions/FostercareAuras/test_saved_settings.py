"""SavedVariables init block of FostercareAuras.lua, run on an existing profile.

FostercareAurasDB.settings was read for group spacing but nothing ever wrote it,
so the retired table is cleared on load (fails on 1.1.0-local). Kept settings must
survive unchanged.
"""
from pathlib import Path
import os
import unittest
from lupa.lua51 import LuaRuntime

ADDON = Path(os.environ["VANILLAFORGE_ADDON_ROOT"])
SOURCE = (ADDON / "FostercareAuras.lua").read_text("utf-8-sig")


def load(profile):
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute('FostercareAurasDB = ' + profile)
    start = SOURCE.index('-- SavedVariables init')
    lua.execute(SOURCE[start:SOURCE.index('\n', SOURCE.index('FostercareAuras = FostercareAuras or {}'))])
    return lua


class SavedSettingsTests(unittest.TestCase):
    def test_retired_settings_table_is_cleared(self):
        lua = load('{ settings = { spacing = 12 }, spells = {} }')
        self.assertIsNone(lua.eval('FostercareAurasDB.settings'))

    def test_kept_settings_survive(self):
        lua = load('{ spells = { a = { type = "Buff" } }, showtooltip = false }')
        self.assertEqual(lua.eval('FostercareAurasDB.spells.a.type'), 'Buff')
        self.assertFalse(lua.eval('FostercareAurasDB.showtooltip'))

    def test_retired_features_are_cleared(self):
        # 2026-10-27: groups, categories, bars, custom code, logic, pet, pfUI retired.
        lua = load('{ pfuiBorder = true, groupSort = { g = "time" }, categories = { "c" },'
                   ' npDurationsCP = { [1] = {} }, spells = {'
                   '  bar = { type = "Bar" }, code = { type = "Custom" },'
                   '  rup = { type = "Debuff", group = "g1", isLeader = true, conditions = { aura = {'
                   '    trackpet = true, auraConditions = { { logicOp = "OR", parenOpen = true } } } } } } }')
        for field in ("pfuiBorder", "groupSort", "categories", "npDurationsCP"):
            self.assertIsNone(lua.eval('FostercareAurasDB.%s' % field), field)
        self.assertIsNone(lua.eval('FostercareAurasDB.spells.bar'))
        self.assertIsNone(lua.eval('FostercareAurasDB.spells.code'))
        self.assertEqual(lua.eval('FostercareAurasDB.spells.rup.type'), 'Debuff')
        self.assertIsNone(lua.eval('FostercareAurasDB.spells.rup.group'))
        self.assertIsNone(lua.eval('FostercareAurasDB.spells.rup.conditions.aura.trackpet'))
        self.assertIsNone(lua.eval('FostercareAurasDB.spells.rup.conditions.aura.auraConditions[1].logicOp'))


if __name__ == '__main__':
    unittest.main()
