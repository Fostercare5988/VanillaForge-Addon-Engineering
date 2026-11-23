"""The minimap tray (spec K8-K10, K12; tests 9-12): which buttons it takes, how it
opens and closes, an owner's moves, the switch off and on, and the Pirate Radio
and Group Finder switch. A first login: the launcher's place is in the client's
layout cache (KP-66).
"""
import unittest
from al_env import load

TAKEN = ("AtlasLootMinimapButton", "LibDBIcon10_UnitXP", "GearRackMinimapButton")


def parent(lua, name):
    return lua.eval(f"(function() local p = {name}:GetParent() return p and (p:GetName() or 'vault') end)()")


class Collect(unittest.TestCase):
    def test_login_takes_the_named_draggable_buttons_only(self):
        lua = load()
        for name in TAKEN:
            self.assertEqual(parent(lua, name), "AutoLazyTray", name)
        for name in ("MinimapZoomIn", "MinimapClock", "MapPin1"):
            self.assertEqual(parent(lua, name), "Minimap", name)
        self.assertEqual(lua.eval("GearRackMinimapButton:GetFrameStrata()"), "DIALOG")

    def test_a_button_made_later_on_the_minimap_is_taken(self):
        lua = load()
        lua.execute("minimapButton('LateButton', 'Button', 'drag') step()")
        self.assertEqual(parent(lua, "LateButton"), "AutoLazyTray")
        lua.execute("b = CreateFrame('Button', 'ByName', 'Minimap') b:SetMovable(true) step()")
        self.assertEqual(parent(lua, "ByName"), "AutoLazyTray")

    def test_a_button_made_on_uiparent_costs_nothing(self):
        lua = load()
        lua.execute("for i = 1, 50 do CreateFrame('Button', 'BarButton' .. i, UIParent) end")
        self.assertEqual(lua.eval("liveTimers()"), 0)

    def test_the_launcher_starts_top_right_and_keeps_the_place_the_client_saved(self):
        lua = load()
        self.assertEqual(lua.eval("(select(1, AutoLazyButton:GetPoint(1)))"), "TOPRIGHT")
        self.assertEqual(lua.eval("(select(4, AutoLazyButton:GetPoint(1)))"), -167)
        self.assertEqual(lua.eval("(select(5, AutoLazyButton:GetPoint(1)))"), -225)
        lua = load(setup="layoutCache.AutoLazyButton = { 300, -400 }")
        self.assertEqual(lua.eval("AutoLazyButton:GetLeft()"), 300)


