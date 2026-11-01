"""Minimap size, view and movable map, 2026-11-01.

* Size resizes the map frame (no scale): the clock, icons and tray buttons on it keep their own size.
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

    def enable(self):
        self.lua.execute('FT.mods["MiniMap Size"].enable()')

    def test_the_map_frame_is_resized_and_nothing_is_scaled(self):
        self.lua.execute("FostercareTweaks_Config.overwrites.minimap_scale = 1.25")
        self.enable()
        self.assertEqual(self.lua.eval("Minimap.w"), 175)
        self.assertEqual(self.lua.eval("Minimap.h"), 175)
        self.assertEqual(self.lua.eval("Minimap.zoomSet"), 3)       # redrawn at the new size
        self.assertIsNone(self.lua.eval("Minimap.scale"))          # no SetScale: children keep their size
        self.assertNotIn("SetScale", source("mods/minimap-tweaks.lua"))

    def test_the_slider_changes_the_size_live(self):
        self.enable()
        self.lua.execute("FT.ApplyMinimapScale(0.8)")
        self.assertEqual(self.lua.eval("Minimap.w"), 112)

    def test_default_changes_nothing(self):
        self.enable()
        self.assertEqual(self.lua.eval("Minimap.w"), 140)
        self.assertIsNone(self.lua.eval("Minimap.zoomSet"))

    def test_size_is_limited_to_the_slider_range(self):
        self.lua.execute("FostercareTweaks_Config.overwrites.minimap_scale = 9")
        self.enable()
        self.assertEqual(self.lua.eval("Minimap.w"), 224)

    def test_the_retired_view_setting_is_cleared(self):
        self.lua.execute("FostercareTweaks_Config.overwrites.minimap_view = 1.5")
        self.enable()
        self.assertIsNone(self.lua.eval("FostercareTweaks_Config.overwrites.minimap_view"))
        self.assertNotIn("ApplyMinimapView", source("mods/minimap-tweaks.lua"))

    def test_the_map_not_the_cluster_must_stay_on_screen(self):
        # Cluster 808..1000 x 808..1000; the map reaches past its right and top.
        self.lua.execute('''
            function MinimapCluster:GetLeft() return 808 end
            function MinimapCluster:GetBottom() return 808 end
            function MinimapCluster:SetClampRectInsets(l, r, t, b) self.insets = { l, r, t, b } end
            function Minimap:GetEffectiveScale() return 1 end
            function Minimap:GetLeft() return 850 end
            function Minimap:GetRight() return 1030 end
            function Minimap:GetTop() return 1010 end
            function Minimap:GetBottom() return 830 end
            MinimapCluster.GetRight = function() return 1000 end
            MinimapCluster.GetTop = function() return 1000 end
        ''')
        self.lua.execute("FT.ApplyMinimapScale(1.6)")
        insets = [self.lua.eval("MinimapCluster.insets[%d]" % i) for i in (1, 2, 3, 4)]
        for got, want in zip(insets, (42, 30, 10, 22)):
            self.assertAlmostEqual(got, want, places=6)

    def test_the_map_handle_covers_the_map_and_moves_by_its_right_edge(self):
        self.enable()
        self.assertEqual(self.lua.eval("MinimapCluster.fctPositionPoint"), "TOPRIGHT")
        self.assertIsNotNone(self.lua.eval("MinimapCluster.fctMover"))


class PiecesAreIndependent(unittest.TestCase):
    """Zone name, clock and icons are saved against the screen, not the map's corner."""

    def setUp(self):
        self.lua = runtime()
        self.lua.execute(SETUP)
        self.lua.execute(source("mods/move-unitframes.lua"))
        self.lua.execute(source("mods/minimap-tweaks.lua"))
        self.lua.execute('mail = MapFrame("MiniMapMailFrame")')

    def test_a_map_relative_position_is_converted_once_and_kept_where_it_stands(self):
        self.lua.execute("""
            local p = FostercareTweaks_Config.unitframe_positions
            p.minimap_mail_r = { point = "TOPLEFT", relPoint = "TOPLEFT", x = 10, y = -5 }
            FT.PlaceIcon(mail, "minimap_mail_s", "Mail", "minimap_mail", "minimap_mail_r")
        """)
        saved = self.lua.eval("FostercareTweaks_Config.unitframe_positions")
        self.assertIsNotNone(saved.minimap_mail_s)
        self.assertIsNone(saved.minimap_mail_r)
        self.assertTrue(self.lua.eval("mail.rel == UIParent"))
        self.assertIsNotNone(self.lua.eval("mail.fctMover"))

    def test_an_older_screen_position_is_adopted(self):
        self.lua.execute("""
            local p = FostercareTweaks_Config.unitframe_positions
            p.minimap_mail = { point = "TOPLEFT", relPoint = "TOPLEFT", x = 310, y = -200 }
            FT.PlaceIcon(mail, "minimap_mail_s", "Mail", "minimap_mail", "minimap_mail_r")
        """)
        saved = self.lua.eval("FostercareTweaks_Config.unitframe_positions")
        self.assertEqual(saved.minimap_mail_s.x, 310)
        self.assertIsNone(saved.minimap_mail)

    def test_the_new_position_wins(self):
        self.lua.execute("""
            local p = FostercareTweaks_Config.unitframe_positions
            p.minimap_mail_s = { point = "TOPLEFT", relPoint = "TOPLEFT", x = 7, y = -9 }
            p.minimap_mail_r = { point = "TOPLEFT", relPoint = "TOPLEFT", x = 1, y = -1 }
            FT.PlaceIcon(mail, "minimap_mail_s", "Mail", "minimap_mail", "minimap_mail_r")
        """)
        self.assertEqual(self.lua.eval("mail.left"), 7)
        self.assertTrue(self.lua.eval("mail.rel == UIParent"))

    def test_resizing_the_map_does_not_touch_a_placed_piece(self):
        self.lua.execute("""
            FostercareTweaks_Config.unitframe_positions.minimap_mail_s = { point = "TOPLEFT", relPoint = "TOPLEFT", x = 7, y = -9 }
            FT.PlaceIcon(mail, "minimap_mail_s", "Mail", nil, nil)
            before = { mail.left, mail.top }
            FT.ApplyMinimapScale(1.6)
        """)
        self.assertEqual(self.lua.eval("mail.left"), 7)
        self.assertEqual(self.lua.eval("mail.top"), self.lua.eval("before[2]"))

    def test_every_piece_is_placed_against_the_screen(self):
        text = source("mods/minimap-tweaks.lua")
        self.assertIn('FT.PlaceIcon(clock, "minimap_clock_s", "Clock"', text)
        self.assertIn('FT.PlaceIcon(frame, entry[2] .. "_s", entry[3]', text)
        self.assertIn('FT.PlaceIcon(MinimapZoneTextButton, "minimap_zone_s", "Zone"', text)
        self.assertNotIn("PlaceOnMinimap", text)


if __name__ == "__main__":
    unittest.main()
