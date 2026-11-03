"""!ErrorLog sees its blind spots (1.3.0, 2026-11-03).

Stratholme: a 1.3 s freeze and nine 116-198 ms frames in combat, each with
0 ms of addon time, while the player saw the drops as NPCs died. Three things
were invisible: hooksecurefunc hooks and the game's own (XML) handlers were
never timed, and the slow frame was taken from the engine's elapsed while the
handlers were charged since the profiler's last tick, two windows that need not
match. Now hooks go to their addon, XML scripts to "Game UI and XML" (each call
only its own time), the frame time is the profiler's clock between ticks, and
every slow frame keeps the events that fired in it.

Runs Profiler.lua under Lua 5.1 with widget mocks, a clock the test moves and a
native-style hooksecurefunc. Real engine dispatch order stays an in-game check.
"""
from pathlib import Path
import os
import unittest
from lupa.lua51 import LuaRuntime

ROOT = Path(os.environ["VANILLAFORGE_ADDON_ROOT"])

BASE = r"""
heap, clockv, now = 50000, 0, 100
GAME = "Interface\\FrameXML\\TargetFrame.lua:1: in function"
stack = GAME
function gcinfo() return heap end
function debugprofilestop() return clockv end
function debugstack() return stack end
function GetTime() return now end
function date() return "11:37:50" end
function GetRealZoneText() return "Stratholme" end
function UnitAffectingCombat() return 1 end
function GetNumRaidMembers() return 0 end
function GetNumPartyMembers() return 4 end
function ReloadUI() end
function table.wipe(t) for k in pairs(t) do t[k] = nil end return t end
SlashCmdList = {}

local kinds, all = {}, {}
function CreateFrame(kind, name)
    kind = kind or "Frame"
    local index = kinds[kind]
    if not index then
        index = {}
        function index:SetScript(s, fn)
            self.scripts[s] = fn
            if s == "OnUpdate" and stack ~= GAME then driver, tick = self, fn end
        end
        function index:GetScript(s) return self.scripts[s] end
        function index:GetName() return self.name end
        function index:Hide() end
        function index:RegisterEvent() end
        function index:RegisterAllEvents() counter = self end
        kinds[kind] = index
    end
    local f = setmetatable({ scripts = {}, name = name }, { __index = index })
    table.insert(all, f)
    if name then _G[name] = f end
    return f
end
function EnumerateFrames(after)
    if not after then return all[1] end
    for i, f in ipairs(all) do if f == after then return all[i + 1] end end
end

-- The engine's hooksecurefunc: the hook runs after the function.
hooks = {}
function hooksecurefunc(a, b, c)
    local name, fn = a, b
    if type(a) ~= "string" then name, fn = b, c end
    hooks[name] = hooks[name] or {}
    table.insert(hooks[name], fn)
end
function TargetFrame_Update()
    for _, h in ipairs(hooks.TargetFrame_Update or {}) do h() end
end

ErrorLog = { onLoad = {}, Print = function() end }
function ErrorLog.ShowReport(report) _, _, text = report() end
"""

LOAD = r"""
    stack = "Interface\\AddOns\\!ErrorLog\\Profiler.lua:1: in function"
    ErrorLog.onLoad[1](db)
    -- The game's target frame, its handler from XML: no addon in the stack.
    stack = GAME
    local target = CreateFrame("Frame", "TargetFrame")
    gameHandler = function() clockv = clockv + 5; TargetFrame_Update() end
    target:SetScript("OnEvent", gameHandler)
    -- An addon follows TargetFrame_Update with a slow hook.
    stack = "Interface\\AddOns\\FostercareTweaks\\mods\\x.lua:117: in function"
    hooksecurefunc("TargetFrame_Update", function() clockv = clockv + 150 end)
    stack = "Interface\\AddOns\\!ErrorLog\\Profiler.lua:1: in function"
    event = "PLAYER_LOGIN"; driver.scripts.OnEvent()
"""

DEATH = r"""
    now = now + 10 -- past the quiet seconds after login
    tick()
    TargetFrame.scripts.OnEvent()
    for _ = 1, 3 do counter.scripts.OnEvent(counter, "UNIT_DIED") end
    counter.scripts.OnEvent(counter, "PLAYER_TARGET_CHANGED")
    clockv = clockv + 10
    tick(nil, 0.016) -- the engine's elapsed says a normal frame
"""


def load():
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(BASE)
    lua.execute((ROOT / "Profiler.lua").read_text("utf-8-sig"))
    lua.execute("db = { profile = true }")
    lua.execute(LOAD)
    return lua


class BlindSpots(unittest.TestCase):
    def test_slow_frame_comes_from_the_profilers_clock(self):
        lua = load()
        lua.execute(DEATH)
        self.assertEqual(lua.eval("#db.hitches"), 1)
        self.assertEqual(lua.eval("db.hitches[1].ms"), 165)

    def test_hook_goes_to_its_addon_and_the_game_handler_keeps_only_its_own_time(self):
        lua = load()
        lua.execute(DEATH)
        top = lua.eval("db.hitches[1].top")
        self.assertIn("FostercareTweaks 150.0 ms over 1 calls (worst x.lua:117 hook TargetFrame_Update)", top)
        self.assertIn("Game UI and XML 5.0 ms over 1 calls (worst TargetFrame OnEvent)", top)
        self.assertEqual(lua.eval("db.hitches[1].lua"), 155)

    def test_slow_frame_keeps_its_events(self):
        lua = load()
        lua.execute(DEATH)
        self.assertEqual(lua.eval("db.hitches[1].events"), "UNIT_DIED x3, PLAYER_TARGET_CHANGED x1")
        lua.execute("ErrorLog.OpenStutters()")
        self.assertIn("events: UNIT_DIED x3, PLAYER_TARGET_CHANGED x1", lua.eval("text"))

    def test_events_are_counted_per_frame(self):
        lua = load()
        lua.execute(DEATH)
        lua.execute(r"""
            counter.scripts.OnEvent(counter, "UNIT_HEALTH")
            clockv = clockv + 16; tick()
            now = now + 2 -- a new stutter, not the same run
            TargetFrame.scripts.OnEvent()
            clockv = clockv + 10; tick()
        """)
        self.assertEqual(lua.eval("#db.hitches"), 2)
        self.assertEqual(lua.eval("db.hitches[1].events"), None)

    def test_wrapped_game_handler_still_reads_as_the_original(self):
        lua = load()
        self.assertTrue(lua.eval("TargetFrame:GetScript('OnEvent') == gameHandler"))
        self.assertTrue(lua.eval("TargetFrame.scripts.OnEvent ~= gameHandler"))

    def test_profilers_own_frames_stay_unwrapped(self):
        lua = load()
        self.assertTrue(lua.eval("driver.scripts.OnUpdate == tick"))
        lua.execute("now = now + 10; clockv = 0; tick(); clockv = 200; tick()")
        self.assertEqual(lua.eval("db.hitches[1].lua"), 0)


if __name__ == "__main__":
    unittest.main()
