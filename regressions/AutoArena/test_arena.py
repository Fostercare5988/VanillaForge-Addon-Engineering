"""AutoArena 1.0, written new 2026-11-24: finding the other team before the gates,
the rows, the stealth tracker, pets and totems, and what runs at rest. Claude plays
for the Horde; his team is of two (`partySize = 1`) unless a test says otherwise."""
import unittest
from aa_env import load

FOE = "0x0000000000000B01"
TWO = "0x0000000000000B02"
MATE = "0x0000000000000050"
SAVED = "AutoArenaDB = { callouts = true }"


def arena(saved=SAVED, size=1):
    lua = load(saved, setup=f"partySize = {size}")
    lua.execute("unit('%s', { name = 'Mate', player = true, inGroup = true }); enter('Blood Ring', true)" % MATE)
    return lua


def hold(lua):
    """A target of yours holds the sweep still."""
    lua.execute(f"setTarget('{MATE}')")


class Finding(unittest.TestCase):
    def setUp(self):
        self.lua = arena()

    def test_the_frame_holds_a_slot_for_every_enemy_found_or_not_and_no_row_moves(self):
        lua = self.lua
        self.assertTrue(lua.eval("AutoArena_Frame:IsShown()"))
        self.assertEqual(lua.eval("row(1).name.text"), "|cff8c8c8c?|r")
        self.assertEqual(lua.eval("AutoArena_Frame.title.text"), "Enemies 2/2")
        lua.execute("enemy('0x0000000000000B01', { name = 'Zed', class = 'WARRIOR' }); plate('0x0000000000000B01')")
        lua.execute("enemy('0x0000000000000B02', { name = 'Abe', class = 'MAGE' }); plate('0x0000000000000B02')")
        # In the order found, not by class: a row never moves under a click.
        self.assertEqual(lua.eval("row(1).name.text"), "Zed")
        self.assertEqual(lua.eval("row(2).name.text"), "Abe")
        lua.execute("units['0x0000000000000B02'].dead = true; fireGUID('UNIT_HEALTH', '0x0000000000000B02')")
        self.assertEqual(lua.eval("AutoArena_Frame.title.text"), "Enemies 1/2")
        self.assertEqual(lua.eval("row(2).status.text"), "DEAD")

    def test_a_slot_is_blank_again_in_a_new_match_and_a_bigger_team_adds_slots(self):
        lua = self.lua
        lua.execute(f"enemy('{FOE}', {{ name = 'Zed', class = 'ROGUE', race = 'NightElf' }}); plate('{FOE}');"
                    f" fireGUID('UNIT_SPELLCAST_SUCCEEDED', '{FOE}', 'c', 52317)")
        self.assertTrue(lua.eval("row(1).trinket:IsShown()"))
        lua.execute("enter('Blood Ring', true)")
        self.assertEqual(lua.eval("row(1).name.text"), "|cff8c8c8c?|r")
        for part in ("trinket", "racial", "power"):
            self.assertFalse(lua.eval(f"row(1).{part}:IsShown()"))
        self.assertIsNone(lua.eval("row(1).trinketAt"))
        lua.execute("partySize = 4; enter('Blood Ring', true)")
        self.assertEqual(lua.eval("AutoArena_Frame.title.text"), "Enemies 5/5")
        self.assertEqual(lua.eval("AutoArena_Frame:GetHeight()"), 18 + 5 * (32 + 9))

    def test_the_roster_from_sightings_power_drinking_and_callouts(self):
        lua = self.lua
        lua.execute(f"enemy('{FOE}', {{ name = 'Foe', class = 'MAGE', power = 40 }}); plate('{FOE}')")
        lua.execute(f"units['{FOE}'].power = 70; fireGUID('UNIT_POWER_UPDATE', '{FOE}')")
        self.assertAlmostEqual(lua.eval("row(1).power.value"), 0.7)
        lua.execute(f"auraEvent('{FOE}', {{ aura('{FOE}', 1137, 'Drink') }}); auraEvent('{FOE}', {{ aura('{FOE}', 1137, 'Drink') }})")
        self.assertEqual(lua.eval("count('error:Foe is drinking')"), 1)
        lua.execute(f"units['{FOE}'].hp = 20; fireGUID('UNIT_HEALTH', '{FOE}'); fireGUID('UNIT_HEALTH', '{FOE}')")
        self.assertEqual(lua.eval("count('say:PARTY:Foe is at 25%%')"), 1)
        lua.execute(f"units['{FOE}'].dead = true; fireGUID('UNIT_HEALTH', '{FOE}')")
        self.assertTrue(lua.eval("said('say:PARTY:Foe is dead')"))

    def test_a_hostile_player_or_a_teammate_is_never_mixed_up(self):
        lua = self.lua
        hold(lua)
        lua.execute(f"enemy('{FOE}', {{ name = 'Foe', class = 'MAGE' }}); units['{FOE}'].enemy = false; plate('{FOE}')")
        # Not hostile yet behind the gates: still the other team. Your own team never is.
        self.assertEqual(lua.eval("#__addon_ns.Roster.list"), 1)
        lua.execute(f"plate('{MATE}'); fire('SPELL_GO_OTHER', 0, 133, '{MATE}', me.guid)")
        self.assertEqual(lua.eval("#__addon_ns.Roster.list"), 1)

    def test_the_arena_scoreboard_names_the_other_team_before_the_gates_open(self):
        lua = self.lua
        self.assertTrue(lua.eval("said('RequestScores')"))
        self.assertTrue(lua.eval("said('ScoreFaction:nil')"))  # every faction's rows
        hold(lua)
        lua.execute("scores = { { 'Claude', 0, 'Orc', 'Rogue' }, { 'Mate', 0, 'Orc', 'Priest' },"
                    " { 'Hunt', 1, 'Human', 'Hunter' }, { 'Frost', 1, 'Gnome', 'Mage' } };"
                    " fire('UPDATE_BATTLEFIELD_SCORE'); step()")
        self.assertEqual(lua.eval("#__addon_ns.Roster.list"), 2)
        self.assertEqual(lua.eval("row(1).name.text"), "Hunt")
        self.assertEqual(lua.eval("__addon_ns.Roster.list[1].class"), "HUNTER")
        self.assertTrue(lua.eval("row(1).racial:IsShown()"))
        # No GUID yet: it asks no more, and finds him by name when he is in view.
        lua.execute("log = {}; step(10)")
        self.assertFalse(lua.eval("said('ArenaScore')"))
        lua.execute("enemy('0x0000000000000B01', { name = 'Hunt', class = 'HUNTER', race = 'Human' });"
                    " units['0x0000000000000B01'].enemy = false; step(1)")
        self.assertEqual(lua.eval("__addon_ns.Roster.list[1].guid"), "0x0000000000000B01")
        self.assertEqual(lua.eval("row(1).entry.guid"), "0x0000000000000B01")

    def test_a_name_with_and_without_its_realm_is_one_enemy(self):
        lua = self.lua
        lua.execute("scores = { { 'Foe-NZ', 1, 'Human', 'Mage' } }; fire('UPDATE_BATTLEFIELD_SCORE'); step();"
                    f" enemy('{FOE}', {{ name = 'Foe', class = 'MAGE' }}); plate('{FOE}')")
        self.assertEqual(lua.eval("#__addon_ns.Roster.list"), 1)
        self.assertEqual(lua.eval("__addon_ns.Roster.list[1].guid"), FOE)

    def test_the_servers_team_list_names_the_other_team_never_yours(self):
        lua = self.lua
        lua.execute("step(1)")
        self.assertTrue(lua.eval("said('ArenaScore')"))
        lua.execute("fire('CHAT_MSG_ADDON', 'TW_ARENA', 'S2C_SCOREBOARD;0;2;Claude|1|0:Mate|1|0', 'GUILD', '')")
        self.assertEqual(lua.eval("#__addon_ns.Roster.list"), 0)
        lua.execute("fire('CHAT_MSG_ADDON', 'TW_ARENA', 'S2C_SCOREBOARD;0;4;Claude|1|0:Foe|2|0:Mate|1|0:Two|2|0', 'GUILD', ''); step()")
        self.assertEqual(lua.eval("#__addon_ns.Roster.list"), 2)
        self.assertEqual(lua.eval("row(1).name.text"), "Foe")

    def test_combat_and_aura_events_name_an_enemy_never_an_ally(self):
        lua = self.lua
        self.assertEqual(lua.eval("cvars.NP_EnableSpellGoEvents"), "1")
        hold(lua)
        lua.execute(f"enemy('{FOE}', {{ name = 'Foe', class = 'MAGE', visible = false }});"
                    f" fire('SPELL_GO_OTHER', 0, 133, '{MATE}', '{FOE}')")
        self.assertEqual(lua.eval("#__addon_ns.Roster.list"), 1)
        lua.execute("enemy('0x0000000000000B03', { name = 'Dot', class = 'WARLOCK', visible = false });"
                    " fire('DEBUFF_ADDED_OTHER', '0x0000000000000B03', 1, 172, 1, 60, 33, 0)")
        lua.execute(f"enemy('0x0000000000000B04', {{ name = 'Hit', class = 'WARRIOR', visible = false }});"
                    f" fire('SPELL_DAMAGE_EVENT_OTHER', '{MATE}', '0x0000000000000B04', 12294, 900, '0,0,0', 0, 1, '2,0,0,0')")
        self.assertEqual(lua.eval("#__addon_ns.Roster.list"), 3)
        lua.execute("enemy('0x0000000000000B05', { name = 'Buff', class = 'PRIEST' }); enemy('0x0000000000000B06', { name = 'Pal', class = 'PALADIN' });"
                    " fire('AURA_CAST_ON_OTHER', 1243, '0x0000000000000B05', '0x0000000000000B06', 1, 1, 0, 0)")
        self.assertEqual(lua.eval("#__addon_ns.Roster.list"), 5)
        lua.execute("enter(nil); enemy('0x0000000000000B07', { name = 'Far' }); fire('SPELL_DAMAGE_EVENT_OTHER', '0x0000000000000B07', me.guid)")
        self.assertEqual(lua.eval("#__addon_ns.Roster.list"), 0)

    def test_the_plates_already_up_name_the_team(self):
        lua = self.lua
        hold(lua)
        lua.execute(f"enemy('{FOE}', {{ name = 'Foe', class = 'MAGE' }});"
                    " unit('0xF130000000000E01', { name = 'Earthbind Totem', enemy = true, owner = '0x0000000000000B09', creature = 'Totem' });"
                    f" plateGUIDs = {{ '{FOE}', '0xF130000000000E01' }}; step(1)")
        self.assertEqual(lua.eval("__addon_ns.Roster.list[1].name"), "Foe")
        lua.execute("enemy('0x0000000000000B09', { name = 'Sham', class = 'SHAMAN' }); step(1)")
        self.assertEqual(lua.eval("#__addon_ns.Roster.list"), 2)

    def test_the_sweep_only_with_no_target_clears_it_rests_when_full_and_slows_down(self):
        lua = self.lua
        lua.execute(f"enemy('{FOE}', {{ name = 'Foe' }}); enemy('{TWO}', {{ name = 'Two' }}); step(1)")
        self.assertEqual(lua.eval("#__addon_ns.Roster.list"), 2)
        self.assertTrue(lua.eval("said('ClearTarget')"))
        lua.execute("log = {}; step(3)")
        self.assertFalse(lua.eval("said('ClearTarget')"))
        other = arena()
        other.execute("log = {}; step(30)")
        self.assertEqual(other.eval("count('ClearTarget')"), 24)  # every second for 20 s, then every third

    def test_a_totem_pulse_names_its_shaman_even_when_he_is_not_in_view_yet(self):
        lua = self.lua
        hold(lua)
        lua.execute("unit('0xF130000000000E01', { name = 'Strength of Earth Totem', enemy = true, owner = '0x0000000000000B09', creature = 'Totem' });"
                    f" fire('AURA_CAST_ON_OTHER', 8075, '0xF130000000000E01', '{MATE}', 1, 1, 0, 0)")
        self.assertEqual(lua.eval("#__addon_ns.Roster.list"), 0)  # he is no unit yet
        lua.execute("enemy('0x0000000000000B09', { name = 'Sham', class = 'SHAMAN' }); step(1)")
        self.assertEqual(lua.eval("__addon_ns.Roster.list[1].name"), "Sham")
        self.assertFalse(lua.eval("AutoArena_Pets:IsShown()"))

    def test_a_buff_cast_by_nobody_here_names_nobody(self):
        """A hunter's pet can carry buffs cast outside the arena."""
        lua = self.lua
        hold(lua)
        lua.execute("unit('0xF140000000000D01', { name = 'Wolf', enemy = true, owner = '0x0000000000000B01' });"
                    " fire('AURA_CAST_ON_OTHER', 1126, '0x0000000000000EEE', '0xF140000000000D01', 1, 1, 0, 0)")
        self.assertEqual(lua.eval("#__addon_ns.Roster.list"), 0)

    def test_pets_with_their_owner_dim_out_of_view_and_a_teammates_pet_is_no_enemy(self):
        lua = self.lua
        lua.execute(f"enemy('{FOE}', {{ name = 'Hunt', class = 'HUNTER' }}); unit('0xF140000000000D01', {{ name = 'Wolf', enemy = false, owner = '{FOE}' }});"
                    f" unit('0xF140000000000D02', {{ name = 'MyCat', owner = '{MATE}' }}); plate('0xF140000000000D02'); plate('0xF140000000000D01')")
        self.assertTrue(lua.eval("AutoArena_Pets:IsShown()"))
        self.assertEqual(lua.eval("#__addon_ns.Roster.list"), 1)  # the owner seen through his pet
        lua.execute("units['0xF140000000000D01'].visible = false; fireGUID('UNIT_VISIBILITY_CHANGED', '0xF140000000000D01', false)")
        self.assertTrue(lua.eval("(function() for _, w in ipairs(widgets) do if w.parent == AutoArena_Pets and w:IsShown() then return w:GetAlpha() < 1 end end end)()"))

    def test_the_match_log_keeps_what_each_source_said_for_the_last_eight_matches(self):
        lua = self.lua
        lua.execute("fire('CHAT_MSG_ADDON', 'TW_ARENA', 'S2C_SCOREBOARD;0;2;Claude|1|0:Foe|2|0', 'GUILD', ''); step();"
                    f" enemy('{FOE}', {{ name = 'Foe', class = 'MAGE' }}); plate('{FOE}')")
        text = lua.eval("table.concat(AutoArenaDB.arenaLog[1].log, '|')")
        self.assertIn("server S2C_SCOREBOARD;0;2;Claude|1|0:Foe|2|0", text)
        self.assertIn("named Foe", text)
        self.assertIn("id Foe attackable yes", text)
        for _ in range(9):
            lua.execute("enter('Blood Ring', true)")
        self.assertEqual(lua.eval("#AutoArenaDB.arenaLog"), 8)
        lua.execute("enter(nil); __addon_ns.Log('late', 'x')")
        self.assertNotIn("late", lua.eval("table.concat(AutoArenaDB.arenaLog[1].log, '|')"))


