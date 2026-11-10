"""The ForgeUI settings window (2026-10-25), replacing Options, UnitFrameOptions,
RaidFrameOptions, ActionBarOptions and SettingsWidgets.

ForgeUI.lua and Settings.lua run with widget stand-ins. Looks, clicks and the
AddOn Options entry stay in-game checks.
"""
from pathlib import Path
import os
import unittest
from wowlua import LuaRuntime

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
function Widget:SetParent(p) self.parent = p end
function Widget:SetWidth(w) self.width = w end
function Widget:GetWidth() return self.width or 420 end
function Widget:SetScale(s) self.scale = s end
function Widget:SetPoint(...) self.pt = { ... } end
function GetSpellInfo(id) return id, "", "icon-" .. tostring(id) end
InterfaceOptionsFrame, GameMenuFrame = CreateFrame("Frame", "InterfaceOptionsFrame"), CreateFrame("Frame", "GameMenuFrame")
InterfaceOptionsFrame.shown, GameMenuFrame.shown = false, false
function HideUIPanel(f) f:Hide() end

FostercareTweaks_Config = { overwrites = {} }
local FT = { mods = {} }
FostercareTweaks = FT
--SETTINGS--
function FT.HookScript(frame, script, fn)
    local old = frame.scripts[script]
    frame.scripts[script] = function(...) if old then old(...) end; fn(...) end
end
function FT.SetEventHandler(frame, fn) frame.scripts.OnEvent = fn end
calls = {}
local function Count(name) return function() calls[name] = (calls[name] or 0) + 1 end end
for _, title in ipairs({ "Hide Stealth / Stance Bar", "Hide Default Cast Bar", "Unit Frame Class Colors", "Enemy Castbars",
    "Auto Stance", "MiniMap Clock", "Chat Timestamps", "Chat Class Colors", "Blue Shaman Class Colors",
    "Hide Gryphons", "Reagent Counter" }) do
    FT.mods[title] = { apply = Count(title) }
end
-- A switch's default is its module's (FT:register); these are on.
for _, title in ipairs({ "Show Standard Buffs", "Show Standard Debuffs", "Show Weapon Enchants",
    "Show Weapon Enchant Borders", "Show Group Labels", "Show Raid Buffs", "Show Raid Aggro Indicator",
    "Show Raid HoT Indicator", "Show Raid Debuff Badges", "Show Energy Ticks" }) do
    FT.mods[title] = { enabled = true }
end
FT.mods["Show All Raid Buffs"] = { enabled = false }
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
watched = {}
FT.WatchedAuras = { List = function() return watched end,
    Add = function(name, unit) table.insert(watched, { name = name, unit = unit, mine = unit == "target" or nil }) end,
    Remove = function(i) table.remove(watched, i) end,
    SetMine = function(i, v) watched[i].mine = v and true or nil end,
    SetShown = function(i, place, v) if place == "icon" then watched[i].noIcon = not v or nil else watched[i][place] = v and true or nil end end }
