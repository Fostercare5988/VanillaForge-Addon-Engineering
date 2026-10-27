"""Reactive proc windows come from COMBAT_LOG_EVENT_UNFILTERED (ClassicAPI 1.17).

The real proc block of FostercareConditions.lua runs under Lua 5.1 with mock frames.
1.0.1 parsed English chat text and registered no combat-log event. Since the
2026-10-27 rogue pass only the rogue's Riposte and Surprise Attack remain; the
Warrior, Mage and Hunter windows were removed, so other classes register no
listener. Real server payloads (OctoWoW) remain an in-game check.
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
                   SOURCE.index('-- FostercareAuras Slide Manager')]
    lua.execute('''
        local dirty_ability, dirty_ability_time = false, false
        local function _RequestImmediateEval() end
        local function _MarkSliderSeen() end
        local function _Now() return GetTime() end
    ''' + block + r'''
        function remaining(name) return _ProcWindowRemaining(name) end
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


class RogueTests(unittest.TestCase):
    def test_riposte_on_parry_and_surprise_attack_on_dodge(self):
        lua = runtime("ROGUE", ["Riposte", "Surprise Attack"])
        lua.execute(swing_missed(MOB, ME, "PARRY"))
        self.assertAlmostEqual(lua.eval('remaining("Riposte")'), 4.0)
        self.assertIsNone(lua.eval('remaining("Surprise Attack")'))
        lua.execute(spell_missed(ME, MOB, "DODGE"))
        self.assertIsNotNone(lua.eval('remaining("Surprise Attack")'))

    def test_untracked_and_other_units_open_nothing(self):
        lua = runtime("ROGUE", [])
        lua.execute(swing_missed(MOB, ME, "PARRY"))
        self.assertIsNone(lua.eval('remaining("Riposte")'))
        lua = runtime("ROGUE", ["Riposte", "Surprise Attack"])
        lua.execute(swing_missed(MOB, "0xOTHER", "PARRY"))
        lua.execute(damage("SWING_DAMAGE", MOB, ME, blocked=12))
        self.assertIsNone(lua.eval('remaining("Riposte")'))
        self.assertIsNone(lua.eval('remaining("Surprise Attack")'))


class OtherClassTests(unittest.TestCase):
    def test_other_classes_do_not_listen(self):
        for cls in ("WARRIOR", "MAGE", "HUNTER", "PRIEST"):
            lua = runtime(cls, ["Overpower", "Arcane Surge", "Lacerate"])
            self.assertIsNone(lua.eval('frames.FostercareProcCL'), cls)


if __name__ == '__main__':
    unittest.main()
