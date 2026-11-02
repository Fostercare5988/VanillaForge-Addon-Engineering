"""Bagnon settings window (ForgeUI), item search and the main bank button, 2026-11-02.

1. The settings window builds both tabs and shows the saved values; its switches write the
   same SavedVariables keys as before (the quality border, tooltip and detailed-tooltip
   switches are gone: those are always on).
2. A window's right-click opens the Windows tab for that window.
3. The search box applies the text through C_Container.SetItemSearch, a slot that does not
   match is dimmed, and closing the box clears the search.
4. Retired settings are cleared on load.
"""
import unittest
from bgn_env import ROOT, load

RICH = '''
    scripts_by = {}
    local function rich(name)
        local w = widget(name)
        function w:SetScript(n, fn) self.scripts = self.scripts or {}; self.scripts[n] = fn end
        function w:CreateTexture() return rich() end
        function w:CreateFontString() local f = rich(); function f:GetText() return self.text end; return f end
        function w:SetFontString(f) self.fontString = f end
        function w:GetFontString() return self.fontString or rich() end
        function w:GetChecked() return self.checked end
        function w:SetChecked(v) self.checked = v end
        function w:GetValue() return self.value or 0 end
        function w:SetValue(v) self.value = v; if self.scripts and self.scripts.OnValueChanged then self.scripts.OnValueChanged(self) end end
        function w:GetScale() return 1 end
        function w:GetLeft() return 100 end
        function w:GetTop() return 100 end
        function w:GetEffectiveScale() return 1 end
        function w:GetWidth() return 100 end
        function w:GetHeight() return 20 end
        if name then _G[name] = w end
        return w
    end
    function CreateFrame(kind, name) return rich(name) end
    UIParent = rich("UIParent")
    function GetAddOnMetadata() return "1.1.0" end
    function InterfaceOptions_AddCategory() end
    UISpecialFrames = {}
    Bagnon = rich("Bagnon"); Banknon = rich("Banknon")
    Bagnon.shown, Banknon.shown = true, true
    BagnonSets.Bagnon = { cols = 10, space = 2, alpha = 0.85, strata = 3, stayOnScreen = 1, bg = {r=0,g=0,b=0,a=1} }
    BagnonSets.Banknon = { cols = 8, space = 3, alpha = 0.5, strata = 2, stayOnScreen = 0, bg = {r=0,g=0,b=0,a=1}, reverse = 1 }
    layoutCalls = {}
    function BagnonFrame_Layout(frame, cols, space) layoutCalls[#layoutCalls + 1] = { frame:GetName(), cols, space } end
    function BagnonFrame_UpdateFreeSlots() end
    function BagnonFrame_Generate() end
    function BagnonFrame_SetStrata(frame, s) BagnonSets[frame:GetName()].strata = s end
    function BagnonFrame_SavePosition() end
    BagnonSets.showBagsAtBank = 1; BagnonSets.showFreeSlots = 0
'''


def build(lua):
    lua.execute(RICH)
    lua.execute("ns = {}")
    for name in ("ForgeUI.lua", "options/Options.lua"):
        source = (ROOT / name).read_text("utf-8-sig")
        lua.globals().loadstring(source, name)("Bagnon", lua.eval("ns"))


