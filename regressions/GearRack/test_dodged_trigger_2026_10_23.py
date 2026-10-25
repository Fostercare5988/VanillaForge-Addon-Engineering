"""GEARRACK_DODGED: Overpower templates from the combat log (ClassicAPI 1.17).

The real registration and dispatch code runs under Lua 5.1 with a recording
register frame. The first release had no GEARRACK_DODGED trigger and read
chat text, so these tests fail on it. Real combat-log payloads remain an
in-game check.
"""
from pathlib import Path
import os
import unittest
from lupa.lua51 import LuaRuntime

ROOT = Path(os.environ["VANILLAFORGE_ADDON_ROOT"])
EQUIPMENT = (ROOT / "src/Equipment.lua").read_text("utf-8")
EVENTS = (ROOT / "src/Events.lua").read_text("utf-8")


def between(text, start, end):
    return text[text.index(start):text.index(end)]


def runtime():
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(r'''
        registered, ran = {}, {}
        GearRackUI_RegisterFrame = {
            RegisterEvent = function(_, ev) registered[ev] = true end,
            UnregisterEvent = function(_, ev) registered[ev] = nil end,
        }
        GearRackUI = { Register = {}, CancelEvent = function() end }
        GearRackDB = { events = {
            Begin = { trigger = "GEARRACK_DODGED", delay = 0, script = "" },
            Log = { trigger = "COMBAT_LOG_EVENT_UNFILTERED", delay = 0, script = "" },
        } }
        function UnitGUID(unit) if unit == "player" then return "0xME" end end
        function GetTime() return 100 end
        function fire(...)
            for i = 1, 21 do _G["arg" .. i] = nil end
            for i = 1, select("#", ...) do _G["arg" .. i] = select(i, ...) end
            event = "COMBAT_LOG_EVENT_UNFILTERED"
            GearRackUI_RegisterFrame_OnEvent(event)
        end
    ''')
    lua.execute('''
        local function event_is_enabled() return true end
        local function run_event_script(name, a1) table.insert(ran, name .. ":" .. tostring(a1)) end
    ''' + between(EQUIPMENT, '-- GEARRACK_DODGED rides on the combat log',
                  '-- use this to initialize, enable or refresh Register')
      + between(EQUIPMENT, 'function GearRackUI_RegisterFrame_OnEvent(',
                '-- Restore the equipment displaced'))
    return lua


def events_runtime():
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute('GearRack = { enabled = true }')
    lua.execute(EVENTS)
    return lua


class DodgedTriggerTests(unittest.TestCase):
    def test_own_dodged_swing_spell_and_shot_fire_with_the_dodger_guid(self):
        lua = runtime()
        lua.execute('GearRackUI_EnableEvent("Begin")')
        lua.execute('fire(1, "SWING_MISSED", false, "0xME", "me", 0, 0, "0xMOB", "mob", 0, 0, "DODGE")')
        lua.execute('fire(1, "SPELL_MISSED", false, "0xME", "me", 0, 0, "0xMOB2", "mob", 0, 0, 1, "X", 1, "DODGE")')
        lua.execute('fire(1, "RANGE_MISSED", false, "0xME", "me", 0, 0, "0xMOB3", "mob", 0, 0, 75, "Shoot", 1, "DODGE")')
        self.assertEqual(list(lua.eval('ran').values()), ["Begin:0xMOB", "Begin:0xMOB2", "Begin:0xMOB3"])

    def test_parries_and_other_units_dodges_do_not_fire(self):
        lua = runtime()
        lua.execute('GearRackUI_EnableEvent("Begin")')
        lua.execute('fire(1, "SWING_MISSED", false, "0xME", "me", 0, 0, "0xMOB", "mob", 0, 0, "PARRY")')
        lua.execute('fire(1, "SWING_MISSED", false, "0xMOB", "mob", 0, 0, "0xME", "me", 0, 0, "DODGE")')
        self.assertEqual(len(lua.eval('ran')), 0)

    def test_combat_log_is_registered_only_while_needed(self):
        lua = runtime()
        lua.execute('GearRackUI_EnableEvent("Begin")')
        self.assertTrue(lua.eval('registered.COMBAT_LOG_EVENT_UNFILTERED'))
        lua.execute('GearRackUI_EnableEvent("Log"); GearRackUI_DisableEvent("Begin")')
        self.assertTrue(lua.eval('registered.COMBAT_LOG_EVENT_UNFILTERED'), "user's own combat-log event lost")
        lua.execute('GearRackUI_EnableEvent("Begin"); GearRackUI_DisableEvent("Log")')
        self.assertTrue(lua.eval('registered.COMBAT_LOG_EVENT_UNFILTERED'), "GEARRACK_DODGED lost its source")
        lua.execute('GearRackUI_DisableEvent("Begin")')
        self.assertIsNone(lua.eval('registered.COMBAT_LOG_EVENT_UNFILTERED'))


class TemplateTests(unittest.TestCase):
    def test_overpower_templates_use_the_combat_log_trigger(self):
        lua = events_runtime()
        begin = lua.eval('GearRackUI_DefaultEvents["Warrior:Overpower Begin"]')
        end = lua.eval('GearRackUI_DefaultEvents["Warrior:Overpower End"]')
        self.assertEqual(begin.trigger, "GEARRACK_DODGED")
        self.assertNotIn("string.find", begin.script)
        self.assertEqual(end.trigger, "GEARRACK_DODGED")
        self.assertEqual(end.delay, 5)


if __name__ == '__main__':
    unittest.main()