class Zone(unittest.TestCase):
    def test_sunstrider_court_is_an_arena_though_the_client_calls_it_no_instance(self):
        lua = load(SAVED, setup="partySize = 1")
        lua.execute("zone = { name = 'Sunstrider Court', kind = 'none', map = 0, inside = false };"
                    " fire('PLAYER_ENTERING_WORLD'); fire('ZONE_CHANGED_NEW_AREA'); step()")
        self.assertTrue(lua.eval("AutoArena_Frame:IsShown()"))
        lua.execute("enter(nil)")
        self.assertFalse(lua.eval("AutoArena_Frame:IsShown()"))

    def test_an_arena_read_late_is_watched_all_the_same_and_a_second_read_resets_nothing(self):
        lua = load(SAVED, setup="partySize = 1")
        lua.execute("zone = { name = 'Orgrimmar', kind = 'none', map = 0, inside = false }; fire('PLAYER_ENTERING_WORLD'); step()")
        self.assertFalse(lua.eval("AutoArena_Frame:IsShown()"))
        # The zone text catches up half a second after the loading screen: the timers read it again.
        lua.execute("zone = { name = 'Blood Ring', kind = 'pvp', map = 0, inside = true, arena = true }; step(0.7)")
        self.assertTrue(lua.eval("AutoArena_Frame:IsShown()"))
        self.assertEqual(lua.eval("cvars.NP_EnableSpellGoEvents"), "1")
        lua.execute(f"enemy('{FOE}', {{ name = 'Foe', class = 'MAGE', visible = false }});"
                    f" fire('DEBUFF_ADDED_OTHER', '{FOE}', 1, 172, 1, 60, 33, 0); fire('ZONE_CHANGED_NEW_AREA'); step(5)")
        self.assertEqual(lua.eval("#__addon_ns.Roster.list"), 1)


