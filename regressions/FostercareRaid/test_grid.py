"""The grid (spec R1-R4, R6, 4.7 "Raid"): a roster change rebuilds only changed
buttons; range from UNIT_IN_RANGE_UPDATE; health text only when its number
changes; aggro on the target's target; unit events only for the shown members.
"""
import unittest
from fr_env import load, in_party, in_raid


class Roster(unittest.TestCase):
    def test_solo_shows_nothing(self):
        lua = load()
        self.assertFalse(lua.eval("grid():IsShown()"))
        self.assertIsNone(lua.eval("btn(1, 1)"), "no button is made before a member needs it")

    def test_a_party_is_one_column_with_you_first(self):
        lua = in_party()
        self.assertEqual([lua.eval(f"shown(1, {k})") for k in (1, 2, 3, 4)], ["Claude", "Ann", "Bob", None])
        self.assertTrue(lua.eval("grid():IsShown()"))
        self.assertEqual(lua.eval("btn(1, 2):GetAttribute('unit')"), "party1")
        self.assertEqual(lua.eval("btn(1, 2):GetAttribute('type1')"), "target")
        self.assertEqual(lua.eval("btn(1, 2):GetAttribute('type2')"), "menu")
        self.assertEqual(lua.eval("grid():GetWidth()"), 58)
        self.assertEqual(lua.eval("grid():GetHeight()"), 3 * 35 + 2 * 3)

    def test_raid_groups_are_columns(self):
        lua = in_raid(load(), [("Claude", "ROGUE", 1), ("Ann", "PRIEST", 3), ("Bob", "MAGE", 1)])
        self.assertEqual(lua.eval("shown(1, 1)"), "Claude")
        self.assertEqual(lua.eval("shown(1, 2)"), "Bob")
        self.assertEqual(lua.eval("shown(3, 1)"), "Ann")
        self.assertEqual(lua.eval("(select(4, btn(3, 1):GetPoint()))"), 2 * (58 + 2))
        self.assertEqual(lua.eval("(select(5, btn(1, 2):GetPoint()))"), -(35 + 3))
        self.assertEqual(lua.eval("grid():GetWidth()"), 8 * 60 - 2)

    def test_a_roster_change_rebuilds_only_the_changed_buttons(self):
        lua = in_party()
        lua.execute("calls.UnitInRange = 0; joinParty('Ann', 'Bob', 'Cid')")
        self.assertEqual(lua.eval("count('UnitInRange')"), 1, "only Cid's button was drawn again")
        self.assertEqual(lua.eval("shown(1, 4)"), "Cid")
        lua.execute("joinParty('Ann')")
        self.assertEqual([lua.eval(f"shown(1, {k})") for k in (1, 2, 3, 4)], ["Claude", "Ann", None, None])
        self.assertIsNone(lua.eval("btn(1, 3):GetAttribute('unit')"))

    def test_a_burst_of_roster_events_is_one_pass(self):
        lua = in_party()
        lua.execute("calls.UnitInRange = 0; party = { 'Ann', 'Bob', 'Cid' }; member('party3', 'Cid', 'MAGE')")
        lua.execute("for i = 1, 5 do fire('PARTY_MEMBERS_CHANGED') end")
        self.assertIsNone(lua.eval("shown(1, 4)"), "the pass waits for the next frame")
        lua.execute("runTimers()")
        self.assertEqual(lua.eval("shown(1, 4)"), "Cid")
        self.assertEqual(lua.eval("count('UnitInRange')"), 1)

    def test_class_colour_from_the_roster_or_the_player_cache(self):
        lua = in_raid(load(), [("Claude", "ROGUE", 1), ("Ann", "PRIEST", 1)])
        self.assertEqual(lua.eval("btn(1, 2).health.c.name"), "PRIEST")
        lua = load()
        lua.execute("known.Ann = 'DRUID'; party = { 'Ann' }; members.party1 = { name = 'Ann', online = true, hp = 1, max = 1 }")
        lua.execute("fire('PARTY_MEMBERS_CHANGED'); runTimers()")
        self.assertEqual(lua.eval("btn(1, 2).health.c.name"), "DRUID")

    def test_the_crown_on_the_leader(self):
        lua = load()
        lua.execute("members.player.leader = true")
        lua.execute("joinParty('Ann')")
        self.assertTrue(lua.eval("btn(1, 1).crown:IsShown()"))
        self.assertFalse(lua.eval("btn(1, 2).crown:IsShown()"))
        lua.execute("members.player.leader = nil; members.party1.leader = true; fire('PARTY_LEADER_CHANGED'); runTimers()")
        self.assertFalse(lua.eval("btn(1, 1).crown:IsShown()"))
        self.assertTrue(lua.eval("btn(1, 2).crown:IsShown()"))


