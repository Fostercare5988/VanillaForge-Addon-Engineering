"""Queue pop and match end (audit 2026-10-19b, P3-8 and P3-11).

The complete AutoBG.lua file runs under Lua 5.1 with generic widget mocks; the
StaticPopup_Show hook is called the way Blizzard's BattlefieldFrame calls it
(data = queue index). Native popup timing remains an in-game check.
"""
from pathlib import Path
import os
import unittest
from lupa.lua51 import LuaRuntime

ROOT = Path(os.environ["VANILLAFORGE_ADDON_ROOT"])
CORE = (ROOT / "AutoBG.lua").read_text("utf-8-sig")

BASE = r'''
function table.wipe(t) for k in pairs(t) do t[k] = nil end return t end
CLASSIC_API_VERSION, SUPERWOW_VERSION = 11707, "2.2"
local Widget = {}
setmetatable(Widget, { __index = function(_, name)
    if string.find(name, "^%u") then return function() end end
end })
function Widget:SetScript(kind, fn) self.scripts = self.scripts or {}; self.scripts[kind] = fn end
function Widget:GetScript(kind) return self.scripts and self.scripts[kind] end
function CreateFrame(_, name) local f = setmetatable({ name = name }, { __index = Widget }); if name then _G[name] = f end; return f end
UIParent = CreateFrame("Frame", "UIParent")
messages, ports, hooks, delayed, leaves = {}, {}, {}, {}, {}
DEFAULT_CHAT_FRAME = { AddMessage = function(_, msg) table.insert(messages, msg) end }
function hooksecurefunc(name, fn) hooks[name] = fn end
local handle = { Cancel = function() end }
C_Timer = { After = function(_, fn) table.insert(delayed, fn) end,
            NewTimer = function() return handle end, NewTicker = function() return handle end }
C_UnitAuras = { GetAuraDataBySpellName = function() end, GetPlayerAuraBySpellID = function() end }
SlashCmdList = {}
MAX_BATTLEFIELD_QUEUES = 3
statuses = {}
function GetBattlefieldStatus(i) local s = statuses[i]; if s then return s[1], s[2] end; return "none" end
function AcceptBattlefieldPort(id, accept) table.insert(ports, { id = id, accept = accept }) end
function GetTime() return 1000 end
zone, pvp = "Orgrimmar", false
function GetRealZoneText() return zone end
function IsInInstance() if pvp then return 1, "pvp" end return nil, "none" end
function UnitIsAFK() return nil end
function UnitExists() return 1 end
function UnitIsDeadOrGhost() return nil end
winner = nil
function GetBattlefieldWinner() return winner end
function PlaySound() end
function StaticPopup_Hide() end
function SpellStopCasting() end
function SpellStopTargeting() end
function ClearTarget() end
function LeaveBattlefield(...) table.insert(leaves, select("#", ...)) end
'''


def runtime():
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(BASE)
    lua.execute(CORE)
    lua.execute('AutoBGFrame.scripts.OnEvent(AutoBGFrame, "ADDON_LOADED", "AutoBG")')
    return lua


def fire(lua, event, arg=None):
    value = 'nil' if arg is None else repr(arg)
    lua.execute('AutoBGFrame.scripts.OnEvent(AutoBGFrame, "%s", %s)' % (event, value))


class AutoAcceptTests(unittest.TestCase):
    def accepted(self, lua):
        lua.execute('n = 0; for _, p in ipairs(ports) do if p.accept == 1 then n = n + 1 end end')
        lua.execute('m = 0; for _, s in ipairs(messages) do if string.find(s, "Auto%-Accepted") then m = m + 1 end end')
        return lua.eval('n'), lua.eval('m')

    def test_instant_accept_happens_once_when_the_popup_shows_first(self):
        lua = runtime()
        lua.execute('AutoBG_Settings.AutoAccept = true; AutoBG_Settings.AutoAcceptDelay = 0')
        lua.execute('statuses[1] = { "confirm", "Warsong Gulch" }')
        # Blizzard's BattlefieldFrame handler runs before AutoBG's and shows the popup.
        lua.execute('hooks.StaticPopup_Show("CONFIRM_BATTLEFIELD_ENTRY", "Warsong Gulch", nil, 1)')
        fire(lua, "UPDATE_BATTLEFIELD_STATUS")
        lua.execute('hooks.StaticPopup_Show("CONFIRM_BATTLEFIELD_ENTRY", "Warsong Gulch", nil, 1)')
        self.assertEqual(self.accepted(lua), (1, 1))

    def test_longest_delay_still_enters_before_an_octowow_invite_runs_out(self):
        # OctoWoW invites ran out after 79 s in play; a saved 119 s delay lost one.
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute(BASE)
        lua.execute(CORE)
        lua.execute('AutoBG_Settings = { AutoAccept = true, AutoAcceptDelay = 119 }')
        fire(lua, "ADDON_LOADED", "AutoBG")
        self.assertEqual(lua.eval('AutoBG_Settings.AutoAcceptDelay'), 79)
        lua.execute('statuses[1] = { "confirm", "Arathi Basin" }')
        fire(lua, "UPDATE_BATTLEFIELD_STATUS")
        lua.execute('m = 0; for _, s in ipairs(messages) do if string.find(s, "Entering in |cFFFFFF0079s", 1, true) then m = m + 1 end end')
        self.assertEqual(lua.eval('m'), 1)

    def test_auto_accept_off_never_accepts(self):
        lua = runtime()
        lua.execute('statuses[1] = { "confirm", "Warsong Gulch" }')
        lua.execute('hooks.StaticPopup_Show("CONFIRM_BATTLEFIELD_ENTRY", "Warsong Gulch", nil, 1)')
        fire(lua, "UPDATE_BATTLEFIELD_STATUS")
        self.assertEqual(self.accepted(lua), (0, 0))


class DefaultSettingsTests(unittest.TestCase):
    def test_new_install_starts_with_the_chosen_countdown_look(self):
        lua = runtime()
        look = [lua.eval('AutoBG_Settings.%s' % k) for k in ("ObjectiveWidth", "ObjectiveHeight", "ObjectiveScale", "ObjectiveOpacity")]
        self.assertEqual(look, [225, 25, 1, 0.9])

    def test_saved_countdown_look_is_kept(self):
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute(BASE)
        lua.execute(CORE)
        lua.execute('AutoBG_Settings = { ObjectiveWidth = 300 }')
        fire(lua, "ADDON_LOADED", "AutoBG")
        self.assertEqual(lua.eval('AutoBG_Settings.ObjectiveWidth'), 300)


class AutoLeaveTests(unittest.TestCase):
    def test_auto_leave_calls_leavebattlefield_like_framexml(self):
        lua = runtime()
        lua.execute('zone, pvp = "Warsong Gulch", true')
        fire(lua, "PLAYER_ENTERING_WORLD")
        lua.execute('winner = 1')
        fire(lua, "CHAT_MSG_BG_SYSTEM_NEUTRAL", "The Alliance wins!")
        lua.execute('for _, fn in ipairs(delayed) do fn() end')
        self.assertEqual(list(lua.eval('leaves').values()), [0])


if __name__ == '__main__':
    unittest.main()