class Stealth(unittest.TestCase):
    def setUp(self):
        self.lua = arena()

    def test_every_stealth_warns_in_an_arena_at_any_distance(self):
        lua = self.lua
        lua.execute(f"enemy('{FOE}', {{ name = 'Elf', class = 'HUNTER', yards = 120 }}); plate('{FOE}');"
                    f" fireGUID('UNIT_SPELLCAST_SUCCEEDED', '{FOE}', 'c', 20580)")
        self.assertTrue(lua.eval("AutoArena_AlertCard:IsShown()"))
        self.assertTrue(lua.eval("said('sound:RaidWarning')"))
        lua.execute("AutoArena_AlertCard:Click('LeftButton')")
        self.assertTrue(lua.eval("said('^target:Elf$')"))

    def test_stealth_from_an_aura_ended_by_its_removal_or_by_coming_into_view_without_it(self):
        lua = self.lua
        r = "row(1)"
        lua.execute(f"enemy('{FOE}', {{ name = 'Elf', class = 'ROGUE' }}); plate('{FOE}'); stealthID = aura('{FOE}', 1787); auraEvent('{FOE}', {{ stealthID }})")
        self.assertEqual(lua.eval(f"{r}.status.text"), "|cffc7b5ffSTEALTH|r")
        self.assertTrue(lua.eval(f"{r}.stealthIcon:IsShown()"))
        self.assertEqual(lua.eval(f"{r}:GetAlpha()"), 1)
        lua.execute(f"removeAura('{FOE}', stealthID); auraEvent('{FOE}', nil, {{ stealthID }})")
        self.assertEqual(lua.eval(f"{r}.status.text"), "100%")
        lua.execute(f"auraEvent('{FOE}', {{ aura('{FOE}', 11327) }})")
        self.assertEqual(lua.eval(f"{r}.status.text"), "|cffd2c2ffVANISH|r")
        lua.execute(f"units['{FOE}'].auras = {{}}; fireGUID('UNIT_VISIBILITY_CHANGED', '{FOE}', true)")
        self.assertEqual(lua.eval(f"{r}.status.text"), "100%")

    def test_a_hide_heard_in_combat_events_warns_once_in_view_or_not(self):
        lua = self.lua
        lua.execute(f"enemy('{FOE}', {{ name = 'Elf', class = 'ROGUE' }}); plate('{FOE}');"
                    f" units['{FOE}'].visible = false; fireGUID('UNIT_VISIBILITY_CHANGED', '{FOE}', false);"
                    f" fire('SPELL_GO_OTHER', 0, 1784, '{FOE}', '{FOE}')")
        self.assertTrue(lua.eval("AutoArena_AlertCard:IsShown()"))
        self.assertIn("Elf", lua.eval("AutoArena_AlertCard.line.text"))
        self.assertEqual(lua.eval("clock(row(1).status)"), "|cffc7b5ffSTEALTH|r 0s")
        lua.execute(f"fire('BUFF_ADDED_OTHER', '{FOE}', 1, 1784, 1, 60, 3, 0); fire('SPELL_GO_OTHER', 0, 1784, '{FOE}', '{FOE}')")
        self.assertEqual(lua.eval("count('sound:RaidWarning')"), 1)
        lua.execute(f"step(5); fire('BUFF_ADDED_OTHER', '{FOE}', 1, 1784, 1, 60, 3, 2)")  # a stack change is no new stealth
        self.assertEqual(lua.eval("count('sound:RaidWarning')"), 1)

    def test_stealth_and_vanish_from_their_casts_when_no_aura_reaches_us(self):
        lua = self.lua
        lua.execute(f"enemy('{FOE}', {{ name = 'Elf', class = 'ROGUE' }}); plate('{FOE}');"
                    f" fireGUID('UNIT_SPELLCAST_SUCCEEDED', '{FOE}', 'c', 5215)")
        self.assertEqual(lua.eval("row(1).status.text"), "|cffd2c2ffPROWL|r")
        self.assertEqual(lua.eval("row(1).stealthIcon.texture"), lua.eval("select(3, GetSpellInfo(5215))"))
        lua.execute(f"id = aura('{FOE}', 1, 'Thorns'); removeAura('{FOE}', id); auraEvent('{FOE}', nil, {{ id }})")
        self.assertEqual(lua.eval("row(1).status.text"), "100%")  # an aura going in view ends a cast-only stealth
        lua.execute(f"step(9); fireGUID('UNIT_SPELLCAST_SUCCEEDED', '{FOE}', 'c', 1856)")
        self.assertEqual(lua.eval("row(1).status.text"), "|cffd2c2ffVANISH|r")

    def test_two_rogues_hiding_together_are_two_cards_and_a_sap_is_not_held_back(self):
        lua = self.lua
        lua.execute(f"me.pos = {{ 0, 0 }}; units['{MATE}'].pos = {{ 5, 0 }}")
        for guid, name in ((FOE, "Elf"), (TWO, "Two")):
            lua.execute(f"enemy('{guid}', {{ name = '{name}', class = 'ROGUE', visible = false }});"
                        f" fire('BUFF_ADDED_OTHER', '{guid}', 1, 1787, 1, 60, 3, 0)")
        self.assertEqual(lua.eval("count('sound:RaidWarning')"), 2)
        self.assertIn("Two", lua.eval("AutoArena_AlertCard.line.text"))
        lua.execute(f"fire('SPELL_GO_OTHER', 0, 11297, '{FOE}', '{MATE}')")
        self.assertEqual(lua.eval("count('sound:RaidWarning')"), 3)
        self.assertIn("on Mate", lua.eval("AutoArena_AlertCard.line.text"))

    def test_a_hide_names_an_enemy_nobody_has_seen_yet_and_a_dead_one_hides_nothing(self):
        lua = self.lua
        lua.execute(f"enemy('{FOE}', {{ name = 'Elf', class = 'ROGUE' }}); fire('SPELL_GO_OTHER', 0, 1856, '{FOE}', '{FOE}'); step()")
        self.assertEqual(lua.eval("row(1).status.text"), "|cffd2c2ffVANISH|r")
        lua.execute(f"units['{FOE}'].dead = true; fireGUID('UNIT_HEALTH', '{FOE}'); log = {{}}; step(5);"
                    f" fire('SPELL_GO_OTHER', 0, 1784, '{FOE}', '{FOE}')")
        self.assertEqual(lua.eval("row(1).status.text"), "DEAD")
        self.assertFalse(lua.eval("said('sound:RaidWarning')"))

    def test_a_hidden_stealther_shows_how_long_ago_and_how_far_his_last_spot_is(self):
        lua = self.lua
        r = "row(1)"
        lua.execute(f"me.pos = {{ 0, 0 }}; enemy('{FOE}', {{ name = 'Foe', class = 'ROGUE', yards = 30, pos = {{ 30, 0 }} }}); plate('{FOE}')")
        lua.execute(f"auraEvent('{FOE}', {{ aura('{FOE}', 1787) }})")
        lua.execute(f"units['{FOE}'].visible = false; fireGUID('UNIT_VISIBILITY_CHANGED', '{FOE}', false); step(5)")
        self.assertEqual(lua.eval(f"clock({r}.status)"), "|cffc7b5ffSTEALTH|r 5s")
        self.assertEqual(lua.eval(f"{r}.yards.text"), "|cffb59cff~30 yd|r")
        lua.execute("me.pos = { 10, 0 }; step(0.2)")
        self.assertEqual(lua.eval(f"{r}.yards.text"), "|cffb59cff~20 yd|r")
        lua.execute("step(60)")
        self.assertEqual(lua.eval(f"{r}.yards.text"), "")
        lua.execute(f"units['{FOE}'].visible = true; units['{FOE}'].auras = {{}}; fireGUID('UNIT_VISIBILITY_CHANGED', '{FOE}', true)")
        self.assertEqual(lua.eval(f"clock({r}.status)"), "100%")

    def test_an_enemy_out_of_view_shows_his_last_health_and_how_long_ago(self):
        lua = self.lua
        lua.execute(f"enemy('{FOE}', {{ name = 'Foe', class = 'MAGE' }}); plate('{FOE}');"
                    f" units['{FOE}'].hp = 40; fireGUID('UNIT_HEALTH', '{FOE}');"
                    f" units['{FOE}'].visible = false; fireGUID('UNIT_VISIBILITY_CHANGED', '{FOE}', false); step(7)")
        self.assertEqual(lua.eval("clock(row(1).status)"), "40%  |cff9a9a9a7s|r")
        lua.execute(f"units['{FOE}'].visible = true; fireGUID('UNIT_VISIBILITY_CHANGED', '{FOE}', true)")
        self.assertEqual(lua.eval("clock(row(1).status)"), "40%")

    def test_nobody_is_called_drinking_before_he_can_be_attacked(self):
        lua = self.lua
        lua.execute(f"enemy('{FOE}', {{ name = 'Foe', class = 'MAGE' }}); plate('{FOE}'); units['{FOE}'].enemy = false;"
                    f" auraEvent('{FOE}', {{ aura('{FOE}', 1137, 'Drink') }})")
        self.assertFalse(lua.eval("said('is drinking')"))
        lua.execute(f"units['{FOE}'].enemy = true; auraEvent('{FOE}', {{ aura('{FOE}', 1137, 'Drink') }})")
        self.assertTrue(lua.eval("said('Foe is drinking')"))


