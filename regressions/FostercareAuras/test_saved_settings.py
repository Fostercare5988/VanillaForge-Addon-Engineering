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
        self.assertIsNone(lua.eval('FostercareAurasDB.spells.rup.conditions.aura.auraConditions'))

    def test_other_classes_forms_and_weapon_filter_are_cleared(self):
        # 2026-10-27 rogue pass: only Stealth / No Stealth remain.
        lua = load('{ spells = {'
                   '  a = { type = "Ability", conditions = { ability = { form = "1. Battle", weaponFilter = "Two-Hand" } } },'
                   '  b = { type = "Buff", conditions = { aura = { form = "1. Stealth" } } } } }')
        self.assertEqual(lua.eval('FostercareAurasDB.spells.a.conditions.ability.form'), 'All')
        self.assertIsNone(lua.eval('FostercareAurasDB.spells.a.conditions.ability.weaponFilter'))
        self.assertEqual(lua.eval('FostercareAurasDB.spells.b.conditions.aura.form'), '1. Stealth')

    def test_rare_rules_and_runtime_flags_are_cleared(self):
        # 2026-10-27 rogue pass: sounds, group state, HP, distance, unit type,
        # extra condition lists; and the sound gate that leaked into saves.
        lua = load('{ spells = { r = { type = "Debuff", _daSoundGate = false, conditions = { aura = {'
                   '  mode = "found", onlyMine = true, grouping = "raid", inRaid = true, hpMode = "my", hpVal = 30,'
                   '  targetDistance = "Behind", targetUnitType = "Boss", soundOnGain = "x.ogg", soundOnGainEnabled = true,'
                   '  auraConditions = { {} }, vfxConditions = { {} } } } } } }')
        for field in ("grouping", "inRaid", "hpMode", "hpVal", "targetDistance", "targetUnitType",
                      "soundOnGain", "soundOnGainEnabled", "auraConditions", "vfxConditions"):
            self.assertIsNone(lua.eval('FostercareAurasDB.spells.r.conditions.aura.%s' % field), field)
        self.assertIsNone(lua.eval('FostercareAurasDB.spells.r._daSoundGate'))
        self.assertEqual(lua.eval('FostercareAurasDB.spells.r.conditions.aura.mode'), 'found')
        self.assertTrue(lua.eval('FostercareAurasDB.spells.r.conditions.aura.onlyMine'))


    def test_icon_cache_keeps_only_tracker_names(self):
        # 2026-10-27: the cache held every spell, mount and companion in the book.
        lua = load('{ cache = { Rupture = "r", ["Black War Kodo"] = "k", Cooking = "c", ["Slice and Dice"] = "s" },'
                   ' spells = { a = { type = "Debuff", displayName = "Rupture" },'
                   '            b = { type = "Buff", displayName = "Slice and Dice" } } }')
        self.assertEqual(lua.eval('FostercareAurasDB.cache.Rupture'), 'r')
        self.assertEqual(lua.eval('FostercareAurasDB.cache["Slice and Dice"]'), 's')
        self.assertIsNone(lua.eval('FostercareAurasDB.cache["Black War Kodo"]'))
        self.assertIsNone(lua.eval('FostercareAurasDB.cache.Cooking'))

if __name__ == '__main__':
    unittest.main()
