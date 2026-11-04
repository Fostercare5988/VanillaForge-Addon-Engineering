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
        lua.execute('ARENA = "Arena"; AutoBG_Targets:BattlefieldScoreUpdate(true)')
        self.assertTrue(lua.eval('AutoBG_Targets.activeBG'))
        self.assertTrue(lua.eval('AutoBG_Targets.activeArena'))
        self.assertEqual(lua.eval('AutoBG_Targets.currentSize'), 5)
        self.assertEqual(lua.eval('AutoBG_Settings.Targets.ButtonWidth[5]'), 195)


    def test_an_enemy_seen_in_an_arena_joins_the_frames(self):
        # The scoreboard may not list the other team; a sighting must.
        import test_targets_guid_events as tge
        lua = tge.runtime(sighting=False)
        lua.execute('''ARENA = "Arena"
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
            function GetBattlefieldStatus(i) if i == 1 then return "active", "Arena" end return "none" end
            AutoBG_Targets:BattlefieldScoreUpdate(true)''')
        self.assertEqual(lua.eval('AutoBG_Targets.EnemyCount()'), 0)


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
    """Spy works in the arenas (2v2, 3v3, 5v5) and stays off in battlegrounds."""

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

    def test_spy_lists_enemies_in_each_arena(self):
        self.assertTrue(self.sighting("arena", "Lordaeron Arena"))
        self.assertTrue(self.sighting("pvp", "Sunstrider Court"))
        self.assertTrue(self.sighting("pvp", "Blood Ring"))

    def test_spy_stays_off_in_a_battleground(self):
        self.assertFalse(self.sighting("pvp", "Warsong Gulch"))


if __name__ == "__main__":
    unittest.main()
