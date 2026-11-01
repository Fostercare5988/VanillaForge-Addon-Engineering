"""Tray buttons keep their size on a scaled minimap, 2026-11-01.

AutoLazy keeps each docked addon button a child of the minimap and only places it
over the tray. On a map scaled by FostercareTweaks the button then came out at the
map's scale. A docked button now takes the tray's scale and gets its own back when
the tray closes. How it looks in game stays a game check.
"""
import unittest

from test_audit_2026_10_26 import tray


class TrayScale(unittest.TestCase):
    def setUp(self):
        self.lua = tray()
        self.lua.execute("""
            Minimap.scale = 1.6                                   -- a scaled map
            Minimap.GetScale = function(f) return f.scale end
            local art = { GetTexture = function() return "Interface\\Icons\\X" end }
            launcher = CreateFrame("Button", "ScaledMapLauncher", Minimap)
            launcher.w, launcher.h = 33, 33
            launcher:SetScript("OnClick", function() end)
            launcher.IsMovable = function() return true end
            launcher.GetNormalTexture = function() return art end
            launcher.GetEffectiveScale = function(f) return Minimap.scale * (rawget(f, "scale") or 1) end
            fire("PLAYER_ENTERING_WORLD"); settle()
        """)

    def test_a_docked_button_is_the_trays_size(self):
        self.lua.execute("AutoLazy.Tray.Open(); settle()")
        self.assertAlmostEqual(self.lua.eval("launcher:GetEffectiveScale()"), 1.0, places=6)

    def test_closing_the_tray_gives_the_button_its_own_scale_back(self):
        self.lua.execute("AutoLazy.Tray.Open(); settle(); AutoLazy.Tray.Close(); settle()")
        self.assertEqual(self.lua.eval("launcher:GetScale()"), 1)

    def test_the_tray_cell_does_not_grow_with_the_map(self):
        self.lua.execute("AutoLazy_ButtonTray.SetWidth = function(f, v) f.recorded = v end; AutoLazy.Tray.Open(); settle()")
        # One 33 px button: the tray is two 7 px margins plus one 41 px cell (55), not 33 * 1.6 + 8 wide.
        self.assertEqual(self.lua.eval('rawget(AutoLazy_ButtonTray, "recorded")'), 55)


if __name__ == "__main__":
    unittest.main()
