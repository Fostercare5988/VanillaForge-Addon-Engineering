"""ThreatMeter 1.0: the new threat addon, behaviour by behaviour (2026-11-08).

It replaces TWThreat, whose per-player bar frames, slide animations, 10 Hz ticker and
XML windows were the problem in the player's screenshot (bars out of rank order,
two names on one row). These tests pin the replacement: one question in flight and
the next as soon as the answer is back, rows drawn from the answer in rank order,
nothing written when nothing changed, warnings rate-limited, and timer errors
reaching the error handler.
"""
import unittest

from tm_env import load

FIGHT = "Tank:1:1000:100:1;A:0:600:60:1;B:0:500:50:1;Me:0:300:30:0"
HOT = "Tank:1:1000:100:1;Me:0:850:85:1"


def fight(saved="", setup=""):
    lua = load(saved, setup)
    lua.execute("startFight()")
    return lua


def names(lua):
    return [lua.eval("barRows()[%d].name" % i) for i in range(1, lua.eval("#barRows()") + 1)]


def glows(lua):
    return lua.eval("(function() local n = 0 for _, w in ipairs(widgets) do "
                    "if w.kind == 'AnimationGroup' then n = n + w.plays end end return n end)()")


class Asking(unittest.TestCase):
    def test_a_fight_with_a_boss_asks_the_group(self):
        lua = fight()
        self.assertEqual(lua.eval("#sent"), 1)
        self.assertEqual(lua.eval("sent[1].prefix"), "TWT_UDTSv4")
        self.assertEqual(lua.eval("sent[1].msg"), "limit=8")
        self.assertEqual(lua.eval("sent[1].channel"), "PARTY")

    def test_a_raid_is_asked_through_the_raid_channel(self):
        lua = fight(setup="raid = 10")
        self.assertEqual(lua.eval("sent[1].channel"), "RAID")

    def test_one_question_in_flight_then_the_next_when_the_answer_is_back(self):
        lua = fight()
        lua.execute("step(0.5)")
        self.assertEqual(lua.eval("#sent"), 1, "no second question before the answer")
        lua.execute('answer("%s")' % FIGHT)
        self.assertEqual(lua.eval("#sent"), 2, "a slow answer is followed at once")

    def test_a_fast_answer_waits_for_the_gap(self):
        lua = fight()
        lua.execute('answer("%s")' % FIGHT)
        lua.execute("step(0.02)")
        self.assertEqual(lua.eval("#sent"), 1, "not faster than ten a second")
        lua.execute("step(0.2)")
        self.assertEqual(lua.eval("#sent"), 2)

    def test_an_answer_nobody_asked_for_is_ignored(self):
        lua = fight()
        lua.execute('answer("%s"); answer("Tank:1:5:100:1")' % FIGHT)
        self.assertEqual(lua.eval("barRows()[1].threat"), "1000")

    def test_a_late_answer_is_asked_for_again(self):
        lua = fight()
        lua.execute("step(1.1)")
        self.assertEqual(lua.eval("#sent"), 2)

    def test_no_answer_for_three_seconds_says_so_in_the_title(self):
        lua = fight()
        for _ in range(4):
            lua.execute("step(1.05)")
        self.assertIn("no threat data", lua.eval("title()"))
        lua.execute('answer("%s")' % FIGHT)
        self.assertNotIn("no threat data", lua.eval("title()"))

    def test_the_query_follows_the_rows_setting(self):
        lua = fight("{rows = 11}")
        self.assertEqual(lua.eval("sent[1].msg"), "limit=11")

    def test_stops_with_the_fight_and_sends_nothing_more(self):
        lua = fight()
        lua.execute('answer("%s"); endFight(); step(3)' % FIGHT)
        self.assertEqual(lua.eval("#sent"), 1)
        self.assertEqual(lua.eval("#barRows()"), 0)
        self.assertEqual(lua.eval("title()"), "ThreatMeter")

    def test_nothing_is_asked_out_of_combat(self):
        lua = load()
        lua.execute("step(5)")
        self.assertEqual(lua.eval("#sent"), 0)

    def test_a_target_that_is_not_fighting_yet_is_watched(self):
        lua = load(setup="targetCombat = false")
        lua.execute("startFight(); step(0.3)")
        self.assertEqual(lua.eval("#sent"), 0)
        lua.execute("targetCombat = true; step(0.6)")
        self.assertEqual(lua.eval("#sent"), 1)

    def test_who_qualifies(self):
        for setup, saved, asked in (
            ('target.classification = "normal"', "", 0),
            ('target.classification = "normal"', "{allEnemies = true}", 1),
            ('target.classification = "rare"', "", 1),
            ('target.classification = "elite"', "", 1),
            ("target.player = true", "{allEnemies = true}", 0),
            ("target.dead = true", "", 0),
            ("target.attackable = false", "", 0),
            ("target.exists = false", "", 0),
            ("party = 0", "", 0),
        ):
            with self.subTest(setup=setup, saved=saved):
                lua = fight(saved, setup)
                self.assertEqual(lua.eval("#sent"), asked)

    def test_a_target_change_drops_the_answer_still_due(self):
        lua = fight()
        lua.execute('target.name = "Other"; ev("PLAYER_TARGET_CHANGED")')
        lua.execute("step(0.3)")
        self.assertEqual(lua.eval("#sent"), 1, "waits for the answer that is still due")
        lua.execute('answer("%s")' % FIGHT)
        self.assertEqual(lua.eval("#barRows()"), 0, "that answer was about the old target")
        lua.execute("step(0.2)")
        self.assertEqual(lua.eval("#sent"), 2)
        lua.execute('answer("%s")' % FIGHT)
        self.assertEqual(lua.eval("#barRows()"), 4)
        self.assertIn("Other", lua.eval("title()"))

    def test_the_stale_flag_does_not_swallow_the_next_fight(self):
        lua = fight()
        lua.execute("endFight(); step(1.2); startFight()")   # the first question never came back
        lua.execute('answer("%s")' % FIGHT)
        self.assertEqual(lua.eval("#barRows()"), 4)

    def test_nothing_polls_between_answers(self):
        lua = fight()
        lua.execute('answer("%s")' % FIGHT)
        lua.execute("step(0.2)")   # the next question is out
        self.assertEqual(lua.eval("#timers"), 1, "one timeout timer, no ticker")

    def test_timer_errors_reach_the_error_handler(self):
        lua = fight()
        lua.execute('answer("%s")' % FIGHT)
        lua.execute('function SendAddonMessage() error("boom") end; step(0.2)')
        self.assertIn("boom", lua.eval("handled[1]"))


