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


class SavedKeySweepTests(unittest.TestCase):
    """One sweep per saved table clears what nothing owns (KNOWN_PATTERNS KP-64)."""

    def test_an_unowned_key_goes_and_what_was_learned_stays(self):
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute(core.BASE)
        lua.execute(core.CORE)
        lua.execute('''AutoBG_Settings = { Retired = true, FlagSpots = { [529] = {} }, ABTicks = { [3] = {} },
            OpeningSpell = 24391, LastPlayedBG = "Arathi Basin", Positions = { AutoBG_SpyFrame = {} } }''')
        core.fire(lua, "ADDON_LOADED", "AutoBG")
        self.assertIsNone(lua.eval('AutoBG_Settings.Retired'))
        for key in ("FlagSpots", "ABTicks", "OpeningSpell", "LastPlayedBG", "Positions"):
            self.assertIsNotNone(lua.eval('AutoBG_Settings.%s' % key), key)

    def test_spy_clears_its_own_leftovers_and_keeps_its_lists(self):
        import test_spy_features as spy
        lua = spy.runtime()
        lua.execute('AutoBG_Settings.Spy = { StableRowsMigration = 1, KoS = { grom = "Grom" } }; AutoBG_Spy:EnsureOptions()')
        self.assertIsNone(lua.eval('AutoBG_Settings.Spy.StableRowsMigration'))
        self.assertEqual(lua.eval('AutoBG_Settings.Spy.KoS.grom'), "Grom")

    def test_the_arena_table_clears_its_leftovers(self):
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute(core.BASE)
        lua.execute(core.CORE)
        lua.execute('AutoBG_Settings = { Arena = { Buffs = true, Durations = { [22] = 10 } } }')
        core.fire(lua, "ADDON_LOADED", "AutoBG")
        lua.execute('AutoBG_ArenaOptions()')
        self.assertIsNone(lua.eval('AutoBG_Settings.Arena.Buffs'))
        self.assertEqual(lua.eval('AutoBG_Settings.Arena.Durations[22]'), 10)


RECORD = '''
local create = CreateFrame
function CreateFrame(...)
    local f = create(...)
    f.events = {}
    f.RegisterEvent = function(self, e) self.events[e] = true end
    f.UnregisterEvent = function(self, e) self.events[e] = nil end
    return f
end
'''


class QuietWorkTests(unittest.TestCase):
    """Work that ran with nothing to do."""

    def test_carrier_debuff_events_wait_for_a_carrier(self):
        # NamPower sends them for every unit once registered, raids included.
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute(carriers.BASE + RECORD)
        lua.execute(carriers.FC)
        self.assertIsNone(lua.eval('AutoBG_FCEventFrame.events.DEBUFF_ADDED_OTHER'))
        lua.execute('local f = AutoBG_FCEventFrame; f.scripts.OnEvent(f, "CHAT_MSG_BG_SYSTEM_HORDE", "The Horde flag was picked up by Grom!")')
        self.assertTrue(lua.eval('AutoBG_FCEventFrame.events.DEBUFF_ADDED_OTHER'))

    def test_a_line_that_changes_no_timer_draws_nothing(self):
        import test_timer_bars as ttb
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute(ttb.BASE + '''
            AutoBG_Settings.QueueTimers = true
            function GetRealZoneText() return "Warsong Gulch" end
            function IsInInstance() return 1, "pvp" end
            function GetBattlefieldStatus(i) if i == 1 then return "queued", "Arathi Basin", 0 end return "none" end
            waits = 0
            function GetBattlefieldTimeWaited() waits = waits + 1; return 1000 end
            function GetBattlefieldEstimatedWaitTime() return 0 end''')
        lua.execute(ttb.TIMERS)
        lua.execute('local f = AutoBG_TimersEventFrame; f.scripts.OnEvent(f, "PLAYER_ENTERING_WORLD")')
        before = lua.eval('waits')
        lua.execute('local f = AutoBG_TimersEventFrame; f.scripts.OnEvent(f, "CHAT_MSG_BG_SYSTEM_NEUTRAL", "Grom: hello")')
        lua.execute('local f = AutoBG_TimersEventFrame; f.scripts.OnEvent(f, "UPDATE_WORLD_STATES")')
        self.assertEqual(lua.eval('waits'), before)

    def test_the_scoreboard_is_not_asked_for_outside_a_match(self):
        import test_event_scope as scope
        lua = scope.targets()
        lua.execute('asked = 0; function RequestBattlefieldScoreData() asked = asked + 1 end')
        scope.enter(lua, None)
        self.assertEqual(lua.eval('asked'), 0)
        scope.enter(lua, "Warsong Gulch")
        self.assertGreater(lua.eval('asked'), 0)


