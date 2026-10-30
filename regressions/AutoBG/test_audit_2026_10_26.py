"""Audit 2026-10-26 reproductions (Alterac Valley session, .private/audit-AutoBG-2026-10-26.md).

Each test fails on AutoBG e24539b and states the behaviour the fix must give:

- An Alterac Valley mine message must never put "Gold Mine" (an Arathi Basin
  base) on the Alterac Valley timers.
- An enemy seen starting an Opening cast at a flag warns, so Alterac Valley
  (where the 40-player enemy frames, and their cast bars, can be off) warns at all.
- (2026-10-27) The flag watch is Arathi Basin only: Alterac Valley messages
  never reach it, and saved Alterac Valley spots are dropped on load.
- The stealth warning card shows real icon paths: Lua drops the backslash in
  "Interface\\Icons" written with single backslashes.

Exact Alterac Valley yell wording for the mines is UNVERIFIED on OctoWoW; the
taken line is the one BigWigs' Alterac Valley module matches. In-game checks
are listed in the audit.
"""
from pathlib import Path
import os
import unittest
from lupa.lua51 import LuaRuntime

import addon_loader
import test_flag_watch
import test_spy_nearby
import test_timer_bars

ROOT = Path(os.environ["VANILLAFORGE_ADDON_ROOT"])
TIMERS = (ROOT / "AutoBG_Timers.lua").read_text("utf-8-sig")
SPY = (ROOT / "AutoBG_Spy.lua").read_text("utf-8-sig")

AV_ZONE = r'''
now = 1000
function GetTime() return now end
tickIntervals = {}
C_Timer.NewTicker = function(interval) table.insert(tickIntervals, interval); return { Cancel = function() end } end
AutoBG_Settings.TestAllTimers = false
function GetRealZoneText() return "Alterac Valley" end
function IsInInstance() return 1, "pvp" end
function GetNumRaidMembers() return 0 end
function UnitName() return "Tester" end
'''


def av_timers():
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(test_timer_bars.BASE)
    lua.execute(AV_ZONE)
    lua.execute(TIMERS)
    lua.execute('local f = AutoBG_TimersEventFrame; f.scripts.OnEvent(f, "PLAYER_ENTERING_WORLD")')
    return lua


def yell(lua, text):
    lua.execute('local f = AutoBG_TimersEventFrame; f.scripts.OnEvent(f, "CHAT_MSG_MONSTER_YELL", %r)' % text)


def av_labels(lua):
    labels = []
    for i in range(1, 9):
        if lua.eval('AutoBG_AVNodeFrame.rows[%d].shown' % i):
            labels.append(lua.eval('rawget(AutoBG_AVNodeFrame.rows[%d].labelFs, "text")' % i))
    return labels


class AlteracMineTests(unittest.TestCase):
    def test_mine_messages_never_show_gold_mine_in_alterac_valley(self):
        lua = av_timers()
        # UNVERIFIED wording: some AV line about a mine with an assault word put
        # "Gold Mine 4:22" on the AV timers (screenshot, 2026-10-26 17:51).
        yell(lua, "The Irondeep Mine is under attack! If left unchecked, the Horde will capture it!")
        self.assertNotIn("Gold Mine", av_labels(lua))
        yell(lua, "The Horde has taken the Coldtooth Mine! Its supplies will now be used for reinforcements!")
        self.assertNotIn("Gold Mine", av_labels(lua))

    def test_taken_mine_counts_five_minutes_in_the_takers_color(self):
        """BigWigs' AV mine timer, confirmed right for OctoWoW by the player."""
        lua = av_timers()
        yell(lua, "The Horde has taken the Irondeep Mine! Its supplies will now be used for reinforcements!")
        self.assertEqual(av_labels(lua), ["Irondeep Mine"])
        self.assertEqual(lua.eval('rawget(AutoBG_AVNodeFrame.rows[1].timeFs, "text")'), "5:00")
        self.assertEqual(lua.eval('AutoBG_AVNodeFrame.rows[1].icon.texture'), "Interface\\AddOns\\AutoBG\\Textures\\Nodes\\Mine_Horde")

    def test_alterac_valley_lines_never_reach_the_flag_watch(self):
        lua = av_timers()
        lua.execute('heard = {}; AutoBG_FlagWatch = { OnNodeMessage = function(_, node) table.insert(heard, node) end }')
        yell(lua, "The Horde has taken the Irondeep Mine! Its supplies will now be used for reinforcements!")
        yell(lua, "The Stormpike Aid Station is under attack! If left unchecked, the Horde will capture it!")
        self.assertEqual(len(lua.eval('heard')), 0)