class OpenClose(unittest.TestCase):
    def test_open_shows_the_shown_ones_in_rows_of_four(self):
        lua = load(setup="for i = 1, 3 do minimapButton('Extra' .. i, 'Button', 'movable') end")
        lua.execute("GearRackMinimapButton:Hide() click(AutoLazyButton)")
        self.assertTrue(lua.eval("AutoLazyTray:IsShown()"))
        self.assertEqual(lua.eval("AutoLazyTray:GetWidth()"), 16 + 4 * 34)
        self.assertEqual(lua.eval("AutoLazyTray:GetHeight()"), 16 + 2 * 34)  # 5 shown
        self.assertEqual(lua.eval("(select(4, Extra3:GetPoint(1)))"), 8)       # the fifth: second row
        self.assertEqual(lua.eval("(select(5, Extra3:GetPoint(1)))"), -42)

    def test_beside_the_launcher_away_from_the_edge(self):
        lua = load()
        lua.execute("AutoLazyButton.left, AutoLazyButton.top = 900, 700 click(AutoLazyButton)")
        self.assertEqual(lua.eval("(select(1, AutoLazyTray:GetPoint(1)))"), "TOPRIGHT")
        self.assertEqual(lua.eval("(select(3, AutoLazyTray:GetPoint(1)))"), "BOTTOMRIGHT")
        lua.execute("AutoLazyTray:Hide() AutoLazyButton.left, AutoLazyButton.top = 20, 100 click(AutoLazyButton)")
        self.assertEqual(lua.eval("(select(1, AutoLazyTray:GetPoint(1)))"), "BOTTOMLEFT")

    def test_a_click_outside_the_launcher_or_escape_closes_it(self):
        lua = load()
        self.assertFalse(lua.eval("receives(AutoLazyTray, 'GLOBAL_MOUSE_UP')"))
        lua.execute("click(AutoLazyButton)")
        self.assertTrue(lua.eval("receives(AutoLazyTray, 'GLOBAL_MOUSE_UP')"))
        lua.execute("AutoLazyTray.hovered = true fire('GLOBAL_MOUSE_UP', 'LeftButton') step()")
        self.assertTrue(lua.eval("AutoLazyTray:IsShown()"))
        lua.execute("AutoLazyTray.hovered = false fire('GLOBAL_MOUSE_UP', 'LeftButton') step()")
        self.assertFalse(lua.eval("AutoLazyTray:IsShown()"))
        self.assertFalse(lua.eval("receives(AutoLazyTray, 'GLOBAL_MOUSE_UP')"))
        lua.execute("click(AutoLazyButton) click(AutoLazyButton)")
        self.assertFalse(lua.eval("AutoLazyTray:IsShown()"))
        self.assertIn("AutoLazyTray", lua.eval("table.concat(UISpecialFrames, ',')"))

    def test_an_owners_setpoint_keeps_the_button_in_its_cell(self):
        lua = load()
        lua.execute("click(AutoLazyButton) GearRackMinimapButton:ClearAllPoints()"
                    " GearRackMinimapButton:SetPoint('CENTER', Minimap, 'CENTER', 50, 50)")
        self.assertEqual(lua.eval("select(2, GearRackMinimapButton:GetPoint(1)):GetName()"), "AutoLazyTray")

    def test_a_button_its_owner_hides_is_left_out(self):
        lua = load()
        lua.execute("click(AutoLazyButton) GearRackMinimapButton:Hide()")
        self.assertEqual(lua.eval("AutoLazyTray:GetWidth()"), 16 + 2 * 34)


class Switches(unittest.TestCase):
    def test_off_puts_each_back_where_its_owner_last_put_it_and_hides_the_launcher(self):
        lua = load()
        lua.execute("GearRackMinimapButton:SetPoint('CENTER', Minimap, 'CENTER', 50, 50)")  # its own drag
        lua.execute("settingsWindow.use('AutoLazy_tray', false)")
        self.assertEqual(parent(lua, "GearRackMinimapButton"), "Minimap")
        self.assertEqual(lua.eval("GearRackMinimapButton:GetFrameStrata()"), "LOW")
        self.assertEqual(lua.eval("(select(4, GearRackMinimapButton:GetPoint(1)))"), 50)
        self.assertEqual(lua.eval("(select(4, AtlasLootMinimapButton:GetPoint(1)))"), 10)
        self.assertFalse(lua.eval("AutoLazyButton:IsShown()"))
        lua.execute("settingsWindow.use('AutoLazy_tray', true)")
        self.assertEqual(parent(lua, "GearRackMinimapButton"), "AutoLazyTray")
        self.assertTrue(lua.eval("AutoLazyButton:IsShown()"))

    def test_off_at_login_leaves_them_on_the_minimap(self):
        lua = load("AutoLazyDB = { tray = false, hideRadioLfg = false }")
        for name in TAKEN + ("EBC_Minimap", "LFTMinimapButton"):
            self.assertEqual(parent(lua, name), "Minimap", name)
        self.assertFalse(lua.eval("AutoLazyButton:IsShown()"))

    def test_radio_and_group_finder_are_hidden_tray_included(self):
        lua = load()
        self.assertEqual(parent(lua, "EBC_Minimap"), "vault")
        self.assertEqual(parent(lua, "LFTMinimapButton"), "vault")
        self.assertFalse(lua.eval("LFTMinimapButton:IsVisible()"))
        lua.execute("settingsWindow.use('AutoLazy_hideRadioLfg', false)")
        self.assertEqual(parent(lua, "EBC_Minimap"), "AutoLazyTray")
        lua.execute("settingsWindow.use('AutoLazy_tray', false)")
        self.assertEqual(parent(lua, "LFTMinimapButton"), "Minimap")


if __name__ == "__main__":
    unittest.main()
