"""Minimap size, view and movable map, 2026-11-01.

* Size scales the map only; the clock and icons keep their own size.
* (A "view" slider that enlarged the frame only enlarged the picture; retired.)
* Ctrl+Shift moves the map; the clock and icons are saved relative to the map so
  they follow it, and positions saved against the screen are converted once.

The mock models only what the code relies on: a frame's effective scale is the
cluster's and positions are offsets from a corner in the frame's own units.
Whether a larger frame shows more world, and how it feels, are game checks.
"""
import unittest

from test_audit_2026_10_26 import runtime, source

SETUP = r'''
    function IsLeftShiftKeyDown() return false end
    function IsRightShiftKeyDown() return false end
    function IsLeftControlKeyDown() return false end
    function IsRightControlKeyDown() return false end
    UIParent.GetLeft = function() return 0 end
    UIParent.GetRight = function() return 1000 end
    UIParent.GetTop = function() return 1000 end
    UIParent.GetEffectiveScale = function() return 1 end
    MinimapCluster = Widget({ scale = 1, right = 990, top = 995 })
    function MinimapCluster:GetScale() return self.scale end
    function MinimapCluster:SetScale(s) self.scale = s end
    function MinimapCluster:GetEffectiveScale() return self.scale end
    function MinimapCluster:GetRight() return self.right end
    function MinimapCluster:GetTop() return self.top end
    function MinimapCluster:ClearAllPoints() end
    -- TOPRIGHT of UIParent, offsets in cluster units
    function MinimapCluster:SetPoint(_, _, _, x, y) self.right, self.top = (1000 + x * self.scale) / self.scale, (1000 + y * self.scale) / self.scale end
    function FT.GetNumber(key, default, low, high)
        local v = FostercareTweaks_Config.overwrites[key]
        return math.max(low, math.min(high, v or default))
    end
    Minimap = Widget({ w = 140, h = 140, zoom = 3 })
    function Minimap:GetWidth() return self.w end
    function Minimap:SetWidth(v) self.w = v end
    function Minimap:SetHeight(v) self.h = v end
    function Minimap:GetZoom() return self.zoom end
    function Minimap:SetZoom(z) self.zoomSet = z end
    -- Map-relative frames: left / top are offsets from the Minimap corner, own units.
    function MapFrame(name)
        local f = Widget({ name = name, left = 10, top = -5 })
        function f:GetLeft() return 300 + self.left end      -- Minimap left is 300 screen units
        function f:GetTop() return 800 + self.top end
        function f:ClearAllPoints() end
        function f:SetPoint(_, rel, _, x, y) self.left, self.top, self.rel = x, y, rel end
        function f:GetEffectiveScale() return 1 end
        _G[name] = f
        return f
    end
    Minimap.GetLeft = function() return 300 end
    Minimap.GetTop = function() return 800 end
    Minimap.GetEffectiveScale = function() return 1 end
    FostercareTweaks_Config.unitframe_positions = {}
'''


