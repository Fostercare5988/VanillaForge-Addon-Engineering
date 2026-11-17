"""Shift turn-ins (spec K5-K7; tests 5-8). Quest IDs and items are the OctoWoW
database's (spec 3, evidence): 8243 Zanza's Potent Potables (19858 x1; Spirit
20079, Sheen 20080, Swiftness 20081), 5402 Minion's Scourgestones (12840 x20),
7223 Armor Scraps (17422 x20).
"""
import unittest
from al_env import load

ZANZA = "quest(8243, { 'item', 19858, 1 }) choices = { 20080, 20079, 20081 }"


def picks(lua):
    return lua.eval("(function() local l = calls.pick or {} return table.concat(l, ',') end)()")


class Complete(unittest.TestCase):
    def test_shift_turns_in_the_biggest_complete_quest_first(self):
        lua = load(setup="quest(1, { 'item', 50203, 1 }) quest(2, { 'item', 50203, 10 }) quest(3, { 'monster', 5, 8 })")
        lua.execute("shift = true; gossip({ { 1, true }, { 3, false }, { 2, true } })")
        self.assertEqual(picks(lua), "active:2")
        lua.execute("gossip({ { 1, true }, { 3, false } })")
        self.assertEqual(picks(lua), "active:2,active:1")
        lua.execute("gossip({ { 3, false } })")
        self.assertEqual(picks(lua), "active:2,active:1")

    def test_scourgestones_the_biggest_first(self):
        lua = load(setup="quest(5402, { 'item', 12840, 20 }) quest(5403, { 'item', 12841, 10 }) quest(5404, { 'item', 12843, 1 })")
        lua.execute("shift = true; gossip({ { 5404, true }, { 5403, true }, { 5402, true } })")
        self.assertEqual(picks(lua), "active:5402")

    def test_no_data_or_a_tie_keeps_the_list_order(self):
        lua = load()
        lua.execute("shift = true; gossip({ { 11, true }, { 12, true } })")
        self.assertEqual(picks(lua), "active:11")

    def test_a_greeting_window_picks_by_place(self):
        lua = load(setup="quest(1, { 'item', 50203, 1 }) quest(2, { 'item', 50203, 10 })")
        lua.execute("shift = true; greeting({ { 1, true }, { 2, true } })")
        self.assertEqual(picks(lua), "active#2")

    def test_no_shift_or_the_switch_off_does_nothing(self):
        lua = load()
        lua.execute("gossip({ { 1, true } })")
        self.assertEqual(picks(lua), "")
        lua = load("AutoLazyDB = { shiftQuests = false }")
        lua.execute("shift = true; gossip({ { 1, true } }) fire('QUEST_PROGRESS') fire('QUEST_COMPLETE')")
        self.assertEqual(picks(lua) + str(lua.eval("count('CompleteQuest') + count('GetQuestReward')")), "0")

    def test_progress_is_completed_and_one_reward_taken(self):
        lua = load()
        lua.execute("shift = true; fire('QUEST_PROGRESS') choices = {} fire('QUEST_COMPLETE')")
        self.assertEqual(lua.eval("count('CompleteQuest')"), 1)
        self.assertEqual(lua.eval("last('GetQuestReward')"), 0)
        lua.execute("choices = { 20079 } fire('QUEST_COMPLETE')")
        self.assertEqual(lua.eval("last('GetQuestReward')"), 1)

    def test_an_incomplete_progress_page_stops(self):
        lua = load()
        lua.execute("shift = true; completable = false; fire('QUEST_PROGRESS')")
        self.assertEqual(lua.eval("count('CompleteQuest')"), 0)


class Offered(unittest.TestCase):
    def test_a_turn_in_you_carry_the_items_for_is_picked(self):
        lua = load(setup="quest(7223, { 'item', 17422, 20 }) bags[17422] = 20")
        lua.execute("shift = true; gossip({}, { { 7223 } })")
        self.assertEqual(picks(lua), "offered:7223")

    def test_too_few_items_a_monster_or_no_objective_is_not_picked(self):
        lua = load(setup="quest(7223, { 'item', 17422, 20 }) bags[17422] = 19 quest(9, { 'item', 17422, 1 }, { 'monster', 5, 1 })"
                         " quest(10)")
        lua.execute("shift = true; gossip({}, { { 7223 }, { 9 }, { 10 } })")
        self.assertEqual(picks(lua), "")

    def test_complete_quests_come_before_offers(self):
        lua = load(setup="quest(7223, { 'item', 17422, 20 }) bags[17422] = 20")
        lua.execute("shift = true; gossip({ { 1, true } }, { { 7223 } })")
        self.assertEqual(picks(lua), "active:1")

    def test_an_uncached_quest_is_asked_for_and_picked_when_it_comes(self):
        lua = load(setup="bags[17422] = 20")
        lua.execute("shift = true; gossip({}, { { 7223 } })")
        self.assertEqual(lua.eval("last('load')"), 7223)
        self.assertEqual(picks(lua), "")
        lua.execute("quest(7223, { 'item', 17422, 20 }) fire('QUEST_DATA_LOAD_RESULT', 7223, 1)")
        self.assertEqual(picks(lua), "offered:7223")

    def test_not_after_the_window_closed(self):
        lua = load(setup="bags[17422] = 20")
        lua.execute("shift = true; gossip({}, { { 7223 } }) closeAll()")
        lua.execute("quest(7223, { 'item', 17422, 20 }) fire('QUEST_DATA_LOAD_RESULT', 7223, 1)")
        self.assertEqual(picks(lua), "")

    def test_an_accept_page_is_never_accepted_and_that_offer_waits(self):
        lua = load(setup="quest(7223, { 'item', 17422, 20 }) bags[17422] = 20")
        lua.execute("shift = true; gossip({}, { { 7223 } }) fire('QUEST_DETAIL')")
        lua.execute("gossip({}, { { 7223 } })")
        self.assertEqual(picks(lua), "offered:7223")
        self.assertIsNone(lua.eval("AcceptQuest"))
        lua.execute("fire('QUEST_TURNED_IN', 7223, 0, 0) gossip({}, { { 7223 } })")
        self.assertEqual(picks(lua), "offered:7223,offered:7223")


