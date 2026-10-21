"""Spirit healer wave: what syncs the respawn countdown and drops its "~".

The complete AutoBG_Timers.lua file runs under Lua 5.1 with widget mocks inside
a battleground. Whether OctoWoW runs one wave for the whole battleground stays
an in-game check.
"""
from pathlib import Path
import os
import unittest
from lupa.lua51 import LuaRuntime

ROOT = Path(os.environ["VANILLAFORGE_ADDON_ROOT"])
TIMERS = (ROOT / "AutoBG_Timers.lua").read_text("utf-8-sig")

BASE = r'''
function table.wipe(t) for k in pairs(t) do t[k] = nil end return t end
CLASSIC_API_VERSION, SUPERWOW_VERSION = 11600, "2.2"
local Widget = {}
setmetatable(Widget, { __index = function(_, name)
    if string.find(name, "^%u") then return function() end end
end })
function Widget:SetText(text) self.text = text end
function Widget:SetScript(kind, fn) self.scripts = self.scripts or {}; self.scripts[kind] = fn end
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
'''


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
    lua.execute('now = %s; for _, fn in ipairs(tickers) do fn() end' % at)
    return lua.eval('AutoBG_RespawnFrame.timeText.text')


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
        self.assertIn("0:20", text)

    def test_teammate_ghost_revival_syncs_the_wave(self):
        lua = runtime()
        lua.execute('ghosts.raid2 = true')
        respawn_text(lua, 1001)  # the once-a-second scan learns the ghost
        lua.execute('now = 1007; ghosts.raid2 = nil')
        fire(lua, "UNIT_HEALTH", "raid2")
        text = respawn_text(lua, 1017)
        self.assertNotIn("~", text)
        self.assertIn("0:20", text)

    def test_health_of_someone_who_was_never_a_ghost_does_not_sync(self):
        lua = runtime()
        respawn_text(lua, 1001)
        fire(lua, "UNIT_HEALTH", "raid1")
        self.assertIn("~", respawn_text(lua, 1005))


if __name__ == '__main__':
    unittest.main()
