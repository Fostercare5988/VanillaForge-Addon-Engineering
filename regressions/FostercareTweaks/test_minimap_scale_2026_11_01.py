"""Minimap size scales the whole cluster; moved icons keep their place, 2026-11-01.

The mock models only what the scale code relies on: a frame's effective scale is
the cluster's, positions are offsets from the UIParent corner in the frame's own
units. How it feels in game (size steps, tooltip anchors) stays a game check.
"""
import unittest

from test_audit_2026_10_26 import runtime, source

SETUP = r'''
    UIParent.GetLeft = function() return 0 end
    UIParent.GetTop = function() return 1000 end
    UIParent.GetEffectiveScale = function() return 1 end
    MinimapCluster = Widget({ scale = 1 })
    function MinimapCluster:GetScale() return self.scale end
    function MinimapCluster:SetScale(s) self.scale = s end
    function MovedFrame(name)
        local f = Widget({ name = name })
        f.left, f.top = 200, 900                       -- own units
        function f:GetEffectiveScale() return MinimapCluster.scale end
        function f:GetLeft() return self.left end
        function f:GetTop() return self.top end
        function f:ClearAllPoints() end
        function f:SetPoint(_, _, _, x, y) self.left, self.top = x, 1000 / self:GetEffectiveScale() + y end   -- UIParent corner: left 0, top 1000 screen units
        _G[name] = f
        return f
    end
    function Screen(f) return f.left * f:GetEffectiveScale(), f.top * f:GetEffectiveScale() end
    function FT.GetNumber(key, default, low, high)
        local v = FostercareTweaks_Config.overwrites[key]
        return math.max(low, math.min(high, v or default))
    end
    FostercareTweaks_Config.unitframe_positions = { minimap_mail = { point = "TOPLEFT", relPoint = "TOPLEFT", x = 200, y = -100 } }
'''


class MinimapScale(unittest.TestCase):
    def setUp(self):
        self.lua = runtime()
        self.lua.execute(SETUP)
        self.lua.execute(source("mods/move-unitframes.lua"))
        self.lua.execute(source("mods/minimap-tweaks.lua"))
        self.lua.execute('mail = MovedFrame("MiniMapMailFrame"); clock = MovedFrame("FCTweaksMinimapClock")')

    def test_login_sets_the_saved_size_and_moves_nothing(self):
        self.lua.execute('FostercareTweaks_Config.overwrites.minimap_scale = 1.25; FT.mods["MiniMap Size"].enable()')
        self.assertEqual(self.lua.eval("MinimapCluster.scale"), 1.25)
        self.assertEqual(self.lua.eval("mail.left"), 200)

    def test_default_size_changes_nothing(self):
        self.lua.execute('FT.mods["MiniMap Size"].enable()')
        self.assertEqual(self.lua.eval("MinimapCluster.scale"), 1)

    def test_size_is_limited_to_the_slider_range(self):
        self.lua.execute('FostercareTweaks_Config.overwrites.minimap_scale = 9; FT.mods["MiniMap Size"].enable()')
        self.assertEqual(self.lua.eval("MinimapCluster.scale"), 1.6)

    def test_a_moved_icon_stays_where_it_is_on_screen(self):
        self.lua.execute("local before = { Screen(mail) }; FT.ApplyMinimapScale(1.5, true); after = { Screen(mail) }; first = before")
        before = tuple(self.lua.eval("first").values())
        after = tuple(self.lua.eval("after").values())
        self.assertAlmostEqual(before[0], after[0], places=6)
        self.assertAlmostEqual(before[1], after[1], places=6)
        self.assertEqual(self.lua.eval("MinimapCluster.scale"), 1.5)
        saved = self.lua.eval("FostercareTweaks_Config.unitframe_positions.minimap_mail")
        self.assertAlmostEqual(saved.x * 1.5, 200, places=6)

    def test_an_icon_never_moved_is_not_given_a_saved_position(self):
        self.lua.execute("FT.ApplyMinimapScale(0.8, true)")
        self.assertIsNone(self.lua.eval("FostercareTweaks_Config.unitframe_positions.minimap_clock"))


if __name__ == "__main__":
    unittest.main()
