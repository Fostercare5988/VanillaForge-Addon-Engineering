"""Spell tables checked against octowow.st/db: racial casts, stealth and trinkets.

Spy names a caster's race from a race-only spell when UnitRace has no answer,
by the spell's name so every rank counts. On OctoWoW, 10793, 10795 and 10796
are mounts, not racials, and 8342, 23133 and 23134 are not stealth effects.
"""
import unittest

import test_spy_nearby as spy_base
import test_targets_guid_events as targets_base

SPELLS = r'''
spellNames = { [20594] = "Stoneform", [9035] = "Hex of Weakness", [10793] = "Striped Nightsaber",
               [10795] = "Ivory Raptor", [11327] = "Vanish", [8342] = "Defibrillate" }
function GetSpellInfo(id) return spellNames[id] end
function UnitRace() return nil end
'''


def spy_runtime():
    lua = spy_base.runtime()
    lua.execute(SPELLS)
    lua.execute('''
        races = {}
        local record = AutoBG_Spy.RecordEnemy
        function AutoBG_Spy:RecordEnemy(name, c, l, guid, hp, st, sn, race, ...)
            races[name] = race or false
            return record(self, name, c, l, guid, hp, st, sn, race, ...)
        end''')
    return lua


def cast(lua, guid, name, spell):
    lua.execute('names["%s"] = "%s"' % (guid, name))
    spy_base.fire(lua, "UNIT_CASTEVENT", guid, "", "CAST", spell, 0)
    return lua.eval('races["%s"]' % name)


class RacialSpellTests(unittest.TestCase):
    def test_racial_spell_names_the_race(self):
        lua = spy_runtime()
        self.assertEqual(cast(lua, "0x0000000000000004", "Brann", 20594), "Dwarf")
        self.assertEqual(cast(lua, "0x0000000000000005", "Zul", 9035), "Troll")

    def test_mounts_do_not_name_a_race(self):
        lua = spy_runtime()
        self.assertFalse(cast(lua, "0x0000000000000004", "Rider", 10793))
        self.assertFalse(cast(lua, "0x0000000000000005", "Raptor", 10795))


class StealthAndTrinketTableTests(unittest.TestCase):
    def setUp(self):
        self.lua = targets_base.runtime()

    def stealth(self, spell):
        return self.lua.eval('(AutoBG_Targets.CheckIsStealthSpell(%d))' % spell)

    def test_vanish_aura_counts_as_stealth(self):
        self.assertTrue(self.stealth(11327))

    def show(self, spell, name, icon):
        self.lua.execute('function GetSpellInfo() return "%s", "", "%s" end' % (name, icon))
        targets_base.fire(self.lua, "UNIT_CASTEVENT", targets_base.GROM, "", "CAST", spell, 0)
        return (targets_base.row_text(self.lua), self.lua.eval('AutoBG_TargetButton1.stealthTexture'))

    def test_each_kind_of_hiding_shows_its_own_label_and_icon(self):
        icon = "Icons/Ability_Vanish"
        self.assertEqual(self.show(1856, "Vanish", icon), ("|cffd2c2ffVANISH|r", icon))
        self.setUp()
        icon = "Icons/INV_Potion_112"
        self.assertEqual(self.show(11392, "Invisibility", icon), ("|cff00ffffINVIS POT|r", icon))
        self.setUp()
        icon = "Icons/INV_Misc_EngGizmos_06"
        self.assertEqual(self.show(4079, "Cloaking", icon), ("|cff00ffffCLOAK|r", icon))

    def test_wrong_old_ids_are_not_stealth(self):
        for spell in (8342, 23133, 23134):
            self.assertFalse(self.stealth(spell), spell)


if __name__ == '__main__':
    unittest.main()