class ClockTests(unittest.TestCase):
    """ClassicAPI writes the clocks (duration text bindings): no OnUpdate is left."""

    def queued(self):
        import test_timer_bars as ttb
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute(ttb.BASE + '''
            now = 1000; function GetTime() return now end
            tickers = 0; C_Timer.NewTicker = function() tickers = tickers + 1; return { Cancel = function() end } end
            AutoBG_Settings.QueueTimers = true
            function GetBattlefieldStatus(i) if i == 1 then return "queued", "Warsong Gulch", 0 end return "none" end
            function GetBattlefieldTimeWaited() return 272000 end
            function GetBattlefieldEstimatedWaitTime() return 360000 end''')
        lua.execute(ttb.TIMERS)
        lua.execute('local f = AutoBG_TimersEventFrame; f.scripts.OnEvent(f, "PLAYER_ENTERING_WORLD")')
        lua.execute('local f = AutoBG_TimersEventFrame; f.scripts.OnEvent(f, "UPDATE_BATTLEFIELD_STATUS")')
        return lua

    def test_no_timer_group_runs_code_every_frame(self):
        lua = self.queued()
        for frame in ("AutoBG_QueueFrame", "AutoBG_NodeFrame", "AutoBG_AVNodeFrame", "AutoBG_RespawnFrame"):
            self.assertIsNone(lua.eval('%s.scripts and %s.scripts.OnUpdate' % (frame, frame)), frame)

    def test_a_queue_clock_counts_up_by_itself(self):
        lua = self.queued()
        self.assertEqual(lua.eval('AutoBG_QueueFrame.rows[1].timeFs.text'), "4:32")
        lua.execute('now = 1005; __frame()')
        self.assertEqual(lua.eval('AutoBG_QueueFrame.rows[1].timeFs.text'), "4:37")

    def test_waiting_in_a_queue_needs_no_once_a_second_pass(self):
        # In Orgrimmar with a queue: nothing ticks.
        self.assertEqual(self.queued().eval('tickers'), 0)


class SpyRestTests(unittest.TestCase):
    """Spy's second-by-second pass sleeps with nobody around; sightings wake it."""

    def test_the_pass_stops_when_the_list_empties_and_a_nameplate_wakes_it(self):
        import test_spy_nearby as nearby
        lua = nearby.runtime()
        lua.execute('visible = false')
        nearby.advance(lua, 33)  # Grom times out, nobody else is in view
        self.assertEqual(lua.eval('#tickers'), 0)
        lua.execute('plates.nameplate3 = { guid = "0x0000000000000002", name = "Thrall" }')
        nearby.fire(lua, "NAME_PLATE_UNIT_ADDED", "nameplate3")
        self.assertEqual(lua.eval('#tickers'), 1)


class ArenaWriteTests(unittest.TestCase):
    """Power follows NamPower's power events; the pass rewrites nothing unchanged."""

    def setup(self):
        case = client.ArenaExtrasTests()
        lua = case.setup()
        lua.execute('AutoBG_Arena.Tick(); local bar = AutoBG_TargetButton1.PowerBar; bar.SetWidth = function(self, w) self.w = w end')
        return case, lua

    def test_a_power_change_shows_at_once(self):
        case, lua = self.setup()
        lua.execute('mana.cur = 60')
        case.event(lua, "UNIT_MANA_GUID", case.GUID, 0, 0, 0, 0, 0, 0)
        self.assertEqual(lua.eval('AutoBG_TargetButton1.PowerBar.w'), 88)  # 148 * 0.6

    def test_a_second_pass_writes_no_icon_again(self):
        case, lua = self.setup()
        case.event(lua, "UNIT_CASTEVENT", case.GUID, "x", "CAST", 21)
        lua.execute('AutoBG_Arena.Tick(); writes = 0; local icon = AutoBG_TargetButton1.Strip.slots[1].Icon; '
                    'local set = icon.SetTexture; icon.SetTexture = function(...) writes = writes + 1; return set(...) end')
        lua.execute('AutoBG_Arena.Tick()')
        self.assertEqual(lua.eval('writes'), 0)


if __name__ == "__main__":
    unittest.main()
