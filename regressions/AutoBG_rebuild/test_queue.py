"""Queueing, pops, the end of a match, the rejoin and the release (spec 4.4 tests
2-4). AutoBG 1.0, written new 2026-11-22."""
import unittest
from abg_env import load

PICK_ALL = "AutoBGDB.queueWSG, AutoBGDB.queueAB, AutoBGDB.queueAV = true, true, true; AutoBGDB.queueOnLogin = false"


def requests(lua):
    return [l for l in lua.eval("log").values() if l.startswith("request:") or l.startswith("arena:")]


class Queueing(unittest.TestCase):
    def test_the_picked_ones_one_every_2_2_seconds(self):
        lua = load("AutoBGDB = { queueOnLogin = false }")
        lua.execute(PICK_ALL + "; __addon_ns.Queue.QueueAll()")
        self.assertEqual(requests(lua), ["request:Warsong"])
        lua.execute("step(2.1)")
        self.assertEqual(len(requests(lua)), 1)
        lua.execute("step(0.2); step(2.2); step(2.2)")
        self.assertEqual(requests(lua), ["request:Warsong", "request:Arathi", "request:Alterac"])
        self.assertEqual(lua.eval("liveTimers()"), 0)

    def test_the_answer_joins_the_teams_row_and_hides_the_window(self):
        lua = load()
        lua.execute("AutoBGDB.teamsWSG = 'xf'; __addon_ns.Queue.QueueAll('Warsong Gulch')")
        lua.execute("shownBattlefield = 'Warsong Gulch'; BattlefieldFrame:Show(); fire('BATTLEFIELDS_SHOW')")
        self.assertTrue(lua.eval("said('^select:1$')") and lua.eval("said('^join:1$')"))
        self.assertFalse(lua.eval("BattlefieldFrame:IsShown()"))
        self.assertIn("(Mixed)", lua.eval("heard('Queued for')"))
        # The server opens it again: hidden for 4 s.
        lua.execute("BattlefieldFrame:Show(); run(BattlefieldFrame, 'OnShow')")
        self.assertFalse(lua.eval("BattlefieldFrame:IsShown()"))

    def test_a_row_the_server_does_not_list_gives_any(self):
        lua = load(setup="battlemaster = { 0 }")
        lua.execute("AutoBGDB.teamsAB = 'fx'; __addon_ns.Queue.QueueAll('Arathi Basin')")
        lua.execute("shownBattlefield = 'Arathi Basin'; fire('BATTLEFIELDS_SHOW')")
        self.assertTrue(lua.eval("said('^join:0$')"))
        self.assertIn("(Any)", lua.eval("heard('Queued for')"))

    def test_an_answer_nobody_asked_for_is_left_alone(self):
        lua = load()
        lua.execute("shownBattlefield = 'Warsong Gulch'; BattlefieldFrame:Show(); fire('BATTLEFIELDS_SHOW')")
        self.assertFalse(lua.eval("said('^join')"))
        self.assertTrue(lua.eval("BattlefieldFrame:IsShown()"))

    def test_a_held_queue_is_skipped_and_the_cap_named(self):
        lua = load()
        lua.execute("queues[1] = { status = 'queued', map = 'Warsong Gulch' }; queues[2] = { status = 'queued', map = 'Blood Ring' };"
                    + PICK_ALL + "; __addon_ns.Queue.QueueAll()")
        self.assertEqual(requests(lua), ["request:Arathi"])
        lua.execute("queues[3] = { status = 'queued', map = 'Arathi Basin' }; step(2.2)")
        self.assertEqual(requests(lua), ["request:Arathi"])
        self.assertIsNotNone(lua.eval("heard('All three queues are taken')"))

    def test_afk_deserter_and_death_stop_it_and_alive_queues(self):
        lua = load()
        lua.execute("afk = 1; __addon_ns.Queue.QueueAll()")
        self.assertIsNotNone(lua.eval("heard('you are AFK')"))
        lua.execute("afk = nil; aura(me.guid, 26013, 'Deserter', 'HARMFUL'); __addon_ns.Queue.QueueAll()")
        self.assertIsNotNone(lua.eval("heard('Deserter')"))
        lua.execute("me.auras = {}; me.dead = true; __addon_ns.Queue.QueueAll()")
        self.assertEqual(requests(lua), [])
        lua.execute("me.dead = nil; fire('PLAYER_ALIVE'); step(2)")
        self.assertEqual(requests(lua), ["request:Alterac"])

    def test_queue_at_login_once_per_session_never_in_a_battleground(self):
        lua = load()
        lua.execute("step(3)")
        self.assertEqual(requests(lua), ["request:Alterac"])
        lua.execute("enter('Warsong Gulch'); enter(nil); step(5)")
        self.assertEqual(requests(lua), ["request:Alterac"])
        lua2 = load(setup="zone = { name = 'Warsong Gulch', kind = 'pvp', map = 489, inside = true }")
        lua2.execute("step(5)")
        self.assertEqual(requests(lua2), [])

    def test_queue_at_login_with_nothing_picked_says_nothing(self):
        """2026-11-23: Claude ticks no battleground now (his saved file of that
        day), and a line at every login said nothing new. Queue now still says it."""
        lua = load("AutoBGDB = { queueAV = false }")
        lua.execute("step(5)")
        self.assertIsNone(lua.eval("heard('Nothing to queue')"))
        lua.execute("__addon_ns.Queue.QueueAll()")
        self.assertIsNotNone(lua.eval("heard('Nothing to queue')"))

    def test_slash_words(self):
        lua = load()
        lua.execute("AutoBGDB.queueOnLogin = false; SlashCmdList.AUTOBG('q ab')")
        self.assertEqual(requests(lua), ["request:Arathi"])
        # The old addon's last fix (18d555c): full names too.
        lua.execute("log = {}; step(5); SlashCmdList.AUTOBG('q alterac')")
        self.assertEqual(requests(lua), ["request:Alterac"])
        lua.execute("log = {}; SlashCmdList.AUTOBG('q thorn')")
        self.assertEqual(requests(lua), [])
        lua.execute("queues[1] = { status = 'queued', map = 'Warsong Gulch' }; queues[2] = { status = 'queued', map = 'Sunstrider Court' };"
                    " SlashCmdList.AUTOBG('leave')")
        self.assertTrue(lua.eval("said('^port:1:nil$')") and lua.eval("said('^leaveArena$')"))
        self.assertIsNotNone(lua.eval("heard('Left 2 queues')"))


