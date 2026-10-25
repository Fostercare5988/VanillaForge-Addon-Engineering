"""The ForgeUI settings window (2026-10-25), replacing Options, UnitFrameOptions,
RaidFrameOptions, ActionBarOptions and SettingsWidgets.

ForgeUI.lua and Settings.lua run with widget stand-ins. Looks, clicks and the
AddOn Options entry stay in-game checks.
"""
from pathlib import Path
import os
import unittest
from lupa.lua51 import LuaRuntime

ROOT = Path(os.environ["VANILLAFORGE_ADDON_ROOT"])

BASE = r'''
widgets = {}
local Widget = {}
local Meta = { __index = function(_, k)
    if Widget[k] then return Widget[k] end
    if string.find(k, "^%u") then return function() end end
end }
function CreateFrame(kind, name)
    local w = setmetatable({ kind = kind, name = name, scripts = {}, shown = true }, Meta)
    if name then widgets[name] = w; _G[name] = w end
    return w
end
function Widget:SetScript(k, f) self.scripts[k] = f end
function Widget:GetScript(k) return self.scripts[k] end
function Widget:Show() self.shown = true; if self.scripts.OnShow then self.scripts.OnShow(self) end end
function Widget:Hide() self.shown = false; if self.scripts.OnHide then self.scripts.OnHide(self) end end
function Widget:IsShown() return self.shown end
function Widget:CreateTexture() return setmetatable({ scripts = {} }, Meta) end
function Widget:CreateFontString() return setmetatable({ scripts = {} }, Meta) end
function Widget:SetText(t) self.text = t end
function Widget:GetText() return self.text end
function Widget:SetFontString(f) self.fs = f end
function Widget:GetFontString() return self.fs end
function Widget:SetChecked(v) self.checked = v and true or false end
function Widget:GetChecked() return self.checked end
function Widget:Enable() self.enabled = true end
function Widget:Disable() self.enabled = false end
function Widget:SetValue(v) self.value = v end
function Widget:GetValue() return self.value end
function Widget:SetAlpha(a) self.alpha = a end
-- A native checkbutton toggles itself before OnClick runs.
function Widget:Click()
    if self.kind == "CheckButton" then self.checked = not self.checked end
    self.scripts.OnClick(self)
end
UIParent, UISpecialFrames = CreateFrame("Frame", "UIParent"), {}
function GetAddOnMetadata() return "1.5.0" end
function ReloadUI() reloaded = true end
categories = {}
function InterfaceOptions_AddCategory(panel) table.insert(categories, panel) end

FostercareTweaks_Config = { overwrites = {} }
local FT = { mods = {} }
FostercareTweaks = FT
function FT.IsEnabled(key, default)
    local v = FostercareTweaks_Config[key]
    if v == nil then return default == true end
    return v == 1
end
function FT.GetOverride(key, default)
    local v = FostercareTweaks_Config.overwrites[key]
    if v == nil then return default end
    return v
end
function FT.ClampNumber(v, d, lo, hi) v = tonumber(v) or d; return math.max(lo, math.min(hi, v)) end
function FT.GetNumber(key, d, lo, hi) return FT.ClampNumber(FT.GetOverride(key), d, lo, hi) end
function FT.SetOverride(key, v) FostercareTweaks_Config.overwrites[key] = v end
function FT.HookScript(frame, script, fn)
    local old = frame.scripts[script]
    frame.scripts[script] = function(...) if old then old(...) end; fn(...) end
end
function FT.SetEventHandler(frame, fn) frame.scripts.OnEvent = fn end
calls = {}
local function Count(name) return function() calls[name] = (calls[name] or 0) + 1 end end
for _, title in ipairs({ "Hide Stealth / Stance Bar", "Hide Default Cast Bar", "Unit Frame Class Colors", "Enemy Castbars" }) do
    FT.mods[title] = { apply = Count(title) }
end
raidTest, groupEnabled = false, true
FT.UnitFrames = {
    ApplyConfiguration = Count("ApplyConfiguration"),
    UpdateAllRaidFrames = Count("UpdateAllRaidFrames"),
    GetGroupDimensions = function() return { enabled = groupEnabled, width = 64, height = 34, scale = 1, spacingX = 4, spacingY = 3 } end,
    ApplyGroupDimensions = function(_, w, h, s, x, y, enabled) applied = { w, h, s, x, y, enabled } end,
    GetRaidHealthFormat = function() return FT.GetOverride("raid_health_format", "deficit") end,
    ToggleRaidTest = function() raidTest = not raidTest end,
    IsRaidTest = function() return raidTest end,
    Auras = { RefreshBorders = Count("RefreshBorders") },
}
FT.ActionBars = { enabled = false, editing = false, bars = {}, definitions = {
    { id = "main", title = "Main", prefix = "Action", columns = 12 },
    { id = "extra", title = "Extra Row 1", prefix = "FCTweaksExtra", columns = 12, extraIndex = 1 },
} }
function FT.ActionBars:GetSettings(id) self.settings = self.settings or {}; self.settings[id] = self.settings[id] or {}; return self.settings[id] end
function FT.ActionBars:SetEnabled(v) self.enabled = v end
function FT.ActionBars:SetEditing(v) if v and not self.enabled then return end; self.editing = v end
function FT.ActionBars:SetValue(id, k, v) self:GetSettings(id)[k] = v end
function FT.ActionBars:ResetBar() end
'''


