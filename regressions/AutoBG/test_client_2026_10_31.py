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
    def test_an_arena_uses_the_smallest_enemy_frames(self):
        import test_targets_guid_events as tge
        lua = tge.runtime()
        lua.execute('AutoBG_Targets:SetupButtonLayout(40)')
        lua.execute('function GetBattlefieldStatus(i) if i == 1 then return "active", "Arena" end return "none" end')
        lua.execute('ARENA = "Arena"; AutoBG_Targets:BattlefieldScoreUpdate(true)')
        self.assertEqual(lua.eval('AutoBG_Targets.currentSize'), 10)


if __name__ == "__main__":
    unittest.main()
