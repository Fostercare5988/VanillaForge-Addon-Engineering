"""Opening Enemy Frames settings inside a battleground keeps the live list (audit 2026-10-19b, P3-10).

The complete AutoBG_Options.lua file runs under Lua 5.1 with generic widget
mocks and a stub enemy-frames module. Native panel behavior remains an in-game check.
"""
from pathlib import Path
import os
import unittest
from lupa.lua51 import LuaRuntime

import addon_loader

ROOT = Path(os.environ["VANILLAFORGE_ADDON_ROOT"])
OPTIONS = (ROOT / "AutoBG_Options.lua").read_text("utf-8-sig")

BASE = r'''
CLASSIC_API_VERSION, SUPERWOW_VERSION = 11707, "2.2"
local Widget = {}
-- Unknown keys on real frames are nil; only fields the panel checks before creating need this.
local DATA_FIELDS = { SelectionMark = true }
setmetatable(Widget, { __index = function(_, name)
    if not DATA_FIELDS[name] and string.find(name, "^%u") then return function() end end
end })
function Widget:SetScript(kind, fn) self.scripts = self.scripts or {}; self.scripts[kind] = fn end
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
previews = 0
AutoBG_Targets = {
    activeBG = true, isConfig = false,
    EnsureOptions = function() end,
    EnableConfigMode = function() previews = previews + 1 end,
}
AutoBG_Spy = {}
AutoBG_Settings = { Targets = { EnableBracket = {}, ButtonHideRealm = {}, ButtonShowHealthText = {},
                                DimStealthed = {}, ShowTrinket = {}, ButtonFontSize = {},
                                ButtonScale = {}, ButtonWidth = {}, ButtonHeight = {} } }
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
