"""Reactive proc windows come from COMBAT_LOG_EVENT_UNFILTERED (ClassicAPI 1.17).

The real proc block of FostercareConditions.lua runs under Lua 5.1 with mock frames.
1.0.1 parsed English chat text and registered no combat-log event, so seven tests
fail on it; test_other_classes_do_not_listen is a control. Real server payloads
(OctoWoW) remain an in-game check.
"""
from pathlib import Path
import os
import unittest
from lupa.lua51 import LuaRuntime

ADDON = Path(os.environ["VANILLAFORGE_ADDON_ROOT"])
SOURCE = (ADDON / "Modules/FostercareConditions.lua").read_text("utf-8-sig")
ME, MOB, TWIN = "0xME", "0xMOB", "0xTWIN"


def runtime(cls, tracked):
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(r'''
        now = 100
        function GetTime() return now end
        function UnitClass() return playerClass, playerClass end
        targetGUID = nil
        function UnitGUID(unit)
            if unit == "player" then return "0xME" end
            if unit == "target" then return targetGUID end
        end
        function UnitExists(unit) return unit ~= "target" or targetGUID ~= nil end
        frames = {}
        function CreateFrame(kind, name)
            local f = { events = {}, scripts = {} }
            function f:RegisterEvent(ev) self.events[ev] = true end
            function f:SetScript(s, fn) self.scripts[s] = fn end
            if name then frames[name] = f end
            return f
        end
        FostercareAurasDB = { spells = {} }
        function fire(...)
            local f = frames.FostercareProcCL
            assert(f and f.events.COMBAT_LOG_EVENT_UNFILTERED, "no combat-log listener")
            for i = 1, 21 do _G["arg" .. i] = nil end
            for i = 1, select("#", ...) do _G["arg" .. i] = select(i, ...) end
            f.scripts.OnEvent()
        end
    ''')
    lua.execute('playerClass = "%s"' % cls)
    for i, name in enumerate(tracked):
        lua.execute('FostercareAurasDB.spells[%d] = { type = "Ability", name = "%s" }' % (i + 1, name))
    block = SOURCE[SOURCE.index('_G.FostercareConditions_ProcWindowDurations ='):
                   SOURCE.index('-- Helpers consumed by ability-usable override')]
    helpers = SOURCE[SOURCE.index('local function _Warrior_Overpower_OK()'):
                     SOURCE.index('-- FostercareAuras Slide Manager')]
    lua.execute('''
        local dirty_ability, dirty_ability_time = false, false
        local function _RequestImmediateEval() end
        local function _MarkSliderSeen() end
        local function _Now() return GetTime() end
    ''' + block + '\n' + helpers + r'''
        function remaining(name) return _ProcWindowRemaining(name) end
        function overpowerOK() return _Warrior_Overpower_OK() end
        function revengeOK() return _Warrior_Revenge_OK() end
    ''')
    return lua


def swing_missed(src, dst, miss):
    return ('fire(1, "SWING_MISSED", false, "%s", "a", 0, 0, "%s", "b", 0, 0, "%s")'
            % (src, dst, miss))


def spell_missed(src, dst, miss, kind="SPELL_MISSED"):
    return ('fire(1, "%s", false, "%s", "a", 0, 0, "%s", "b", 0, 0, 133, "Fireball", 4, "%s")'
            % (kind, src, dst, miss))


def damage(kind, src, dst, resisted="nil", blocked="nil", critical="nil"):
    if kind == "SWING_DAMAGE":
        return ('fire(1, "SWING_DAMAGE", false, "%s", "a", 0, 0, "%s", "b", 0, 0, 50, 0, 1, %s, %s, nil, %s)'
                % (src, dst, resisted, blocked, critical))
    return ('fire(1, "%s", false, "%s", "a", 0, 0, "%s", "b", 0, 0, 75, "Shot", 1, 50, 0, 1, %s, %s, nil, %s)'
            % (kind, src, dst, resisted, blocked, critical))