class MinimapSize(unittest.TestCase):
    def setUp(self):
        self.lua = runtime()
        self.lua.execute(SETUP)
        self.lua.execute(source("mods/move-unitframes.lua"))
        self.lua.execute(source("mods/minimap-tweaks.lua"))
        self.lua.execute('''
            function Minimap:GetScale() return self.scale or 1 end
            function Minimap:SetScale(v) self.scale = v end
            for _, n in ipairs({ "FCTweaksMinimapClock", "MiniMapMailFrame", "MiniMapBattlefieldFrame", "MiniMapTrackingFrame" }) do
                local f = MapFrame(n)
                function f:SetScale(v) self.scale = v end
            end
        ''')

    def enable(self):
        self.lua.execute('FT.mods["MiniMap Size"].enable()')

    def test_the_map_scales_and_the_icons_keep_their_size(self):
        self.lua.execute("FostercareTweaks_Config.overwrites.minimap_scale = 1.25")
        self.enable()
        self.assertEqual(self.lua.eval("Minimap.scale"), 1.25)
        self.assertEqual(self.lua.eval("MinimapCluster.scale"), 1)
        for name in ("FCTweaksMinimapClock", "MiniMapMailFrame", "MiniMapBattlefieldFrame", "MiniMapTrackingFrame"):
            self.assertAlmostEqual(self.lua.eval("%s.scale * Minimap.scale" % name), 1.0, places=9, msg=name)

    def test_the_slider_changes_the_size_live(self):
        self.enable()
        self.lua.execute("FT.ApplyMinimapScale(0.8)")
        self.assertEqual(self.lua.eval("Minimap.scale"), 0.8)
        self.assertAlmostEqual(self.lua.eval("MiniMapMailFrame.scale"), 1.25, places=9)

    def test_default_keeps_everything_at_one(self):
        self.enable()
        self.assertEqual(self.lua.eval("Minimap.scale"), 1)
        self.assertEqual(self.lua.eval("MiniMapMailFrame.scale"), 1)

    def test_size_is_limited_to_the_slider_range(self):
        self.lua.execute("FostercareTweaks_Config.overwrites.minimap_scale = 9")
        self.enable()
        self.assertEqual(self.lua.eval("Minimap.scale"), 1.6)

    def test_the_retired_view_setting_is_cleared(self):
        self.lua.execute("FostercareTweaks_Config.overwrites.minimap_view = 1.5")
        self.enable()
        self.assertIsNone(self.lua.eval("FostercareTweaks_Config.overwrites.minimap_view"))
        self.assertNotIn("ApplyMinimapView", source("mods/minimap-tweaks.lua"))

    def test_the_map_handle_covers_the_map_and_moves_by_its_right_edge(self):
        self.enable()
        self.assertEqual(self.lua.eval("MinimapCluster.fctPositionPoint"), "TOPRIGHT")
        self.assertIsNotNone(self.lua.eval("MinimapCluster.fctMover"))


class IconsFollowTheMap(unittest.TestCase):
    def setUp(self):
        self.lua = runtime()
        self.lua.execute(SETUP)
        self.lua.execute(source("mods/move-unitframes.lua"))
        self.lua.execute(source("mods/minimap-tweaks.lua"))
        self.lua.execute('mail = MapFrame("MiniMapMailFrame")')

    def test_a_position_saved_against_the_screen_is_converted_once(self):
        self.lua.execute('''
            local p = FostercareTweaks_Config.unitframe_positions
            p.minimap_mail = { point = "TOPLEFT", relPoint = "TOPLEFT", x = 310, y = -200 }
            FT.PlaceOnMinimap(mail, "minimap_mail_r", "minimap_mail", "Mail")
        ''')
        saved = self.lua.eval("FostercareTweaks_Config.unitframe_positions")
        self.assertIsNotNone(saved.minimap_mail_r)
        self.assertIsNone(saved.minimap_mail)
        self.assertEqual(self.lua.eval("mail.rel == Minimap"), True)
        self.assertIsNotNone(self.lua.eval("mail.fctMover"))

    def test_a_new_position_is_used_as_saved_and_the_old_one_is_ignored(self):
        self.lua.execute('''
            local p = FostercareTweaks_Config.unitframe_positions
            p.minimap_mail_r = { point = "TOPLEFT", relPoint = "TOPLEFT", x = 7, y = -9 }
            FT.PlaceOnMinimap(mail, "minimap_mail_r", "minimap_mail", "Mail")
        ''')
        self.assertEqual(self.lua.eval("mail.left"), 7)
        self.assertEqual(self.lua.eval("mail.top"), -9)

    def test_clock_and_icons_are_placed_on_the_map(self):
        text = source("mods/minimap-tweaks.lua")
        self.assertIn('PlaceOnMinimap(clock, "minimap_clock_r", "minimap_clock"', text)
        self.assertIn('PlaceOnMinimap(frame, entry[2] .. "_r", entry[2], entry[3])', text)


if __name__ == "__main__":
    unittest.main()
