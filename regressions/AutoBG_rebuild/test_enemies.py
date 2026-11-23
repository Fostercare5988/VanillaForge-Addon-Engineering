"""The enemy roster and its rows, the carriers, the scoreboard names (spec 4.4
tests 9-11). AutoBG 1.0, written new 2026-11-22. Claude plays for the Horde, so
the scoreboard's enemies are faction 1."""
import unittest
from abg_env import load

ROGUE = "0x0000000000000A01"
MAGE = "0x0000000000000A02"


def match(lua, extra=""):
    lua.execute("scores = { { 'Thandril-NZ', 1, 'Night Elf', 'Rogue' }, { 'Ashka', 1, 'Human', 'Mage' },"
                " { 'Claude', 0, 'Orc', 'Rogue' }, { 'Mate', 1, 'Human', 'Priest' }, { 'Grom', 0, 'Orc', 'Warrior' } }"
                "; unit('0x0000000000000050', { name = 'Mate', player = true, inGroup = true })" + extra)
    lua.execute("enter('Warsong Gulch'); fire('UPDATE_BATTLEFIELD_SCORE'); step()")


def names(lua, size=10):
    return lua.eval(f'''(function()
        local out = {{}}
        for _, r in ipairs(AutoBG_TargetsMainFrame{size}.rows) do if r:IsShown() then out[#out + 1] = r.name.text end end
        return table.concat(out, '|')
    end)()''')


def seen(lua, guid, extra=""):
    lua.execute(f"enemy('{guid}', {{ name = '{'Thandril-NZ' if guid == ROGUE else 'Ashka'}', class = '{'ROGUE' if guid == ROGUE else 'MAGE'}',"
                f" race = '{'NightElf' if guid == ROGUE else 'Human'}' {extra} }})")
    return lua.eval(f"plate('{guid}')")


class Roster(unittest.TestCase):
    def test_the_scoreboard_less_you_your_group_and_your_own_team(self):
        lua = load()
        match(lua)
        self.assertEqual(names(lua), "Ashka|Thandril")
        self.assertEqual(lua.eval("AutoBG_TargetsMainFrame10.title.text"), "Enemies 2/2")
        self.assertTrue(lua.eval("AutoBG_TargetsMainFrame10:IsShown()"))
        self.assertFalse(lua.eval("AutoBG_TargetsMainFrame15:IsShown()"))

    def test_hide_realm_names_off_shows_them(self):
        lua = load("AutoBGDB = { sizes = { [10] = { hideRealm = false } } }")
        match(lua)
        self.assertEqual(names(lua), "Ashka|Thandril-NZ")

    def test_a_teammate_of_the_other_faction_leaves_when_seen(self):
        lua = load()
        match(lua)
        lua.execute(f"unit('{MAGE}', {{ name = 'Ashka', player = true, class = 'MAGE' }}); plate('{MAGE}')")
        self.assertEqual(names(lua), "Thandril")
        lua.execute("fire('UPDATE_BATTLEFIELD_SCORE'); step()")
        self.assertEqual(names(lua), "Thandril")

    def test_a_hostile_player_seen_joins_and_the_scoreboard_is_asked(self):
        lua = load()
        match(lua)
        lua.execute("log = {}; enemy('0x0000000000000A09', { name = 'Zed', class = 'WARRIOR' }); plate('0x0000000000000A09'); step(1)")
        self.assertEqual(names(lua), "Ashka|Thandril|Zed")
        self.assertTrue(lua.eval("said('RequestScores')"))
        lua.execute("fire('UPDATE_BATTLEFIELD_SCORE'); step()")
        self.assertIn("Zed", names(lua))

    def test_the_guids_are_registered_once_per_frame_never_an_ally(self):
        lua = load()
        match(lua)
        seen(lua, ROGUE)
        seen(lua, MAGE)
        f = "(function() for _, w in ipairs(widgets) do local ok, g = w:IsGUIDEventRegistered('UNIT_SPELLCAST_START'); if ok then return { w:IsGUIDEventRegistered('UNIT_SPELLCAST_START') } end end end)()"
        got = list(lua.eval(f).values())
        self.assertEqual(sorted(got[1:]), sorted([ROGUE, MAGE]))
        self.assertNotIn("0x0000000000000050", got)

    def test_a_guid_from_a_members_target(self):
        lua = load()
        match(lua)
        lua.execute(f"enemy('{ROGUE}', {{ name = 'Thandril-NZ', class = 'ROGUE' }}); tokens.party1target = '{ROGUE}';"
                    " fire('UNIT_TARGET', 'party1'); step()")
        self.assertEqual(lua.eval(f"__addon_ns.Enemies.byGUID['{ROGUE}'].name"), "Thandril-NZ")
        self.assertEqual(lua.eval("row(2).count.text"), "1")

    def test_an_uncached_name_is_not_listed(self):
        lua = load()
        match(lua)
        lua.execute("enemy('0x0000000000000A0F', { name = 'Unknown' }); plate('0x0000000000000A0F')")
        self.assertEqual(names(lua), "Ashka|Thandril")


