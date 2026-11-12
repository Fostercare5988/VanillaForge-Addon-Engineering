"""!ErrorLog 1.6.0 records an addon's steps to disk to find a freeze, 2026-11-12.

A freeze loses everything in memory, so /trace writes each step of the named
addon with WriteCustomFile as it happens: its own functions always, other
global and C_ functions only inside them, and the event that led there once.
/trace off takes every hook out again, the setting survives a reload, and two
files take turns so the newest lines are kept. Runs ErrorLog.lua and Trace.lua
on the shared game model; the real file on disk stays a game check.
"""
from pathlib import Path
import os
import unittest

import wowkit

ROOT = Path(os.environ["VANILLAFORGE_ADDON_ROOT"])

BASE = r'''
function geterrorhandler() return function() end end
function seterrorhandler() end
function date() return "2026-11-12 10:00:00" end
function GetRealZoneText() return "Orgrimmar" end
function GetCallstackHeight() return 2 end
function GetErrorCallstackHeight() return 2 end
function debugstack() return "" end
function debuglocals() end
GameTooltip = newWidget("GameTooltip", "GameTooltip")
files = {}
function WriteCustomFile(name, text, mode)
    if mode == "w" then files[name] = {} end
    table.insert(files[name], text)
end
local create = CreateFrame
function CreateFrame(...)
    local f = create(...)
    function f:RegisterAllEvents() self:RegisterEvent("MAIL_SHOW"); self:RegisterEvent("BAG_UPDATE") end
    return f
end

-- A small addon: two globals, a table of functions, and game calls inside.
C_Container = { GetContainerNumFreeSlots = function(bag) return 4, 0 end }
function GetContainerNumSlots(bag) return 16 end
function Bagnon_Count(bag) return GetContainerNumSlots(bag) + C_Container.GetContainerNumFreeSlots(bag) end
function BagnonFrame_Open(name) return Bagnon_Count(0) end
BagnonDB = { GetMoney = function(player) return 5 end }
function Banknon_Boom() error("boom") end
realOpen, realSlots, realFree, realFloor = BagnonFrame_Open, GetContainerNumSlots, C_Container.GetContainerNumFreeSlots, floor
'''

A, B = "ErrorLogTraceA.txt", "ErrorLogTraceB.txt"


def load(saved="ErrorLog_DB = nil"):
    lua = wowkit.runtime()
    lua.execute(BASE)
    lua.execute(saved)
    wowkit.load_files(lua, ROOT, ["ErrorLog.lua", "Trace.lua"], "!ErrorLog")
    lua.execute('fire("ADDON_LOADED", "!ErrorLog"); fire("PLAYER_LOGIN"); chat = {}')
    return lua


def trace(lua, text=""):
    lua.globals().SlashCmdList.ERRORLOGTRACE(text)
    return " / ".join(lua.eval("chat").values())


def written(lua, name=A):
    return [line.split(" ", 2)[2].rstrip("\n") for line in lua.eval(f"files['{name}']").values()][1:]