class Events(unittest.TestCase):
    def test_unit_events_only_for_the_shown_members(self):
        lua = in_party()
        for e in ("UNIT_HEALTH", "UNIT_AURA_DELTA", "UNIT_IN_RANGE_UPDATE", "UNIT_POWER_UPDATE"):
            self.assertEqual(lua.eval(f"unitsOf({e!r})"), "player,party1,party2", e)
        lua.execute("joinParty()")
        self.assertIsNone(lua.eval("unitsOf('UNIT_HEALTH')"), "solo: no unit events")

    def test_at_rest_solo_only_the_roster_events(self):
        lua = load()
        self.assertEqual(lua.eval("listening(grid())"), "PARTY_MEMBERS_CHANGED,PLAYER_ENTERING_WORLD,RAID_ROSTER_UPDATE")
        self.assertEqual(lua.eval("liveTimers and liveTimers() or #timers"), 0)
        self.assertIsNone(lua.eval("(function() for _, w in ipairs(widgets) do "
                                   "if w.scripts.OnUpdate and string.find(w.name or '', '^Fostercare') then return w.name end end end)()"))

    def test_an_event_of_one_member_draws_only_that_member(self):
        lua = in_party()
        lua.execute("calls.SetText = 0; members.party1.hp = 2000; fire('UNIT_HEALTH', 'party1')")
        self.assertEqual(lua.eval("btn(1, 2).hp.text"), "-1.0K")
        self.assertEqual(lua.eval("count('SetText')"), 1)


class Health(unittest.TestCase):
    def test_missing_health_and_full(self):
        lua = in_party()
        self.assertEqual(lua.eval("btn(1, 2).hp.text"), "")
        lua.execute("members.party1.hp = 2950; fire('UNIT_HEALTH', 'party1')")
        self.assertEqual(lua.eval("btn(1, 2).hp.text"), "-50")
        self.assertEqual(lua.eval("btn(1, 2).health:GetValue()"), 2950)

    def test_the_text_is_built_only_when_the_number_changes(self):
        lua = in_party()
        lua.execute("members.party1.hp = 1000; fire('UNIT_HEALTH', 'party1'); calls.AbbreviateNumbers = 0")
        lua.execute("fire('UNIT_HEALTH', 'party1'); fire('UNIT_MAXHEALTH', 'party1')")
        self.assertEqual(lua.eval("count('AbbreviateNumbers')"), 0)

    def test_dead_ghost_and_offline(self):
        lua = in_party()
        lua.execute("members.party1.dead = true; fire('UNIT_HEALTH', 'party1')")
        self.assertIn("Dead", lua.eval("btn(1, 2).hp.text"))
        lua.execute("members.party1.dead = nil; members.party1.ghost = true; fire('UNIT_HEALTH', 'party1')")
        self.assertIn("Ghost", lua.eval("btn(1, 2).hp.text"))
        lua.execute("members.party2.online = false; fire('UNIT_CONNECTION', 'party2')")
        self.assertIn("Off", lua.eval("btn(1, 3).hp.text"))
        self.assertEqual(lua.eval("btn(1, 3):GetAlpha()"), 0.4)

    def test_power_and_its_colour(self):
        lua = in_party()
        lua.execute("members.party1.power, members.party1.mana, members.party1.maxMana = 3, 40, 100")
        lua.execute("fire('UNIT_DISPLAYPOWER', 'party1')")
        self.assertEqual(lua.eval("btn(1, 2).power:GetValue()"), 40)
        self.assertEqual(lua.eval("btn(1, 2).power.c.g"), 1, "energy's colour")


class Range(unittest.TestCase):
    def test_range_from_the_event_and_at_first_show(self):
        lua = load()
        lua.execute("inRange.party1 = false; joinParty('Ann')")
        self.assertEqual(lua.eval("btn(1, 2):GetAlpha()"), 0.45)
        self.assertEqual(lua.eval("btn(1, 1):GetAlpha()"), 1, "you are always in range")
        lua.execute("fire('UNIT_IN_RANGE_UPDATE', 'party1', true)")
        self.assertEqual(lua.eval("btn(1, 2):GetAlpha()"), 1)
        lua.execute("calls.UnitInRange = 0; fire('UNIT_IN_RANGE_UPDATE', 'party1', false)")
        self.assertEqual(lua.eval("btn(1, 2):GetAlpha()"), 0.45)
        self.assertEqual(lua.eval("count('UnitInRange')"), 0, "the event says it; nothing asks again")