class Drawing(unittest.TestCase):
    def setUp(self):
        self.lua = fight()
        self.lua.execute('answer("%s")' % FIGHT)

    def test_rows_in_rank_order_with_their_numbers(self):
        lua = self.lua
        self.assertEqual(names(lua), ["Tank", "A", "B", "Me"])
        self.assertEqual([lua.eval("barRows()[%d].perc" % i) for i in range(1, 5)], ["100%", "60%", "50%", "30%"])
        self.assertEqual(lua.eval("barRows()[2].threat"), "600")
        self.assertEqual(lua.eval("barRows()[1].value"), 100)

    def test_a_server_answer_out_of_order_is_sorted_by_threat(self):
        lua = self.lua
        lua.execute('answer("Me:0:300:30:0;A:0:600:60:1;Tank:1:1000:100:1;B:0:500:50:1")')
        self.assertEqual(names(lua), ["Tank", "A", "B", "Me"])

    def test_the_title_has_the_target_and_our_share(self):
        self.assertEqual(self.lua.eval("title()"), "Boss  |cffffd10030%")

    def test_rows_beyond_the_setting_stay_hidden(self):
        lua = fight("{rows = 3}")
        lua.execute('answer("%s")' % FIGHT)
        self.assertEqual(names(lua), ["Tank", "A", "B"])

    def test_class_colours_and_the_heat_of_our_own_bar(self):
        lua = self.lua
        mage = lua.eval("barRows()[2].color")
        self.assertAlmostEqual(mage[1], 0.41)
        mine = lua.eval("barRows()[4].color")
        self.assertAlmostEqual(mine[1], 0.6)        # 30% is green turning yellow
        lua.execute('step(0.2); answer("Tank:1:1000:100:1;Me:0:900:90:0")')
        hot = lua.eval("barRows()[2].color")
        self.assertEqual(hot[1], 1)
        self.assertLess(hot[2], 0.4)

    def test_the_tank_is_named_in_gold(self):
        gold = self.lua.eval("barRows()[1].nameColor")
        self.assertEqual(gold[2], 0.82)

    def test_a_bar_that_changes_owner_does_not_glide_from_the_old_player(self):
        lua = self.lua
        lua.execute('step(0.2); answer("Tank:1:1000:100:1;A:0:700:70:1;B:0:500:50:1;Me:0:300:30:0")')
        self.assertEqual(lua.eval("barRows()[2].interpolation"), 1, "A stays in its row: eased")
        lua.execute('step(0.2); answer("A:0:1200:120:1;Tank:1:1000:100:1;B:0:500:50:1;Me:0:300:30:0")')
        self.assertEqual(lua.eval("barRows()[1].name"), "A")
        self.assertEqual(lua.eval("barRows()[1].interpolation"), 0, "a new owner starts where it is")

    def test_an_identical_answer_writes_no_text(self):
        lua = self.lua
        before = [lua.eval("barRows()[%d].writes" % i) for i in range(1, 5)]
        lua.execute('step(0.2); answer("%s")' % FIGHT)
        after = [lua.eval("barRows()[%d].writes" % i) for i in range(1, 5)]
        self.assertEqual(before, after)

    def test_threat_per_second_from_real_time(self):
        lua = self.lua
        for t in range(1, 5):
            lua.execute('step(0.5); answer("Tank:1:1000:100:1;Me:0:%d:30:0")' % (300 + 100 * t))
        # +400 threat over 2 seconds, Me is the second row
        self.assertEqual(lua.eval("barRows()[2].tps"), 200)

    def test_the_footer_says_how_much_threat_pulls_aggro(self):
        lua = fight()
        lua.execute('answer("Tank:1:1000:100:1;Me:0:300:30:1")')
        self.assertEqual(lua.eval("footRow().name"), "Pull aggro")
        self.assertEqual(lua.eval("footRow().threat"), "+800")        # 110% of 1000, in melee, minus 300
        lua.execute('step(0.2); answer("Tank:1:1000:100:1;Me:0:300:30:0")')
        self.assertEqual(lua.eval("footRow().threat"), "+1000")       # 130% outside melee

    def test_the_footer_when_we_hold_aggro(self):
        lua = fight()
        lua.execute('answer("Me:1:1000:100:1;A:0:700:70:1")')
        self.assertEqual(lua.eval("footRow().name"), "You hold aggro")

    def test_no_footer_without_a_tank_in_the_answer(self):
        lua = fight()
        lua.execute('answer("A:0:700:70:1;Me:0:300:30:0")')
        self.assertIsNone(lua.eval("footRow()"))


