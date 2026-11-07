"""Minimap clock and icons are Ctrl+Shift movable; the clock has no frame, 2026-11-01.

The mail, battleground and tracking icons are hidden by the game until needed, so
a mover on them could not be grabbed. While Ctrl+Shift is held the mover shows
them; on release the game's own rule decides again (mail waiting, a queue, a
tracking spell). The clock drops its border and background and takes the zone
text's font. Where the buttons land and how the clock looks stay in-game checks.
"""
import unittest

from test_audit_2026_10_26 import runtime, source

SETUP = r'''
    keys = false
    function IsLeftShiftKeyDown() return keys end
    function IsRightShiftKeyDown() return false end
    function IsLeftControlKeyDown() return keys end
    function IsRightControlKeyDown() return false end
    function IsShiftKeyDown() return keys end
    function IsControlKeyDown() return keys end
    function SetEventHandler() end
    Minimap, MinimapCluster, MinimapZoneText = Widget(), Widget(), Widget()
    pendingMail = false
    function HasNewMail() return pendingMail end
'''


class MoversShowHiddenIcons(unittest.TestCase):
    def setUp(self):
        self.lua = runtime()
        self.lua.execute(SETUP)
        self.lua.execute(source("mods/move-unitframes.lua"))
        self.lua.execute(r'''
            mail = Widget({ shown = false })
            mail.fctRestoreShown = function(f) if HasNewMail() then f:Show() else f:Hide() end end
            FT.RegisterFrameMover(mail, "minimap_mail", "Mail")
        ''')

    def test_icon_is_shown_while_moving_and_hidden_again_after(self):
        self.lua.execute("keys = true; FT.UpdateFrameMovers()")
        self.assertTrue(self.lua.eval("mail:IsShown()"))
        self.assertTrue(self.lua.eval("mail.fctMover:IsShown()"))
        self.lua.execute("keys = false; FT.UpdateFrameMovers()")
        self.assertFalse(self.lua.eval("mail:IsShown()"))

    def test_mail_that_arrived_meanwhile_stays_visible(self):
        self.lua.execute("keys = true; FT.UpdateFrameMovers(); pendingMail = true; keys = false; FT.UpdateFrameMovers()")
        self.assertTrue(self.lua.eval("mail:IsShown()"))

    def test_a_shown_icon_is_left_alone(self):
        self.lua.execute("mail:Show(); keys = true; FT.UpdateFrameMovers(); keys = false; FT.UpdateFrameMovers()")
        self.assertTrue(self.lua.eval("mail:IsShown()"))


class ClockLooksLikeZoneText(unittest.TestCase):
    def test_clock_has_no_border_or_background_and_is_movable(self):
        source_text = source("mods/minimap-tweaks.lua")
        clock = source_text[source_text.index('FT:register({\n    title = "MiniMap Clock"'.replace("\n", "\r\n") if "\r\n" in source_text else 'FT:register({\n    title = "MiniMap Clock"'):source_text.index("MiniMap Square")]
        self.assertNotIn("SetBackdrop", clock)
        self.assertIn("MinimapZoneText:GetFont()", clock)
        self.assertIn('PlaceIcon(clock, "minimap_clock_s"', clock)

    def test_the_zone_name_is_movable(self):
        text = source("mods/minimap-tweaks.lua")
        self.assertIn('PlaceIcon(MinimapZoneTextButton, "minimap_zone_s", "Zone"', text)

    def test_the_three_icons_are_registered(self):
        text = source("mods/minimap-tweaks.lua")
        for name in ("MiniMapMailFrame", "MiniMapBattlefieldFrame", "MiniMapTrackingFrame"):
            self.assertIn('"%s"' % name, text)


if __name__ == "__main__":
    unittest.main()
