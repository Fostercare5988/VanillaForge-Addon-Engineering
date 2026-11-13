"""Spirit healer wave: what syncs the respawn countdown and drops its "~".

The complete AutoBG_Timers.lua file runs under Lua 5.1 with widget mocks inside
a battleground. Whether OctoWoW runs one wave for the whole battleground stays
an in-game check.
"""
from pathlib import Path
import os
import unittest
from wowlua import LuaRuntime
from clock_mock import CLOCK

ROOT = Path(os.environ["VANILLAFORGE_ADDON_ROOT"])
TIMERS = (ROOT / "AutoBG_Timers.lua").read_text("utf-8-sig")

BASE = r'''
function AutoBG_QueueMap(map) return map end
function table.wipe(t) for k in pairs(t) do t[k] = nil end return t end
CLASSIC_API_VERSION, SUPERWOW_VERSION = 11711, "2.2"
-- AutoBG.lua's shared helpers (loaded before this file in the client).
function AutoBG_SavePosition() end
function AutoBG_LoadPosition() end
function AutoBG_FindPlayerClass(name) return name and playerClasses and playerClasses[name] end
function AutoBG_GetClassColor() return nil end
function AutoBG_GetBGIcon() return nil end
function GetAreaSpiritHealerTime() return 0 end
local Widget = {}
setmetatable(Widget, { __index = function(_, name)
    if string.find(name, "^%u") then return function() end end
end })
function Widget:SetText(text) self.text = text end
function Widget:SetScript(kind, fn)
    self.scripts = self.scripts or {}
    local raw = fn
    -- The client also sets the legacy globals before a script runs.
    if kind == "OnEvent" and fn then
        fn = function(s, ev, ...)
            event = ev
            if select("#", ...) > 0 then arg1, arg2, arg3, arg4, arg5, arg6, arg7 = ... end
            return raw(s, ev, ...)
        end
    elseif kind == "OnUpdate" and fn then
        fn = function(s, dt) arg1 = dt or arg1 or 0; return raw(s, dt) end
    end
    self.scripts[kind] = fn
end
function Widget:IsShown() return self.shown end
function Widget:Show() self.shown = true end
function Widget:Hide() self.shown = false end
function Widget:GetName() return self.name end
function Widget:GetStringWidth() return 0 end
function Widget:GetWidth() return 100 end
function Widget:CreateTexture() return setmetatable({}, { __index = Widget }) end
function Widget:CreateFontString() return setmetatable({}, { __index = Widget }) end
function CreateFrame(_, name) local f = setmetatable({ name = name }, { __index = Widget }); if name then _G[name] = f end; return f end
UIParent = CreateFrame("Frame", "UIParent")
local handle = { Cancel = function() end }
tickers = {}
Enum = { StatusBarInterpolation = { Immediate = 0 }, StatusBarTimerDirection = { ElapsedTime = 0, RemainingTime = 1 } }
C_DurationUtil = { CreateDuration = function() return { SetTimeSpan = function(self, s, e) self.startTime, self.endTime = s, e end } end }
function Widget:SetTimerDuration(d, i, dir) self.timer, self.timerDirection = d, dir; self.fillValue = nil end
function Widget:SetMinMaxValues(lo, hi) self.timer = nil; self.maxValue = hi end
function Widget:SetValue(v) self.fillValue = v end
C_Timer = { After = function() end, NewTimer = function() return handle end,
            NewTicker = function(_, fn) table.insert(tickers, fn); return handle end }
MAX_BATTLEFIELD_QUEUES = 3
function GetBattlefieldStatus() return "none" end
now = 1000
function GetTime() return now end
function GetRealZoneText() return "Warsong Gulch" end
function IsInInstance() return 1, "pvp" end
function UnitFactionGroup() return "Alliance" end
function GetNumWorldStateUI() return 0 end
ghosts = {}
function GetNumRaidMembers() return 2 end
function UnitIsGhost(u) return ghosts[u] end
function UnitIsDeadOrGhost(u) return ghosts[u] end
AutoBG_Settings = { RessTimer = true }
''' + CLOCK


def runtime():
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(BASE)
    lua.execute(TIMERS)
    fire(lua, "PLAYER_ENTERING_WORLD")
    return lua


def fire(lua, event, arg=None):
    value = 'nil' if arg is None else repr(arg)
    lua.execute('AutoBG_TimersEventFrame.scripts.OnEvent(AutoBG_TimersEventFrame, "%s", %s)' % (event, value))


def respawn_text(lua, at):
    lua.execute('now = %s; for _, fn in ipairs(tickers) do fn() end; __frame()' % at)
    return lua.eval('AutoBG_RespawnFrame.rows[1].timeFs.text')


class SpiritWaveTests(unittest.TestCase):
    def test_unsynced_countdown_is_marked_as_a_guess(self):
        lua = runtime()
        self.assertIn("~", respawn_text(lua, 1005))

    def test_own_return_from_ghost_syncs_the_wave(self):
        lua = runtime()
        lua.execute('now = 1003')
        fire(lua, "PLAYER_UNGHOST")
        text = respawn_text(lua, 1013)
        self.assertNotIn("~", text)
        self.assertEqual(text, "20")

    def test_teammate_ghost_revival_syncs_the_wave(self):
        lua = runtime()
        lua.execute('ghosts.raid2 = true')
        respawn_text(lua, 1001)  # the once-a-second scan learns the ghost
        lua.execute('now = 1007; ghosts.raid2 = nil')
        fire(lua, "UNIT_HEALTH", "raid2")
        text = respawn_text(lua, 1017)
        self.assertNotIn("~", text)
        self.assertEqual(text, "20")

    def test_health_of_someone_who_was_never_a_ghost_does_not_sync(self):
        lua = runtime()
        respawn_text(lua, 1001)
        fire(lua, "UNIT_HEALTH", "raid1")
        self.assertIn("~", respawn_text(lua, 1005))

    def test_the_enemy_frames_get_the_next_wave(self):
        # 2026-11-13: dead enemies count down to it (test_enemy_respawn.py).
        lua = runtime()
        lua.execute('now = 1003')
        fire(lua, "PLAYER_UNGHOST")
        lua.execute('now = 1013')
        self.assertEqual(list(lua.eval('{AutoBG_NextSpiritWave()}').values()), [1033, True])

    def test_the_wave_is_followed_with_the_bar_off(self):
        # Fails on 6623680: with Spirit healer waves off nothing ran in Warsong.
        lua = runtime()
        lua.execute('AutoBG_Settings.RessTimer = false; function GetAreaSpiritHealerTime() return 10 end')
        fire(lua, "PLAYER_ENTERING_WORLD")
        lua.execute('now = 1005; for _, fn in ipairs(tickers) do fn() end')
        self.assertEqual(list(lua.eval('{AutoBG_NextSpiritWave()}').values()), [1015, True])


if __name__ == '__main__':
    unittest.main()
