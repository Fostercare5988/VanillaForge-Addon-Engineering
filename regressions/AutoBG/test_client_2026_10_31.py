"""OctoWoW client 2026.10.31: Cross-Faction battlegrounds and arena queues.

Source: the client's FrameXML (tools/extract_framexml.py). BattlefieldFrame.lua
lists two reserved instance numbers after First Available, OCTO_BG_ROW_XF_ID
(9001, Cross-Faction) and OCTO_BG_ROW_FX_ID (9002, Factioned); a pick goes back
as the join's list index. Turtle_ArenaUI.lua: JoinArenaQueue(0) is Skirmish,
1-3 Rated 2v2/3v3/5v5, LeaveArenaQueue() leaves; the queue status names an
arena queue ARENA ("Arena"). The player chose: always Cross-Faction, and arena
queueing (Skirmish and rated) in Auto queue.

Fails on AutoBG 4a92a80, except the First Available fallback.
How the server answers a Skirmish request, the arena's instance type and its
zone name stay in-game checks.
"""
import unittest

import test_match_flow as core

CLIENT = r'''
ARENA = "Arena"
OCTO_BG_ROW_FA_ID, OCTO_BG_ROW_XF_ID, OCTO_BG_ROW_FX_ID = 9000, 9001, 9002
function AutoBG_QueueMap(map) return map end
function OctoBGQueueName(map, id)
    local labels = { [9000] = "First Available", [9001] = "Cross-Faction", [9002] = "Factioned" }
    if labels[id] then return map .. " (" .. labels[id] .. ")" end
    if id and id ~= 0 then return map .. " " .. id end
    return map
end
listed, shownMap = {}, "Warsong Gulch"
function GetNumBattlefields() return #listed end
function GetBattlefieldInstanceInfo(k) return listed[k] end
function GetBattlefieldInfo() return shownMap end
selected, joined = nil, {}
function SetSelectedBattlefield(k) selected = k end
function JoinBattlefield(k) table.insert(joined, k) end
function CloseBattlefield() end
function CloseDropDownMenus() end
function HideUIPanel() end
queued, arenaQueued, arenaLeft = {}, {}, 0
function JoinBattlegroundQueue(t) table.insert(queued, t) end
function JoinArenaQueue(t) table.insert(arenaQueued, t) end
function LeaveArenaQueue() arenaLeft = arenaLeft + 1 end
'''


def runtime():
    from lupa.lua51 import LuaRuntime
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(core.BASE + CLIENT)
    lua.execute(core.CORE)
    core.fire(lua, "ADDON_LOADED", "AutoBG")
    return lua


class CrossFactionTests(unittest.TestCase):
    def request(self, lua, bg="Warsong Gulch"):
        lua.execute('AutoBG_TriggerBattlegroundFinder(%r)' % bg)
        core.fire(lua, "BATTLEFIELDS_SHOW")

    def test_the_cross_faction_row_is_joined_when_listed(self):
        lua = runtime()
        lua.execute('listed = { 9001, 9002, 4 }')
        self.request(lua)
        self.assertEqual(lua.eval('joined[1]'), 1)
        self.assertEqual(lua.eval('selected'), 1)

    def test_first_available_when_the_row_is_not_listed(self):
        lua = runtime()
        lua.execute('listed = { 4, 7 }')
        self.request(lua)
        self.assertEqual(lua.eval('joined[1]'), 0)