class Aggro(unittest.TestCase):
    def test_the_corner_on_the_member_your_enemy_target_attacks(self):
        lua = in_party()
        lua.execute("member('target', 'Ogre', 'WARRIOR', { enemy = true }); members.targettarget = members.party2")
        lua.execute("fire('PLAYER_TARGET_CHANGED')")
        self.assertTrue(lua.eval("btn(1, 3).aggro:IsShown()"))
        self.assertFalse(lua.eval("btn(1, 2).aggro:IsShown()"))
        lua.execute("members.targettarget = members.party1; fire('UNIT_TARGET', 'target')")
        self.assertTrue(lua.eval("btn(1, 2).aggro:IsShown()"))
        self.assertFalse(lua.eval("btn(1, 3).aggro:IsShown()"))

    def test_a_friendly_target_gives_no_corner(self):
        lua = in_party()
        lua.execute("member('target', 'Ann', 'PRIEST'); members.targettarget = members.party2; fire('PLAYER_TARGET_CHANGED')")
        self.assertFalse(lua.eval("btn(1, 3).aggro:IsShown()"))

    def test_off_stops_listening_and_hides_the_corner(self):
        lua = in_party()
        lua.execute("member('target', 'Ogre', 'WARRIOR', { enemy = true }); members.targettarget = members.party2")
        lua.execute("fire('PLAYER_TARGET_CHANGED')")
        lua.execute("settingsWindow.use('FostercareRaid_aggro', false)")
        self.assertFalse(lua.eval("btn(1, 3).aggro:IsShown()"))
        self.assertIsNone(lua.eval("grid().events.PLAYER_TARGET_CHANGED"))
        self.assertIsNone(lua.eval("grid().events.UNIT_TARGET"))


class Marks(unittest.TestCase):
    def test_raid_marks_follow_their_event(self):
        lua = in_party()
        lua.execute("marks.party1 = 8; fire('RAID_TARGET_UPDATE')")
        self.assertTrue(lua.eval("btn(1, 2).mark:IsShown()"))
        self.assertEqual(lua.eval("btn(1, 2).mark.markIndex"), 8)
        lua.execute("marks.party1 = nil; fire('RAID_TARGET_UPDATE')")
        self.assertFalse(lua.eval("btn(1, 2).mark:IsShown()"))


class Moving(unittest.TestCase):
    def test_ctrl_shift_shows_the_handle_and_a_drag_is_the_clients_to_save(self):
        lua = in_party()
        handle = "(function() for _, w in ipairs(widgets) do if w.parent == grid() and w.strata == nil and w.scripts.OnMouseDown then return w end end end)()"
        lua.execute(f"H = {handle}")
        lua.execute("shift, ctrl = 1, 1; fire('MODIFIER_STATE_CHANGED')")
        self.assertTrue(lua.eval("H:IsShown()"))
        lua.execute("run(H, 'OnMouseDown')")
        self.assertTrue(lua.eval("grid().moving"))
        lua.execute("shift = nil; fire('MODIFIER_STATE_CHANGED')")
        self.assertFalse(lua.eval("H:IsShown()"))
        self.assertIsNone(lua.eval("grid().moving"))
        self.assertTrue(lua.eval("grid():IsUserPlaced()"))

    def test_solo_nothing_listens_for_the_keys(self):
        lua = load()
        self.assertIsNone(lua.eval("(function() for _, w in ipairs(widgets) do if w.events.MODIFIER_STATE_CHANGED then return true end end end)()"))


class FirstLogin(unittest.TestCase):
    def test_the_grid_placed_by_hand_waits_for_the_client(self):
        # The client puts the grid back after PLAYER_ENTERING_WORLD at a first
        # login (FostercareBars, 2026-11-17).
        lua = in_party(setup="layoutCache.FostercareRaidFrame = { 300, -200 }")
        self.assertEqual(lua.eval("shown(1, 2)"), "Ann")
        lua.execute("settingsWindow.use('FostercareRaid_scale', 1.3)")
        lua.execute("step(0)")
        self.assertEqual(lua.eval("grid():GetLeft()"), 300)


if __name__ == "__main__":
    unittest.main()
