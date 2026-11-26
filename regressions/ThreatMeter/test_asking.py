"""ThreatMeter 1.0: asking the server (spec 4.5, tests 3-6, 11, 12, 15).

One question in flight, the next as soon as the answer is in and at most ten a
second, asked again after 1 s without an answer; an answer due at a target change is
dropped. Only bosses, elites, rare elites and rares in combat, in a party or raid.
A target not yet fighting wakes the meter by UNIT_FLAGS, not by a watch timer.
"""
import unittest

from tm_env import FIGHT, fight, load, names


class WhoIsAskedAbout(unittest.TestCase):
    def test_a_boss_in_combat_in_a_party_is_asked_about(self):
        lua = fight()
        self.assertEqual(lua.eval("#sent"), 1)
        self.assertEqual(lua.eval("sent[1].prefix"), "TWT_UDTSv4")
        self.assertEqual(lua.eval("sent[1].msg"), "limit=14")
        self.assertEqual(lua.eval("sent[1].channel"), "PARTY")

    def test_a_raid_is_asked_through_the_raid_channel(self):
        lua = fight(setup="makeRaid(10)")
        self.assertEqual(lua.eval("sent[1].channel"), "RAID")

    def test_elites_rare_elites_and_rares_qualify(self):
        for kind in ("elite", "rareelite", "rare"):
            lua = fight(setup='target.kind = "%s"' % kind)
            self.assertEqual(lua.eval("#sent"), 1, kind)

    def test_targets_that_do_not_qualify_are_not_asked_about(self):
        cases = {
            "a normal enemy": 'target.kind = "normal"',
            "a player": "target.player = true",
            "a dead boss": "target.dead = true",
            "a friendly boss": "target.enemy = false",
            "no target": "target.exists = false",
            "solo": "party = 0",
        }
        for case, setup in cases.items():
            lua = fight(setup=setup)
            self.assertEqual(lua.eval("#sent"), 0, case)

    def test_the_question_asks_for_the_most_whatever_the_window_shows(self):
        """Review 2026-11-26: it asked for as many as shown, so you could fall out of
        the answer (test_window, test_with_three_players_shown_the_fourth_is_still_warned)."""
        lua = fight("ThreatMeterDB = { rows = 8 }")
        self.assertEqual(lua.eval("sent[1].msg"), "limit=14")
        lua.execute('settingsWindow.use("ThreatMeter_rows", 5); answer("%s"); step(0.2)' % FIGHT)
        self.assertEqual(lua.eval("sent[#sent].msg"), "limit=14")


class TargetNotFightingYet(unittest.TestCase):
    def test_its_combat_flag_wakes_the_meter(self):
        lua = fight(setup="target.combat = false")
        self.assertEqual(lua.eval("#sent"), 0)
        self.assertTrue(lua.eval('receives(%s, "UNIT_FLAGS", "target")' % FRAME))
        self.assertFalse(lua.eval('receives(%s, "UNIT_FLAGS", "party1")' % FRAME))
        self.assertEqual(lua.eval("liveTimers()"), 0, "no watch timer")
        lua.execute('fire("UNIT_FLAGS", "target")')
        self.assertEqual(lua.eval("#sent"), 0, "still not fighting")
        lua.execute('target.combat = true; fire("UNIT_FLAGS", "target")')
        self.assertEqual(lua.eval("#sent"), 1)
        self.assertFalse(lua.eval('receives(%s, "UNIT_FLAGS", "target")' % FRAME), "unregistered once it fights")

    def test_out_of_combat_the_flag_is_not_listened_to(self):
        lua = load(setup="target.combat = false")
        self.assertNotIn("UNIT_FLAGS", lua.eval("listening()"))


# The meter's event frame: the one that hears PLAYER_TARGET_CHANGED.
FRAME = "(function() for _, w in ipairs(widgets) do if w.events.PLAYER_TARGET_CHANGED then return w end end end)()"