class ArenaQueueTests(unittest.TestCase):
    def test_auto_queue_includes_the_chosen_arena(self):
        lua = runtime()
        lua.execute('AutoBG_Settings.AutoQueue_WSG, AutoBG_Settings.AutoQueue_AB, AutoBG_Settings.AutoQueue_AV = false, false, false')
        lua.execute('AutoBG_Settings.AutoQueue_Arena, AutoBG_Settings.ArenaType = true, 2')
        lua.execute('AutoBG_QueueAllBGs()')
        self.assertEqual(lua.eval('arenaQueued[1]'), 2)  # Rated 3v3

    def test_an_arena_queue_is_left_the_arena_way(self):
        lua = runtime()
        lua.execute('statuses[1] = { "queued", "Arena" }; statuses[2] = { "queued", "Warsong Gulch" }')
        lua.execute('AutoBG_CancelAllQueues()')
        self.assertEqual(lua.eval('arenaLeft'), 1)
        self.assertEqual(lua.eval('#ports'), 1)  # only the battleground goes through AcceptBattlefieldPort

    def test_slash_command_queues_the_chosen_arena(self):
        lua = runtime()
        lua.execute('AutoBG_Settings.ArenaType = 0; SlashCmdList.AUTOBG("q arena")')
        self.assertEqual(lua.eval('arenaQueued[1]'), 0)  # Skirmish

    def test_no_auto_release_in_an_arena(self):
        lua = runtime()
        lua.execute('''released = 0; function RepopMe() released = released + 1 end
            function HasSoulstone() return nil end
            pvp, zone = true, "Blood Ring"; statuses[1] = { "active", "Arena" }''')
        core.fire(lua, "PLAYER_ENTERING_WORLD")
        core.fire(lua, "PLAYER_DEAD")
        self.assertEqual(lua.eval('released'), 0)


class QueueBarTests(unittest.TestCase):
    def test_the_queue_bar_names_the_row(self):
        import test_timer_bars as ttb
        from lupa.lua51 import LuaRuntime
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute(ttb.BASE + CLIENT + '''
            AutoBG_Settings.QueueTimers = true
            function GetBattlefieldStatus(i) if i == 1 then return "queued", "Warsong Gulch", 9001 end return "none" end
            function GetBattlefieldTimeWaited() return 65000 end
            function GetBattlefieldEstimatedWaitTime() return 0 end
        ''')
        lua.execute(ttb.TIMERS)
        lua.execute('local f = AutoBG_TimersEventFrame; f.scripts.OnEvent(f, "UPDATE_BATTLEFIELD_STATUS")')
        self.assertEqual(lua.eval('AutoBG_QueueFrame.rows[1].labelFs.text'), "Warsong Gulch (Cross-Faction)")

    def test_no_spirit_healer_bar_in_an_arena(self):
        import test_timer_bars as ttb
        from lupa.lua51 import LuaRuntime
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute(ttb.BASE + CLIENT + '''
            AutoBG_Settings.RessTimer = true
            function GetNumRaidMembers() return 0 end
            function GetRealZoneText() return "Blood Ring" end
            function IsInInstance() return 1, "pvp" end
            function AutoBG_IsArenaZone() return true end
            function GetBattlefieldStatus(i) if i == 1 then return "active", "Arena", 0 end return "none" end
        ''')
        lua.execute(ttb.TIMERS)
        lua.execute('local f = AutoBG_TimersEventFrame; f.scripts.OnEvent(f, "PLAYER_ENTERING_WORLD")')
        self.assertFalse(lua.eval('AutoBG_RespawnFrame.rows[1].shown'))