def frame_update(lua, frame, at):
    """One drawn frame at time `at`: the group's OnUpdate, with `this` set like the client."""
    lua.execute('now = %s; this = %s; %s.scripts.OnUpdate()' % (at, frame, frame))


def row(lua, frame, i, field):
    return lua.eval('rawget(%s.rows[%d], "%s")' % (frame, i, field))


class TimerLookTests(unittest.TestCase):
    """The 2026-10-26 look: BigWigs-style clock, banners, rows that drain themselves."""

    def test_clock_reads_like_bigwigs(self):
        lua = av_timers()
        yell(lua, "The Stonehearth Graveyard is under attack! If left unchecked, the Horde will capture it!")
        self.assertEqual(lua.eval('AutoBG_AVNodeFrame.rows[1].timeFs.text'), "5:00")
        frame_update(lua, "AutoBG_AVNodeFrame", 1000 + 300 - 111.4)
        self.assertEqual(lua.eval('AutoBG_AVNodeFrame.rows[1].timeFs.text'), "1:51")
        frame_update(lua, "AutoBG_AVNodeFrame", 1000 + 300 - 21.5)
        self.assertEqual(lua.eval('AutoBG_AVNodeFrame.rows[1].timeFs.text'), "21")
        self.assertEqual(row(lua, "AutoBG_AVNodeFrame", 1, "announceText"), "Stonehearth Graveyard (Horde) captured in 21")
        self.assertTrue(row(lua, "AutoBG_AVNodeFrame", 1, "sparkShown"))

    def test_last_ten_seconds_turn_gold(self):
        lua = av_timers()
        yell(lua, "The Stonehearth Graveyard is under attack! If left unchecked, the Horde will capture it!")
        self.assertFalse(row(lua, "AutoBG_AVNodeFrame", 1, "displayUrgent"))
        frame_update(lua, "AutoBG_AVNodeFrame", 1000 + 300 - 9.5)
        self.assertTrue(row(lua, "AutoBG_AVNodeFrame", 1, "displayUrgent"))

    def test_a_row_that_runs_out_leaves_at_once(self):
        lua = av_timers()
        yell(lua, "The Stonehearth Graveyard is under attack! If left unchecked, the Horde will capture it!")
        frame_update(lua, "AutoBG_AVNodeFrame", 1301)
        self.assertEqual(av_labels(lua), [])
        self.assertFalse(lua.eval('AutoBG_AVNodeFrame.shown'))

    def test_logic_ticks_once_a_second(self):
        lua = av_timers()
        yell(lua, "The Stonehearth Graveyard is under attack! If left unchecked, the Horde will capture it!")
        self.assertEqual(list(lua.eval('tickIntervals').values()), [1])

    def test_respawn_bar_counts_down_and_starts_the_next_wave(self):
        lua = av_timers()
        lua.execute('AutoBG_Settings.RessTimer = true; AutoBG_Timers_UpdateVisibility()')
        self.assertEqual(lua.eval('AutoBG_RespawnFrame.rows[1].labelFs.text'), "Respawn")
        self.assertEqual(lua.eval('AutoBG_RespawnFrame.rows[1].icon.texture'), "Interface\\Icons\\Spell_Holy_Resurrection")
        frame_update(lua, "AutoBG_RespawnFrame", 1012.5)
        self.assertEqual(lua.eval('AutoBG_RespawnFrame.rows[1].timeFs.text'), "~18")
        # The chat line reads as a sentence: "Ress in 18", no colon, no "~".
        self.assertEqual(lua.eval('AutoBG_RespawnFrame.rows[1].announceText'), "Ress in 18")
        frame_update(lua, "AutoBG_RespawnFrame", 1030.2)  # the wave passes
        frame_update(lua, "AutoBG_RespawnFrame", 1030.5)
        self.assertEqual(lua.eval('AutoBG_RespawnFrame.rows[1].timeFs.text'), "~30")

    def test_queue_row_shows_wait_and_fills_toward_the_estimate(self):
        lua = av_timers()
        lua.execute(r'''
            AutoBG_Settings.QueueTimers = true
            function GetBattlefieldStatus(i) if i == 1 then return "queued", "Warsong Gulch" end return "none" end
            function GetBattlefieldTimeWaited() return 272000 end
            function GetBattlefieldEstimatedWaitTime() return 360000 end
            local f = AutoBG_TimersEventFrame; f.scripts.OnEvent(f, "UPDATE_BATTLEFIELD_STATUS")''')
        self.assertEqual(lua.eval('AutoBG_QueueFrame.rows[1].labelFs.text'), "Warsong Gulch")
        self.assertEqual(lua.eval('AutoBG_QueueFrame.rows[1].timeFs.text'), "4:32")
        self.assertEqual(row(lua, "AutoBG_QueueFrame", 1, "estText"), "Estimated: 6:00")
        self.assertEqual(row(lua, "AutoBG_QueueFrame", 1, "announceText"), "In WSG queue for 4:32")
        self.assertEqual(row(lua, "AutoBG_QueueFrame", 1, "fillDuration"), 360)