class Pace(unittest.TestCase):
    def test_one_question_in_flight_then_the_next_when_the_answer_is_in(self):
        lua = fight()
        lua.execute("step(0.5)")
        self.assertEqual(lua.eval("#sent"), 1, "no second question before the answer")
        lua.execute('answer("%s")' % FIGHT)
        self.assertEqual(lua.eval("#sent"), 2, "a slow answer is followed at once")

    def test_a_fast_answer_waits_until_a_tenth_of_a_second_after_the_question(self):
        lua = fight()
        lua.execute('step(0.03); answer("%s"); step(0.03)' % FIGHT)
        self.assertEqual(lua.eval("#sent"), 1)
        lua.execute("step(0.05)")
        self.assertEqual(lua.eval("#sent"), 2)

    def test_an_event_right_after_a_fast_answer_does_not_ask_early(self):
        """Built 2026-11-26: an event (a flag, the roster) called the asker past the floor."""
        lua = fight()
        lua.execute('answer("%s"); fire("UNIT_FLAGS", "target"); fire("GROUP_ROSTER_UPDATE")' % FIGHT)
        self.assertEqual(lua.eval("#sent"), 1)
        lua.execute("step(0.1)")
        self.assertEqual(lua.eval("#sent"), 2)

    def test_no_answer_in_a_second_asks_again(self):
        lua = fight()
        lua.execute("step(0.99)")
        self.assertEqual(lua.eval("#sent"), 1)
        lua.execute("step(0.02)")
        self.assertEqual(lua.eval("#sent"), 2)

    def test_an_old_questions_timeout_does_not_cut_a_later_one_short(self):
        lua = fight()
        lua.execute('step(0.5); answer("%s")' % FIGHT)  # question 2 at 0.5 s
        lua.execute("step(0.6)")                          # question 1's timeout at 1.0 s
        self.assertEqual(lua.eval("#sent"), 2, "question 2 has 0.4 s left")
        lua.execute("step(0.45)")
        self.assertEqual(lua.eval("#sent"), 3)

    def test_three_seconds_without_an_answer_say_so_and_an_answer_clears_it(self):
        lua = fight()
        lua.execute("step(1); step(1)")
        self.assertNotIn("no threat data", lua.eval("title()"))
        lua.execute("step(1)")
        self.assertIn("no threat data", lua.eval("title()"))
        lua.execute('answer("%s")' % FIGHT)
        self.assertEqual(lua.eval("title()"), "Onyxia  60%")

    def test_an_answer_nobody_asked_for_is_not_read(self):
        lua = fight()
        lua.execute('answer("%s"); answer("Tank:1:5:100:1")' % FIGHT)
        self.assertEqual(names(lua), ["Tank", "Healer", "Me"])

    def test_other_addon_messages_are_heard_only_while_a_question_is_out(self):
        lua = fight()
        self.assertIn("CHAT_MSG_ADDON", lua.eval("listening()"))
        lua.execute('step(0.03); answer("%s")' % FIGHT)
        self.assertNotIn("CHAT_MSG_ADDON", lua.eval("listening()"))
        lua.execute('fire("CHAT_MSG_ADDON", "BigWigs", "hello", "RAID", "Tank")')  # nothing breaks
        self.assertEqual(lua.eval("#handled"), 0)


class Staleness(unittest.TestCase):
    def test_an_answer_due_at_a_target_change_is_dropped(self):
        lua = fight()
        lua.execute('retarget("Razorgore", "worldboss")')
        self.assertEqual(lua.eval("#sent"), 1, "the old question is still out")
        lua.execute('answer("%s")' % FIGHT)
        self.assertEqual(names(lua), [], "it was about Onyxia")
        self.assertEqual(lua.eval("title()"), "Razorgore")
        lua.execute("step(0.1)")
        self.assertEqual(lua.eval("#sent"), 2, "then the new target is asked about")
        lua.execute('answer("Tank:1:50:100:1;Me:0:40:80:0")')
        self.assertEqual(names(lua), ["Tank", "Me"])

    def test_a_lost_answer_after_a_target_change_runs_into_its_timeout(self):
        lua = fight()
        lua.execute('retarget("Razorgore", "worldboss"); step(1.01)')
        self.assertEqual(lua.eval("#sent"), 2)

    def test_a_target_change_to_a_normal_enemy_stops_the_meter(self):
        lua = fight()
        lua.execute('answer("%s"); retarget("Whelp", "normal"); step(0.2); step(1); step(1)' % FIGHT)
        self.assertEqual(lua.eval("#sent"), 1, "nothing after the change")
        self.assertEqual(names(lua), [])
        self.assertEqual(lua.eval("title()"), "ThreatMeter")

    def test_the_target_dying_stops_the_meter_at_the_next_question(self):
        lua = fight()
        lua.execute('target.dead = true; answer("%s"); step(1); step(1)' % FIGHT)
        self.assertEqual(lua.eval("#sent"), 1)
        self.assertEqual(lua.eval("title()"), "ThreatMeter")