class ArenaFrameTests(unittest.TestCase):
    def test_an_arena_has_its_own_enemy_frame_bracket(self):
        import test_targets_guid_events as tge
        lua = tge.runtime()
        lua.execute('function GetBattlefieldStatus(i) if i == 1 then return "active", "Arena" end return "none" end')
        lua.execute('ARENA = "Arena"; function AutoBG_IsArenaZone() return true end; AutoBG_Targets:BattlefieldScoreUpdate(true)')
        self.assertTrue(lua.eval('AutoBG_Targets.activeBG'))
        self.assertTrue(lua.eval('AutoBG_Targets.activeArena'))
        self.assertEqual(lua.eval('AutoBG_Targets.currentSize'), 5)
        self.assertEqual(lua.eval('AutoBG_Settings.Targets.ButtonWidth[5]'), 195)


    def test_an_enemy_seen_in_an_arena_joins_the_frames(self):
        # The scoreboard may not list the other team; a sighting must.
        import test_targets_guid_events as tge
        lua = tge.runtime(sighting=False)
        lua.execute('''ARENA = "Arena"
            function AutoBG_IsArenaZone() return true end
            function GetBattlefieldStatus(i) if i == 1 then return "active", "Arena" end return "none" end
            function UnitCanAttack() return true end
            function UnitClass() return "Warrior", "WARRIOR" end
            AutoBG_Targets:BattlefieldScoreUpdate(true)
            target = "Grom"''')
        lua.execute('AutoBG_Targets.scripts.OnEvent(AutoBG_Targets, "PLAYER_TARGET_CHANGED")')
        self.assertEqual(lua.eval('AutoBG_TargetButton1.targetName'), "Grom")


    def test_the_scoreboard_does_not_pick_arena_opponents(self):
        # Cross-faction: a team mixes factions, so only a sighting you can
        # attack lists an opponent in an arena.
        import test_targets_guid_events as tge
        lua = tge.runtime(sighting=False)
        lua.execute('''ARENA = "Arena"
            function AutoBG_IsArenaZone() return true end
            function GetBattlefieldStatus(i) if i == 1 then return "active", "Arena" end return "none" end
            AutoBG_Targets:BattlefieldScoreUpdate(true)''')
        self.assertEqual(lua.eval('AutoBG_Targets.EnemyCount()'), 0)


    def test_an_enemy_a_teammate_targets_joins_the_frames(self):
        # The server lists only your own team, so the enemies your team looks at count.
        import test_targets_guid_events as tge
        lua = tge.runtime(sighting=False)
        lua.execute('''ARENA = "Arena"
            function AutoBG_IsArenaZone() return true end
            function GetBattlefieldStatus(i) if i == 1 then return "active", "Arena" end return "none" end
            function UnitCanAttack() return true end
            function UnitClass() return "Warrior", "WARRIOR" end
            AutoBG_Targets:BattlefieldScoreUpdate(true)
            local exists, name = UnitExists, UnitName
            function UnitExists(u) return u == "party1target" or exists(u) end
            function UnitName(u) if u == "party1target" then return "Grom" end return name(u) end
            for _, tick in ipairs(tickers) do tick() end''')
        self.assertEqual(lua.eval('(AutoBG_Targets.GetEnemy(1))'), "Grom")

    def test_unitxp_steps_through_the_enemies_and_clears_the_target(self):
        import test_targets_guid_events as tge
        lua = tge.runtime(sighting=False)
        lua.execute('''ARENA = "Arena"
            function AutoBG_IsArenaZone() return true end
            function GetBattlefieldStatus(i) if i == 1 then return "active", "Arena" end return "none" end
            function UnitCanAttack() return true end
            function UnitClass() return "Warrior", "WARRIOR" end
            AutoBG_Targets:BattlefieldScoreUpdate(true)
            local names, i = { "Grom", "Thrall", "Rexxar" }, 0
            local exists, name, guid = UnitExists, UnitName, UnitGUID
            function UnitExists(u) if u == "target" then return target ~= nil end return exists(u) end
            function UnitName(u) if u == "target" then return target end return name(u) end
            function UnitGUID(u) if u == "target" then return target and ("0x" .. target) end return guid(u) end
            function ClearTarget() target = nil end
            function UnitXP(a, b)
                i = i % 3 + 1
                target = names[i]
                return true
            end
            for _, tick in ipairs(tickers) do tick() end''')
        self.assertEqual(lua.eval('AutoBG_Targets.EnemyCount()'), 3)
        self.assertIsNone(lua.eval('target'))

    def test_the_sweep_leaves_your_own_target_alone(self):
        import test_targets_guid_events as tge
        lua = tge.runtime(sighting=False)
        lua.execute('''ARENA = "Arena"
            function AutoBG_IsArenaZone() return true end
            function GetBattlefieldStatus(i) if i == 1 then return "active", "Arena" end return "none" end
            AutoBG_Targets:BattlefieldScoreUpdate(true)
            target = "Mine"; moved = false
            function UnitXP() moved = true; return true end
            for _, tick in ipairs(tickers) do tick() end''')
        self.assertFalse(lua.eval('moved'))

    def test_a_queue_status_that_lingers_after_leaving_is_not_an_arena(self):
        import test_targets_guid_events as tge
        lua = tge.runtime(sighting=False)
        lua.execute('''ARENA = "Arena"
            function AutoBG_IsArenaZone() return false end
            function GetBattlefieldStatus(i) if i == 1 then return "active", "Arena" end return "none" end
            AutoBG_Targets:BattlefieldScoreUpdate(true)''')
        self.assertFalse(lua.eval('AutoBG_Targets.activeBG'))