def window():
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(BASE)
    ns = lua.table()
    for name in ("ForgeUI.lua", "Settings.lua"):
        lua.execute((ROOT / name).read_text("utf-8-sig"), "FostercareTweaks", ns)
    return lua


class SettingsWindow(unittest.TestCase):
    def test_opens_on_every_page(self):
        lua = window()
        for name in ("general", "unit", "auras", "raid", "bars"):
            lua.execute('FostercareTweaks.OpenSettings("%s")' % name)
            self.assertTrue(lua.eval('FostercareTweaksSettingsGUI:IsShown()'))

    def test_listed_in_addon_options(self):
        lua = window()
        self.assertEqual(lua.eval('categories[1].name'), "FostercareTweaks")

    def test_live_switch_applies_without_reload(self):
        lua = window()
        lua.execute('FostercareTweaks.OpenSettings("general"); widgets.FTOpt_HideStealthStanceBar:Click()')
        self.assertEqual(lua.eval('FostercareTweaks_Config["Hide Stealth / Stance Bar"]'), 1)
        self.assertEqual(lua.eval('calls["Hide Stealth / Stance Bar"]'), 1)

    def test_reload_feature_asks_for_reload(self):
        lua = window()
        lua.execute('FostercareTweaks.OpenSettings("general")')
        self.assertFalse(lua.eval('widgets.FTOptReload1.shown'))
        lua.execute('widgets.FTOpt_VendorValues:Click()')
        self.assertEqual(lua.eval('FostercareTweaks_Config["Vendor Values"]'), 1)
        self.assertTrue(lua.eval('widgets.FTOptReload1.shown'))
        self.assertTrue(lua.eval('widgets.FTOptReload5.shown'))

    def test_raid_buff_switch_without_saved_count(self):
        """P2-1 (old RaidFrameOptions): the switch on a profile that never saved
        raid_buff_count must refresh the raid frames."""
        lua = window()
        lua.execute('FostercareTweaks.OpenSettings("raid"); widgets.FTOpt_ShowAllRaidBuffs:Click()')
        self.assertEqual(lua.eval('calls.UpdateAllRaidFrames'), 1)

    def test_raid_master_switch(self):
        lua = window()
        lua.execute('FostercareTweaks.OpenSettings("raid"); widgets.FTOpt_RaidFrames:Click()')
        self.assertFalse(lua.eval('applied[6]'))

    def test_move_bars_needs_layouts(self):
        lua = window()
        lua.execute('FostercareTweaks.OpenSettings("bars"); widgets.FTOpt_MoveBars:Click()')
        self.assertFalse(lua.eval('FostercareTweaks.ActionBars.editing'))
        lua.execute('widgets.FTOpt_Layouts:Click(); widgets.FTOpt_MoveBars:Click()')
        self.assertTrue(lua.eval('FostercareTweaks.ActionBars.editing'))
        lua.execute('FostercareTweaksSettingsGUI:Hide()')
        self.assertFalse(lua.eval('FostercareTweaks.ActionBars.editing'))


if __name__ == "__main__":
    unittest.main()