class Rows(unittest.TestCase):
    def setUp(self):
        self.lua = load()
        match(self.lua)
        seen(self.lua, ROGUE)
        self.r = "row(2)"

    def test_health_by_guid(self):
        lua = self.lua
        lua.execute(f"units['{ROGUE}'].hp = 40; fireGUID('UNIT_HEALTH', '{ROGUE}')")
        self.assertEqual(lua.eval(f"{self.r}.status.text"), "40%")
        self.assertAlmostEqual(lua.eval(f"{self.r}.health.value"), 0.4)

    def test_dead_counts_to_the_wave_and_comes_back_unless_the_body_is_in_view(self):
        lua = self.lua
        lua.execute("healerTime = 20; fire('AREA_SPIRIT_HEALER_IN_RANGE')")
        lua.execute(f"units['{ROGUE}'].dead = true; fireGUID('UNIT_HEALTH', '{ROGUE}')")
        self.assertEqual(lua.eval(f"clock({self.r}.status)"), "DEAD 20")
        self.assertEqual(lua.eval("AutoBG_TargetsMainFrame10.title.text"), "Enemies 1/2")
        lua.execute("step(20.1)")
        self.assertEqual(lua.eval(f"clock({self.r}.status)"), "DEAD 30")  # the body lies in view
        lua.execute(f"units['{ROGUE}'].visible = false; fireGUID('UNIT_VISIBILITY_CHANGED', '{ROGUE}', false); step(30)")
        self.assertEqual(lua.eval(f"clock({self.r}.status)"), "100%")

    def test_a_guessed_wave_revives_nobody(self):
        lua = self.lua
        lua.execute("tokens.raid3 = '0x0000000000000050'; units['0x0000000000000050'].dead = true; fire('UNIT_HEALTH', 'raid3');"
                    " units['0x0000000000000050'].dead = nil; fire('UNIT_HEALTH', 'raid3')")  # a rough wave
        lua.execute(f"units['{ROGUE}'].dead = true; units['{ROGUE}'].visible = false; fireGUID('UNIT_HEALTH', '{ROGUE}')")
        self.assertEqual(lua.eval(f"clock({self.r}.status)"), "DEAD ~30")
        lua.execute("step(31)")
        self.assertEqual(lua.eval(f"string.sub(clock({self.r}.status), 1, 4)"), "DEAD")

    def test_stealth_from_an_aura_by_id_ended_by_its_removal_or_by_coming_into_view_without_it(self):
        lua = self.lua
        lua.execute(f"units['{ROGUE}'].yards = 20; stealthID = aura('{ROGUE}', 1787); auraEvent('{ROGUE}', {{ stealthID }})")
        self.assertEqual(lua.eval(f"{self.r}.status.text"), "STEALTH")
        self.assertEqual(lua.eval(f"{self.r}:GetAlpha()"), 0.5)
        self.assertTrue(lua.eval("said('sound:RaidWarning')"))
        lua.execute(f"removeAura('{ROGUE}', stealthID); auraEvent('{ROGUE}', nil, {{ stealthID }})")
        self.assertEqual(lua.eval(f"{self.r}.status.text"), "100%")
        lua.execute(f"auraEvent('{ROGUE}', {{ aura('{ROGUE}', 11327) }})")
        self.assertEqual(lua.eval(f"{self.r}.status.text"), "VANISH")
        lua.execute(f"units['{ROGUE}'].auras = {{}}; fireGUID('UNIT_VISIBILITY_CHANGED', '{ROGUE}', true)")
        self.assertEqual(lua.eval(f"{self.r}.status.text"), "100%")

    def test_stealth_and_vanish_from_their_casts_when_no_aura_reaches_us(self):
        """2026-11-23, the player: no STEALTH/PROWL on the rows. The enemy leaves
        view as he stealths, so his aura often never arrives; the cast does.
        Fails on fc7ba38."""
        lua = self.lua
        lua.execute(f"fireGUID('UNIT_SPELLCAST_SUCCEEDED', '{ROGUE}', 'c', 1787);"
                    f" units['{ROGUE}'].visible = false; fireGUID('UNIT_VISIBILITY_CHANGED', '{ROGUE}', false)")
        self.assertEqual(lua.eval(f"{self.r}.status.text"), "STEALTH")
        self.assertEqual(lua.eval(f"{self.r}:GetAlpha()"), 0.5)
        lua.execute(f"units['{ROGUE}'].visible = true; fireGUID('UNIT_VISIBILITY_CHANGED', '{ROGUE}', true)")
        self.assertEqual(lua.eval(f"{self.r}.status.text"), "100%")
        lua.execute(f"step(9); fireGUID('UNIT_SPELLCAST_SUCCEEDED', '{ROGUE}', 'c', 1856)")
        self.assertEqual(lua.eval(f"{self.r}.status.text"), "VANISH")

    def test_the_stealth_card_is_for_live_danger_only_and_targets_him(self):
        """2026-11-23, the player: the big MELD card should warn only of an enemy in
        front of you, not of anyone stealthing anywhere, and target him on a click.
        Fails on 0bd447d."""
        lua = self.lua
        lua.execute(f"units['{ROGUE}'].yards = 120; fireGUID('UNIT_SPELLCAST_SUCCEEDED', '{ROGUE}', 'c', 20580)")
        self.assertEqual(lua.eval(f"{self.r}.status.text"), "MELD")  # the row still says it
        self.assertFalse(lua.eval("AutoBG_SpyAlertWindow:IsShown()"))
        self.assertFalse(lua.eval("said('sound:RaidWarning')"))
        # Shadowmeld next to you is no alarm either: only Stealth, Vanish and Prowl, as Spy.
        lua.execute(f"units['{ROGUE}'].yards = 15; fireGUID('UNIT_SPELLCAST_SUCCEEDED', '{ROGUE}', 'c', 20580)")
        self.assertFalse(lua.eval("AutoBG_SpyAlertWindow:IsShown()"))
        lua.execute(f"fireGUID('UNIT_SPELLCAST_SUCCEEDED', '{ROGUE}', 'c', 1787)")
        self.assertTrue(lua.eval("AutoBG_SpyAlertWindow:IsShown()"))
        self.assertIn("is stealthed 15 yd away", lua.eval("AutoBG_SpyAlertWindow.line.text"))
        self.assertTrue(lua.eval("said('sound:RaidWarning')"))
        lua.execute("AutoBG_SpyAlertWindow:Click('LeftButton')")
        self.assertTrue(lua.eval("said('^target:Thandril%-NZ$')"))

    def test_a_cast_only_stealth_ends_when_an_aura_goes_in_view(self):
        lua = self.lua
        lua.execute(f"fireGUID('UNIT_SPELLCAST_SUCCEEDED', '{ROGUE}', 'c', 5215)")
        self.assertEqual(lua.eval(f"{self.r}.status.text"), "PROWL")
        lua.execute(f"id = aura('{ROGUE}', 1, 'Thorns'); removeAura('{ROGUE}', id); auraEvent('{ROGUE}', nil, {{ id }})")
        self.assertEqual(lua.eval(f"{self.r}.status.text"), "100%")

    def test_an_invisibility_potion_ends_after_15_seconds(self):
        lua = self.lua
        lua.execute(f"auraEvent('{ROGUE}', {{ aura('{ROGUE}', 3680) }}); step(14.9)")
        self.assertEqual(lua.eval(f"{self.r}.status.text"), "INVIS POT")
        lua.execute("step(0.2)")
        self.assertEqual(lua.eval(f"{self.r}.status.text"), "100%")

    def test_casts_start_stop_and_channel_and_one_with_no_stop_leaves_at_its_end(self):
        lua = self.lua
        cast = f"{self.r}.cast"
        lua.execute(f"units['{ROGUE}'].cast = {{ name = 'Frostbolt', icon = 'Interface@@Icons@@Spell_Frost_FrostBolt02', from = now, to = now + 2.5 }};"
                    f" fireGUID('UNIT_SPELLCAST_START', '{ROGUE}')")
        self.assertTrue(lua.eval(f"{cast}:IsShown()"))
        self.assertEqual(lua.eval(f"{cast}.text.text"), "Frostbolt")
        # 2026-11-23, the player: the spell's icon beside the cast bar, as the old addon had.
        self.assertEqual(lua.eval(f"{cast}.icon.texture"), "Interface@@Icons@@Spell_Frost_FrostBolt02")
        self.assertEqual(list(lua.eval(f"{cast}.barColor").values()), [1, 0.55, 0.1])
        lua.execute(f"fireGUID('UNIT_SPELLCAST_INTERRUPTED', '{ROGUE}')")
        self.assertFalse(lua.eval(f"{cast}:IsShown()"))
        lua.execute(f"units['{ROGUE}'].cast = {{ name = 'Drain', channel = true, from = now, to = now + 5, locked = true }}; fireGUID('UNIT_SPELLCAST_CHANNEL_START', '{ROGUE}')")
        self.assertEqual(list(lua.eval(f"{cast}.barColor").values()), [0.55, 0.55, 0.55])
        lua.execute("step(5.2)")
        self.assertFalse(lua.eval(f"{cast}:IsShown()"))

    def test_a_click_on_the_cast_bar_targets_the_caster(self):
        """2026-11-23, the player: a heal or an Opening seen on the cast bar should
        be one click from targeting him. Fails on faf52b9."""
        lua = self.lua
        lua.execute(f"units['{ROGUE}'].cast = {{ name = 'Opening', from = now, to = now + 5 }}; fireGUID('UNIT_SPELLCAST_START', '{ROGUE}')")
        lua.execute(f"{self.r}.castButton:Click('LeftButton')")
        self.assertTrue(lua.eval("said('^target:Thandril%-NZ$')"))
        lua.execute(f"{self.r}.castButton:Click('RightButton')")
        self.assertTrue(lua.eval("said('^focus:Thandril%-NZ$')"))

    def test_the_trinket_from_the_immune_aura_one_use_per_two_reports(self):
        lua = self.lua
        lua.execute(f"log = {{}}; auraEvent('{ROGUE}', {{ aura('{ROGUE}', 52317) }}); fireGUID('UNIT_SPELLCAST_SUCCEEDED', '{ROGUE}', 'c', 52317)")
        self.assertEqual(lua.eval(f"{self.r}.trinket.cd.cdDuration"), 180)
        self.assertEqual(lua.eval("count('SetCooldown')"), 1)
        lua.execute(f"fireGUID('UNIT_HEALTH', '{ROGUE}')")
        self.assertEqual(lua.eval("count('SetCooldown')"), 1)

    def test_the_racial_from_the_race_and_its_use(self):
        lua = self.lua
        self.assertTrue(lua.eval(f"{self.r}.racial:IsShown()"))
        self.assertEqual(lua.eval(f"{self.r}.racial.tex.texture"), "Icon20580")
        lua.execute(f"fireGUID('UNIT_SPELLCAST_SUCCEEDED', '{ROGUE}', 'c', 20580)")
        self.assertEqual(lua.eval(f"{self.r}.racial.cd.cdDuration"), 60)

    def test_the_yards_follow_the_distance_look_and_each_size_can_hide_them(self):
        """2026-11-23, players asked for the distance on the enemy frames."""
        lua = self.lua
        lua.execute(f"units['{ROGUE}'].yards = 24.4; step(0.5)")
        self.assertIn("24 yd", lua.eval(f"{self.r}.yards.text"))
        lua.execute(f"units['{ROGUE}'].yards = 71; step(0.5)")
        self.assertIn("71 yd", lua.eval(f"{self.r}.yards.text"))
        lua.execute(f"units['{ROGUE}'].visible = false; fireGUID('UNIT_VISIBILITY_CHANGED', '{ROGUE}', false)")
        self.assertEqual(lua.eval(f"{self.r}.yards.text"), "")
        lua.execute(f"units['{ROGUE}'].visible = true; fireGUID('UNIT_VISIBILITY_CHANGED', '{ROGUE}', true);"
                    " settingsWindow.use('AutoBG_size', '10'); settingsWindow.use('AutoBG_size_yards', false); step(0.5)")
        self.assertEqual(lua.eval(f"{self.r}.yards.text"), "")
        self.assertFalse(lua.eval("AutoBGDB.sizes[15].yards == false"))

    def test_a_racial_switched_off_is_not_shown(self):
        lua = self.lua
        lua.execute("settingsWindow.use('AutoBG_racial_NightElf', false)")
        self.assertFalse(lua.eval(f"{self.r}.racial:IsShown()"))
        self.assertTrue(lua.eval("row(1).racial:IsShown()"))  # Ashka, a Human: Perception
        lua.execute("settingsWindow.defaults()")
        self.assertTrue(lua.eval(f"{self.r}.racial:IsShown()"))

    def test_raid_icons_borders_and_the_range_stripe(self):
        lua = self.lua
        lua.execute(f"units['{ROGUE}'].mark = 8; fire('RAID_TARGET_UPDATE')")
        self.assertEqual(lua.eval(f"{self.r}.mark.markIndex"), 8)
        lua.execute(f"setTarget('{ROGUE}')")
        self.assertEqual(lua.eval(f"{self.r}.edge.texture"), 1)
        self.assertTrue(lua.eval(f"{self.r}.edge:IsShown()"))
        lua.execute(f"units['{ROGUE}'].yards = 60; step(0.5)")
        self.assertTrue(lua.eval(f"{self.r}.stripe:IsShown()"))
        self.assertIn("1 in range", lua.eval("AutoBG_TargetsMainFrame10.title.text"))
        lua.execute(f"units['{ROGUE}'].yards = 90; step(0.5)")
        self.assertFalse(lua.eval(f"{self.r}.stripe:IsShown()"))

    def test_clicks_bind_the_guid_and_a_name_only_row_selects_by_name(self):
        lua = self.lua
        self.assertEqual(lua.eval(f"{self.r}:GetAttribute('unit')"), ROGUE)
        self.assertEqual(lua.eval(f"{self.r}:GetAttribute('type2')"), "focus")
        self.assertIsNone(lua.eval("row(1):GetAttribute('unit')"))
        lua.execute(f"enemy('{MAGE}', {{ name = 'Ashka', class = 'MAGE' }}); row(1):Click('LeftButton')")
        self.assertTrue(lua.eval("said('^target:Ashka$')"))

    def test_the_title_drags_only_out_of_combat(self):
        lua = self.lua
        lua.execute("fire('PLAYER_IN_COMBAT_CHANGED', true); run(AutoBG_TargetsMainFrame10, 'OnDragStart')")
        self.assertFalse(lua.eval("AutoBG_TargetsMainFrame10.moving"))
        lua.execute("fire('PLAYER_IN_COMBAT_CHANGED', false); run(AutoBG_TargetsMainFrame10, 'OnDragStart')")
        self.assertTrue(lua.eval("AutoBG_TargetsMainFrame10.moving"))


