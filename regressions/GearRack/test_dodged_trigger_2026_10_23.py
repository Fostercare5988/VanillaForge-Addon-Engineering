"""GEARRACK_DODGED: Overpower presets from the combat log (GearRack 1.1.0, ClassicAPI 1.17).

The real registration, dispatch and migration code runs under Lua 5.1 with a
recording register frame. 1.0.0 has no GEARRACK_DODGED trigger and kept the
chat-text presets, so the dispatch, registration and migration tests fail on it;
test_edited_preset_is_left_alone is a control. Real combat-log payloads remain
an in-game check.
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


def events_runtime(saved):
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute('GearRack = { enabled = true }; GearRackDB = { events = {} }')
    lua.execute(EVENTS)
    for name, (trigger, delay, script) in saved.items():
        lua.globals().GearRackDB.events[name] = lua.table_from(
            {"trigger": trigger, "delay": delay, "script": script})
    lua.execute('GearRackUI_MigrateDefaultEvents()')
    return lua


OLD_BEGIN = ("--[[Equip a set when the opponent dodges.  Associate a heavy-hitting 2h set with this event. ]]\n"
             "local _,_,i = GetShapeshiftFormInfo(1)\nif string.find(arg1 or \"\",\"^You.+dodge[sd]\") and i then\n"
             "GearRack.EquipSet()\nGEARRACK_OVERPOWER=1\nend")
OLD_END = ("--[[Equip a set five seconds after opponent dodged: your normal weapons. ]]\n"
           "if GEARRACK_OVERPOWER==1 then\nGearRack.EquipSet()\nGEARRACK_OVERPOWER=nil\nend")


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


class MigrationTests(unittest.TestCase):
    def test_stock_chat_text_presets_move_to_the_new_trigger(self):
        lua = events_runtime({
            "Warrior:Overpower Begin": ("CHAT_MSG_COMBAT_SELF_MISSES", 0, OLD_BEGIN),
            "Warrior:Overpower End": ("CHAT_MSG_COMBAT_SELF_MISSES", 5, OLD_END),
        })
        begin = lua.eval('GearRackDB.events["Warrior:Overpower Begin"]')
        end = lua.eval('GearRackDB.events["Warrior:Overpower End"]')
        self.assertEqual(begin.trigger, "GEARRACK_DODGED")
        self.assertNotIn("string.find", begin.script)
        self.assertEqual(end.trigger, "GEARRACK_DODGED")
        self.assertEqual(end.delay, 5)

    def test_edited_preset_is_left_alone(self):
        lua = events_runtime({
            "Warrior:Overpower Begin": ("CHAT_MSG_COMBAT_SELF_MISSES", 0, OLD_BEGIN + " -- mine"),
        })
        self.assertEqual(lua.eval('GearRackDB.events["Warrior:Overpower Begin"].trigger'),
                         "CHAT_MSG_COMBAT_SELF_MISSES")


if __name__ == '__main__':
    unittest.main()