class Pops(unittest.TestCase):
    def test_sound_flash_and_line_once_per_invite_and_the_invite_row(self):
        lua = load()
        lua.execute("queues[1] = { status = 'confirm', map = 'Warsong Gulch', expires = 61000 }; fire('UPDATE_BATTLEFIELD_STATUS')")
        lua.execute("fire('UPDATE_BATTLEFIELD_STATUS'); step(2)")
        self.assertEqual(lua.eval("count('sound:ReadyCheck')"), 3)
        self.assertEqual(lua.eval("count('^flash$')"), 1)
        self.assertIsNotNone(lua.eval("heard('Warsong Gulch.* is ready')"))
        r = "AutoBG_QueueFrame.rows[1]"
        self.assertEqual(lua.eval(f"{r}.label.text"), "Warsong Gulch: enter")
        self.assertEqual(lua.eval(f"clock({r}.clock)"), "59")

    def test_a_reload_with_no_time_left_guesses_80_seconds(self):
        lua = load()
        lua.execute("queues[1] = { status = 'confirm', map = 'Arathi Basin', expires = 0 }; fire('UPDATE_BATTLEFIELD_STATUS')")
        self.assertEqual(lua.eval("clock(AutoBG_QueueFrame.rows[1].clock)"), "~1:20")

    def test_the_switch_off_is_silent(self):
        lua = load("AutoBGDB = { popAlert = false }")
        lua.execute("queues[1] = { status = 'confirm', map = 'Warsong Gulch', expires = 60000 }; fire('UPDATE_BATTLEFIELD_STATUS'); step(2)")
        self.assertFalse(lua.eval("said('sound') or said('flash')"))
        self.assertIsNotNone(lua.eval("heard('is ready')"))

    def test_a_queue_counts_up(self):
        lua = load()
        lua.execute("queues[2] = { status = 'queued', map = 'Warsong Gulch', instance = 9001, waited = 30000, estimate = 120000 };"
                    " fire('UPDATE_BATTLEFIELD_STATUS'); step(15)")
        r = "AutoBG_QueueFrame.rows[1]"
        self.assertEqual(lua.eval(f"{r}.label.text"), "Warsong Gulch (Cross-Faction)")
        self.assertEqual(lua.eval(f"clock({r}.clock)"), "45")
        lua.execute("queues[2] = {}; fire('UPDATE_BATTLEFIELD_STATUS')")
        self.assertFalse(lua.eval("AutoBG_QueueFrame:IsShown()"))


