"""Audit 2026-10-26 reproductions (Alterac Valley session, .private/audit-AutoBG-2026-10-26.md).

Each test fails on AutoBG e24539b and states the behaviour the fix must give:

- An Alterac Valley mine message must never put "Gold Mine" (an Arathi Basin
  base) on the Alterac Valley timers.
- An enemy seen starting an Opening cast at a flag warns, so Alterac Valley
  (where the 40-player enemy frames, and their cast bars, can be off) warns at all.
- A node message that only reports a holder ("was taken") right after your own
  Opening must not save your spot as that node's flag.
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
        self.assertEqual(lua.eval('AutoBG_AVNodeFrame.rows[1].icon.texture'), "Interface\\WorldStateFrame\\HordeFlag")

    def test_mine_lines_do_not_teach_flag_spots(self):
        lua = av_timers()
        lua.execute('heard = {}; AutoBG_FlagWatch = { OnNodeMessage = function(_, node) table.insert(heard, node) end }')
        yell(lua, "The Horde has taken the Irondeep Mine! Its supplies will now be used for reinforcements!")
        self.assertEqual(len(lua.eval('heard')), 0)


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


class FlagSpotLearningTests(unittest.TestCase):
    PLAYER = "0x0000000000000001"

    def own_opening(self, lua):
        lua.execute('pos.player = { 674, -148 }')
        lua.execute('AutoBG_FlagWatch.onEvent(AutoBG_FlagWatch, "UNIT_CASTEVENT", "%s", nil, "CAST", 24391, 0)'
                    % self.PLAYER)

    def test_holder_message_after_your_opening_does_not_move_a_flag(self):
        """Saved AV spots on 2026-10-26: Snowfall and Iceblood Graveyard both sat
        on Dun Baldar North Bunker, where the player had opened a flag."""
        lua = test_flag_watch.runtime()
        self.own_opening(lua)
        lua.execute('AutoBG_FlagWatch:OnNodeMessage("Snowfall Graveyard", '
                    '"The Snowfall Graveyard was taken by the Horde!", "Horde")')
        self.assertIsNone(lua.eval('AutoBG_Settings.FlagSpots and AutoBG_Settings.FlagSpots[529] '
                                   'and AutoBG_Settings.FlagSpots[529]["Snowfall Graveyard"]'))

    def test_assault_after_your_opening_still_learns_the_flag(self):
        lua = test_flag_watch.runtime()
        self.own_opening(lua)
        lua.execute('AutoBG_FlagWatch:OnNodeMessage("Dun Baldar North Bunker", '
                    '"The Dun Baldar North Bunker is under attack! If left unchecked, the Horde will destroy it!", "Horde")')
        self.assertEqual(lua.eval('AutoBG_Settings.FlagSpots[529]["Dun Baldar North Bunker"].y'), 674)

    def test_two_openings_in_one_window_teach_nothing(self):
        lua = test_flag_watch.runtime()
        self.own_opening(lua)
        lua.execute('pos["%s"] = { 300, 300 }' % test_flag_watch.BALLOON)
        lua.execute('AutoBG_FlagWatch.onEvent(AutoBG_FlagWatch, "UNIT_CASTEVENT", "%s", nil, "CAST", 24391, 0)'
                    % test_flag_watch.BALLOON)
        lua.execute('AutoBG_FlagWatch:OnNodeMessage("Icewing Bunker", '
                    '"The Icewing Bunker is under attack! If left unchecked, the Horde will destroy it!", "Horde")')
        self.assertIsNone(lua.eval('AutoBG_Settings.FlagSpots and AutoBG_Settings.FlagSpots[529] '
                                   'and AutoBG_Settings.FlagSpots[529]["Icewing Bunker"]'))

    def test_spots_saved_on_top_of_each_other_are_dropped(self):
        """The saved AV spots of 2026-10-26: three flags at one place."""
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute(test_flag_watch.SETUP)
        lua.execute(r'''AutoBG_Settings.FlagSpots = { [529] = {
            ["Snowfall Graveyard"] = { y = -147.70, x = 673.79, n = 1 },
            ["Dun Baldar North Bunker"] = { y = -147.61, x = 673.87, n = 6 },
            ["Iceblood Graveyard"] = { y = -147.53, x = 673.88, n = 1 },
            ["Icewing Bunker"] = { y = -355.71, x = 202.61, n = 9 } } }''')
        lua.execute(test_flag_watch.WATCH)
        lua.execute('AutoBG_FlagWatch.onEvent(AutoBG_FlagWatch, "PLAYER_ENTERING_WORLD")')
        left = sorted(lua.eval('AutoBG_Settings.FlagSpots[529]').keys())
        self.assertEqual(left, ["Icewing Bunker"])


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