class Settings(unittest.TestCase):
    def test_both_tabs_show_the_saved_values(self):
        lua = load("localization", "utility")
        build(lua)
        lua.execute("BagnonOptions_Open()")
        self.assertTrue(lua.eval("Bagnon_Options.shown"))
        self.assertEqual(lua.eval("Bagnon_AtBank.checked"), True)
        self.assertFalse(lua.eval("Bagnon_FreeSlots.checked"))
        self.assertEqual(lua.eval("Bagnon_Enchants.checked"), True)
        lua.execute('BagnonOptions_Open("Banknon")')
        self.assertEqual(lua.eval("Bagnon_Columns.value"), 8)
        self.assertEqual(lua.eval("Bagnon_Spacing.value"), 3)
        self.assertEqual(lua.eval("Bagnon_Opacity.value"), 50)
        self.assertEqual(lua.eval("Bagnon_Reverse.checked"), True)
        self.assertFalse(lua.eval("Bagnon_StayOnScreen.checked"))

    def test_switches_write_the_saved_keys(self):
        lua = load("localization", "utility")
        build(lua)
        lua.execute("BagnonOptions_Open()")
        lua.execute("Bagnon_AtAH:SetChecked(true); Bagnon_AtAH.scripts.OnClick(Bagnon_AtAH)")
        self.assertEqual(lua.eval("BagnonSets.showBagsAtAH"), 1)
        lua.execute("Bagnon_Enchants:SetChecked(false); Bagnon_Enchants.scripts.OnClick(Bagnon_Enchants)")
        self.assertEqual(lua.eval("BagnonSets.enchantBadges"), 0)

    def test_a_window_slider_lays_out_that_window(self):
        lua = load("localization", "utility")
        build(lua)
        lua.execute('BagnonOptions_Open("Banknon"); Bagnon_Columns:SetValue(6)')
        self.assertEqual(list(lua.eval("layoutCalls[#layoutCalls]").values())[:2], ["Banknon", 6])

    def test_the_removed_switches_are_gone(self):
        lua = load("localization", "utility")
        build(lua)
        lua.execute("BagnonOptions_Open()")
        for name in ("Bagnon_Quality", "Bagnon_Tooltips", "Bagnon_ForeverTooltips"):
            self.assertIsNone(lua.eval(name))


class Search(unittest.TestCase):
    SETUP = RICH + '''
        searchText = nil
        C_Container.SetItemSearch = function(text) searchText = text end
        function BagnonFrame_UpdateLock() end
        local function box(name)
            local b = _G[name .. "Search"] or widget(name .. "Search")
            _G[name .. "Search"] = b
            function b:SetText(t) self.text = t end
            function b:GetText() return self.text or "" end
            return b
        end
        box("Bagnon"); box("Banknon")
        Bagnon.player = "Tester"; Banknon.player = "Tester"
    '''

    def test_typing_sets_the_search_and_closing_clears_it(self):
        lua = load("localization", "utility")
        lua.execute(self.SETUP)
        lua.globals().loadstring((ROOT / "core/Search.lua").read_text("utf-8-sig"), "search")()
        lua.execute('BagnonSearch_Open(Bagnon)')
        self.assertTrue(lua.eval("BagnonSearch.shown"))
        lua.execute('BagnonSearch_OnTextChanged({ GetText = function() return "potion" end })')
        self.assertEqual(lua.eval("searchText"), "potion")
        self.assertTrue(lua.eval("Bagnon_Searching()"))
        lua.execute("BagnonSearch_Close(Bagnon)")
        self.assertEqual(lua.eval("searchText"), "")
        self.assertFalse(lua.eval("Bagnon_Searching()"))

    def test_a_slot_that_does_not_match_is_dimmed(self):
        lua = load("localization", "utility", "frame", "item")
        lua.execute('''
            shade = {}
            function SetItemButtonDesaturated(b, d, r) shade.d, shade.r = d, r end
            function SetItemButtonTextureVertexColor() end
            C_Container.GetContainerItemInfo = function(bag, slot, buf) buf.isFiltered = (slot == 2); return buf end
            local parent = widget(nil, 0)
            item1 = widget("S1", 1); item1.parent = parent; item1.qualityBorder = widget()
            item2 = widget("S2", 2); item2.parent = parent; item2.qualityBorder = widget()
            Bagnon_SetSearching(true)
            BagnonItem_SetLocked(item1, nil); first = shade.r
            BagnonItem_SetLocked(item2, nil); second = shade.r
        ''')
        self.assertEqual(lua.eval("first"), 0.5)
        self.assertEqual(lua.eval("second"), 0.3)


class Retired(unittest.TestCase):
    def test_old_switch_settings_are_cleared(self):
        from test_cleanup_2026_11_02 import Events as CleanupEvents
        lua = load("localization", "utility")
        lua.execute(CleanupEvents.SETUP + '''
            BagnonSets.showTooltips = 1; BagnonSets.qualityBorders = 0; BagnonSets.showForeverTooltips = 1
        ''')
        lua.execute((ROOT / "Events.lua").read_text("utf-8-sig"), "Events.lua")
        lua.execute('scripts.OnEvent(widget(), "ADDON_LOADED", "Bagnon")')
        for key in ("showTooltips", "qualityBorders", "showForeverTooltips"):
            self.assertIsNone(lua.eval("BagnonSets." + key))


if __name__ == "__main__":
    unittest.main()