class LateEnemyTests(unittest.TestCase):
    def test_a_player_who_was_not_an_enemy_at_first_is_looked_at_again(self):
        # Seen once before the match was known, a hostile player must not stay ignored.
        import test_targets_guid_events as tge
        lua = tge.runtime(sighting=False)
        lua.execute('''ARENA = "Arena"
            function AutoBG_IsArenaZone() return true end
            function GetBattlefieldStatus(i) if i == 1 then return "active", "Arena" end return "none" end
            hostile = false
            guidNames["0x0000000000000042"] = "Grom"
            function UnitCanAttack() return hostile end
            function UnitClass() return "Rogue", "ROGUE" end
            AutoBG_Targets:BattlefieldScoreUpdate(true)''')
        tge.fire(lua, "UNIT_HEALTH_GUID", "0x0000000000000042")
        self.assertEqual(lua.eval('AutoBG_Targets.EnemyCount()'), 0)
        lua.execute('hostile = true; NOW = 1006')
        tge.fire(lua, "UNIT_HEALTH_GUID", "0x0000000000000042")
        self.assertEqual(lua.eval('AutoBG_Targets.EnemyCount()'), 1)


class ArenaPetTests(unittest.TestCase):
    """Enemy pets are listed in arenas only."""

    def setup(self, arena=True):
        import test_targets_guid_events as tge
        from addon_loader import ROOT, load
        lua = tge.runtime(sighting=False)
        lua.execute('''ARENA = "Arena"
            function AutoBG_IsArenaZone() return %s end
            function GetBattlefieldStatus(i) if i == 1 then return "active", "%s" end return "none" end
            function UnitExists(u) return u ~= "gone" end
            function UnitIsMinion(u) return u == "0xF140000000000001" or u == "0xF140000000000002" end
            function UnitCreatureType(u) if u == "0xF140000000000002" then return "Totem" end return "Demon" end
            function UnitOwnerGUID() return "0x0000000000000099" end
            function UnitName(u) if u == "0x0000000000000099" then return "Spanthout" end return "Felguard" end
            timers = {}
            C_Timer.NewTimer = function(_, fn) table.insert(timers, fn); return { Cancel = function() end } end
            AutoBG_Targets:BattlefieldScoreUpdate(true)''' % ("true" if arena else "false", "Arena" if arena else "Warsong Gulch"))
        load(lua, (ROOT / "AutoBG_ArenaPets.lua").read_text("utf-8-sig"), "AutoBG_ArenaPets.lua")
        lua.execute('AutoBG_Targets:BattlefieldScoreUpdate(true); AutoBG_Targets.MainFrame.GetWidth = function() return 150 end')
        return lua

    def health(self, lua, guid):
        lua.execute('AutoBG_ArenaPetsListener.scripts.OnEvent(AutoBG_ArenaPetsListener, "UNIT_HEALTH_GUID", "%s")' % guid)

    def test_an_enemy_pet_is_listed_with_its_owner(self):
        lua = self.setup()
        self.health(lua, "0xF140000000000001")
        self.assertEqual(lua.eval('AutoBG_ArenaPets.Count()'), 1)
        lua.execute('for _, fn in ipairs(timers) do fn() end')
        self.assertEqual(lua.eval('AutoBG_ArenaPet1.Name.text'), "Felguard |cffaaaaaaSpanthout|r")

    def test_a_totem_and_a_player_are_not_pets(self):
        lua = self.setup()
        self.health(lua, "0xF140000000000002")
        self.health(lua, "0x0000000000000042")
        self.assertEqual(lua.eval('AutoBG_ArenaPets.Count()'), 0)

    def test_a_new_pet_replaces_the_old_one_of_the_same_owner(self):
        lua = self.setup()
        lua.execute('function UnitIsMinion() return true end')
        self.health(lua, "0xF140000000000001")
        self.health(lua, "0xF140000000000003")
        self.assertEqual(lua.eval('AutoBG_ArenaPets.Count()'), 1)

    def test_nothing_is_listed_in_a_battleground(self):
        lua = self.setup(arena=False)
        self.health(lua, "0xF140000000000001")
        self.assertEqual(lua.eval('AutoBG_ArenaPets.Count()'), 0)