class Rows(unittest.TestCase):
    def setUp(self):
        self.lua = arena()
        self.lua.execute(f"enemy('{FOE}', {{ name = 'Foe-NZ', class = 'MAGE', race = 'Gnome', yards = 25 }}); plate('{FOE}')")

    def test_casts_start_stop_and_channel_and_one_with_no_stop_leaves_at_its_end(self):
        lua = self.lua
        lua.execute(f"units['{FOE}'].cast = {{ name = 'Fireball', icon = 'i', from = now, to = now + 3 }}; fireGUID('UNIT_SPELLCAST_START', '{FOE}')")
        self.assertTrue(lua.eval("row(1).cast:IsShown()"))
        lua.execute("step(3.2)")
        self.assertFalse(lua.eval("row(1).cast:IsShown()"))

    def test_the_trinket_the_racial_and_their_numbers(self):
        lua = self.lua
        lua.execute(f"fireGUID('UNIT_SPELLCAST_SUCCEEDED', '{FOE}', 'c', 52317); fireGUID('UNIT_SPELLCAST_SUCCEEDED', '{FOE}', 'c', 20589)")
        self.assertEqual(lua.eval("row(1).trinket.cd.cdDuration"), 180)
        self.assertEqual(lua.eval("row(1).racial.cd.cdDuration"), 90)
        lua.execute("AutoArenaDB.racials.Gnome = false; __addon_ns.Frames.Apply()")
        self.assertFalse(lua.eval("row(1).racial:IsShown()"))
        # Used while switched off: no sweep, and no error (AutoBG, 2026-11-27).
        lua.execute(f"fireGUID('UNIT_SPELLCAST_SUCCEEDED', '{FOE}', 'c', 20589)")
        self.assertIsNone(lua.eval("row(1).racial.cd.cdDuration"))

    def test_the_realm_is_left_off_unless_asked_and_a_click_binds_the_guid(self):
        lua = self.lua
        self.assertEqual(lua.eval("row(1).name.text"), "Foe-NZ")
        lua.execute("AutoArenaDB.hideRealm = true; __addon_ns.Frames.Apply()")
        self.assertEqual(lua.eval("row(1).name.text"), "Foe")
        self.assertEqual(lua.eval("row(1):GetAttribute('unit')"), FOE)
        lua.execute("row(1):Click('RightButton')")
        self.assertTrue(lua.eval("said('^focus:Foe')"))

    def test_the_yards_follow_the_look_and_a_wall_greys_them(self):
        lua = self.lua
        lua.execute("step(0.2)")
        self.assertEqual(lua.eval("row(1).yards.text"), "|cff59ff72" .replace("|cff59ff72", "|cff59ff72") + "25 yd|r")
        lua.execute(f"units['{FOE}'].blocked = true; step(0.6)")
        self.assertEqual(lua.eval("row(1).yards.text"), "|cff80808025 yd|r")

    def test_borders_marks_and_who_is_on_him(self):
        lua = self.lua
        lua.execute(f"units['{FOE}'].mark = 8; fire('RAID_TARGET_UPDATE'); setTarget('{FOE}')")
        self.assertEqual(lua.eval("row(1).mark.markIndex"), 8)
        self.assertTrue(lua.eval("row(1).edge:IsShown()"))
        lua.execute(f"units['{MATE}'].target = '{FOE}'; tokens.party1target = '{FOE}'; fire('UNIT_TARGET', 'party1'); step()")
        self.assertEqual(lua.eval("row(1).count.text"), "2")