class WarriorTests(unittest.TestCase):
    def test_overpower_follows_the_unit_that_dodged_not_its_name(self):
        lua = runtime("WARRIOR", ["Overpower"])
        lua.execute(spell_missed(ME, MOB, "DODGE"))
        lua.execute('targetGUID = "%s"' % MOB)
        self.assertTrue(lua.eval('overpowerOK()'))
        self.assertAlmostEqual(lua.eval('remaining("Overpower")'), 4.0)
        lua.execute('targetGUID = "%s"' % TWIN)  # same name, different mob
        self.assertFalse(lua.eval('overpowerOK()'))

    def test_white_hit_dodge_opens_overpower(self):
        lua = runtime("WARRIOR", ["Overpower"])
        lua.execute(swing_missed(ME, MOB, "DODGE"))
        lua.execute('targetGUID = "%s"' % MOB)
        self.assertTrue(lua.eval('overpowerOK()'))

    def test_revenge_on_parry_and_partial_block_from_any_attacker(self):
        lua = runtime("WARRIOR", ["Revenge"])
        lua.execute(swing_missed("0xENEMYPLAYER", ME, "PARRY"))
        self.assertTrue(lua.eval('revengeOK()'))
        lua.execute('now = 200')
        self.assertFalse(lua.eval('revengeOK()'))
        lua.execute(damage("SWING_DAMAGE", MOB, ME, blocked=12))
        self.assertTrue(lua.eval('revengeOK()'))

    def test_untracked_and_other_units_open_nothing(self):
        lua = runtime("WARRIOR", [])
        lua.execute(spell_missed(ME, MOB, "DODGE"))
        self.assertIsNone(lua.eval('remaining("Overpower")'))
        lua = runtime("WARRIOR", ["Overpower", "Revenge"])
        lua.execute(swing_missed(MOB, "0xOTHER", "DODGE"))
        lua.execute(swing_missed(ME, MOB, "PARRY"))
        self.assertIsNone(lua.eval('remaining("Overpower")'))
        self.assertIsNone(lua.eval('remaining("Revenge")'))


class OtherClassTests(unittest.TestCase):
    def test_rogue_riposte_on_parry_and_surprise_attack_on_dodge(self):
        lua = runtime("ROGUE", ["Riposte", "Surprise Attack"])
        lua.execute(swing_missed(MOB, ME, "PARRY"))
        self.assertIsNotNone(lua.eval('remaining("Riposte")'))
        self.assertIsNone(lua.eval('remaining("Surprise Attack")'))
        lua.execute(swing_missed(ME, MOB, "DODGE"))
        self.assertIsNotNone(lua.eval('remaining("Surprise Attack")'))

    def test_mage_arcane_surge_on_full_or_partial_resist_only(self):
        lua = runtime("MAGE", ["Arcane Surge"])
        lua.execute(damage("SWING_DAMAGE", ME, MOB, resisted=5))
        self.assertIsNone(lua.eval('remaining("Arcane Surge")'))
        lua.execute(damage("SPELL_DAMAGE", ME, MOB, resisted=20))
        self.assertIsNotNone(lua.eval('remaining("Arcane Surge")'))
        lua = runtime("MAGE", ["Arcane Surge"])
        lua.execute(spell_missed(ME, MOB, "RESIST"))
        self.assertIsNotNone(lua.eval('remaining("Arcane Surge")'))

    def test_hunter_lacerate_on_ranged_crit(self):
        lua = runtime("HUNTER", ["Lacerate"])
        lua.execute(damage("RANGE_DAMAGE", ME, MOB))
        self.assertIsNone(lua.eval('remaining("Lacerate")'))
        lua.execute(damage("RANGE_DAMAGE", ME, MOB, critical=1))
        self.assertIsNotNone(lua.eval('remaining("Lacerate")'))

    def test_other_classes_do_not_listen(self):
        lua = runtime("PRIEST", [])
        self.assertIsNone(lua.eval('frames.FostercareProcCL'))


if __name__ == '__main__':
    unittest.main()