class Carriers(unittest.TestCase):
    def test_pickups_set_the_cards_and_drops_clear_them(self):
        lua = load()
        match(lua)
        seen(lua, ROGUE)
        lua.execute("line('The Horde flag was picked up by Thandril-NZ!', 'CHAT_MSG_BG_SYSTEM_ALLIANCE')")
        self.assertTrue(lua.eval("AutoBG_AllianceFC:IsShown()"))
        self.assertIn("Thandril", lua.eval("AutoBG_AllianceFC.name.text"))
        self.assertEqual(lua.eval("AutoBG_AllianceFC:GetAttribute('unit')"), ROGUE)
        lua.execute(f"units['{ROGUE}'].hp = 30; aura('{ROGUE}', 1, 'Focused Assault', 'HARMFUL'); units['{ROGUE}'].auras[1].applications = 3;"
                    f" fireGUID('UNIT_HEALTH', '{ROGUE}')")
        self.assertAlmostEqual(lua.eval("AutoBG_AllianceFC.health.value"), 0.3)
        self.assertIn("3x", lua.eval("AutoBG_AllianceFC.info.text"))
        lua.execute("SlashCmdList.AUTOBG('efc')")
        self.assertTrue(lua.eval("said('^target:Thandril%-NZ$')"))
        lua.execute("line('The Horde flag was dropped by Thandril-NZ!', 'CHAT_MSG_BG_SYSTEM_ALLIANCE')")
        self.assertFalse(lua.eval("AutoBG_AllianceFC:IsShown()"))

    def test_the_flags_placed_at_their_bases_clear_both(self):
        lua = load()
        match(lua)
        lua.execute("line('The Alliance flag was picked up by Grom!'); line('The Horde flag was picked up by Ashka!')")
        self.assertTrue(lua.eval("AutoBG_HordeFC:IsShown() and AutoBG_AllianceFC:IsShown()"))
        lua.execute("line('The flags are now placed at their bases.')")
        self.assertFalse(lua.eval("AutoBG_HordeFC:IsShown() or AutoBG_AllianceFC:IsShown()"))

    def test_joined_after_the_pickups_the_flags_they_wear_name_both(self):
        """2026-11-23, the player: joining with both flags out, the cards never
        showed, though the enemy carrier could be targeted. Fails on 59c79f4,
        which knew carriers only from the pickup lines."""
        lua = load()
        lua.execute("unit('0x0000000000000051', { name = 'Grom', player = true, inGroup = true, class = 'WARRIOR' });"
                    " tokens.raid2 = '0x0000000000000051'; aura('0x0000000000000051', 23335, 'Silverwing Flag')")
        match(lua)
        self.assertTrue(lua.eval("AutoBG_HordeFC:IsShown()"))
        self.assertIn("Grom", lua.eval("AutoBG_HordeFC.name.text"))
        self.assertFalse(lua.eval("AutoBG_AllianceFC:IsShown()"))
        lua.execute(f"enemy('{ROGUE}', {{ name = 'Thandril-NZ', class = 'ROGUE' }}); flagID = aura('{ROGUE}', 23333, 'Warsong Flag');"
                    f" setTarget('{ROGUE}')")
        self.assertTrue(lua.eval("AutoBG_AllianceFC:IsShown()"))
        self.assertEqual(lua.eval("AutoBG_AllianceFC:GetAttribute('unit')"), ROGUE)
        lua.execute(f"removeAura('{ROGUE}', flagID); auraEvent('{ROGUE}', nil, {{ flagID }})")
        self.assertFalse(lua.eval("AutoBG_AllianceFC:IsShown()"))
        self.assertTrue(lua.eval("AutoBG_HordeFC:IsShown()"))

    def test_a_card_with_no_guid_yet_selects_by_name_with_either_button(self):
        """2026-11-23, seen in play (Enemies.lua:58): a unit button's click with no
        verb reaches its handler with no arguments; it read self and button."""
        lua = load()
        match(lua)
        lua.execute("line('The Horde flag was picked up by Ashka!')")
        self.assertIsNone(lua.eval("AutoBG_AllianceFC:GetAttribute('unit')"))
        lua.execute(f"enemy('{MAGE}', {{ name = 'Ashka', class = 'MAGE' }}); AutoBG_AllianceFC:Click('RightButton')")
        self.assertTrue(lua.eval("said('^focus:Ashka$')"))

    def test_a_flag_picked_up_in_sight_of_the_group(self):
        lua = load()
        lua.execute("unit('0x0000000000000051', { name = 'Grom', player = true, inGroup = true }); tokens.raid2 = '0x0000000000000051'")
        match(lua)
        lua.execute("id = aura('0x0000000000000051', 23335, 'Silverwing Flag'); fire('UNIT_AURA_DELTA', 'raid2', { addedAuraInstanceIDs = { id } })")
        self.assertTrue(lua.eval("AutoBG_HordeFC:IsShown()"))
        lua.execute("enter('Arathi Basin'); fire('UNIT_AURA_DELTA', 'raid2', { addedAuraInstanceIDs = { id } })")
        self.assertFalse(lua.eval("AutoBG_HordeFC:IsShown()"))