class Size(unittest.TestCase):
    def test_a_full_raid_fits_in_the_window(self):
        lua = fight("{rows = 40}")
        self.assertEqual(lua.eval("sent[1].msg"), "limit=40")
        body = ";".join("P%d:%d:%d:%d:1" % (i, i == 1, 4000 - i * 50, 100 - i) for i in range(1, 41))
        lua.execute('answer("%s")' % body)
        self.assertEqual(lua.eval("#barRows()"), 40)
        self.assertEqual(lua.eval("barRows()[40].name"), "P40")

    def test_a_wide_window_shows_every_column(self):
        lua = fight("{width = 300}")
        lua.execute('answer("%s")' % FIGHT)
        self.assertTrue(lua.eval("barRows()[1].tpsShown"))
        self.assertTrue(lua.eval("barRows()[1].threatShown"))

    def test_a_narrow_window_drops_columns_before_names(self):
        lua = fight("{width = 150}")
        lua.execute('answer("%s")' % FIGHT)
        self.assertFalse(lua.eval("barRows()[1].tpsShown"))
        lua = fight("{width = 200}")
        lua.execute('answer("%s")' % FIGHT)
        self.assertTrue(lua.eval("barRows()[1].threatShown"))


class Badge(unittest.TestCase):
    def test_the_badge_shows_our_share_and_hides_after_the_fight(self):
        lua = fight()
        lua.execute('answer("%s")' % FIGHT)
        self.assertEqual(lua.eval("badgeText()"), "30%")
        self.assertTrue(lua.eval("badge().shown"))
        lua.execute("endFight()")
        self.assertFalse(lua.eval("badge().shown"))

    def test_the_badge_can_be_off(self):
        lua = fight("{badge = false}")
        lua.execute('answer("%s")' % FIGHT)
        self.assertFalse(lua.eval("badge().shown"))


