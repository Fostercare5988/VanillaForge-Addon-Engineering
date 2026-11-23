"""The flag watch, stealth warnings, Spy, the arena, positions at a first login
and what runs at rest (spec 4.4 tests 12-18). AutoBG 1.0, written new 2026-11-22."""
import unittest
from abg_env import load

FOE = "0x0000000000000B01"
SPOTS = "AutoBGDB = { queueOnLogin = false, spots = { [529] = { Stables = { x = 1167, y = 1201, n = 10 }, Farm = { x = 805, y = 874, n = 10 } } } }"


def arathi(lua, at=(1167, 1201)):
    lua.execute("scores = { { 'Foe', 1, 'Human', 'Rogue' } }; enter('Arathi Basin'); fire('UPDATE_BATTLEFIELD_SCORE'); step()")
    lua.execute(f"enemy('{FOE}', {{ name = 'Foe', class = 'ROGUE', pos = {{ {at[0]}, {at[1]} }} }}); plate('{FOE}')")


class FlagWatch(unittest.TestCase):
    def test_a_visible_opening_names_the_nearest_base(self):
        lua = load(SPOTS)
        arathi(lua, (1170, 1199))
        lua.execute(f"units['{FOE}'].cast = {{ name = 'Opening', from = now, to = now + 5 }}; fireGUID('UNIT_SPELLCAST_START', '{FOE}')")
        self.assertTrue(lua.eval("AutoBG_FlagAlert:IsShown()"))
        self.assertEqual(lua.eval("AutoBG_FlagAlert.line.text"), "Foe is opening the Stables")
        self.assertTrue(lua.eval("said('sound:igPVPUpdate')"))
        self.assertEqual(lua.eval("row(1, 15).status.text"), "|cffff4040OPENING|r")
        lua.execute("ctrl = true; AutoBG_FlagAlert:Click('LeftButton')")
        self.assertTrue(lua.eval("said('^say:BATTLEGROUND:Foe is opening the Stables$')"))
        lua.execute(f"fireGUID('UNIT_SPELLCAST_STOP', '{FOE}')")
        self.assertEqual(lua.eval("row(1, 15).status.text"), "100%")

    def test_with_no_spots_it_is_a_flag(self):
        lua = load("AutoBGDB = { queueOnLogin = false }")
        arathi(lua)
        lua.execute(f"units['{FOE}'].cast = {{ name = 'Opening', from = now, to = now + 5 }}; fireGUID('UNIT_SPELLCAST_START', '{FOE}')")
        self.assertEqual(lua.eval("AutoBG_FlagAlert.line.text"), "Foe is opening a flag")

    def test_out_of_stealth_at_a_flag_his_side_does_not_hold_and_standing_warns(self):
        lua = load(SPOTS)
        arathi(lua)
        lua.execute(f"units['{FOE}'].visible = false; fireGUID('UNIT_VISIBILITY_CHANGED', '{FOE}', false)")
        lua.execute(f"units['{FOE}'].visible = true; fireGUID('UNIT_VISIBILITY_CHANGED', '{FOE}', true)")
        self.assertFalse(lua.eval("AutoBG_FlagAlert:IsShown()"))
        lua.execute("step(0.5)")
        self.assertEqual(lua.eval("AutoBG_FlagAlert.line.text"), "Foe is opening the Stables")
        lua.execute(f"units['{FOE}'].pos = {{ 1180, 1201 }}; step(0.5)")
        self.assertEqual(lua.eval("row(1, 15).status.text"), "100%")
        self.assertEqual(lua.eval("liveTimers() < 6"), True)

    def test_at_his_own_sides_flag_nothing_and_moving_away_clears_it(self):
        lua = load(SPOTS)
        arathi(lua)
        lua.execute("line('Ally claims the Stables! If left unchallenged, the Alliance will control it in 1 minute!')")
        lua.execute(f"fireGUID('UNIT_VISIBILITY_CHANGED', '{FOE}', true); step(0.5)")
        self.assertFalse(lua.eval("AutoBG_FlagAlert:IsShown()"))

    def test_spots_learn_from_assault_and_defend_lines_not_taken(self):
        lua = load("AutoBGDB = { queueOnLogin = false }")
        arathi(lua, (900, 900))
        lua.execute("line('Foe has assaulted the Blacksmith!', 'CHAT_MSG_BG_SYSTEM_ALLIANCE')")
        self.assertEqual(lua.eval("AutoBGDB.spots[529].Blacksmith.n"), 1)
        lua.execute(f"units['{FOE}'].pos = {{ 910, 900 }}; line('Foe has defended the Blacksmith!')")
        self.assertEqual(lua.eval("AutoBGDB.spots[529].Blacksmith.x"), 905)
        lua.execute("line('The Alliance has taken the Blacksmith!')")
        self.assertEqual(lua.eval("AutoBGDB.spots[529].Blacksmith.n"), 2)
        lua.execute("line('Foe has assaulted the Farm!')")  # within 15 yards of the Blacksmith: refused
        self.assertIsNone(lua.eval("AutoBGDB.spots[529].Farm"))

    def test_outside_arathi_nothing(self):
        lua = load(SPOTS)
        lua.execute("enter('Warsong Gulch')")
        lua.execute(f"enemy('{FOE}', {{ name = 'Foe', pos = {{ 1167, 1201 }} }}); plate('{FOE}')")
        lua.execute(f"units['{FOE}'].cast = {{ name = 'Opening', from = now, to = now + 5 }}; fireGUID('UNIT_SPELLCAST_START', '{FOE}')")
        self.assertFalse(lua.eval("AutoBG_FlagAlert:IsShown()"))