class ArenaExtrasTests(unittest.TestCase):
    """The power bar, the icon strip, the drinking alert and the callouts."""
    GUID = "0x0000000000000042"

    def setup(self):
        import test_targets_guid_events as tge
        from addon_loader import ROOT, load
        lua = tge.runtime(sighting=False)
        lua.execute('''ARENA = "Arena"
            function AutoBG_IsArenaZone() return true end
            function GetBattlefieldStatus(i) if i == 1 then return "active", "Arena" end return "none" end
            guidNames["0x0000000000000042"] = "Grom"
            names = { [11] = "Blink", [12] = "Frostbolt", [77] = "Drink", [88] = "Shadow Sight", [99] = "Power Word: Shield" }
            function GetSpellInfo(id) return names[id], nil, "Icon" .. id end
            mana = { cur = 30, max = 100 }
            function UnitMana() return mana.cur end
            function UnitManaMax() return mana.max end
            function UnitPowerType() return 0 end
            said, errors, sounds, shadow = {}, {}, {}, {}
            function SendChatMessage(text, channel) table.insert(said, channel .. ": " .. text) end
            UIErrorsFrame = { AddMessage = function(_, text) table.insert(errors, text) end }
            function PlaySound(name) table.insert(sounds, name) end
            function AutoBG_Timers_ShadowSight(who, enemy) table.insert(shadow, who .. (enemy and " enemy" or "")) end
            function UnitCanAttack() return true end
            function UnitClass() return "Mage", "MAGE" end
            getmetatable(UIParent).__index.SetTexture = function(self, t) self.texture = t end''')
        load(lua, (ROOT / "AutoBG_Arena.lua").read_text("utf-8-sig"), "AutoBG_Arena.lua")
        lua.execute('AutoBG_Targets:BattlefieldScoreUpdate(true)')
        tge.fire(lua, "UNIT_HEALTH_GUID", self.GUID)
        lua.execute('for i = 1, 5 do AutoBG_TargetButton1.GetWidth = function() return 150 end end')
        return lua

    def event(self, lua, ev, *args):
        values = ", ".join(repr(a) if isinstance(a, str) else str(a) for a in args)
        lua.execute('AutoBG_ArenaListener.scripts.OnEvent(AutoBG_ArenaListener, "%s", %s)' % (ev, values))

    def test_the_power_bar_follows_the_enemy_power(self):
        lua = self.setup()
        lua.execute('AutoBG_Arena.Tick()')
        self.assertTrue(lua.eval('AutoBG_TargetButton1.PowerBar.shown'))

    def test_an_instant_ability_gets_an_icon_but_a_cast_time_spell_does_not(self):
        lua = self.setup()
        self.event(lua, "UNIT_CASTEVENT", self.GUID, "x", "START", 12)
        self.event(lua, "UNIT_CASTEVENT", self.GUID, "x", "CAST", 12)
        self.event(lua, "UNIT_CASTEVENT", self.GUID, "x", "CAST", 11)
        lua.execute('AutoBG_Arena.Tick()')
        self.assertEqual(lua.eval('AutoBG_TargetButton1.Strip.slots[1].Icon.texture'), "Icon11")
        self.assertFalse(lua.eval('AutoBG_TargetButton1.Strip.slots[2].shown'))

    def test_more_abilities_than_the_list_holds_do_not_break_it(self):
        # table.remove leaves a length counter in this Lua; the full list must not use it.
        lua = self.setup()
        lua.execute('for id = 100, 120 do names[id] = "Spell" .. id end')
        for spell in range(100, 121):
            self.event(lua, "UNIT_CASTEVENT", self.GUID, "x", "CAST", spell)
        lua.execute('AutoBG_Arena.Tick()')
        self.assertTrue(lua.eval('AutoBG_TargetButton1.Strip.slots[1].shown'))

    def test_a_used_again_and_again_spell_is_hidden(self):
        lua = self.setup()
        for _ in range(3):
            self.event(lua, "UNIT_CASTEVENT", self.GUID, "x", "CAST", 11)
        lua.execute('AutoBG_Arena.Tick()')
        self.assertFalse(lua.eval('AutoBG_TargetButton1.Strip.slots[1].shown'))

    def test_a_buff_gained_later_shows_and_one_at_first_sight_does_not(self):
        lua = self.setup()
        self.event(lua, "UNIT_CASTEVENT", self.GUID, "x", "CAST", 11)
        self.event(lua, "BUFF_ADDED_OTHER", self.GUID, 1, 99, 1, 60, 0, 0)
        lua.execute('AutoBG_Arena.Tick()')
        self.assertEqual(lua.eval('AutoBG_TargetButton1.Strip.slots[1].Icon.texture'), "Icon11")
        lua.execute('NOW = 1003')
        self.event(lua, "BUFF_ADDED_OTHER", self.GUID, 1, 99, 1, 60, 0, 0)
        lua.execute('AutoBG_Arena.Tick()')
        self.assertEqual(lua.eval('AutoBG_TargetButton1.Strip.slots[1].Icon.texture'), "Icon99")

    def test_an_enemy_drinking_is_announced(self):
        lua = self.setup()
        self.event(lua, "UNIT_CASTEVENT", self.GUID, "x", "CAST", 11)
        lua.execute('NOW = 1003')
        self.event(lua, "BUFF_ADDED_OTHER", self.GUID, 1, 77, 1, 60, 0, 0)
        self.assertEqual(list(lua.eval('errors').values()), ["Grom is drinking!"])
        self.assertEqual(list(lua.eval('sounds').values()), ["RaidWarning"])

    def test_callouts_are_off_until_switched_on_and_say_each_thing_once(self):
        lua = self.setup()
        lua.execute('health.hp = 800; raidSize = 5')
        self.event(lua, "UNIT_HEALTH_GUID", self.GUID)
        self.assertEqual(lua.eval('#said'), 0)
        lua.execute('AutoBG_ArenaOptions().Callouts = true')
        self.event(lua, "UNIT_HEALTH_GUID", self.GUID)
        self.event(lua, "UNIT_HEALTH_GUID", self.GUID)
        self.event(lua, "UNIT_DIED", self.GUID)
        self.event(lua, "UNIT_DIED", self.GUID)
        self.assertEqual(list(lua.eval('said').values()), ["RAID: Grom is LOW (20%)", "RAID: Grom is DEAD"])

    def test_a_shadow_sight_pickup_goes_to_the_timers(self):
        lua = self.setup()
        self.event(lua, "BUFF_ADDED_OTHER", self.GUID, 1, 88, 1, 60, 0, 0)
        self.assertEqual(list(lua.eval('shadow').values()), ["Grom enemy"])

    def test_nothing_is_decorated_outside_an_arena(self):
        lua = self.setup()
        lua.execute('AutoBG_Arena.Tick(); AutoBG_Arena.SetActive(false)')
        self.assertFalse(lua.eval('AutoBG_TargetButton1.Strip.shown'))