class Warning(unittest.TestCase):
    def test_one_warning_then_quiet_for_five_seconds(self):
        lua = fight()
        lua.execute('answer("%s")' % HOT)
        self.assertEqual(lua.eval("sounds"), 1)
        self.assertEqual(glows(lua), 1)
        lua.execute('step(1); answer("%s")' % HOT)
        self.assertEqual(lua.eval("sounds"), 1)
        lua.execute('step(4.5); answer("%s")' % HOT)
        self.assertEqual(lua.eval("sounds"), 2)

    def test_below_the_threshold_it_stays_quiet(self):
        lua = fight()
        lua.execute('answer("Tank:1:1000:100:1;Me:0:790:79:1")')
        self.assertEqual(lua.eval("sounds"), 0)

    def test_a_tank_is_not_warned(self):
        lua = fight()
        lua.execute('answer("Me:1:1000:100:1;A:0:700:70:1")')
        self.assertEqual(lua.eval("sounds"), 0)

    def test_each_warning_can_be_off(self):
        lua = fight("{sound = false}")
        lua.execute('answer("%s")' % HOT)
        self.assertEqual(lua.eval("sounds"), 0)
        self.assertEqual(glows(lua), 1)
        lua = fight("{screenGlow = false, sound = false}")
        lua.execute('answer("%s")' % HOT)
        self.assertEqual(glows(lua), 0)

    def test_the_threshold_is_a_setting(self):
        lua = fight("{threshold = 90}")
        lua.execute('answer("%s")' % HOT)
        self.assertEqual(lua.eval("sounds"), 0)


class Preview(unittest.TestCase):
    def test_sample_players_through_the_real_path(self):
        lua = load()
        lua.execute("ns().SetPreview(true)")
        self.assertEqual(lua.eval("#barRows()"), 8)
        self.assertIn("Me", names(lua))
        self.assertEqual(lua.eval("#sent"), 0, "a preview asks the server nothing")
        lua.execute("ns().SetPreview(false)")
        self.assertEqual(lua.eval("#barRows()"), 0)

    def test_a_fight_ends_the_preview(self):
        lua = load()
        lua.execute("ns().SetPreview(true); startFight()")
        self.assertFalse(lua.eval("ns().previewing"))
        self.assertEqual(lua.eval("#sent"), 1)

    def test_no_preview_in_combat(self):
        lua = load()
        lua.execute("combat = true; ns().SetPreview(true)")
        self.assertFalse(lua.eval("ns().previewing"))

    def test_no_preview_while_off(self):
        lua = load("{enabled = false}")
        lua.execute("ns().SetPreview(true)")
        self.assertFalse(lua.eval("ns().previewing"))


class Window(unittest.TestCase):
    def test_saved_settings_are_kept_and_the_rest_filled_in(self):
        lua = load("{scale = 0.9, rows = 11, rowHeight = 26, threshold = 70}")
        self.assertEqual(lua.eval("ThreatMeterDB.threshold"), 70)
        self.assertEqual(lua.eval("ThreatMeterDB.badge"), True)
        self.assertEqual(lua.eval("ThreatMeter_Window.scale"), 0.9)

    def test_hide_out_of_combat_and_opacity(self):
        lua = load("{hideOut = true, alphaCombat = 0.7, alphaOut = 0.4}")
        self.assertFalse(lua.eval("ThreatMeter_Window.shown"))
        lua.execute("startFight()")
        self.assertTrue(lua.eval("ThreatMeter_Window.shown"))
        self.assertAlmostEqual(lua.eval("ThreatMeter_Window.alpha"), 0.7)
        lua.execute("endFight()")
        self.assertFalse(lua.eval("ThreatMeter_Window.shown"))

    def test_the_window_is_as_tall_as_what_it_shows(self):
        lua = fight()
        idle = lua.eval("ThreatMeter_Window.height")
        lua.execute('answer("%s")' % FIGHT)
        self.assertGreater(lua.eval("ThreatMeter_Window.height"), idle + 4 * 22 - 1)

    def test_a_locked_window_does_not_move(self):
        lua = load("{locked = true}")
        lua.execute('run(ThreatMeter_Window, "OnDragStart")')
        self.assertFalse(lua.eval("ThreatMeter_Window.moving"))

    def test_a_dragged_window_remembers_where_it_was_left(self):
        lua = load()
        lua.execute('local w = ThreatMeter_Window; w:ClearAllPoints(); w:SetPoint("TOPLEFT", UIParent, "BOTTOMLEFT", 300, 700)')
        lua.execute('run(ThreatMeter_Window, "OnDragStop")')
        self.assertEqual(lua.eval("ThreatMeterDB.window[2]"), "BOTTOMLEFT")
        self.assertEqual(lua.eval("ThreatMeterDB.window[3]"), 300)

    def test_close_turns_it_off_and_on_turns_it_back_on(self):
        lua = fight()
        lua.execute('answer("%s")' % FIGHT)
        lua.execute("local b = ThreatMeter_Close; b.scripts.OnClick(b)")
        self.assertFalse(lua.eval("ThreatMeter_Window.shown"))
        self.assertFalse(lua.eval("ThreatMeterDB.enabled"))
        self.assertFalse(lua.eval("badge().shown"))
        lua.execute("step(5); endFight(); startFight()")
        self.assertEqual(lua.eval("#sent"), 1, "off: nothing is asked of the server")
        lua.execute('SlashCmdList.THREATMETER("on")')
        self.assertTrue(lua.eval("ThreatMeter_Window.shown"))
        self.assertEqual(lua.eval("#sent"), 2, "on in a fight starts asking at once")

    def test_off_registers_no_events(self):
        lua = load("{enabled = false}")
        self.assertFalse(lua.eval("ThreatMeter_Window.shown"))
        lua.execute("startFight()")
        self.assertEqual(lua.eval("#sent"), 0)
        lua.execute("local s = ThreatMeter_enabled; s:SetChecked(true); s.scripts.OnClick(s)")
        self.assertEqual(lua.eval("#sent"), 1)

    def test_the_old_hidden_window_setting_becomes_off(self):
        lua = load("{shown = false}")
        self.assertFalse(lua.eval("ThreatMeterDB.enabled"))
        self.assertIsNone(lua.eval("ThreatMeterDB.shown"))
        self.assertIsNone(lua.eval("ThreatMeterDB.shown"))


