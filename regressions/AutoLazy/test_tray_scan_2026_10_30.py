"""AutoLazy tray discovery without the global walk, 2026-10-30.

Measured in Alterac Valley (/lag): the tray's full refresh took up to 31.8 ms
(AutoLazy_MinimapTray.lua:585), and AutoLazy made 5.5 KB/s of new Lua memory,
27 times FostercareTweaks. A full scan walked every global and queued every
frame for a test, and the CreateFrame hook queued every Button any addon made,
such as nameplate and aura icons. A launcher is only accepted on the minimap
frames or UIParent, so only their children and Buttons made there are tested
now. Fails on 3a88a50. Frame time in game stays the real check.
"""
import unittest
from test_audit_2026_10_26 import tray


FOREIGN = r'''
plate = CreateFrame("Frame", "SomeNameplate", UIParent)
plate.counted = false
'''


class TrayScan(unittest.TestCase):
    def test_login_scan_skips_buttons_of_other_frames(self):
        lua = tray(FOREIGN + r'''
            for i = 1, 300 do CreateFrame("Button", "PlateIcon" .. i, plate).counted = true end
        ''')
        lua.execute('fire("PLAYER_ENTERING_WORLD"); settle()')
        self.assertEqual(lua.eval("tests"), 0)

    def test_buttons_made_later_on_other_frames_are_not_queued(self):
        lua = tray(FOREIGN)
        lua.execute('''
            fire("PLAYER_ENTERING_WORLD"); settle(); tests = 0
            for i = 1, 300 do CreateFrame("Button", nil, plate).counted = true end
            settle()
        ''')
        self.assertEqual(lua.eval("tests"), 0)

    def test_known_launcher_is_found_wherever_it_sits(self):
        lua = tray(FOREIGN + r'''
            local b = CreateFrame("Button", "AutoBG_QuickQueueButton", plate)
            b.w, b.h = 32, 32
            b:SetScript("OnClick", function() end)
            b.GetNormalTexture = function() return { GetTexture = function() return "Interface\Icons\X" end } end
        ''')
        lua.execute('fire("PLAYER_ENTERING_WORLD"); settle()')
        self.assertEqual(lua.eval("#AutoLazy.Tray.GetEntries()"), 1)

    def test_uiparent_launcher_is_found(self):
        lua = tray(r'''
            local b = CreateFrame("Button", "SomeAddonMinimapButton", UIParent)
            b.w, b.h = 32, 32
            b:SetScript("OnClick", function() end)
            b.GetNormalTexture = function() return { GetTexture = function() return "Interface\Icons\X" end } end
        ''')
        lua.execute('fire("PLAYER_ENTERING_WORLD"); settle()')
        self.assertEqual(lua.eval("#AutoLazy.Tray.GetEntries()"), 1)


if __name__ == "__main__":
    unittest.main()