class AfterTheMatch(unittest.TestCase):
    def test_casts_stopped_then_left_and_the_same_battleground_queued_again(self):
        lua = load("AutoBGDB = { queueOnLogin = false }")
        lua.execute("enter('Arathi Basin'); winner = 1; line('The Horde wins!', 'CHAT_MSG_BG_SYSTEM_HORDE')")
        self.assertTrue(lua.eval("said('SpellStopCasting')"))
        self.assertFalse(lua.eval("said('LeaveBattlefield')"))
        lua.execute("step(0.3)")
        self.assertTrue(lua.eval("said('LeaveBattlefield')"))
        lua.execute("winner = nil; enter(nil); step(1.5)")
        self.assertEqual(requests(lua), ["request:Arathi"])
        lua.execute("shownBattlefield = 'Arathi Basin'; fire('BATTLEFIELDS_SHOW')")
        self.assertTrue(lua.eval("said('^join:0$')"))  # Any, Claude's teams
        lua.execute("queues[1] = { status = 'queued', map = 'Arathi Basin' }; step(2)")
        self.assertEqual(len(requests(lua)), 1)

    def test_three_tries_then_a_line(self):
        lua = load("AutoBGDB = { queueOnLogin = false }")
        lua.execute("enter('Warsong Gulch'); __addon_ns.Queue.CheckEnd(); winner = 1; __addon_ns.Queue.CheckEnd(); step(0.3)")
        lua.execute("winner = nil; enter(nil); step(1.5); step(2); step(2); step(2)")
        self.assertEqual(requests(lua), ["request:Warsong"] * 3)
        self.assertIsNotNone(lua.eval("heard('after three tries')"))

    def test_a_match_left_by_hand_is_rejoined_and_an_arena_as_skirmish(self):
        lua = load("AutoBGDB = { queueOnLogin = false }")
        lua.execute("enter('Blood Ring', true); LeaveBattlefield(); enter(nil); step(1.5)")
        self.assertEqual(requests(lua), ["arena:0"])

    def test_staying_and_no_rejoin(self):
        lua = load("AutoBGDB = { queueOnLogin = false, leave = false, rejoin = false }")
        lua.execute("enter('Warsong Gulch'); winner = 1; fire('UPDATE_BATTLEFIELD_STATUS'); step(1)")
        self.assertFalse(lua.eval("said('LeaveBattlefield')"))
        lua.execute("winner = nil; enter(nil); step(5)")
        self.assertEqual(requests(lua), [])

    def test_deserter_stops_the_rejoin(self):
        lua = load("AutoBGDB = { queueOnLogin = false }")
        lua.execute("enter('Warsong Gulch'); winner = 1; fire('UPDATE_BATTLEFIELD_STATUS'); step(0.3)")
        lua.execute("winner = nil; aura(me.guid, 1, 'Deserter', 'HARMFUL'); enter(nil); step(2)")
        self.assertEqual(requests(lua), [])
        self.assertIsNotNone(lua.eval("heard('Not queueing again')"))

    def test_release_with_no_soulstone_never_in_an_arena(self):
        lua = load()
        lua.execute("enter('Warsong Gulch'); fire('PLAYER_DEAD')")
        self.assertTrue(lua.eval("said('RepopMe')") and lua.eval("said('hide:DEATH')"))
        lua.execute("log = {}; soulstone = 1; fire('PLAYER_DEAD')")
        self.assertFalse(lua.eval("said('RepopMe')"))
        lua.execute("soulstone = nil; enter('Lordaeron Arena', true); fire('PLAYER_DEAD')")
        self.assertFalse(lua.eval("said('RepopMe')"))

    def test_deserter_end_rings(self):
        lua = load()
        lua.execute("local id = aura(me.guid, 1, 'Deserter', 'HARMFUL'); fire('UNIT_AURA_DELTA', 'player', { addedAuraInstanceIDs = { id } })")
        self.assertIsNotNone(lua.eval("heard('no queueing until it ends')"))
        lua.execute("me.auras = {}; fire('UNIT_AURA_DELTA', 'player', { removedAuraInstanceIDs = { 1 } }); step(2)")
        self.assertIsNotNone(lua.eval("heard('Deserter is gone')"))
        self.assertEqual(lua.eval("count('sound:ReadyCheck')"), 3)


if __name__ == "__main__":
    unittest.main()
