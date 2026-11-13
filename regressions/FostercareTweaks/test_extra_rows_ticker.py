"""Extra Rows 2-7 sleep while nothing changes without an event (audit 2026-11-13, 1.20.0).

Their 0.2 s ticker refreshed every action whenever a shown row held one: out
of combat, with no target, all session. Only two things change without an
event: the range to a target and the flash of an active auto attack or auto
shot. The ticker now runs only then; usable state follows the player's power
(UNIT_POWER_UPDATE) when no ticker reads it, and the rest follows the events
the rows already hear. Fails on 701d8b1.

In-game check: with Extra Row 2 shown and no target, nothing on it changes
when it should (mana for a spell, a cooldown ending, a count); with a target,
a spell's key turns red out of range and back.
"""
import unittest

from wowlua import LuaRuntime

from test_audit_2026_10_25 import source
from test_unitframe_hot_paths import slice


class ExtraRowsTickerSleeps(unittest.TestCase):
    def setUp(self):
        lua = self.lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute(r'''
            EA = { visible = {} }
            target, partial, full = false, 0, 0
            function UnitExists(u) return u == "target" and target end
            function RefreshVisible(all) if all then full = full + 1 else partial = partial + 1 end end
            tickers, callbacks = {}, {}
            C_Timer = {
                After = function(_, fn) callbacks[#callbacks + 1] = fn end,
                NewTicker = function(_, fn)
                    local t = { fn = fn }
                    function t:Cancel() self.cancelled = true end
                    tickers[#tickers + 1] = t
                    return t
                end,
            }
            button = {}
            EA.visible[{ buttons = { button } }] = true
        ''')
        lua.execute(slice(source("ExtraActions.lua"), "-- The 0.2 s ticker has work only", "local function SyncOwner")
                    + "\nSync, Flush, Queue = SyncTicker, FlushRefresh, QueueRefresh")

    def running(self):
        return self.lua.eval("EA.ticker ~= nil and not EA.ticker.cancelled")

    def test_no_target_and_nothing_flashing_means_no_ticker(self):
        self.lua.execute("EA.anyActions = true; Sync()")
        self.assertFalse(self.running())

    def test_a_target_starts_it_and_losing_it_stops_it(self):
        lua = self.lua
        lua.execute("EA.anyActions = true; target = true; Queue(); callbacks[1]()")   # PLAYER_TARGET_CHANGED
        self.assertTrue(self.running())
        lua.execute("EA.ticker.fn()")
        self.assertEqual(lua.eval("partial"), 1)
        lua.execute("target = false; Queue(); callbacks[2]()")
        self.assertFalse(self.running())

    def test_a_flashing_auto_attack_keeps_it(self):
        self.lua.execute("EA.anyActions = true; button.fctCurrent = true; Sync()")
        self.assertTrue(self.running())

    def test_rows_without_actions_never_tick(self):
        self.lua.execute("EA.anyActions = false; target = true; Sync()")
        self.assertFalse(self.running())

    def test_power_reads_usable_state_when_no_ticker_runs(self):
        text = source("ExtraActions.lua")
        self.assertIn('RegisterUnitEvent("UNIT_POWER_UPDATE", "player")', text)
        self.assertIn("if not EA.ticker then RefreshVisible(false) end", text)


if __name__ == "__main__":
    unittest.main()
