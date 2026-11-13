"""Audit 2026-11-13: the side you play on, the invite's own time, per-rank lengths.

Each test fails on AutoBG e4ebc39 (tools/run_suite.py AutoBG test_audit_2026_11_13.py
--old e4ebc39). The client's GetBattlefieldPortExpiration (ms left, as
BattlefieldFrame.lua:325 shows it) and the server's mixed teams stay in-game checks.
"""
import unittest
from wowlua import LuaRuntime

import test_match_flow as core
import test_carrier_health as carriers
import test_ab_projection as projection
import test_client_2026_10_31 as client


def core_and_carriers():
    """AutoBG.lua and AutoBG_FC.lua together: a Horde player in Warsong Gulch
    whose raid holds Grom."""
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(core.BASE)
    lua.execute(core.CORE)
    core.fire(lua, "ADDON_LOADED", "AutoBG")
    # The carrier file's client, without its stand-ins for AutoBG.lua's side.
    base = carriers.BASE.split("-- AutoBG.lua owns the side")[0] + carriers.BASE.split("function AutoBG_NoteSide() end\n")[1]
    lua.execute(base)
    lua.execute('''function UnitFactionGroup(u) if u == "player" then return "Horde" end end
        function UnitInRaid(u) return u == "raid3" and 1 or nil end
        function UnitInParty() return nil end
        function UnitCanAttack() return nil end''')
    lua.execute(carriers.FC)
    return lua


def pickup(lua, text):
    lua.execute('local f = AutoBG_FCEventFrame; f.scripts.OnEvent(f, "CHAT_MSG_BG_SYSTEM_ALLIANCE", %r)' % text)


class SideTests(unittest.TestCase):
    """OctoWoW's mixed teams: your faction is not the side you play on."""

    def test_a_raid_member_carrying_the_horde_flag_puts_you_on_the_alliance_side(self):
        lua = core_and_carriers()
        pickup(lua, "The Horde flag was picked up by Grom!")
        self.assertEqual(lua.eval('AutoBG_GetFriendlyCarrier()'), "Grom")
        self.assertIsNone(lua.eval('AutoBG_GetEnemyCarrier()'))
        self.assertEqual(lua.eval('AutoBG_MySide()'), "Alliance")

    def test_an_enemy_carrying_the_horde_flag_keeps_you_on_the_horde_side(self):
        # A control: passes on the old code too.
        lua = core_and_carriers()
        lua.execute('function UnitInRaid() return nil end; function UnitCanAttack() return 1 end')
        pickup(lua, "The Horde flag was picked up by Grom!")
        self.assertEqual(lua.eval('AutoBG_GetEnemyCarrier()'), "Grom")

    def test_the_side_is_forgotten_at_the_next_loading_screen(self):
        # The new path (no reproduction: the old code had no side to forget).
        lua = core_and_carriers()
        pickup(lua, "The Horde flag was picked up by Grom!")
        core.fire(lua, "PLAYER_ENTERING_WORLD")
        self.assertEqual(lua.eval('AutoBG_MySide()'), "Horde")

    def test_the_projection_reads_the_side_you_play_on(self):
        # Horde by faction, playing for the Alliance, which is ahead.
        lua = projection.runtime(3, 1500, 2, 1000)
        lua.execute('function AutoBG_MySide() return "Alliance" end; AutoBG_Timers_UpdateVisibility()')
        self.assertIn("Win", lua.eval('AutoBG_ABProjectionFrame.r1Status.text'))


class InviteTimeTests(unittest.TestCase):
    """The enter comes before this invite runs out, not only before 80 s."""

    def pop(self, left_ms):
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute(core.BASE)
        lua.execute(core.CORE)
        lua.execute('AutoBG_Settings = { AutoAccept = true, AutoAcceptDelay = 78 }')
        core.fire(lua, "ADDON_LOADED", "AutoBG")
        lua.execute('expirations[1] = %d; statuses[1] = { "confirm", "Arathi Basin" }' % left_ms)
        core.fire(lua, "UPDATE_BATTLEFIELD_STATUS")
        lua.execute('m = nil; for _, s in ipairs(messages) do local _, _, n = string.find(s, "Entering in |cFFFFFF00(%d+)s") if n then m = tonumber(n) end end')
        return lua.eval('m')

    def test_an_invite_with_30_seconds_left_is_entered_after_29(self):
        # A reload or loading screen during the pop leaves less than the delay.
        self.assertEqual(self.pop(30000), 29)

    def test_a_fresh_invite_keeps_the_chosen_delay(self):
        self.assertEqual(self.pop(80000), 78)