class ShadowSightTests(unittest.TestCase):
    def runtime(self):
        import test_timer_bars as ttb
        from lupa.lua51 import LuaRuntime
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute(ttb.BASE + '''
            function GetRealZoneText() return "Blood Ring" end
            function IsInInstance() return 1, "pvp" end
            function AutoBG_IsArenaZone() return true end
            function AutoBG_ArenaOptions() return { ShadowSight = true } end''')
        lua.execute(ttb.TIMERS)
        lua.execute('local f = AutoBG_TimersEventFrame; f.scripts.OnEvent(f, "PLAYER_ENTERING_WORLD")')
        return lua

    def test_the_orbs_are_timed_from_the_start_of_the_round_and_a_pickup_adds_the_rest(self):
        lua = self.runtime()
        lua.execute('local f = AutoBG_TimersEventFrame; f.scripts.OnEvent(f, "CHAT_MSG_BG_SYSTEM_NEUTRAL", "The Arena battle has begun!")')
        self.assertEqual(lua.eval('AutoBG_ShadowSightFrame.rows[1].labelFs.text'), "Orbs appear")
        lua.execute('AutoBG_Timers_ShadowSight("Grom", true)')
        self.assertEqual(lua.eval('AutoBG_ShadowSightFrame.rows[1].labelFs.text'), "Shadow Sight: Grom (enemy)")
        self.assertEqual(lua.eval('AutoBG_ShadowSightFrame.rows[2].labelFs.text'), "Orb back")
        self.assertIsNone(lua.eval('AutoBG_ShadowSightFrame.rows[3].labelFs.text'))