class Spy(unittest.TestCase):
    def test_sightings_newest_on_top_never_the_group_dim_then_gone(self):
        lua = load("AutoBGDB = { queueOnLogin = false }")
        lua.execute("enemy('0x0000000000000C01', { name = 'Leuka', class = 'PALADIN' }); plate('0x0000000000000C01')")
        lua.execute("enemy('0x0000000000000C02', { name = 'Zoe', class = 'ROGUE', level = 58 }); setTarget('0x0000000000000C02')")
        lua.execute("unit('0x0000000000000C03', { name = 'Mate', player = true, enemy = true, inGroup = true }); setTarget('0x0000000000000C03')")
        self.assertEqual(lua.eval("AutoBG_SpyFrame.title.text"), "Spy  2")
        first = lua.eval("(function() for _, w in ipairs(widgets) do if w.parent == AutoBG_SpyFrame and w.entry then return w.name.text end end end)()")
        self.assertEqual(first, "58  Zoe")
        self.assertTrue(lua.eval("said('sound:MapPing')"))
        lua.execute("units['0x0000000000000C02'].visible = false; fireGUID('UNIT_VISIBILITY_CHANGED', '0x0000000000000C02', false); step(5.1)")
        self.assertEqual(lua.eval("AutoBG_SpyFrame.title.text"), "Spy  2")
        lua.execute("step(25)")
        self.assertEqual(lua.eval("AutoBG_SpyFrame.title.text"), "Spy  1")

    def test_far_sightings_from_nampower_and_a_stealth_warning(self):
        lua = load("AutoBGDB = { queueOnLogin = false }")
        lua.execute("enemy('0x0000000000000C05', { name = 'Far', class = 'MAGE' }); fire('SPELL_GO_OTHER', 0, 133, '0x0000000000000C05', '0x0000000000000000')")
        self.assertEqual(lua.eval("AutoBG_SpyFrame.title.text"), "Spy  1")
        lua.execute("fire('SPELL_GO_OTHER', 0, 133, '0xF130000000000C06', '0x0000000000000000')")  # a creature
        lua.execute("enemy('0x0000000000000C07', { name = 'Sneak', class = 'ROGUE' }); fire('BUFF_ADDED_OTHER', '0x0000000000000C07', 1, 1787, 1, 60, 3, 0)")
        self.assertTrue(lua.eval("AutoBG_SpyAlertWindow:IsShown()"))
        self.assertIn("Sneak", lua.eval("AutoBG_SpyAlertWindow.line.text"))
        self.assertTrue(lua.eval("said('sound:RaidWarning')"))

    def test_one_warning_per_8_seconds_and_the_same_enemy_quiet_for_60(self):
        lua = load()
        lua.execute("__addon_ns.StealthWarn('A', nil, 'STEALTH', 'ROGUE', true); __addon_ns.StealthWarn('B', nil, 'STEALTH', 'ROGUE', true)")
        self.assertEqual(lua.eval("count('sound:RaidWarning')"), 1)
        lua.execute("step(9); __addon_ns.StealthWarn('A', nil, 'STEALTH', 'ROGUE', true)")
        self.assertEqual(lua.eval("count('sound:RaidWarning')"), 1)
        lua.execute("__addon_ns.StealthWarn('B', nil, 'STEALTH', 'ROGUE', true)")
        self.assertEqual(lua.eval("count('sound:RaidWarning')"), 2)

    def test_warning_sounds_off_keeps_the_card_quiet_outside_battlegrounds(self):
        lua = load("AutoBGDB = { spySounds = false }")
        lua.execute("__addon_ns.StealthWarn('A', nil, 'PROWL', 'DRUID', false)")
        self.assertTrue(lua.eval("AutoBG_SpyAlertWindow:IsShown()"))
        self.assertFalse(lua.eval("said('sound')"))

    def test_rests_in_battlegrounds_and_raids_and_with_its_switch_off(self):
        lua = load()
        lua.execute("enemy('0x0000000000000C01', { name = 'Leuka' }); plate('0x0000000000000C01')")
        lua.execute("enter('Warsong Gulch')")
        self.assertFalse(lua.eval("AutoBG_SpyFrame:IsShown()"))
        self.assertFalse(lua.eval("receives(AutoBG_SpyFrame, 'x') or __addon_ns.Spy.active"))
        lua.execute("zone = { name = 'Molten Core', kind = 'raid', map = 409, inside = true }; fire('PLAYER_ENTERING_WORLD')")
        self.assertFalse(lua.eval("__addon_ns.Spy.active"))
        lua.execute("enter(nil); settingsWindow.use('AutoBG_spy', false)")
        self.assertFalse(lua.eval("__addon_ns.Spy.active"))

    def test_the_list_holds_still_under_the_mouse_and_x_clears(self):
        lua = load()
        lua.execute("enemy('0x0000000000000C01', { name = 'Leuka' }); plate('0x0000000000000C01')")
        lua.execute("local r = AutoBG_SpyFrame; for _, w in ipairs(widgets) do if w.parent == r and w.entry then hoverRow = w end end")
        lua.execute("run(hoverRow, 'OnEnter'); enemy('0x0000000000000C02', { name = 'Zoe' }); plate('0x0000000000000C02')")
        self.assertEqual(lua.eval("AutoBG_SpyFrame.title.text"), "Spy  1")
        lua.execute("run(hoverRow, 'OnLeave')")
        self.assertEqual(lua.eval("AutoBG_SpyFrame.title.text"), "Spy  2")
        lua.execute("for _, w in ipairs(widgets) do if w.parent == AutoBG_SpyFrame and w.text and w.text.text == 'x' then run(w, 'OnClick') end end")
        self.assertFalse(lua.eval("AutoBG_SpyFrame:IsShown()"))

    def test_a_waiting_plate_is_read_on_its_name_update(self):
        lua = load()
        lua.execute("unit('0x0000000000000C09', { name = 'Unknown', player = true, faction = 'Alliance' }); token = plate('0x0000000000000C09')")
        self.assertFalse(lua.eval("AutoBG_SpyFrame:IsShown()"))
        lua.execute("units['0x0000000000000C09'].name = 'Late'; units['0x0000000000000C09'].enemy = true; fire('UNIT_NAME_UPDATE', token)")
        self.assertEqual(lua.eval("AutoBG_SpyFrame.title.text"), "Spy  1")

    def test_far_casts_are_switched_on_with_the_list(self):
        """2026-11-23, fails on the first build: NamPower sends SPELL_GO_OTHER only
        while NP_EnableSpellGoEvents is 1 (EVENTS.md, default 0) and nothing set it,
        so a fresh install saw no far casters."""
        self.assertEqual(load().eval("cvars.NP_EnableSpellGoEvents"), "1")
        self.assertIsNone(load("AutoBGDB = { spy = false }").eval("cvars.NP_EnableSpellGoEvents"))

    def test_health_moves_its_bar_and_another_aura_going_keeps_the_stealth(self):
        """2026-11-23, the stealth part fails on the first build: any aura removed
        cleared the stealth line."""
        lua = load()
        guid = "0x0000000000000C01"
        lua.execute(f"enemy('{guid}', {{ name = 'Zoe', class = 'ROGUE' }}); plate('{guid}')")
        lua.execute("for _, w in ipairs(widgets) do if w.parent == AutoBG_SpyFrame and w.entry then spyRow = w end end")
        lua.execute(f"units['{guid}'].hp = 40; fireGUID('UNIT_HEALTH', '{guid}')")
        self.assertAlmostEqual(lua.eval("spyRow.health.value"), 0.4)
        lua.execute(f"stealthID = aura('{guid}', 1787); auraEvent('{guid}', {{ stealthID }})")
        lua.execute(f"other = aura('{guid}', 1, 'Thorns'); auraEvent('{guid}', {{ other }}); auraEvent('{guid}', nil, {{ other }})")
        self.assertEqual(lua.eval("spyRow.entry.stealth"), "STEALTH")
        lua.execute(f"auraEvent('{guid}', nil, {{ stealthID }})")
        self.assertIsNone(lua.eval("spyRow.entry.stealth"))