class RankLengthTests(unittest.TestCase):
    """A blessing's length is learned per spell ID: ranks last differently."""

    def test_a_lower_rank_does_not_count_down_from_the_higher_ranks_length(self):
        case = client.ArenaExtrasTests()
        lua = case.setup()
        lua.execute('names[23] = "Blessing of Freedom"')
        guid = case.GUID
        case.event(lua, "BUFF_ADDED_OTHER", guid, 1, 99, 1, 60, 0, 0)  # first sight
        lua.execute('NOW = 1003')
        case.event(lua, "BUFF_ADDED_OTHER", guid, 1, 22, 1, 60, 0, 0)
        lua.execute('NOW = 1013')
        case.event(lua, "BUFF_REMOVED_OTHER", guid, 1, 22, 1, 60, 0, 0)  # 22 lasts 10 s
        lua.execute('NOW = 1020')
        case.event(lua, "BUFF_ADDED_OTHER", guid, 1, 23, 1, 60, 0, 0)  # the other rank
        lua.execute('NOW = 1021; AutoBG_Arena.Tick()')
        # No length known for 23 yet: the seconds since it began, not 10 - 1.
        self.assertEqual(lua.eval('AutoBG_TargetButton1.Strip.slots[1].Age.text'), "1")


class LearnedTickTests(unittest.TestCase):
    """Arathi Basin ticks come from the score in play, not from vanilla tables."""

    def test_a_whole_tick_is_learned_and_drives_the_estimate(self):
        lua = projection.runtime(3, 1480, 0, 500)
        lua.execute('NOW = 1006; function GetTime() return NOW end; SetScores(3, 1500, 0, 500)')
        lua.execute('AutoBG_Timers_UpdateVisibility()')
        # 500 left at 20 every 6 s: 150 s (the vanilla 10 every 6 s gave 300).
        self.assertEqual(lua.eval('AutoBG_ABProjectionFrame.r1Status.text'), "|cFFFF5555Loss 02:30|r")
        self.assertEqual(lua.eval('AutoBG_Settings.ABTicks[3].gain'), 20)
        self.assertEqual(lua.eval('AutoBG_Settings.ABTicks[3].every'), 6)

    def test_a_tick_across_a_base_change_teaches_nothing(self):
        lua = projection.runtime(3, 1480, 0, 500)
        lua.execute('NOW = 1003; function GetTime() return NOW end; SetScores(4, 1480, 0, 500)')
        lua.execute('NOW = 1006; SetScores(4, 1500, 0, 500)')
        self.assertIsNone(lua.eval('AutoBG_Settings.ABTicks'))

    def test_an_estimate_from_unseen_ticks_looks_like_a_guess(self):
        text = projection.shown(projection.runtime(3, 1500, 2, 1000))
        self.assertTrue(text['r1Status'].startswith('|cFFFF5555~Loss'), text['r1Status'])


class InviteRowTests(unittest.TestCase):
    """An invite counts down on the queue bar until it runs out (as Capping shows it)."""

    def test_an_invite_shows_the_time_it_has_left(self):
        import test_timer_bars as ttb
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute(ttb.BASE + '''
            AutoBG_Settings.QueueTimers = true
            function GetBattlefieldStatus(i) if i == 1 then return "confirm", "Warsong Gulch", 0 end return "none" end
            function GetBattlefieldPortExpiration(i) return 42000 end''')
        lua.execute(ttb.TIMERS)
        lua.execute('local f = AutoBG_TimersEventFrame; f.scripts.OnEvent(f, "UPDATE_BATTLEFIELD_STATUS")')
        self.assertEqual(lua.eval('AutoBG_QueueFrame.rows[1].labelFs.text'), "Warsong Gulch: enter")
        self.assertEqual(lua.eval('AutoBG_QueueFrame.rows[1].timeFs.text'), "42")


if __name__ == "__main__":
    unittest.main()
