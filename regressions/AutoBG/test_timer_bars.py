"""Objective countdown bars: titles, faction colors, icons and group height.

The complete AutoBG_Timers.lua file runs under Lua 5.1 with generic widget mocks
in timer test mode. Textures, fonts and screen placement remain in-game checks.
"""
from pathlib import Path
import os
import re
import unittest
from lupa.lua51 import LuaRuntime

ROOT = Path(os.environ["VANILLAFORGE_ADDON_ROOT"])
TIMERS = (ROOT / "AutoBG_Timers.lua").read_text("utf-8-sig")

BASE = r'''
function table.wipe(t) for k in pairs(t) do t[k] = nil end return t end
CLASSIC_API_VERSION, SUPERWOW_VERSION = 11711, "2.2"
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

    def test_wsg_flags_use_faction_fill_and_banner_icons(self):
        lua = runtime()
        self.assertEqual(lua.eval('AutoBG_WSGFlagFrame.rows[1].labelFs.text'), "Alliance Flag")
        self.assertEqual(lua.eval('AutoBG_WSGFlagFrame.rows[1].icon.texture'), "Interface\\Icons\\INV_BannerPVP_02")
        alliance = list(lua.eval('AutoBG_WSGFlagFrame.rows[1].bar.color').values())
        horde = list(lua.eval('AutoBG_WSGFlagFrame.rows[2].bar.color').values())
        self.assertGreater(alliance[2], alliance[0])
        self.assertGreater(horde[0], horde[2])

    def test_start_timer_uses_neutral_icon(self):
        lua = runtime()
        self.assertEqual(lua.eval('AutoBG_StartTimerFrame.rows[1].icon.texture'), "Interface\\Icons\\INV_Misc_PocketWatch_01")
        self.assertEqual(lua.eval('AutoBG_StartTimerFrame.rows[1].timeFs.text'), "45")
        self.assertEqual(lua.eval('AutoBG_StartTimerFrame.rows[1].labelFs.text'), "Game Starts")

    def test_objectives_use_own_icons_in_their_side_color(self):
        lua = runtime()
        nodes = "Interface\\AddOns\\AutoBG\\Textures\\Nodes\\"
        self.assertEqual(lua.eval('AutoBG_NodeFrame.rows[1].icon.texture'), nodes + "Blacksmith_Horde")
        self.assertEqual(lua.eval('AutoBG_NodeFrame.rows[2].icon.texture'), nodes + "LumberMill_Alliance")
        self.assertEqual(lua.eval('AutoBG_AVNodeFrame.rows[1].icon.texture'), nodes + "Tower_Horde")
        self.assertEqual(lua.eval('AutoBG_AVNodeFrame.rows[2].icon.texture'), nodes + "Tower_Alliance")

    def test_every_objective_icon_file_exists(self):
        table = TIMERS[TIMERS.index("local NODE_KINDS"):TIMERS.index("local NODE_ICONS")]
        kinds = set(re.findall(r'= "(\w+)"', table))
        self.assertEqual(len(kinds), 8)
        for kind in kinds:
            for side in ("Alliance", "Horde", "Neutral"):
                self.assertTrue((ROOT / "Textures" / "Nodes" / f"{kind}_{side}.tga").is_file(), kind + side)

    def start_clock(self, line, event="CHAT_MSG_BG_SYSTEM_NEUTRAL"):
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute(BASE + r'''
            AutoBG_Settings.TestAllTimers = false
            function GetRealZoneText() return "Alterac Valley" end
            function IsInInstance() return 1, "pvp" end
        ''')
        lua.execute(TIMERS)
        lua.execute('local f = AutoBG_TimersEventFrame; f.scripts.OnEvent(f, "PLAYER_ENTERING_WORLD")')
        lua.globals().line, lua.globals().ev = line, event
        lua.execute('local f = AutoBG_TimersEventFrame; f.scripts.OnEvent(f, ev, line)')
        row = lua.eval('AutoBG_StartTimerFrame.rows[1]')
        return row.timeFs.text if row.shown else None

    def test_game_start_reads_until_the_battle_begins(self):
        # The OctoWoW line from the 2026-10-27 screenshot started no timer.
        self.assertEqual(self.start_clock("1 minute until the battle for Alterac Valley begins."), "1:00")
        self.assertEqual(self.start_clock("2 minutes until the battle for Alterac Valley begins."), "2:00")
        self.assertEqual(self.start_clock("30 seconds until the battle for Alterac Valley begins."), "30")
        self.assertEqual(self.start_clock("The battle for Arathi Basin begins in 1 minute."), "1:00")

    def test_game_close_warning_is_not_a_start(self):
        # "30 seconds" in the empty-game warning once showed a start timer.
        for n in (60, 45, 30, 15):
            self.assertIsNone(self.start_clock(f"Not enough players. This game will close in {n} seconds.",
                                               "CHAT_MSG_SYSTEM"))

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