class Scoreboard(unittest.TestCase):
    def test_names_in_class_colour_realm_left_off(self):
        lua = load()
        match(lua)
        lua.execute("WorldStateScoreFrame_Update()")
        self.assertIn("Thandril|r", lua.eval("WorldStateScoreButton1NameButtonName.text"))
        self.assertTrue(lua.eval("string.find(WorldStateScoreButton1NameButtonName.text, '^|cff') ~= nil"))
        self.assertNotIn("-NZ", lua.eval("WorldStateScoreButton1NameButtonName.text"))

    def test_each_update_colours_the_names_the_stock_code_wrote_again(self):
        """2026-11-23, fails on the first build: the stock update writes every name
        each time (WorldStateFrame.lua:493), and a name written once was skipped, so
        from the second update on the names were plain, with their realms."""
        stock = ("function WorldStateScoreFrame_Update() for i = 1, 3 do local s = scores[i];"
                 " if s then _G['WorldStateScoreButton' .. i .. 'NameButtonName']:SetText(s[1]) end end end")
        lua = load(setup=stock)
        match(lua)
        lua.execute("WorldStateScoreFrame_Update(); WorldStateScoreFrame_Update()")
        self.assertTrue(lua.eval("string.find(WorldStateScoreButton1NameButtonName.text, '^|cff.*Thandril|r$') ~= nil"))


class Preview(unittest.TestCase):
    def test_the_preview_shows_the_size_the_page_edits_and_ends_with_the_window(self):
        lua = load()
        lua.execute("settingsWindow.use('AutoBG_size', '15'); __addon_ns.Preview(true)")
        self.assertTrue(lua.eval("AutoBG_TargetsMainFrame15:IsShown()"))
        self.assertEqual(lua.eval("#__addon_ns.Enemies.roster"), 15)
        self.assertTrue(lua.eval("AutoBG_NodeFrame:IsShown() and AutoBG_SpyFrame:IsShown() and AutoBG_HordeFC:IsShown()"))
        lua.execute("SettingsPanel:Show(); SettingsPanel:Hide()")
        self.assertFalse(lua.eval("AutoBG_TargetsMainFrame15:IsShown() or AutoBG_NodeFrame:IsShown() or AutoBG_SpyFrame:IsShown()"))


if __name__ == "__main__":
    unittest.main()