class Rewards(unittest.TestCase):
    def test_several_wait_the_first_time(self):
        lua = load(setup=ZANZA)
        lua.execute("shift = true; fire('QUEST_COMPLETE')")
        self.assertEqual(lua.eval("count('GetQuestReward')"), 0)
        self.assertEqual(lua.eval("#chat"), 0)

    def test_the_hand_chosen_zanza_potion_is_taken_again(self):
        lua = load(setup=ZANZA)
        lua.execute("fire('QUEST_COMPLETE') GetQuestReward(2) forget()")  # Spirit, by hand
        lua.execute("shift = true; fire('QUEST_COMPLETE')")
        self.assertEqual(lua.eval("last('GetQuestReward')"), 2)
        lua.execute("choices = { 20081, 20079, 20080 } forget() fire('QUEST_COMPLETE')")  # the same items in another order
        self.assertEqual(lua.eval("count('GetQuestReward')"), 0)

    def test_another_quests_choice_is_not_used(self):
        lua = load(setup=ZANZA)
        lua.execute("fire('QUEST_COMPLETE') GetQuestReward(2) forget()")
        lua.execute("choices = { 1, 20079, 3 } shift = true; fire('QUEST_COMPLETE')")
        self.assertEqual(lua.eval("count('GetQuestReward')"), 0)


class Repeat(unittest.TestCase):
    SETUP = "quest(5402, { 'item', 12840, 20 }) quest(7223, { 'item', 17422, 40 }) bags[12840] = 40 bags[17422] = 40"

    def test_the_last_turn_in_here_is_picked_again_first(self):
        lua = load(setup=self.SETUP)
        lua.execute("fire('QUEST_COMPLETE') fire('QUEST_TURNED_IN', 5402, 0, 0)")  # by hand
        lua.execute("shift = true; gossip({}, { { 7223 }, { 5402 } })")
        self.assertEqual(picks(lua), "offered:5402")

    def test_it_stops_when_the_items_run_out(self):
        lua = load(setup=self.SETUP)
        lua.execute("fire('QUEST_COMPLETE') fire('QUEST_TURNED_IN', 5402, 0, 0) bags[12840] = 0 bags[17422] = 0")
        lua.execute("shift = true; gossip({}, { { 5402 } })")
        self.assertEqual(picks(lua), "")

    def test_another_npc_gets_no_repeat_first(self):
        lua = load(setup=self.SETUP)
        lua.execute("fire('QUEST_COMPLETE') fire('QUEST_TURNED_IN', 5402, 0, 0) guids.npc = 'Creature-2'")
        lua.execute("shift = true; gossip({}, { { 7223 }, { 5402 } })")
        self.assertEqual(picks(lua), "offered:7223")

    def test_a_chain_step_without_shift_is_ours_only_here_and_soon(self):
        lua = load()
        lua.execute("shift = true; gossip({ { 1, true } }) shift = false")
        lua.execute("fire('QUEST_PROGRESS')")
        self.assertEqual(lua.eval("count('CompleteQuest')"), 1)       # same NPC, at once
        lua.execute("step(3) fire('QUEST_PROGRESS')")
        self.assertEqual(lua.eval("count('CompleteQuest')"), 1)       # 3 s later
        lua.execute("shift = true; gossip({ { 1, true } }) shift = false; guids.npc = 'Creature-2' fire('QUEST_PROGRESS')")
        self.assertEqual(lua.eval("count('CompleteQuest')"), 1)       # another NPC
        lua.execute("guids.npc = 'Creature-1' gossip({ { 1, true } })")
        self.assertEqual(picks(lua), "active:1,active:1")              # a new window needs Shift


if __name__ == "__main__":
    unittest.main()
