"""Raid buff switches on a profile that never saved raid_buff_count (P2-1)."""
from pathlib import Path
import os
import unittest
from lupa.lua51 import LuaRuntime

ROOT = Path(os.environ["VANILLAFORGE_ADDON_ROOT"])
OPTIONS = (ROOT / "RaidFrameOptions.lua").read_text("utf-8-sig")
HELPERS = (ROOT / "Helpers.lua").read_text("utf-8-sig")


def runtime():
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute('''
        FostercareTweaks_Config = { overwrites = {} }
        FT = { overwrites = {}, UnitFrames = { refreshes = 0 } }
        function FT.UnitFrames:UpdateAllRaidFrames() self.refreshes = self.refreshes + 1 end
        function FT.UnitFrames:GetRaidBuffSettings()
            local cfg = FostercareTweaks_Config
            local count = math.max(1, math.min(8, math.floor(tonumber(cfg.overwrites.raid_buff_count) or 4)))
            return cfg["Show Raid Buffs"] ~= 0, count, 10, cfg["Show All Raid Buffs"] == 1
        end
        local function Check(setting, checked)
            return { setting = setting, checked = checked,
                GetChecked = function(self) return self.checked end }
        end
        raidBuffCB = Check("Show Raid Buffs", nil)
        raidAllBuffsCB = Check("Show All Raid Buffs", nil)
        raidBuffCountSlider = { label = { SetText = function(self, t) self.text = t end },
            EnableMouse = function() end, SetAlpha = function() end }
    ''')
    getter = HELPERS[HELPERS.index('function FT.GetOverride'):
                     HELPERS.index('function FT.ClampNumber')]
    body = OPTIONS[OPTIONS.index('local function UpdateRaidBuffCountControl()'):
                   OPTIONS.index('raidBuffCB.setting, raidAllBuffsCB.setting')]
    lua.execute(getter)
    lua.execute('''
        local raidAllBuffsCB, raidBuffCountSlider = raidAllBuffsCB, raidBuffCountSlider
        local isRaidUpdating = false
    ''' + body + '''
        Switch = OnRaidBuffSwitch
    ''')
    return lua


def call(lua, fn, control):
    run = lua.eval('function(f, c) local ok, err = pcall(f, c); return ok, tostring(err) end')
    return run(fn, control)


class RaidBuffSwitchTests(unittest.TestCase):
    def test_unticking_all_buffs_without_saved_count_refreshes_frames(self):
        lua = runtime()
        ok, err = call(lua, lua.eval('Switch'), lua.eval('raidAllBuffsCB'))
        self.assertTrue(ok, "switch raised: %s" % err)
        self.assertEqual(lua.eval('FT.UnitFrames.refreshes'), 1)
        self.assertEqual(lua.eval('raidBuffCountSlider.label.text'), "Buffs Per Player: 4")

    def test_toggling_raid_buffs_without_saved_count_refreshes_frames(self):
        lua = runtime()
        ok, err = call(lua, lua.eval('Switch'), lua.eval('raidBuffCB'))
        self.assertTrue(ok, "switch raised: %s" % err)
        self.assertEqual(lua.eval('FT.UnitFrames.refreshes'), 1)


if __name__ == '__main__':
    unittest.main()
