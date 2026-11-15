"""Audit 2026-11-15: repros for what the audit found.

Each test fails on the commit before its fix (tools/run_suite.py --old).
"""
import unittest
from wowlua import LuaRuntime

from wowlua import LuaRuntime as _Lua

import test_ab_projection as projection
import test_carrier_health as carrier
import test_client_2026_10_31 as client
import test_flag_watch as flag_watch
import test_queue_types as queue_env
import test_spirit_wave as spirit


def core():
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(queue_env.BASE)
    lua.execute(queue_env.CORE)
    lua.execute('AutoBGFrame.scripts.OnEvent(AutoBGFrame, "ADDON_LOADED", "AutoBG")')
    return lua


class QueueByNameTests(unittest.TestCase):
    """/abg q took only the short names: "/abg q arathi" queued the last
    battleground played (or opened the menu), not Arathi Basin."""

    def queued(self, command):
        lua = core()
        # pcall: the old code fell through to the battleground menu here.
        lua.execute('pcall(SlashCmdList.AUTOBG, %r)' % command)
        return list(lua.eval('queued').values())

    def test_full_and_partial_names_queue_that_battleground(self):
        self.assertEqual(self.queued("q arathi"), ["Arathi"])
        self.assertEqual(self.queued("q warsong"), ["Warsong"])
        self.assertEqual(self.queued("q alterac"), ["Alterac"])
        self.assertEqual(self.queued("q thorn"), ["ThornGorge"])

    def test_short_names_still_work(self):
        self.assertEqual(self.queued("q ab"), ["Arathi"])
        self.assertEqual(self.queued("q wsg"), ["Warsong"])
        self.assertEqual(self.queued("q av"), ["Alterac"])



class EstimateWithoutPassTests(unittest.TestCase):
    """The Arathi Basin estimate is worked out on events; its time left counts
    down by itself (a duration text binding), with no once-a-second pass."""

    def runtime(self):
        lua = projection.runtime(2, 1000, 3, 1500)
        lua.execute('NOW = 1000; function GetTime() return NOW end; __frame()')
        return lua

    def test_the_time_left_counts_down_with_no_pass(self):
        lua = self.runtime()
        # Horde, 500 to go at 3 bases (10 every 6 s, a guess): 5 minutes.
        self.assertIn("~Win 05:00", lua.eval('AutoBG_ABProjectionFrame.r1Status.text'))
        lua.execute('NOW = 1010; __frame()')
        self.assertIn("~Win 04:50", lua.eval('AutoBG_ABProjectionFrame.r1Status.text'))

    def test_ctrl_click_tells_the_time_left_now(self):
        lua = self.runtime()
        lua.execute('said = {}; function AutoBG_SendAnnouncement(t) table.insert(said, t) end; function IsControlKeyDown() return 1 end')
        lua.execute('NOW = 1030; AutoBG_ABProjectionFrame.scripts.OnClick()')
        self.assertEqual(lua.eval('said[1]'), "Win in about 04:30")

    def test_a_burst_of_score_updates_draws_one_estimate(self):
        lua = self.runtime()
        lua.execute('draws = 0; local fs = AutoBG_ABProjectionFrame.r1Score; local set = fs.SetText; '
                    'fs.SetText = function(self, t) draws = draws + 1; set(self, t) end')
        # Each alone would change the Alliance's final score (A 1420, then A 1400).
        lua.execute('SetScores(2, 1100, 3, 1520); SetScores(2, 1100, 3, 1540); __frame()')
        self.assertEqual(lua.eval('draws'), 1)

    def test_no_ticker_runs_in_a_battleground(self):
        lua = self.runtime()
        lua.execute('made = 0; C_Timer.NewTicker = function() made = made + 1; return { Cancel = function() end } end')
        lua.execute('local f = AutoBG_TimersEventFrame; f.scripts.OnEvent(f, "PLAYER_ENTERING_WORLD"); AutoBG_Timers_UpdateVisibility()')
        self.assertEqual(lua.eval('made'), 0)


class SpiritWaveEventTests(unittest.TestCase):
    """The wave is synced from events; the look at the dead runs only while
    someone lies dead."""

    def runtime(self):
        lua = spirit.runtime()
        lua.execute('scans, cancels = 0, 0; C_Timer.NewTicker = function(_, fn) scans = scans + 1; scan = fn; '
                    'return { Cancel = function() cancels = cancels + 1 end } end')
        return lua

    def test_the_look_at_the_dead_stops_when_nobody_lies_dead(self):
        lua = self.runtime()
        lua.execute('ghosts.raid1 = true')
        spirit.fire(lua, "UNIT_HEALTH", "raid1")
        self.assertEqual(lua.eval('scans'), 1)
        lua.execute('ghosts.raid1 = nil')
        spirit.fire(lua, "UNIT_HEALTH", "raid1")
        lua.execute('scan()')
        self.assertEqual(lua.eval('cancels'), 1)

    def test_nobody_dead_means_no_look(self):
        lua = self.runtime()
        spirit.fire(lua, "UNIT_HEALTH", "raid1")
        self.assertEqual(lua.eval('scans'), 0)

    def test_the_spirit_healer_in_an_arena_syncs_nothing(self):
        lua = self.runtime()
        lua.execute('arenaZone = true; function GetAreaSpiritHealerTime() return 10 end')
        spirit.fire(lua, "PLAYER_ENTERING_WORLD")
        spirit.fire(lua, "AREA_SPIRIT_HEALER_IN_RANGE")
        self.assertFalse(list(lua.eval('{AutoBG_NextSpiritWave()}').values())[1])