class Arena(unittest.TestCase):
    def setUp(self):
        self.lua = load("AutoBGDB = { queueOnLogin = false, callouts = true }", setup="partySize = 1")
        self.lua.execute("enter('Blood Ring', true)")

    def test_the_roster_from_sightings_power_drinking_and_callouts(self):
        lua = self.lua
        lua.execute(f"enemy('{FOE}', {{ name = 'Foe', class = 'MAGE', power = 40 }}); plate('{FOE}')")
        self.assertTrue(lua.eval("AutoBG_TargetsMainFrame5:IsShown()"))
        r = "row(1, 5)"
        lua.execute(f"units['{FOE}'].power = 70; fireGUID('UNIT_POWER_UPDATE', '{FOE}')")
        self.assertAlmostEqual(lua.eval(f"{r}.power.value"), 0.7)
        lua.execute(f"auraEvent('{FOE}', {{ aura('{FOE}', 1137, 'Drink') }}); auraEvent('{FOE}', {{ aura('{FOE}', 1137, 'Drink') }})")
        self.assertEqual(lua.eval("count('error:Foe is drinking')"), 1)
        lua.execute(f"units['{FOE}'].hp = 20; fireGUID('UNIT_HEALTH', '{FOE}'); fireGUID('UNIT_HEALTH', '{FOE}')")
        self.assertEqual(lua.eval("count('say:PARTY:Foe is at 25%%')"), 1)
        lua.execute(f"units['{FOE}'].dead = true; fireGUID('UNIT_HEALTH', '{FOE}')")
        self.assertTrue(lua.eval("said('say:PARTY:Foe is dead')"))
        self.assertEqual(lua.eval(f"{r}.status.text"), "DEAD")

    def test_pets_with_their_owner_dim_out_of_view_and_no_ticker(self):
        lua = self.lua
        lua.execute(f"enemy('{FOE}', {{ name = 'Hunt', class = 'HUNTER' }}); unit('0xF140000000000D01', {{ name = 'Wolf', enemy = true, owner = '{FOE}' }})")
        lua.execute("plate('0xF140000000000D01')")
        self.assertTrue(lua.eval("AutoBG_ArenaPets:IsShown()"))
        self.assertEqual(lua.eval("#__addon_ns.Enemies.roster"), 1)  # the owner seen through his pet
        lua.execute("units['0xF140000000000D01'].visible = false; fireGUID('UNIT_VISIBILITY_CHANGED', '0xF140000000000D01', false)")
        self.assertTrue(lua.eval("(function() for _, w in ipairs(widgets) do if w.parent == AutoBG_ArenaPets and w:IsShown() then return w:GetAlpha() < 1 end end end)()"))

    def test_the_sweep_only_with_no_target_clears_it_and_rests_when_full(self):
        lua = self.lua
        lua.execute(f"enemy('{FOE}', {{ name = 'Foe' }}); enemy('0x0000000000000B02', {{ name = 'Two' }}); step(1)")
        self.assertEqual(lua.eval("#__addon_ns.Enemies.roster"), 2)
        self.assertTrue(lua.eval("said('ClearTarget')"))
        live = lua.eval("liveTimers()")
        lua.execute("step(1)")
        self.assertLess(lua.eval("liveTimers()"), live + 1)
        lua.execute("log = {}; step(3)")
        self.assertFalse(lua.eval("said('ClearTarget')"))