class Trace(unittest.TestCase):
    def test_in_toc(self):
        lines = [l.strip() for l in (ROOT / "!ErrorLog.toc").read_text("utf-8-sig").splitlines()]
        self.assertGreater(lines.index("Trace.lua"), lines.index("ErrorLog.lua"))

    def test_off_until_started(self):
        lua = load()
        self.assertTrue(lua.eval("BagnonFrame_Open == realOpen and GetContainerNumSlots == realSlots"))
        self.assertIn("trace is off", trace(lua))
        self.assertIsNone(lua.eval("files['%s']" % A))

    def test_records_the_addon_and_the_game_calls_inside_it(self):
        lua = load()
        self.assertIn("recording Bagnon", trace(lua, "Bagnon"))
        self.assertEqual(lua.eval('BagnonFrame_Open("Bagnon")'), 20)
        self.assertEqual(written(lua), [
            '>BagnonFrame_Open("Bagnon")',
            "  >Bagnon_Count(0)",
            "    >GetContainerNumSlots(0)",
            "    <GetContainerNumSlots = 16",
            "    >C_Container.GetContainerNumFreeSlots(0)",
            "    <C_Container.GetContainerNumFreeSlots = 4, 0",
            "  <Bagnon_Count = 20",
            "<BagnonFrame_Open = 20",
        ])

    def test_game_calls_outside_the_addon_are_not_recorded(self):
        lua = load()
        trace(lua, "Bagnon")
        lua.execute("GetContainerNumSlots(1); C_Container.GetContainerNumFreeSlots(1)")
        self.assertEqual(written(lua), [])

    def test_tables_of_the_addon_and_a_second_name(self):
        lua = load()
        trace(lua, "bagnon Banknon")
        lua.execute('BagnonDB.GetMoney("Claude"); pcall(Banknon_Boom)')
        self.assertEqual(written(lua)[:3], ['>BagnonDB.GetMoney("Claude")', "<BagnonDB.GetMoney = 5", ">Banknon_Boom()"])

    def test_the_event_before_the_first_step_is_written_once(self):
        lua = load()
        trace(lua, "Bagnon")
        lua.execute('fire("BAG_UPDATE", 2); fire("MAIL_SHOW"); Bagnon_Count(1); Bagnon_Count(1)')
        lines = written(lua)
        self.assertEqual(lines[0], "EVENT MAIL_SHOW nil nil")
        self.assertEqual(sum(l.startswith("EVENT") for l in lines), 1)

    def test_lua_and_library_functions_are_left_alone(self):
        lua = load()
        trace(lua, "Bagnon")
        self.assertTrue(lua.eval("floor == realFloor"))
        self.assertTrue(lua.eval("WriteCustomFile ~= nil and BagnonFrame_Open ~= realOpen"))

    def test_off_takes_the_hooks_out(self):
        lua = load()
        trace(lua, "Bagnon")
        lua.execute("chat = {}")
        self.assertIn("trace off", trace(lua, "off"))
        self.assertTrue(lua.eval("BagnonFrame_Open == realOpen and GetContainerNumSlots == realSlots"))
        self.assertTrue(lua.eval("C_Container.GetContainerNumFreeSlots == realFree"))
        self.assertIsNone(lua.eval("ErrorLog_DB.trace"))
        lua.execute("Bagnon_Count(0)")
        self.assertEqual(written(lua), [])

    def test_a_hook_someone_put_over_ours_stays_and_passes_through(self):
        lua = load()
        trace(lua, "Bagnon")
        lua.execute('''
            local ours = BagnonFrame_Open
            function BagnonFrame_Open(name) return ours(name) + 1 end
            theirs = BagnonFrame_Open
        ''')
        trace(lua, "off")
        self.assertTrue(lua.eval("BagnonFrame_Open == theirs"))
        self.assertEqual(lua.eval('BagnonFrame_Open("Bagnon")'), 21)
        self.assertEqual(written(lua), [])

    def test_stays_on_across_a_reload(self):
        lua = load()
        trace(lua, "Bagnon")
        self.assertEqual(lua.eval("ErrorLog_DB.trace"), "Bagnon")
        again = load('ErrorLog_DB = { errors = {}, session = 1, trace = "Bagnon" }')
        again.execute("Bagnon_Count(0)")
        self.assertEqual(written(again)[0], ">Bagnon_Count(0)")

    def test_an_unknown_name_starts_nothing(self):
        lua = load()
        self.assertIn("no function starts with Nothere", trace(lua, "Nothere"))
        self.assertTrue(lua.eval("GetContainerNumSlots == realSlots"))
        self.assertIsNone(lua.eval("ErrorLog_DB.trace"))

    def test_an_error_inside_does_not_leave_game_calls_recorded(self):
        lua = load()
        trace(lua, "Banknon")
        lua.execute("pcall(Banknon_Boom); step(0.1); GetContainerNumSlots(1)")
        lines = written(lua)  # the model's own step() is a global too, so it shows
        self.assertEqual(lines[0], ">Banknon_Boom()")
        self.assertFalse(any("GetContainerNumSlots" in l for l in lines), lines)

    def test_the_two_files_take_turns(self):
        lua = load()
        trace(lua, "Bagnon")
        lua.execute("for i = 1, 5001 do BagnonFrame_Open(i) end")  # 8 lines a call: 40008
        self.assertIn("part 3", lua.eval("files['%s'][1]" % A))
        self.assertIn("part 2", lua.eval("files['%s'][1]" % B))
        self.assertEqual(written(lua)[-1], "<BagnonFrame_Open = 20")


if __name__ == "__main__":
    unittest.main()
