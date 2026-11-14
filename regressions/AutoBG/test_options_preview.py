"""Opening Enemy Frames settings inside a battleground keeps the live list (audit 2026-10-19b, P3-10).

The complete AutoBG_Options.lua file runs under Lua 5.1 with generic widget
mocks and a stub enemy-frames module. Native panel behavior remains an in-game check.
"""
from pathlib import Path
import os
import unittest
from wowlua import LuaRuntime

import addon_loader

ROOT = Path(os.environ["VANILLAFORGE_ADDON_ROOT"])
OPTIONS = (ROOT / "AutoBG_Options.lua").read_text("utf-8-sig")

BASE = r'''
CLASSIC_API_VERSION, SUPERWOW_VERSION = 11711, "2.2"
local Widget = {}
-- Unknown keys on real frames are nil; only fields the panel checks before creating need this.
local DATA_FIELDS = { SelectionMark = true }
setmetatable(Widget, { __index = function(_, name)
    if not DATA_FIELDS[name] and string.find(name, "^%u") then return function() end end
end })
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
function Widget:Show()
    if self.shown then return end
    self.shown = true
    if self.scripts and self.scripts.OnShow then self.scripts.OnShow() end
end
function Widget:Hide() self.shown = false end
function Widget:GetValue() return 0 end
function Widget:SetFontString(fs) self.fontString = fs end
function Widget:GetFontString() return self.fontString end
function Widget:SetText(text) self.text = text end
function Widget:GetText() return self.text end
function GetAddOnMetadata() return "1.0.0" end
function Widget:CreateTexture() return setmetatable({}, { __index = Widget }) end
function Widget:CreateFontString() return setmetatable({}, { __index = Widget }) end
function CreateFrame(_, name, parent, template)
    local f = setmetatable({ name = name }, { __index = Widget })
    if name then
        _G[name] = f
        if template == "OptionsSliderTemplate" then
            for _, part in ipairs({ "Low", "High", "Text" }) do _G[name .. part] = CreateFrame("Frame", name .. part) end
        end
    end
    return f
end
UIParent = CreateFrame("Frame", "UIParent")
UISpecialFrames = {}
tinsert = table.insert
function UnitFactionGroup() return "Alliance" end
-- ClassicAPI's AddOn Options: categories in order, and the frames around them.
categories = {}
function InterfaceOptions_AddCategory(panel) table.insert(categories, panel) end
InterfaceOptionsFrame, GameMenuFrame = CreateFrame("Frame", "InterfaceOptionsFrame"), CreateFrame("Frame", "GameMenuFrame")
function HideUIPanel(f) f:Hide() end
previews = 0
local function Nothing() end
AutoBG_Targets = {
    activeBG = true, isConfig = false,
    EnsureOptions = Nothing, SetupButtonLayout = Nothing, ApplyRowFeatures = Nothing,
    RenderRoster = Nothing, ResetPosition = Nothing,
    EnableConfigMode = function() previews = previews + 1 end,
}
AutoBG_Spy = {
    EnsureOptions = function() AutoBG_Settings.Spy = AutoBG_Settings.Spy or {}; return AutoBG_Settings.Spy end,
    RenderRows = Nothing, ApplyScale = Nothing, ClearHistory = Nothing, ResetPosition = Nothing,
}
function AutoBG_ArenaOptions() AutoBG_Settings.Arena = AutoBG_Settings.Arena or {}; return AutoBG_Settings.Arena end
AutoBG_Arena, AutoBG_ArenaPets = { Refresh = Nothing }, { Refresh = Nothing }
AutoBG_MAX_ENTER_DELAY = 78
for _, name in ipairs({ "AutoBG_Timers_UpdateVisibility", "AutoBG_FC_UpdateVisibility", "AutoBG_LoadTimerPositions",
    "AutoBG_ResetTimerPositions", "AutoBG_ResetFCPositions", "AutoBG_Timers_SetPreview", "AutoBG_FC_SetPreview",
    "AutoBG_Print", "AutoBG_QueueAllBGs", "AutoBG_CancelAllQueues", "AutoBG_PlayNotificationSound",
    "AutoBG_StopNotificationSound" }) do _G[name] = Nothing end
-- What Targets:EnsureOptions fills on load.
local function Sizes(a, b) return { [10] = a, [15] = a, [40] = b, [5] = a } end
AutoBG_Settings = { Positions = {}, Targets = { EnableBracket = Sizes(true, true), ButtonHideRealm = Sizes(true, true),
                                ShowTrinket = Sizes(true, true), ButtonFontSize = Sizes(20, 11),
                                ButtonScale = Sizes(1, 0.9), ButtonWidth = Sizes(195, 210), ButtonHeight = Sizes(25, 20),
                                ButtonOpacity = {}, TrinketPos = "LEFT", ShowCastBars = true } }
'''


def runtime(in_battleground):
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(BASE)
    lua.execute('AutoBG_Targets.activeBG = %s' % ('true' if in_battleground else 'false'))
    addon_loader.load(lua, OPTIONS, "AutoBG_Options.lua")
    lua.execute('AutoBG_OpenOptions("targets")')
    return lua


class OptionsPreviewTests(unittest.TestCase):
    def test_enemy_frames_tab_keeps_the_live_list_in_a_battleground(self):
        self.assertEqual(runtime(in_battleground=True).eval('previews'), 0)

    def test_enemy_frames_tab_still_previews_outside_battlegrounds(self):
        self.assertEqual(runtime(in_battleground=False).eval('previews'), 1)


if __name__ == '__main__':
    unittest.main()