class FlagWatchCastTests(unittest.TestCase):
    def test_visible_enemy_starting_an_opening_at_a_flag_warns(self):
        """23c5f07 left visible openers to the enemy frame cast bar; with the
        40-player frames off, Alterac Valley showed no warning at all."""
        lua = test_flag_watch.runtime()
        test_flag_watch.learn_blacksmith(lua)
        # Balloon walks up in plain sight, so the stealth heuristic stays quiet...
        for step in range(3):
            lua.execute('pos["%s"] = { 58 - %d, 49 }' % (test_flag_watch.BALLOON, step * 3))
            test_flag_watch.ticks(lua, 1)
        # ...and starts the Opening cast at the flag.
        lua.execute('AutoBG_FlagWatch.onEvent(AutoBG_FlagWatch, "UNIT_CASTEVENT", "%s", nil, "START", 24391, 5000)'
                    % test_flag_watch.BALLOON)
        self.assertEqual(list(lua.eval('alerts').values()), ["Opening Blacksmith Balloon"])

    def start(self, lua, kind="START"):
        lua.execute('AutoBG_FlagWatch.onEvent(AutoBG_FlagWatch, "UNIT_CASTEVENT", "%s", nil, "%s", 24391, 5000)'
                    % (test_flag_watch.BALLOON, kind))

    def test_row_mark_lasts_while_the_cast_runs_and_ends_with_it(self):
        lua = test_flag_watch.runtime()
        test_flag_watch.learn_blacksmith(lua)
        lua.execute('pos["%s"] = { 60, 49 }' % test_flag_watch.BALLOON)
        test_flag_watch.ticks(lua, 1)
        lua.execute('pos["%s"] = { 52, 49 }' % test_flag_watch.BALLOON)
        test_flag_watch.ticks(lua, 1)
        self.start(lua)
        test_flag_watch.ticks(lua, 4)  # visible and still, but the cast holds the mark
        self.assertEqual(lua.eval('opening.Balloon'), "Blacksmith")
        self.start(lua, "FAIL")
        self.assertIsNone(lua.eval('opening.Balloon'))

    def test_opening_at_an_unlearned_flag_still_warns(self):
        lua = test_flag_watch.runtime()
        lua.execute('pos["%s"] = { 400, 400 }' % test_flag_watch.BALLOON)
        self.start(lua)
        self.assertEqual(list(lua.eval('alerts').values()), ["Opening a flag Balloon"])

    def test_friendly_or_unknown_caster_does_not_warn(self):
        lua = test_flag_watch.runtime()
        test_flag_watch.learn_blacksmith(lua)
        lua.execute('AutoBG_FlagWatch.onEvent(AutoBG_FlagWatch, "UNIT_CASTEVENT", "0x0000000000000009", nil, "START", 24391, 5000)')
        self.assertEqual(len(lua.eval('alerts')), 0)