'''


def window():
    lua = LuaRuntime(unpack_returned_tuples=True)
    helpers = (ROOT / "Helpers.lua").read_text("utf-8-sig")
    core = helpers[helpers.index("-- A switch: its saved value"):helpers.index("-- One load watcher")]
    lua.execute(BASE.replace("--SETTINGS--", core))
    ns = lua.table()
    for name in ("ForgeUI.lua", "ForgeLayout.lua", "Settings.lua"):
        lua.execute((ROOT / name).read_text("utf-8-sig"), "FostercareTweaks", ns)
    return lua


class SettingsWindow(unittest.TestCase):
    def test_opens_on_every_page(self):
        lua = window()
        for name in ("general", "unit", "auras", "watched", "raid", "bars"):
            lua.execute('FostercareTweaks.OpenSettings("%s")' % name)
            self.assertTrue(lua.eval('FostercareTweaksSettingsGUI:IsShown()'))

    def test_listed_in_addon_options(self):
        lua = window()
        self.assertEqual(lua.eval('categories[1].name'), "FostercareTweaks")

    def test_every_page_is_a_category_in_addon_options(self):
        # 2026-11-02, the player's notes: the menus in ClassicAPI's AddOn Options.
        lua = window()
        names = [lua.eval("categories[%d].name" % i) for i in range(2, 8)]
        self.assertEqual(names, ["General", "Frames", "Auras", "Watched", "Raid", "Bars"])   # 2026-11-10
        self.assertTrue(all(lua.eval("categories[%d].parent" % i) == "FostercareTweaks" for i in range(2, 8)))

    def test_a_category_borrows_its_page_and_gives_it_back(self):
        lua = window()
        lua.execute('FostercareTweaks.OpenSettings("general")')
        lua.execute('host = categories[4]; host.shown = false; host:Show()')         # Auras
        self.assertFalse(lua.eval("FostercareTweaksSettingsGUI:IsShown()"))         # one place at a time
        self.assertTrue(lua.eval("FTOptPage3.parent == host.holder"))
        self.assertTrue(lua.eval("FTOptPage3:IsShown()"))
        self.assertEqual(lua.eval("host.holder.width"), 420)                       # the scroll frame's width
        # One column at full size: the right column's switches move under the left's.
        self.assertEqual(lua.eval("widgets.FTOpt_ShowStandardBuffs.pt[4]"), 28)
        self.assertLess(lua.eval("widgets.FTOpt_ShowStandardBuffs.pt[5]"), lua.eval("widgets.FTOpt_uf_debuff_size.pt[5]"))
        self.assertIsNone(lua.eval("FTOptPage3.scale"))
        lua.execute('widgets.FTOpt_WatchName:SetText("Sprint"); widgets.FTOpt_WatchBuff:Click()')
        self.assertEqual(lua.eval("watched[1].name"), "Sprint")                     # it works there
        lua.execute("host:Hide()")
        self.assertTrue(lua.eval("FTOptPage3.parent == FostercareTweaksSettingsGUI"))
        lua.execute('FostercareTweaks.OpenSettings("auras")')
        self.assertTrue(lua.eval("FTOptPage3:IsShown()"))                           # back in the window
        self.assertEqual(lua.eval("widgets.FTOpt_ShowStandardBuffs.pt[4]"), 264)   # two columns again

    def test_in_addon_options_every_page_is_one_column(self):
        # 2026-11-02 in play: pages shrunk to fit were unreadable; one column at
        # full size instead. Nothing on a page starts right of the left margin,
        # and no two controls share a line.
        lua = window()
        lua.execute('FostercareTweaks.OpenSettings("watched"); widgets.FTOpt_WatchName:SetText("Sprint"); widgets.FTOpt_WatchBuff:Click()')
        for index in range(1, 7):
            lua.execute("host = categories[%d]; host.shown = false; host:Show()" % (index + 1))
            spots = lua.eval('''(function()
                local page, t = FTOptPage%d, {}
                for name, w in pairs(widgets) do
                    if w.pt and w.pt[2] == page and w:IsShown() then t[#t + 1] = { name, w.pt[4], w.pt[5] } end
                end
                return t end)()''' % index)
            seen = {}
            for i in range(1, len(spots) + 1):
                name, x, y = spots[i][1], spots[i][2], spots[i][3]
                if name == "FTOpt_WatchDebuff":
                    continue                       # shares a line with Add your buff, half each
                self.assertLess(x, 120, "page %d: %s at x=%s" % (index, name, x))
                if name.startswith("FTOpt_") and not name.startswith("FTOptReload"):
                    self.assertNotIn(round(y), seen, "page %d: %s shares a line with %s" % (index, name, seen.get(round(y))))
                    seen[round(y)] = name
            lua.execute("host:Hide()")

    def test_the_window_closes_addon_options(self):
        lua = window()
        lua.execute('InterfaceOptionsFrame.shown = true; FostercareTweaks.OpenSettings("raid")')
        self.assertFalse(lua.eval("InterfaceOptionsFrame:IsShown()"))

    def test_live_switch_applies_without_reload(self):
        lua = window()
        lua.execute('FostercareTweaks.OpenSettings("general"); widgets.FTOpt_HideStealthStanceBar:Click()')
        self.assertEqual(lua.eval('FostercareTweaks_Config["Hide Stealth / Stance Bar"]'), 1)
        self.assertEqual(lua.eval('calls["Hide Stealth / Stance Bar"]'), 1)

    def test_reload_feature_asks_for_reload(self):
        lua = window()
        lua.execute('FostercareTweaks.OpenSettings("general")')
        self.assertFalse(lua.eval('widgets.FTOptReload1.shown'))
        lua.execute('widgets.FTOpt_MiniMapSquare:Click()')
        self.assertEqual(lua.eval('FostercareTweaks_Config["MiniMap Square"]'), 1)
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


class ActionBarRows(unittest.TestCase):
    """2026-11-02 (the player's notes): one row per bar, no bar picker."""

    def setUp(self):
        self.lua = window()
        self.lua.execute('heights = {}; local set = FostercareTweaksSettingsGUI.SetHeight;'
                         ' FostercareTweaksSettingsGUI.SetHeight = function(_, h) heights[#heights + 1] = h end;'
                         ' FostercareTweaks.OpenSettings("bars")')

    def test_a_row_turns_its_bar_on_and_layouts_with_it(self):
        lua = self.lua
        lua.execute('widgets.FTOpt_BarShow_extra:Click()')
        self.assertTrue(lua.eval('FostercareTweaks.ActionBars.enabled'))
        self.assertTrue(lua.eval('FostercareTweaks.ActionBars:GetSettings("extra").visible'))

    def test_the_main_bar_is_always_shown(self):
        self.assertFalse(self.lua.eval('widgets.FTOpt_BarShow_main.enabled'))
        self.assertTrue(self.lua.eval('widgets.FTOpt_BarShow_main.checked'))

    def test_each_row_has_its_size(self):
        lua = self.lua
        lua.execute('local s = widgets.FTOpt_BarSize_extra; s:SetValue(1.25); s.scripts.OnValueChanged(s)')
        self.assertEqual(lua.eval('FostercareTweaks.ActionBars:GetSettings("extra").scale'), 1.25)

    def test_more_opens_the_rest_under_the_row_and_closes_again(self):
        lua = self.lua
        closed = lua.eval('heights[#heights]')
        lua.execute('widgets.FTOpt_BarMore_main:Click()')
        self.assertTrue(lua.eval('widgets.FTOpt_BarDetails.shown'))
        self.assertGreater(lua.eval('heights[#heights]'), closed)
        lua.execute('widgets.FTOpt_Bar_growUp:Click()')
        self.assertTrue(lua.eval('FostercareTweaks.ActionBars:GetSettings("main").growUp'))
        lua.execute('widgets.FTOpt_BarMore_main:Click()')
        self.assertFalse(lua.eval('widgets.FTOpt_BarDetails.shown'))
        self.assertEqual(lua.eval('heights[#heights]'), closed)

    def test_no_bar_picker(self):
        self.assertIsNone(self.lua.eval('widgets.FTOpt_Barmain'))


if __name__ == "__main__":
    unittest.main()