class ArenaStripWithoutPassTests(unittest.TestCase):
    """The arena strip ran a 0.5 s pass for the whole match to redraw its
    ages (and made garbage doing it, /lag 2026-11-14 in Blood Ring). The ages
    are engine-written now and the strip is drawn on events."""

    def setup(self):
        case = client.ArenaExtrasTests()
        lua = case.setup()
        lua.execute('__frame()')
        return case, lua

    def test_no_pass_runs_in_an_arena(self):
        case, lua = self.setup()
        # Targets' own tickers (sweep, scoreboard, range) are not the strip's.
        lua.execute('made = 0; local new = C_Timer.NewTicker; C_Timer.NewTicker = function(...) made = made + 1; return new(...) end')
        lua.execute('AutoBG_Arena.SetActive(false); AutoBG_Arena.SetActive(true); __frame()')
        self.assertEqual(lua.eval('made'), 0)

    def test_the_age_counts_by_itself(self):
        case, lua = self.setup()
        case.event(lua, "UNIT_CASTEVENT", case.GUID, "x", "CAST", 21)
        lua.execute('__frame(); NOW = 1045; __frame()')
        self.assertEqual(lua.eval('AutoBG_TargetButton1.Strip.slots[1].Age.text'), "45")
        lua.execute('NOW = 1130; __frame()')
        self.assertEqual(lua.eval('AutoBG_TargetButton1.Strip.slots[1].Age.text'), "2m")

    def test_a_used_ability_leaves_after_five_minutes(self):
        case, lua = self.setup()
        case.event(lua, "UNIT_CASTEVENT", case.GUID, "x", "CAST", 21)
        lua.execute('__frame(); NOW = 1299; __frame()')
        self.assertTrue(lua.eval('AutoBG_TargetButton1.Strip.slots[1].shown'))
        lua.execute('NOW = 1301; __frame()')
        self.assertFalse(lua.eval('AutoBG_TargetButton1.Strip.slots[1].shown'))


class CarrierPreviewTests(unittest.TestCase):
    def test_the_preview_cards_need_no_ticker(self):
        # The sample carriers stand still; the 0.5 s scan ran under them for nothing.
        lua = _Lua(unpack_returned_tuples=True)
        lua.execute(carrier.BASE.replace('function GetRealZoneText() return "Warsong Gulch" end',
                                         'function GetRealZoneText() return "Orgrimmar" end')
                    + '\nmade = 0; C_Timer.NewTicker = function() made = made + 1; return { Cancel = function() end } end')
        lua.execute(carrier.FC)
        lua.execute('AutoBG_FC_SetPreview(true); AutoBG_FC_UpdateVisibility()')
        self.assertIn("Leafwhisper", lua.eval('AutoBG_AllianceFC.nameText.text'))
        self.assertEqual(lua.eval('made'), 0)


class FlagWatchSwitchTests(unittest.TestCase):
    def runtime(self, on):
        lua = _Lua(unpack_returned_tuples=True)
        lua.execute(flag_watch.SETUP)
        lua.execute('AutoBG_Settings.Targets = { FlagWatch = %s }' % ("true" if on else "false"))
        lua.execute(flag_watch.WATCH)
        lua.execute('AutoBG_FlagWatch.onEvent(AutoBG_FlagWatch, "PLAYER_ENTERING_WORLD")')
        return lua

    def test_switched_off_it_looks_at_no_flag(self):
        # It looked four times a second in Arathi Basin with the warnings off.
        self.assertIsNone(self.runtime(False).eval('tick'))

    def test_switched_on_in_a_match_it_starts_looking(self):
        lua = self.runtime(False)
        lua.execute('AutoBG_Settings.Targets.FlagWatch = true; AutoBG_FlagWatch:Sync()')
        self.assertIsNotNone(lua.eval('tick'))
        lua.execute('AutoBG_Settings.Targets.FlagWatch = false; AutoBG_FlagWatch:Sync()')
        self.assertIsNone(lua.eval('tick'))



class LingeringArenaStatusTests(unittest.TestCase):
    """After an arena the queue status can still say "active" for a moment. It
    names the arena by its zone ("Blood Ring", confirmed 2026-11-04), not
    "Arena", so the enemy frames took it for a battleground: match events in the
    open world, and Spy rested until the status cleared."""

    def test_an_arena_status_named_by_its_zone_is_no_match_outside(self):
        import test_targets_guid_events as tge
        lua = tge.runtime(sighting=False)
        lua.execute('''ARENA = "Arena"
            function AutoBG_IsArenaZone() return false end
            function GetBattlefieldStatus(i) if i == 1 then return "active", "Blood Ring" end return "none" end
            AutoBG_Targets:BattlefieldScoreUpdate(true)''')
        self.assertFalse(lua.eval('AutoBG_Targets.activeBG'))

    def test_a_battleground_status_is_still_a_match(self):
        import test_targets_guid_events as tge
        lua = tge.runtime(sighting=False)
        lua.execute('AutoBG_Targets:BattlefieldScoreUpdate(true)')
        self.assertTrue(lua.eval('AutoBG_Targets.activeBG'))



class GroupOnTheScoreboardTests(unittest.TestCase):
    """Your group is never the enemy, whatever side the scoreboard puts it on.
    The enemy frames rebuilt their own list of the group's names on every
    scoreboard pass; they ask Spy's, kept current by the roster events."""

    def test_a_raid_member_on_the_enemy_side_gets_no_row(self):
        import test_targets_guid_events as tge
        lua = tge.runtime(sighting=False)
        self.assertEqual(lua.eval('AutoBG_Targets.EnemyCount()'), 1)
        lua.execute('groupMembers.Grom = true; AutoBG_Targets:BattlefieldScoreUpdate(true)')
        self.assertEqual(lua.eval('AutoBG_Targets.EnemyCount()'), 0)


if __name__ == '__main__':
    unittest.main()