class FlagWatchArathiOnlyTests(unittest.TestCase):
    """2026-10-27: "Opening Stormpike Aid Station" in Alterac Valley was noise;
    the flag watch belongs to Arathi Basin alone."""

    def test_no_warning_in_alterac_valley(self):
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute(test_flag_watch.SETUP)
        lua.execute('function GetRealZoneText() return "Alterac Valley" end')
        lua.execute(test_flag_watch.WATCH)
        lua.execute('AutoBG_FlagWatch.onEvent(AutoBG_FlagWatch, "PLAYER_ENTERING_WORLD")')
        self.assertIsNone(lua.eval('tick'))
        lua.execute('AutoBG_FlagWatch:OnNodeMessage("Stormpike Aid Station", '
                    '"Tester claims the Stormpike Aid Station!", "Alliance")')
        self.assertIsNone(lua.eval('AutoBG_Settings.FlagSpots'))

    def test_saved_alterac_valley_spots_are_dropped_and_arathi_kept(self):
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute(test_flag_watch.SETUP)
        lua.execute(r'''AutoBG_Settings.FlagSpots = {
            [529] = { ["Stables"] = { y = 1200.5, x = 1167.0, n = 10 },
                      ["Farm"] = { y = 873.4, x = 805.2, n = 10 } },
            [30] = { ["Stormpike Aid Station"] = { y = -29.2, x = 639.7, n = 10 },
                     ["Icewing Bunker"] = { y = -356.3, x = 202.5, n = 6 } } }''')
        lua.execute(test_flag_watch.WATCH)
        lua.execute('AutoBG_FlagWatch.onEvent(AutoBG_FlagWatch, "PLAYER_ENTERING_WORLD")')
        self.assertEqual(sorted(lua.eval('AutoBG_Settings.FlagSpots[529]').keys()), ["Farm", "Stables"])
        self.assertIsNone(lua.eval('AutoBG_Settings.FlagSpots[30]'))


class RetiredSettingsTests(unittest.TestCase):
    def test_load_clears_preview_and_unread_settings(self):
        import test_core_fixes as core
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute(core.BASE + r'''
            spyOptions = { StableRowsMigration = 1 }
            AutoBG_Spy = { EnsureOptions = function() return spyOptions end }
            AutoBG_Settings = { TestAllTimers = true, AutoQueue_TG = false }''')
        lua.execute(core.CORE)
        lua.execute('AutoBGFrame.scripts.OnEvent(AutoBGFrame, "ADDON_LOADED", "AutoBG")')
        self.assertIsNone(lua.eval('AutoBG_Settings.TestAllTimers'))
        self.assertIsNone(lua.eval('AutoBG_Settings.AutoQueue_TG'))
        self.assertIsNone(lua.eval('spyOptions.StableRowsMigration'))

    def test_no_battlegroundtargets_globals(self):
        import re
        for name in ("AutoBG_Targets.lua", "AutoBG_Spy.lua", "AutoBG_Options.lua", "AutoBG_FC.lua"):
            source = (ROOT / name).read_text("utf-8-sig")
            self.assertIsNone(re.search(r'BattlegroundTargets\w*\s*=|"BattlegroundTargets', source), name)


class EnemyByGUIDTests(unittest.TestCase):
    def test_caster_guid_names_a_never_targeted_enemy_with_class(self):
        import test_targets_guid_events as tg
        lua = tg.runtime(sighting=False)
        lua.execute('guidNames["%s"] = "Grom"' % tg.GROM)
        self.assertEqual(tuple(lua.eval('{AutoBG_Targets.EnemyByGUID("%s")}' % tg.GROM).values()), ("Grom", "WARRIOR"))
        self.assertIsNone(lua.eval('AutoBG_Targets.EnemyByGUID("0x0000000000000099")'))


SPY_BASE = test_spy_nearby.BASE.replace(
    "function Widget:SetText(text) self.text = text end",
    "function Widget:SetText(text) self.text = text end\nfunction Widget:SetTexture(t) self.texture = t end")


class StealthCardIconTests(unittest.TestCase):
    def test_stealth_card_icons_are_real_texture_paths(self):
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute(SPY_BASE)
        addon_loader.load(lua, SPY, "AutoBG_Spy.lua")
        lua.execute('AutoBG_SpyEventFrame.scripts.OnEvent(AutoBG_SpyEventFrame, "PLAYER_LOGIN")')
        expected = {
            "Stealth": "Interface\\Icons\\Ability_Stealth",
            "Shadowmeld": "Interface\\Icons\\Ability_Racial_ShadowMeld",
            "Invisibility": "Interface\\Icons\\Spell_Nature_Invisibilty",
            "Cloaking": "Interface\\Icons\\INV_Misc_EngGizmos_04",
        }
        for kind, path in expected.items():
            lua.execute('AutoBG_Spy:ShowAlert(%r, "Sneaky", "ROGUE", nil)' % kind)
            self.assertEqual(lua.eval('rawget(AutoBG_SpyAlertWindow.Icon, "texture")'), path, kind)


if __name__ == '__main__':
    unittest.main()