class RosterAndCombat(unittest.TestCase):
    def test_a_roster_change_reads_nothing_until_the_next_answer(self):
        lua = fight(setup="makeRaid(40)")
        lua.execute('answer("%s")' % FIGHT)
        lua.execute("roster = 0")
        for _ in range(10):
            lua.execute('fire("GROUP_ROSTER_UPDATE")')
        self.assertEqual(lua.eval("roster"), 0)
        lua.execute('step(0.2); answer("%s")' % FIGHT)
        self.assertEqual(lua.eval("roster"), 40, "a raid of 40 read once")
        lua.execute('step(0.2); answer("%s")' % FIGHT)
        self.assertEqual(lua.eval("roster"), 40, "and not again without a change")

    def test_leaving_the_group_stops_the_meter(self):
        lua = fight()
        lua.execute('answer("%s"); party = 0; fire("GROUP_ROSTER_UPDATE"); step(0.2); step(1)' % FIGHT)
        self.assertEqual(lua.eval("#sent"), 1)
        self.assertEqual(names(lua), [])

    def test_the_end_of_the_fight_clears_the_rows_and_asks_nothing_more(self):
        lua = fight()
        lua.execute('answer("%s"); calm(); step(0.2); step(1); step(3)' % FIGHT)
        self.assertEqual(lua.eval("#sent"), 1)
        self.assertEqual(names(lua), [])
        self.assertEqual(lua.eval("title()"), "ThreatMeter")
        self.assertFalse(lua.eval("ThreatMeter_Badge:IsShown()"))


class AtRest(unittest.TestCase):
    def test_out_of_combat_four_events_no_onupdate_no_timer(self):
        lua = load()
        self.assertEqual(lua.eval("listening()"),
                         "GROUP_ROSTER_UPDATE,PLAYER_ENTERING_WORLD,PLAYER_IN_COMBAT_CHANGED,PLAYER_TARGET_CHANGED")
        self.assertEqual(lua.eval("liveTimers()"), 0)

    def test_after_a_fight_no_timer_is_left(self):
        lua = fight()
        lua.execute('answer("%s"); step(0.2); answer("%s"); calm(); step(2)' % (FIGHT, FIGHT))
        self.assertEqual(lua.eval("liveTimers()"), 0)
        self.assertNotIn("OnUpdate", lua.eval("listening()"))

    def test_a_question_that_fails_to_go_out_is_asked_again(self):
        """Review 2026-11-26: the timeout was armed after the send, so a send that
        failed left its question out for good, and the meter never asked again."""
        lua = fight()
        lua.execute('realSend = SendAddonMessage; SendAddonMessage = function() error("send failed") end; step(1)')
        self.assertEqual(lua.eval("#handled"), 1, "the error reaches the error handler")
        lua.execute("SendAddonMessage = realSend; step(0.5); step(0.55)")
        self.assertEqual(lua.eval("#sent"), 2, "the failed question ran into its timeout")

    def test_a_timer_error_reaches_the_error_handler(self):
        lua = fight()
        lua.execute('function IsInRaid() error("boom") end; step(1.01)')
        self.assertEqual(lua.eval("#handled"), 1)
        self.assertIn("boom", lua.eval("handled[1]"))

    def test_an_answer_makes_no_table_and_no_closure(self):
        lua = fight()
        lua.execute('answer("%s"); step(0.2)' % FIGHT)
        lua.execute('''
            local msg = "TWTv4=%s"
            C_Timer.After = function() end
            asked = 0
            SendAddonMessage = function() asked = asked + 1 end
            collectgarbage("collect"); collectgarbage("stop")
            local before = collectgarbage("count")
            for i = 1, 200 do step(0.2); fire("CHAT_MSG_ADDON", "TWT", msg, "RAID", "Tank") end
            grew = (collectgarbage("count") - before) * 1024
            collectgarbage("restart")
        ''' % FIGHT)
        self.assertEqual(lua.eval("asked"), 200, "every answer was read and followed")
        self.assertLess(lua.eval("grew"), 200 * 24, "under 24 bytes an answer: no table, no closure")


if __name__ == "__main__":
    unittest.main()