class Settings(unittest.TestCase):
    def test_pages_are_in_addon_options(self):
        lua = load()
        labels = [lua.eval("categories[%d].name" % i) for i in range(1, lua.eval("#categories") + 1)]
        self.assertEqual(labels, ["ThreatMeter", "Window", "Alerts"])

    def test_a_switch_changes_the_setting_and_the_window(self):
        lua = load()
        lua.execute("local s = ThreatMeter_hideOut; s:SetChecked(true); s.scripts.OnClick(s)")
        self.assertTrue(lua.eval("ThreatMeterDB.hideOut"))
        self.assertFalse(lua.eval("ThreatMeter_Window.shown"))

    def test_a_slider_changes_the_setting_and_what_is_asked_for(self):
        lua = load()
        lua.execute("local s = ThreatMeter_rows; s:SetValue(10); s.scripts.OnValueChanged(s)")
        self.assertEqual(lua.eval("ThreatMeterDB.rows"), 10)
        lua.execute("startFight()")
        self.assertEqual(lua.eval("sent[1].msg"), "limit=10")

    def test_normal_enemies_switch_takes_effect_on_the_current_target(self):
        lua = load(setup='target.classification = "normal"')
        lua.execute("startFight()")
        self.assertEqual(lua.eval("#sent"), 0)
        lua.execute("local s = ThreatMeter_allEnemies; s:SetChecked(true); s.scripts.OnClick(s)")
        self.assertEqual(lua.eval("#sent"), 1)

    def test_slash_opens_the_settings(self):
        lua = load()
        lua.execute('SlashCmdList.THREATMETER("")')
        self.assertTrue(lua.eval("ThreatMeter_Options.shown"))


class Guard(unittest.TestCase):
    def test_without_classicapi_it_says_so_and_does_nothing(self):
        lua = load(setup="CLASSIC_API_VERSION = nil")
        self.assertIsNone(lua.eval("ThreatMeter_Window"))
        self.assertIn("needs ClassicAPI", lua.eval("chat[#chat]"))
        lua.execute("startFight()")
        self.assertEqual(lua.eval("#sent"), 0)


class Garbage(unittest.TestCase):
    def test_an_answer_costs_little_memory(self):
        lua = fight()
        body = ";".join("P%d:%d:%d:%d:1" % (i, i == 1, 2000 - i * 100, 100 - i * 5) for i in range(1, 11))
        lua.execute('answer("%s")' % body)
        lua.execute('collectgarbage("collect"); collectgarbage("stop"); __before = collectgarbage("count")')
        for i in range(100):
            lua.execute('step(0.2); answer("%s")' % body.replace(":95:", ":%d:" % (90 - i % 5), 1))
        grown = lua.eval('collectgarbage("count") - __before')
        lua.execute('collectgarbage("restart")')
        self.assertLess(grown / 100, 4, "KB per answer for ten players")


if __name__ == "__main__":
    unittest.main()
