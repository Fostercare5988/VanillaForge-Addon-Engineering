"""Objective countdown bars: titles, faction colors, icons and group height.

The complete AutoBG_Timers.lua file runs under Lua 5.1 with generic widget mocks
in timer test mode. Textures, fonts and screen placement remain in-game checks.
"""
from pathlib import Path
import os
import unittest
from lupa.lua51 import LuaRuntime

ROOT = Path(os.environ["VANILLAFORGE_ADDON_ROOT"])
TIMERS = (ROOT / "AutoBG_Timers.lua").read_text("utf-8-sig")

BASE = r'''
function table.wipe(t) for k in pairs(t) do t[k] = nil end return t end
CLASSIC_API_VERSION, SUPERWOW_VERSION = 11707, "2.2"
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
function Widget:SetHeight(h) self.height = h end
function Widget:SetTexture(t) self.texture = t end
function Widget:SetStatusBarColor(r, g, b) self.color = { r, g, b } end
function Widget:CreateTexture() return setmetatable({}, { __index = Widget }) end
function Widget:CreateFontString() return setmetatable({}, { __index = Widget }) end
function CreateFrame(_, name) local f = setmetatable({ name = name }, { __index = Widget }); if name then _G[name] = f end; return f end
UIParent = CreateFrame("Frame", "UIParent")
local handle = { Cancel = function() end }
C_Timer = { After = function() end, NewTimer = function() return handle end, NewTicker = function() return handle end }
MAX_BATTLEFIELD_QUEUES = 3
function GetBattlefieldStatus() return "none" end
function GetTime() return 1000 end
function GetRealZoneText() return "Orgrimmar" end
function IsInInstance() return nil, "none" end
function UnitFactionGroup() return "Alliance" end
function GetNumWorldStateUI() return 0 end
AutoBG_Settings = { TestAllTimers = true, ABTimers = true, AVTimers = true, WSGTimers = true,
                    StartTimer = true, NodeColors = true, ABProjection = false,
                    RessTimer = false, QueueTimers = false }
'''


def runtime():
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(BASE)
    lua.execute(TIMERS)
    lua.execute('AutoBG_Timers_UpdateVisibility()')
    return lua


class TimerBarTests(unittest.TestCase):
    def test_groups_are_titled_by_battleground(self):
        lua = runtime()
        self.assertEqual(lua.eval('AutoBG_NodeFrame.titleFs.text'), "Arathi Basin")
        self.assertEqual(lua.eval('AutoBG_AVNodeFrame.titleFs.text'), "Alterac Valley")
        self.assertEqual(lua.eval('AutoBG_WSGFlagFrame.titleFs.text'), "Warsong Gulch")
        self.assertIsNone(lua.eval('AutoBG_StartTimerFrame.titleFs'))

    def test_wsg_flags_use_faction_fill_and_flag_icons(self):
        lua = runtime()
        self.assertEqual(lua.eval('AutoBG_WSGFlagFrame.rows[1].labelFs.text'), "Alliance Flag")
        self.assertEqual(lua.eval('AutoBG_WSGFlagFrame.rows[1].icon.texture'), "Interface\\WorldStateFrame\\AllianceFlag")
        alliance = list(lua.eval('AutoBG_WSGFlagFrame.rows[1].bar.color').values())
        horde = list(lua.eval('AutoBG_WSGFlagFrame.rows[2].bar.color').values())
        self.assertGreater(alliance[2], alliance[0])
        self.assertGreater(horde[0], horde[2])

    def test_start_timer_uses_neutral_icon(self):
        lua = runtime()
        self.assertEqual(lua.eval('AutoBG_StartTimerFrame.rows[1].icon.texture'), "Interface\\Icons\\INV_Misc_PocketWatch_01")
        self.assertEqual(lua.eval('AutoBG_StartTimerFrame.rows[1].timeFs.text'), "0:45")

    def test_open_world_arathi_highlands_is_not_arathi_basin(self):
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute(BASE + r'''
            AutoBG_Settings.TestAllTimers = false
            AutoBG_Settings.ABProjection = true
            function GetRealZoneText() return "Arathi Highlands" end
            worldStateReads = 0
            function GetNumWorldStateUI() worldStateReads = worldStateReads + 1; return 0 end
        ''')
        lua.execute(TIMERS)
        lua.execute('local f = AutoBG_TimersEventFrame; f.scripts.OnEvent(f, "PLAYER_ENTERING_WORLD")')
        self.assertEqual(lua.eval('worldStateReads'), 0)

    def test_group_height_fits_title_and_rows(self):
        lua = runtime()
        # 15 title + 2 rows * 25 (the default bar height) + 1 gap * 2
        self.assertEqual(lua.eval('AutoBG_WSGFlagFrame.height'), 67)


if __name__ == '__main__':
    unittest.main()