class CrossFactionBattlegroundTests(unittest.TestCase):
    """Teams mix factions: a roster name you cannot attack is a teammate."""

    def test_a_teammate_on_the_enemy_side_of_the_scoreboard_leaves_the_list(self):
        import test_targets_guid_events as tge
        lua = tge.runtime(sighting=False)
        lua.execute('function UnitCanAttack() return false end; target = "Grom"')
        lua.execute('AutoBG_Targets.scripts.OnEvent(AutoBG_Targets, "PLAYER_TARGET_CHANGED")')
        self.assertEqual(lua.eval('AutoBG_Targets.EnemyCount()'), 0)

    def test_an_attackable_player_the_scoreboard_missed_joins_the_list(self):
        import test_targets_guid_events as tge
        lua = tge.runtime(sighting=False)
        lua.execute('''function UnitClass() return "Mage", "MAGE" end
            target = "Zed"''')
        lua.execute('AutoBG_Targets.scripts.OnEvent(AutoBG_Targets, "PLAYER_TARGET_CHANGED")')
        self.assertEqual(lua.eval('AutoBG_Targets.EnemyCount()'), 2)


class ArenaSpyTests(unittest.TestCase):
    """Spy rests in the arenas (2v2, 3v3, 5v5) and in battlegrounds: the enemy frames own them."""

    def sighting(self, instance, zone=None):
        from test_spy_nearby import advance, runtime
        lua = runtime()
        # The shared zone helper from AutoBG.lua, with the OctoWoW arena names.
        lua.execute('''
            local zones = { ["lordaeron arena"] = true, ["sunstrider court"] = true, ["blood ring"] = true }
            function AutoBG_IsArenaZone()
                local inInstance, t = IsInInstance()
                return (inInstance and t == "arena") or zones[string.lower(GetRealZoneText())] == true
            end
        ''')
        if zone:
            lua.execute('zoneName = "%s"' % zone)
        lua.execute('function IsInInstance() return 1, "%s" end' % instance)
        from test_spy_nearby import fire
        fire(lua, "PLAYER_ENTERING_WORLD")
        lua.execute('AutoBG_Spy:RecordEnemy("Grom", "WARRIOR", 60, "0x0000000000000001", 100, nil, nil, "Orc")')
        advance(lua, 1)
        return lua.eval('AutoBG_Spy.Frame.shown') and True or False

    def test_spy_stays_off_in_each_arena(self):
        self.assertFalse(self.sighting("arena", "Lordaeron Arena"))
        self.assertFalse(self.sighting("pvp", "Sunstrider Court"))
        self.assertFalse(self.sighting("pvp", "Blood Ring"))

    def test_spy_stays_off_in_a_battleground(self):
        self.assertFalse(self.sighting("pvp", "Warsong Gulch"))


if __name__ == "__main__":
    unittest.main()