class AtRest(unittest.TestCase):
    def test_nothing_runs_in_the_open_world_after_login_a_zone_change_and_a_loading_screen(self):
        lua = load("AutoBGDB = { queueOnLogin = false }")
        lua.execute("fire('ZONE_CHANGED_NEW_AREA'); enter('Warsong Gulch'); enter(nil); step(1)")
        self.assertEqual(lua.eval("liveTimers()"), 0)
        self.assertEqual(lua.eval("onUpdates()"), 0)
        for e in ("CHAT_MSG_BG_SYSTEM_NEUTRAL", "UPDATE_WORLD_STATES", "UPDATE_BATTLEFIELD_SCORE", "UNIT_TARGET",
                  "NAME_PLATE_UNIT_ADDED", "PLAYER_FLAGS_CHANGED"):
            busy = lua.eval(f"(function() for _, w in ipairs(widgets) do if w.events['{e}'] and w ~= AutoBG_SpyFrame then return w end end end)()")
            if e == "NAME_PLATE_UNIT_ADDED":
                continue  # Spy's sightings, in the open world
            self.assertIsNone(busy, e)

    def test_positions_where_the_client_has_them_at_a_first_login(self):
        cache = {"AutoBG_QueueFrame": (-18, 2), "AutoBG_TargetsMainFrame10": (1300, -315), "AutoBG_SpyFrame": (1380, -243)}
        lua = load(cache=cache)
        for name, (x, y) in cache.items():
            self.assertEqual(lua.eval(f"{name}:GetLeft()"), x, name)
            self.assertTrue(lua.eval(f"{name}:IsUserPlaced()"), name)

    def test_odd_data_no_target_empty_raid_and_a_score_row_with_no_class(self):
        lua = load()
        lua.execute("scores = { { 'Nobody', 1, nil, nil } }; enter('Alterac Valley'); fire('UPDATE_BATTLEFIELD_SCORE'); step()")
        self.assertEqual(lua.eval("row(1, 40).name.text"), "Nobody")
        lua.execute("fire('PLAYER_TARGET_CHANGED'); fire('UNIT_TARGET', 'raid1'); step(); fire('RAID_TARGET_UPDATE')")
        lua.execute("row(1, 40):Click('LeftButton')")


if __name__ == "__main__":
    unittest.main()