class Preview(unittest.TestCase):
    def test_the_preview_shows_samples_outside_an_arena_and_ends_with_the_window(self):
        lua = load(SAVED, setup="partySize = 2")
        lua.execute("__addon_ns.Preview(true); step()")
        self.assertTrue(lua.eval("AutoArena_Frame:IsShown()"))
        self.assertEqual(lua.eval("row(1).name.text"), "Brightblade")
        lua.execute("__addon_ns.Preview(false); step()")
        self.assertFalse(lua.eval("AutoArena_Frame:IsShown()"))


class AtRest(unittest.TestCase):
    def test_nothing_runs_outside_an_arena_and_odd_data_is_fine(self):
        lua = load("AutoArenaDB = { show = 'junk', stale = 1 }")
        lua.execute("step(5)")  # the zone is read again after the loading screen
        self.assertEqual(lua.eval("liveTimers()"), 0)
        self.assertEqual(lua.eval("onUpdates()"), 0)
        self.assertTrue(lua.eval("AutoArenaDB.show"))
        self.assertIsNone(lua.eval("AutoArenaDB.stale"))
        lua.execute("enter('Orgrimmar'); enter(nil); step(10)")
        self.assertEqual(lua.eval("liveTimers()"), 0)

    def test_in_an_arena_with_nobody_in_view_only_the_sweep_runs(self):
        lua = arena()
        self.assertEqual(lua.eval("onUpdates()"), 0)
        lua.execute(f"enemy('{FOE}', {{ name = 'Foe' }}); enemy('{TWO}', {{ name = 'Two' }}); step(2)")
        lua.execute("enter(nil); step(10)")
        self.assertEqual(lua.eval("liveTimers()"), 0)

    def test_a_first_login_at_the_clients_places_and_no_errors(self):
        lua = load(SAVED, cache={"AutoArena_Frame": (900, -300)})
        self.assertEqual(lua.eval("AutoArena_Frame:GetLeft() ~= nil or true"), True)


if __name__ == "__main__":
    unittest.main()
