"""!ErrorLog garbage per addon (1.1.0, 2026-10-26).

From a Dire Maul /lag report: ten collections in 17 minutes, each a 100+ ms
frame, and GearRack listed with 94.9 ms because a collection started inside
its handler. The profiler now charges new Lua memory to the addon whose
handler made it, and says when a collection started inside a handler.

Runs Profiler.lua under Lua 5.1 with a stub ErrorLog, widget mocks and a Lua
memory counter the test controls. Real collector timing stays an in-game check.
"""
from pathlib import Path
import os
import unittest
from lupa.lua51 import LuaRuntime

ROOT = Path(os.environ["VANILLAFORGE_ADDON_ROOT"])

BASE = r'''
heap, clockv, now = 50000, 0, 100
stack = "Interface\\AddOns\\!ErrorLog\\Profiler.lua:307: in function"
function gcinfo() return heap end
function debugprofilestop() return clockv end
function debugstack() return stack end
function GetTime() return now end
function date() return "12:00:00" end
function GetRealZoneText() return "Dire Maul" end
function UnitAffectingCombat() return 1 end
function GetNumRaidMembers() return 0 end
function GetNumPartyMembers() return 2 end
function ReloadUI() end
SlashCmdList = {}
local kinds = {}
function CreateFrame(kind)
    kind = kind or "Frame"
    local index = kinds[kind]
    if not index then
        index = { scripts = nil }
        function index:SetScript(s, fn)
            self.scripts[s] = fn
            if s == "OnUpdate" then tick = fn end -- only the profiler's driver sets one
        end
        function index:GetScript(s) return self.scripts[s] end
        function index:Hide() end
        function index:RegisterEvent() end
        kinds[kind] = index
    end
    return setmetatable({ scripts = {} }, { __index = index })
end
ErrorLog = { onLoad = {}, Print = function() end }
function ErrorLog.ShowReport(report) _, _, text = report() end

-- A handler set by `addon` that makes `kb` of new memory in `ms`.
function handler(addon, kb, ms)
    stack = "Interface\\AddOns\\" .. addon .. "\\Core.lua:10: in function"
    local f = CreateFrame("Frame")
    f:SetScript("OnEvent", function() heap = heap + kb; clockv = clockv + (ms or 0) end)
    stack = "Interface\\AddOns\\!ErrorLog\\Profiler.lua:1: in function"
    return f.scripts.OnEvent
end
'''


def load():
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(BASE)
    lua.execute((ROOT / "Profiler.lua").read_text("utf-8-sig"))
    lua.execute('ErrorLog.onLoad[1]({ profile = true })')
    return lua


SESSION = '''
    local gear, lazy = handler("GearRack", 30), handler("AutoLazy", 5)
    collect = handler("GearRack", -12000, 95)
    tick(nil, 0.016)
    now = now + 10
    for _ = 1, 10 do gear(nil, "BAG_UPDATE"); lazy(nil, "BAG_UPDATE") end
    tick(nil, 0.016)
    collect(nil, "UNIT_INVENTORY_CHANGED")
    tick(nil, 0.107)
    ErrorLog.OpenStutters()
'''


class GarbagePerAddon(unittest.TestCase):
    def report(self):
        lua = load()
        lua.execute(SESSION)
        return lua.eval("text")

    def test_addons_ranked_by_new_memory(self):
        text = self.report()
        gear = text.index("KB/s  GearRack")
        lazy = text.index("KB/s  AutoLazy")
        self.assertLess(gear, lazy)
        self.assertIn("30.0 KB/s  GearRack", text)
        self.assertIn("5.0 KB/s  AutoLazy", text)

    def test_collection_names_the_handler_it_started_in(self):
        text = self.report()
        self.assertIn("freed 11.7 MB (Lua memory 37 MB), started inside GearRack", text)
        self.assertIn("worst one held a garbage collection", text)


if __name__ == "__main__":
    unittest.main()
