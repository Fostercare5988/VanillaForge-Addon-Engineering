"""Raid frames follow ClassicAPI 1.18.14 range events, 2026-11-01.

The raid grid used to run a 0.25 s ticker that called UnitInRange for every
button and rechecked the aggro square. UNIT_IN_RANGE_UPDATE fires only when
UnitInRange changes, UNIT_CONNECTION covers offline dimming, and aggro follows
the enemy target (PLAYER_TARGET_CHANGED, UNIT_TARGET "target").

Whether the client reports a member who is already out of range at login (the
first check does not fire, so the button reads UnitInRange when it starts to
show) and whether UNIT_TARGET fires for "target" when the enemy retargets
remain in-game checks.
"""
import os
import unittest
from pathlib import Path

from test_audit_2026_10_26 import RAID_ROSTER, runtime, source

ROOT = Path(os.environ["VANILLAFORGE_ADDON_ROOT"])


class RaidRangeFollowsEvents(unittest.TestCase):
    def setUp(self):
        self.lua = runtime()
        self.lua.execute(RAID_ROSTER)
        self.lua.execute(r'''
            tickers = 0
            C_Timer.NewTicker = function() tickers = tickers + 1; return { Cancel = NOOP } end
            inRange, connected = {}, {}
            function UnitInRange(u) return inRange[u] ~= false end
            function UnitIsConnected(u) return connected[u] ~= false end
            aggroOn = true
            function UF:IsRaidShowAggro() return aggroOn end
            tt = nil
            function UnitCanAttack() return true end
            function UnitGUID(u) if u == "targettarget" then return tt end return "0x" .. u end
        ''')
        self.lua.execute(source("mods/unitframes/raid.lua"))
        self.lua.execute('UF:EnableRaidFrames(true); UF:UpdateGroupRoster(true)')

    def alpha(self, unit):
        return self.lua.eval('(function() for _, b in pairs(frames) do if b.unit == "%s" then return b.rangeAlpha end end end)()' % unit)

    def test_no_ticker_is_created(self):
        self.assertEqual(self.lua.eval('tickers'), 0)

    def test_range_event_dims_and_restores_one_button(self):
        self.assertEqual(self.alpha("raid7"), 1)
        self.lua.execute('inRange.raid7 = false; fire(FCTweaksRaidFrame, "UNIT_IN_RANGE_UPDATE", "raid7", false)')
        self.assertEqual(self.alpha("raid7"), 0.45)
        self.assertEqual(self.alpha("raid8"), 1)
        self.lua.execute('inRange.raid7 = true; fire(FCTweaksRaidFrame, "UNIT_IN_RANGE_UPDATE", "raid7", true)')
        self.assertEqual(self.alpha("raid7"), 1)

    def test_connection_event_dims_offline_member(self):
        self.lua.execute('connected.raid3 = false; fire(FCTweaksRaidFrame, "UNIT_CONNECTION", "raid3", false)')
        self.assertEqual(self.alpha("raid3"), 0.4)

    def test_health_events_no_longer_read_range(self):
        self.lua.execute('asked = 0; local f = UnitInRange; function UnitInRange(u) asked = asked + 1; return f(u) end')
        self.lua.execute('for i = 1, 20 do fire(FCTweaksRaidFrame, "UNIT_HEALTH", "raid7") end')
        self.assertEqual(self.lua.eval('asked'), 0)

    def test_range_events_are_filtered_to_members(self):
        self.assertFalse(self.lua.eval('fire(FCTweaksRaidFrame, "UNIT_IN_RANGE_UPDATE", "nameplate3", false)'))

    def test_aggro_follows_target_events(self):
        self.lua.execute('tt = "0xraid4"')
        self.lua.execute('fire(FCTweaksRaidFrame, "PLAYER_TARGET_CHANGED")')
        self.assertTrue(self.lua.eval('(function() for _, b in pairs(frames) do if b.unit == "raid4" then return b.aggroSquare:IsShown() end end end)()'))
        self.lua.execute('tt = "0xraid9"; fire(FCTweaksRaidFrame, "UNIT_TARGET", "target")')
        self.assertFalse(self.lua.eval('(function() for _, b in pairs(frames) do if b.unit == "raid4" then return b.aggroSquare:IsShown() end end end)()'))
        self.assertTrue(self.lua.eval('(function() for _, b in pairs(frames) do if b.unit == "raid9" then return b.aggroSquare:IsShown() end end end)()'))


if __name__ == "__main__":
    unittest.main()
