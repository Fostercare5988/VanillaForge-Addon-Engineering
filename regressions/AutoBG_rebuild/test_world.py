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

    def test_the_gold_mine_is_not_the_lumber_mill(self):
        """2026-11-23, seen in play: Bibs opening the Gold Mine, 441 yards away, was
        called the Lumber Mill. UnitPosition gives posY first; read as x, y the Gold
        Mine's spot lands on the Lumber Mill's. Claude's learned spots. Fails on 35dc4bf."""
        spots = ("AutoBGDB = { queueOnLogin = false, spots = { [529] = { ['Gold Mine'] = { x = 1146.3, y = 848.9, n = 10 },"
                 " ['Lumber Mill'] = { x = 855.5, y = 1149.4, n = 10 } } } }")
        lua = load(spots)
        arathi(lua, (1146, 850))
        lua.execute(f"units['{FOE}'].cast = {{ name = 'Opening', from = now, to = now + 5 }}; fireGUID('UNIT_SPELLCAST_START', '{FOE}')")
        self.assertEqual(lua.eval("AutoBG_FlagAlert.line.text"), "Foe is opening the Gold Mine")

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
        # A dead enemy cannot be attacked: not listed, but looked at again once alive.
        lua.execute("enemy('0x0000000000000C08', { name = 'Corpse', class = 'MAGE', dead = true }).enemy = false;"
                    " fire('SPELL_GO_OTHER', 0, 133, '0x0000000000000C08', '0x0000000000000000')")
        self.assertEqual(lua.eval("AutoBG_SpyFrame.title.text"), "Spy  1")
        lua.execute("units['0x0000000000000C08'].dead, units['0x0000000000000C08'].enemy = nil, true;"
                    " fire('SPELL_GO_OTHER', 0, 133, '0x0000000000000C08', '0x0000000000000000')")
        self.assertEqual(lua.eval("AutoBG_SpyFrame.title.text"), "Spy  2")
        lua.execute("enemy('0x0000000000000C07', { name = 'Sneak', class = 'ROGUE', yards = 25 }); fire('BUFF_ADDED_OTHER', '0x0000000000000C07', 1, 1787, 1, 60, 3, 0)")
        self.assertTrue(lua.eval("AutoBG_SpyAlertWindow:IsShown()"))
        self.assertIn("Sneak", lua.eval("AutoBG_SpyAlertWindow.line.text"))
        self.assertTrue(lua.eval("said('sound:RaidWarning')"))

    def test_each_new_stealth_warns_with_3_seconds_between_cards(self):
        """2026-11-23: as the Nampower Spy, each new stealth warns; the same rogue
        stealthing again near you is danger again. Was one per 8 s, the same enemy
        quiet for 60."""
        lua = load()
        lua.execute("__addon_ns.StealthWarn('A', nil, 'STEALTH', 'ROGUE', true); __addon_ns.StealthWarn('B', nil, 'STEALTH', 'ROGUE', true)")
        self.assertEqual(lua.eval("count('sound:RaidWarning')"), 1)
        lua.execute("step(3); __addon_ns.StealthWarn('A', nil, 'VANISH', 'ROGUE', true)")
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


    # 2026-11-24, the player: arena enemy tracking as good as it can be, the
    # stealth warnings there too, "use totems or buffs to track where people are".
    def test_every_stealth_warns_in_an_arena_at_any_distance(self):
        lua = self.lua
        lua.execute(f"enemy('{FOE}', {{ name = 'Elf', class = 'HUNTER', yards = 120 }}); plate('{FOE}');"
                    f" fireGUID('UNIT_SPELLCAST_SUCCEEDED', '{FOE}', 'c', 20580)")
        self.assertTrue(lua.eval("AutoBG_SpyAlertWindow:IsShown()"))
        self.assertTrue(lua.eval("said('sound:RaidWarning')"))

    def test_combat_that_names_an_enemy_lists_him_never_an_ally(self):
        lua = self.lua
        self.assertEqual(lua.eval("cvars.NP_EnableSpellGoEvents"), "1")
        lua.execute(f"enemy('{FOE}', {{ name = 'Foe', class = 'MAGE', visible = false }});"
                    " unit('0x0000000000000050', { name = 'Mate', player = true, inGroup = true })")
        lua.execute(f"fire('SPELL_GO_OTHER', 0, 133, '0x0000000000000050', '{FOE}')")
        self.assertEqual(lua.eval("#__addon_ns.Enemies.roster"), 1)
        lua.execute("enemy('0x0000000000000B03', { name = 'Dot', class = 'WARLOCK', visible = false });"
                    " fire('DEBUFF_ADDED_OTHER', '0x0000000000000B03', 1, 172, 1, 60, 33, 0)")
        lua.execute("enemy('0x0000000000000B04', { name = 'Hit', class = 'WARRIOR', visible = false });"
                    " fire('SPELL_DAMAGE_EVENT_OTHER', '0x0000000000000050', '0x0000000000000B04', 12294, 900, '0,0,0', 0, 1, '2,0,0,0')")
        self.assertEqual(lua.eval("#__addon_ns.Enemies.roster"), 3)
        lua.execute("enter(nil); enemy('0x0000000000000B05', { name = 'Far' }); fire('SPELL_DAMAGE_EVENT_OTHER', '0x0000000000000B05', me.guid)")
        self.assertEqual(lua.eval("#__addon_ns.Enemies.roster"), 0)

    def test_a_totem_names_its_shaman_and_gets_no_pet_row(self):
        lua = self.lua
        lua.execute(f"enemy('{FOE}', {{ name = 'Sham', class = 'SHAMAN', visible = false }});"
                    f" unit('0xF130000000000E01', {{ name = 'Grounding Totem', enemy = true, owner = '{FOE}', creature = 'Totem' }});"
                    " plate('0xF130000000000E01')")
        self.assertEqual(lua.eval(f"__addon_ns.Enemies.byGUID['{FOE}'].name"), "Sham")
        self.assertFalse(lua.eval("AutoBG_ArenaPets:IsShown()"))

    def test_the_servers_arena_scoreboard_lists_the_other_team_never_yours(self):
        lua = self.lua
        lua.execute("unit('0x0000000000000050', { name = 'Mate', player = true, inGroup = true }); step(1)")
        self.assertTrue(lua.eval("said('ArenaScore')"))
        lua.execute("fire('CHAT_MSG_ADDON', 'TW_ARENA', 'S2C_SCOREBOARD;0;2;Claude|1|0:Mate|1|0', 'GUILD', '')")
        self.assertEqual(lua.eval("#__addon_ns.Enemies.roster"), 0)
        lua.execute("fire('CHAT_MSG_ADDON', 'TW_ARENA', 'S2C_SCOREBOARD;0;4;Claude|1|0:Foe|2|0:Mate|1|0:Two|2|0', 'GUILD', ''); step()")
        self.assertEqual(lua.eval("#__addon_ns.Enemies.roster"), 2)
        self.assertEqual(lua.eval("row(1, 5).name.text"), "Foe")
        # Asked again only while the list is short.
        lua.execute("log = {}; step(10)")
        self.assertFalse(lua.eval("said('ArenaScore')"))

    def test_a_hidden_stealther_shows_how_long_ago_and_how_far_his_last_spot_is(self):
        lua = self.lua
        r = "row(1, 5)"
        lua.execute(f"me.pos = {{ 0, 0 }}; enemy('{FOE}', {{ name = 'Foe', class = 'ROGUE', yards = 30, pos = {{ 30, 0 }} }}); plate('{FOE}')")
        lua.execute(f"auraEvent('{FOE}', {{ aura('{FOE}', 1787) }})")
        self.assertTrue(lua.eval("AutoBG_SpyAlertWindow:IsShown()"))
        lua.execute(f"units['{FOE}'].visible = false; fireGUID('UNIT_VISIBILITY_CHANGED', '{FOE}', false); step(5)")
        self.assertEqual(lua.eval(f"clock({r}.status)"), "|cffc7b5ffSTEALTH|r 5s")
        self.assertEqual(lua.eval(f"{r}.yards.text"), "|cffb59cff~30 yd|r")
        lua.execute("me.pos = { 10, 0 }; step(0.2)")
        self.assertEqual(lua.eval(f"{r}.yards.text"), "|cffb59cff~20 yd|r")
        lua.execute("step(60)")
        self.assertEqual(lua.eval(f"{r}.yards.text"), "")
        self.assertEqual(lua.eval(f"clock({r}.status)"), "|cffc7b5ffSTEALTH|r 1m")
        lua.execute(f"units['{FOE}'].visible = true; units['{FOE}'].auras = {{}}; fireGUID('UNIT_VISIBILITY_CHANGED', '{FOE}', true)")
        self.assertEqual(lua.eval(f"clock({r}.status)"), "100%")

    def test_a_hidden_enemys_spell_on_your_group_says_who_what_on_whom_and_where(self):
        lua = self.lua
        r = "row(1, 5)"
        lua.execute("me.pos = { 0, 0 }; unit('0x0000000000000050', { name = 'Mate', player = true, inGroup = true, pos = { 50, 0 } })")
        lua.execute(f"enemy('{FOE}', {{ name = 'Foe', class = 'ROGUE', visible = false }}); fire('BUFF_ADDED_OTHER', '{FOE}', 1, 1787, 1, 60, 3, 0)")
        lua.execute(f"fire('SPELL_GO_OTHER', 0, 11297, '{FOE}', '0x0000000000000050'); step(0.2)")
        self.assertTrue(lua.eval("AutoBG_SpyAlertWindow:IsShown()"))
        self.assertIn("Spell11297", lua.eval("AutoBG_SpyAlertWindow.title.text"))
        self.assertIn("on Mate", lua.eval("AutoBG_SpyAlertWindow.line.text"))
        self.assertEqual(lua.eval(f"{r}.yards.text"), "|cffb59cff~50 yd|r")
        # A spell of his on the other side tells nothing.
        lua.execute("AutoBG_SpyAlertWindow:Hide(); step(5)")
        lua.execute(f"enemy('0x0000000000000B02', {{ name = 'Two' }}); fire('SPELL_GO_OTHER', 0, 2061, '{FOE}', '0x0000000000000B02')")
        self.assertFalse(lua.eval("AutoBG_SpyAlertWindow:IsShown()"))


    # 2026-11-24, the player: better enemy tracking, and the stealth tracker in
    # every arena, for the quick Saps and CCs.
    def test_the_frame_holds_a_slot_for_every_enemy_found_or_not_and_no_row_moves(self):
        lua = self.lua  # partySize 1: a team of two
        self.assertTrue(lua.eval("AutoBG_TargetsMainFrame5:IsShown()"))
        self.assertEqual(lua.eval("row(1, 5).name.text"), "|cff8c8c8c?|r")
        self.assertEqual(lua.eval("AutoBG_TargetsMainFrame5.title.text"), "Enemies 2/2")
        lua.execute("enemy('0x0000000000000B01', { name = 'Zed', class = 'WARRIOR' }); plate('0x0000000000000B01')")
        lua.execute("enemy('0x0000000000000B02', { name = 'Abe', class = 'MAGE' }); plate('0x0000000000000B02')")
        # In the order found, not by class: a row never moves under a click.
        self.assertEqual(lua.eval("row(1, 5).name.text"), "Zed")
        self.assertEqual(lua.eval("row(2, 5).name.text"), "Abe")
        self.assertEqual(lua.eval("AutoBG_TargetsMainFrame5.title.text"), "Enemies 2/2")
        lua.execute("units['0x0000000000000B02'].dead = true; fireGUID('UNIT_HEALTH', '0x0000000000000B02')")
        self.assertEqual(lua.eval("AutoBG_TargetsMainFrame5.title.text"), "Enemies 1/2")

    def test_a_slot_is_blank_again_in_a_new_match_and_a_bigger_team_adds_slots(self):
        lua = self.lua
        lua.execute("enemy('0x0000000000000B01', { name = 'Zed', class = 'ROGUE', race = 'NightElf' });"
                    " plate('0x0000000000000B01'); fireGUID('UNIT_SPELLCAST_SUCCEEDED', '0x0000000000000B01', 'c', 52317)")
        self.assertTrue(lua.eval("row(1, 5).trinket:IsShown()"))
        lua.execute("enter('Blood Ring', true)")  # a new match
        self.assertEqual(lua.eval("row(1, 5).name.text"), "|cff8c8c8c?|r")
        self.assertFalse(lua.eval("row(1, 5).trinket:IsShown()"))
        self.assertFalse(lua.eval("row(1, 5).racial:IsShown()"))
        self.assertIsNone(lua.eval("row(1, 5).trinketAt"))
        self.assertFalse(lua.eval("row(1, 5).power:IsShown()"))
        lua.execute("partySize = 4; enter('Blood Ring', true)")
        self.assertEqual(lua.eval("AutoBG_TargetsMainFrame5.title.text"), "Enemies 5/5")
        # The frame is as tall as its rows, spaced as they are.
        self.assertEqual(lua.eval("AutoBG_TargetsMainFrame5:GetHeight()"), 18 + 5 * (32 + 9))

    def test_an_enemy_out_of_view_shows_his_last_health_and_how_long_ago(self):
        lua = self.lua
        r = "row(1, 5)"
        lua.execute(f"enemy('{FOE}', {{ name = 'Foe', class = 'MAGE' }}); plate('{FOE}');"
                    f" units['{FOE}'].hp = 40; fireGUID('UNIT_HEALTH', '{FOE}');"
                    f" units['{FOE}'].visible = false; fireGUID('UNIT_VISIBILITY_CHANGED', '{FOE}', false); step(7)")
        self.assertEqual(lua.eval(f"clock({r}.status)"), "40%  |cff9a9a9a7s|r")
        lua.execute(f"units['{FOE}'].visible = true; fireGUID('UNIT_VISIBILITY_CHANGED', '{FOE}', true)")
        self.assertEqual(lua.eval(f"clock({r}.status)"), "40%")

    def test_a_hide_heard_in_combat_events_warns_once_in_view_or_not(self):
        lua = self.lua
        lua.execute(f"enemy('{FOE}', {{ name = 'Elf', class = 'ROGUE' }}); plate('{FOE}');"
                    f" units['{FOE}'].visible = false; fireGUID('UNIT_VISIBILITY_CHANGED', '{FOE}', false);"
                    f" fire('SPELL_GO_OTHER', 0, 1784, '{FOE}', '{FOE}')")
        self.assertTrue(lua.eval("AutoBG_SpyAlertWindow:IsShown()"))
        self.assertIn("Elf", lua.eval("AutoBG_SpyAlertWindow.line.text"))
        self.assertEqual(lua.eval("clock(row(1, 5).status)"), "|cffc7b5ffSTEALTH|r 0s")
        # The aura of the same stealth, and a second report: one card, one sound.
        lua.execute(f"fire('BUFF_ADDED_OTHER', '{FOE}', 1, 1784, 1, 60, 3, 0); fire('SPELL_GO_OTHER', 0, 1784, '{FOE}', '{FOE}')")
        self.assertEqual(lua.eval("count('sound:RaidWarning')"), 1)
        # A stack change (state 2) is no new stealth.
        lua.execute(f"step(5); fire('BUFF_ADDED_OTHER', '{FOE}', 1, 1784, 1, 60, 3, 2)")
        self.assertEqual(lua.eval("count('sound:RaidWarning')"), 1)

    def test_two_rogues_hiding_together_are_two_cards_and_a_sap_is_not_held_back(self):
        lua = self.lua
        lua.execute("me.pos = { 0, 0 }; unit('0x0000000000000050', { name = 'Mate', player = true, inGroup = true, pos = { 5, 0 } })")
        for guid, name in ((FOE, "Elf"), ("0x0000000000000B02", "Two")):
            lua.execute(f"enemy('{guid}', {{ name = '{name}', class = 'ROGUE', visible = false }});"
                        f" fire('BUFF_ADDED_OTHER', '{guid}', 1, 1787, 1, 60, 3, 0)")
        self.assertEqual(lua.eval("count('sound:RaidWarning')"), 2)
        self.assertIn("Two", lua.eval("AutoBG_SpyAlertWindow.line.text"))
        lua.execute(f"fire('SPELL_GO_OTHER', 0, 11297, '{FOE}', '0x0000000000000050')")
        self.assertEqual(lua.eval("count('sound:RaidWarning')"), 3)
        self.assertIn("on Mate", lua.eval("AutoBG_SpyAlertWindow.line.text"))

    def test_a_hide_names_an_enemy_nobody_has_seen_yet_and_a_dead_one_hides_nothing(self):
        lua = self.lua
        lua.execute(f"enemy('{FOE}', {{ name = 'Elf', class = 'ROGUE' }}); fire('SPELL_GO_OTHER', 0, 1856, '{FOE}', '{FOE}'); step()")
        self.assertEqual(lua.eval("#__addon_ns.Enemies.roster"), 1)
        self.assertEqual(lua.eval("row(1, 5).status.text"), "|cffd2c2ffVANISH|r")
        lua.execute(f"units['{FOE}'].dead = true; fireGUID('UNIT_HEALTH', '{FOE}'); log = {{}}; step(5);"
                    f" fire('SPELL_GO_OTHER', 0, 1784, '{FOE}', '{FOE}')")
        self.assertEqual(lua.eval("row(1, 5).status.text"), "DEAD")
        self.assertFalse(lua.eval("said('sound:RaidWarning')"))

    def test_an_enemy_not_yet_hostile_is_looked_at_again_an_ally_never(self):
        """Before the gates open the other team may not be attackable: the first
        look must not settle it for the match."""
        lua = self.lua
        lua.execute(f"enemy('{FOE}', {{ name = 'Foe', class = 'MAGE' }}); units['{FOE}'].enemy = false;"
                    " unit('0x0000000000000050', { name = 'Mate', player = true, inGroup = true });"
                    " setTarget('0x0000000000000050');"  # a target holds the sweep still
                    f" fire('SPELL_GO_OTHER', 0, 133, '{FOE}', '0x0000000000000050')")
        self.assertEqual(lua.eval("#__addon_ns.Enemies.roster"), 0)
        lua.execute(f"units['{FOE}'].enemy = true; fire('SPELL_GO_OTHER', 0, 133, '{FOE}', '0x0000000000000050')")
        self.assertEqual(lua.eval("#__addon_ns.Enemies.roster"), 0)  # not within a second
        lua.execute(f"step(1.1); fire('SPELL_GO_OTHER', 0, 133, '{FOE}', '0x0000000000000050')")
        self.assertEqual(lua.eval("#__addon_ns.Enemies.roster"), 1)
        self.assertEqual(lua.eval("__addon_ns.Enemies.roster[1].name"), "Foe")

    def test_a_name_the_scoreboard_gave_stays_while_he_is_not_yet_attackable(self):
        lua = self.lua
        lua.execute("fire('CHAT_MSG_ADDON', 'TW_ARENA', 'S2C_SCOREBOARD;0;2;Claude|1|0:Foe|2|0', 'GUILD', ''); step()")
        lua.execute(f"enemy('{FOE}', {{ name = 'Foe', class = 'MAGE' }}); units['{FOE}'].enemy = false; setTarget('{FOE}')")
        self.assertEqual(lua.eval("#__addon_ns.Enemies.roster"), 1)
        lua.execute(f"units['{FOE}'].enemy = true; setTarget('{FOE}')")
        self.assertEqual(lua.eval("__addon_ns.Enemies.byGUID['" + FOE + "'].name"), "Foe")

    def test_the_sweep_slows_down_when_it_finds_nobody(self):
        lua = self.lua
        lua.execute("log = {}; step(30)")
        self.assertEqual(lua.eval("count('ClearTarget')"), 24)  # every second for 20 s, then every third

    def test_an_arena_read_late_is_watched_all_the_same(self):
        """The zone text can lag the loading screen: the setup follows the zone
        change too. Fails on 2ada37f."""
        lua = load("AutoBGDB = { queueOnLogin = false }", setup="partySize = 1")
        lua.execute("zone = { name = '', kind = 'none', map = 0, inside = false }; fire('PLAYER_ENTERING_WORLD'); step()")
        self.assertFalse(lua.eval("AutoBG_TargetsMainFrame5:IsShown()"))
        lua.execute("zone = { name = 'Blood Ring', kind = 'pvp', map = 0, inside = true, arena = true };"
                    " fire('ZONE_CHANGED_NEW_AREA'); step()")
        self.assertTrue(lua.eval("AutoBG_TargetsMainFrame5:IsShown()"))
        self.assertEqual(lua.eval("cvars.NP_EnableSpellGoEvents"), "1")
        lua.execute(f"enemy('{FOE}', {{ name = 'Foe', class = 'MAGE', visible = false }});"
                    f" fire('DEBUFF_ADDED_OTHER', '{FOE}', 1, 172, 1, 60, 33, 0)")
        self.assertEqual(lua.eval("#__addon_ns.Enemies.roster"), 1)
        # A second zone event in the same arena resets nothing.
        lua.execute("fire('ZONE_CHANGED_NEW_AREA'); step()")
        self.assertEqual(lua.eval("#__addon_ns.Enemies.roster"), 1)


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

    def test_a_dropped_queue_bar_comes_back_there_whatever_the_client_saved(self):
        lua = load()
        lua.execute("queues[1] = { status = 'queued', map = 'Warsong Gulch' }; fire('UPDATE_BATTLEFIELD_STATUS')")
        lua.execute("local g = AutoBG_QueueFrame; run(g, 'OnDragStart'); g.left, g.top = 300, 500; run(g, 'OnDragStop')")
        self.assertEqual(lua.eval("AutoBGDB.places.AutoBG_QueueFrame[1]"), 300)
        self.assertFalse(lua.eval("AutoBG_QueueFrame:IsUserPlaced()"))
        # The next login: the client's file still has the 0, 0 it wrote before.
        lua = load("AutoBGDB = { places = { AutoBG_QueueFrame = { 300, 500 } } }", cache={"AutoBG_QueueFrame": (0, 0)})
        lua.execute("queues[1] = { status = 'queued', map = 'Warsong Gulch' }; fire('UPDATE_BATTLEFIELD_STATUS'); step()")
        point = lua.eval("(function() local p = AutoBG_QueueFrame.points; p = p[#p]; return p[1] .. ' ' .. p[4] .. ' ' .. p[5] end)()")
        self.assertEqual(point, "TOPLEFT 300 500")

    def test_odd_data_no_target_empty_raid_and_a_score_row_with_no_class(self):
        lua = load()
        lua.execute("scores = { { 'Nobody', 1, nil, nil } }; enter('Alterac Valley'); fire('UPDATE_BATTLEFIELD_SCORE'); step()")
        self.assertEqual(lua.eval("row(1, 40).name.text"), "Nobody")
        lua.execute("fire('PLAYER_TARGET_CHANGED'); fire('UNIT_TARGET', 'raid1'); step(); fire('RAID_TARGET_UPDATE')")
        lua.execute("row(1, 40):Click('LeftButton')")


if __name__ == "__main__":
    unittest.main()
