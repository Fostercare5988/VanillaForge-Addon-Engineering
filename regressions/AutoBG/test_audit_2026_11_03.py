"""Audit 2026-11-03: bugs found reading the code and the saved settings.

Each test fails on AutoBG 2b10a35.
- "/abg t" toggled only the saved TestAllTimers flag: timers and carrier
  frames went into preview, the enemy frames, Spy and the flag card did not,
  and the flag was written to SavedVariables.
- Leaving a queue during a delayed auto-enter printed "the invite ended ...
  Lower the enter delay", which blames the delay for the player's own click.
- Spy recorded enemies inside a battleground while the queue status was not
  "active" (after leaving, before the loading screen): the saved stats hold
  "Mayve-NZ" met in Alterac Valley.
"""
import unittest

import test_match_flow as core
import test_spy_nearby as spy


class PreviewCommandTests(unittest.TestCase):
    def setUp(self):
        self.lua = core.runtime()
        self.lua.execute('''
            previews = {}
            previewOn = false
            function AutoBG_IsPreviewActive() return previewOn end
            function AutoBG_SetPreview(on) previewOn = on; table.insert(previews, on) end
        ''')

    def test_short_test_command_uses_the_one_preview_switch(self):
        self.lua.execute('SlashCmdList.AUTOBG("t")')
        self.assertEqual(self.lua.eval('previews[1]'), True)
        self.assertIsNone(self.lua.eval('AutoBG_Settings.TestAllTimers'))

    def test_long_test_command_toggles_it_back(self):
        self.lua.execute('SlashCmdList.AUTOBG("test"); SlashCmdList.AUTOBG("test")')
        self.assertEqual(self.lua.eval('previews[2]'), False)


class LeftQueueTests(unittest.TestCase):
    def pop(self):
        lua = core.runtime()
        lua.execute('AutoBG_Settings.AutoAccept = true; AutoBG_Settings.AutoAcceptDelay = 30')
        lua.execute('statuses[1] = { "confirm", "Arathi Basin" }')
        core.fire(lua, "UPDATE_BATTLEFIELD_STATUS")
        return lua

    def ran_out_messages(self, lua):
        lua.execute('m = 0; for _, s in ipairs(messages) do if string.find(s, "ended after") then m = m + 1 end end')
        return lua.eval('m')

    def test_leaving_the_queue_is_not_reported_as_a_missed_enter(self):
        lua = self.pop()
        lua.execute('now = now + 12')
        # The minimap's Leave Queue calls AcceptBattlefieldPort(id) with no accept.
        lua.execute('AcceptBattlefieldPort(1); if hooks.AcceptBattlefieldPort then hooks.AcceptBattlefieldPort(1) end')
        lua.execute('statuses[1] = nil')
        core.fire(lua, "UPDATE_BATTLEFIELD_STATUS")
        self.assertEqual(self.ran_out_messages(lua), 0)

    def test_an_invite_that_runs_out_is_still_reported(self):
        lua = self.pop()
        lua.execute('now = now + 25; statuses[1] = nil')
        core.fire(lua, "UPDATE_BATTLEFIELD_STATUS")
        self.assertEqual(self.ran_out_messages(lua), 1)


class SpyBattlegroundTests(unittest.TestCase):
    def test_no_sightings_inside_a_battleground_instance(self):
        lua = spy.runtime()
        lua.execute('function IsInInstance() return 1, "pvp" end; zoneName = "Alterac Valley"')
        spy.fire(lua, "PLAYER_ENTERING_WORLD")
        # The queue status already left "active": the enemy frames are off.
        lua.execute('AutoBG_Targets.activeBG = false; names["0x0000000000000002"] = "Mayve-NZ"')
        spy.fire(lua, "UNIT_CASTEVENT", "0x0000000000000002", "0x0000000000000000", "CAST", 1234, 0)
        lua.execute('AutoBG_Spy:RenderRows()')
        self.assertFalse(lua.eval('AutoBG_SpyFrame.shown'))
        self.assertIsNone(lua.eval('AutoBG_Settings.Spy.Stats and AutoBG_Settings.Spy.Stats["mayve-nz"]'))


class MovedPathTests(unittest.TestCase):
    """Paths the 2026-11-03 cleanup moved; these pass on the old code too."""

    def test_match_end_lines_are_read_only_in_a_battleground(self):
        from wowlua import LuaRuntime
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute(core.BASE)
        lua.execute(core.CORE)
        lua.execute('''
            registered = {}
            function AutoBGFrame:RegisterEvent(e) registered[e] = true end
            function AutoBGFrame:UnregisterEvent(e) registered[e] = nil end
        ''')
        core.fire(lua, "ADDON_LOADED", "AutoBG")
        self.assertIsNone(lua.eval('registered.CHAT_MSG_SYSTEM'))
        lua.execute('pvp, zone = true, "Warsong Gulch"')
        core.fire(lua, "PLAYER_ENTERING_WORLD")
        self.assertTrue(lua.eval('registered.CHAT_MSG_BG_SYSTEM_HORDE and registered.CHAT_MSG_SYSTEM'))
        lua.execute('pvp, zone = false, "Orgrimmar"')
        core.fire(lua, "PLAYER_ENTERING_WORLD")
        self.assertIsNone(lua.eval('registered.CHAT_MSG_SYSTEM'))

    def test_a_name_with_no_queue_says_so(self):
        lua = core.runtime()
        lua.execute('queued = {}; function JoinBattlegroundQueue(t) table.insert(queued, t) end')
        lua.execute('AutoBG_TriggerBattlegroundFinder("Blood Ring")')
        self.assertEqual(lua.eval('#queued'), 0)
        lua.execute('AutoBG_TriggerBattlegroundFinder("tg")')
        self.assertEqual(lua.eval('queued[1]'), "ThornGorge")

    def test_old_targets_leftovers_are_cleared(self):
        import test_targets_guid_events as targets
        lua = targets.runtime()
        lua.execute('''
            AutoBG_Settings.Targets.pos = {}
            AutoBG_Settings.Targets.Spy = { Enabled = true }
            AutoBG_Settings.Targets.IndependentPositionsVersion = 1
            AutoBG_Settings.Positions = { AutoBG_TargetsMainFrame = { x = 1 }, AutoBG_TargetsMainFrame10 = { x = 2 } }
            AutoBG_Targets:EnsureOptions()
        ''')
        self.assertIsNone(lua.eval('AutoBG_Settings.Targets.pos or AutoBG_Settings.Targets.Spy or AutoBG_Settings.Targets.IndependentPositionsVersion'))
        self.assertIsNone(lua.eval('AutoBG_Settings.Positions.AutoBG_TargetsMainFrame'))
        self.assertEqual(lua.eval('AutoBG_Settings.Positions.AutoBG_TargetsMainFrame10.x'), 2)


class CarrierEventTests(unittest.TestCase):
    """Carrier health follows NamPower UNIT_HEALTH_GUID; a 0.5 s ticker finds
    the unit and reads the distance (it was a 0.15 s poll of everything)."""

    def runtime(self):
        import test_carrier_health as tch
        from wowlua import LuaRuntime
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute(tch.BASE + '''
            hp, maxHp = 3690, 4500
            intervals, registered = {}, {}
            C_Timer.NewTicker = function(s) table.insert(intervals, s); return { Cancel = function() end } end
        ''')
        lua.execute(tch.FC)
        lua.execute('''
            function AutoBG_FCEventFrame:RegisterEvent(e) registered[e] = true end
            function AutoBG_FCEventFrame:UnregisterEvent(e) registered[e] = nil end
        ''')
        lua.execute('local f = AutoBG_FCEventFrame; f.scripts.OnEvent(f, "PLAYER_ENTERING_WORLD")')
        lua.execute('local f = AutoBG_FCEventFrame; f.scripts.OnEvent(f, "CHAT_MSG_BG_SYSTEM_HORDE", "The Horde flag was picked up by Grom!")')
        lua.execute('AutoBG_FC_UpdateVisibility()')
        return lua

    def test_health_event_updates_the_carrier_at_once(self):
        lua = self.runtime()
        self.assertTrue(lua.eval('registered.UNIT_HEALTH_GUID'))
        self.assertEqual(lua.eval('intervals[1]'), 0.5)
        lua.execute('hp = 900; local f = AutoBG_FCEventFrame; f.scripts.OnEvent(f, "UNIT_HEALTH_GUID", "0x00000000000000C3", 0, 0, 0, 0, 0, 3)')
        self.assertEqual(lua.eval('AutoBG_AllianceFC.hpText.text'), "900 / 4500")

    def test_other_units_health_is_ignored(self):
        lua = self.runtime()
        lua.execute('hp = 900; local f = AutoBG_FCEventFrame; f.scripts.OnEvent(f, "UNIT_HEALTH_GUID", "0x0000000000000099", 0, 0, 0, 0, 0, 0)')
        self.assertEqual(lua.eval('AutoBG_AllianceFC.hpText.text'), "3690 / 4500")

    def test_no_health_events_without_a_carrier(self):
        lua = self.runtime()
        lua.execute('local f = AutoBG_FCEventFrame; f.scripts.OnEvent(f, "CHAT_MSG_BG_SYSTEM_ALLIANCE", "The Horde flag was dropped by Grom!")')
        self.assertIsNone(lua.eval('registered.UNIT_HEALTH_GUID'))


class TimerEventTests(unittest.TestCase):
    def runtime(self, zone, pvp):
        import test_timer_bars as ttb
        from wowlua import LuaRuntime
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute(ttb.BASE + '''
            function GetRealZoneText() return "%s" end
            function IsInInstance() return %s end
            registered = {}
        ''' % (zone, '1, "pvp"' if pvp else 'nil, "none"'))
        lua.execute(ttb.TIMERS)
        lua.execute('''
            function AutoBG_TimersEventFrame:RegisterEvent(e) registered[e] = true end
            function AutoBG_TimersEventFrame:UnregisterEvent(e) registered[e] = nil end
            local f = AutoBG_TimersEventFrame; f.scripts.OnEvent(f, "PLAYER_ENTERING_WORLD")
        ''')
        return lua

    def test_battleground_lines_are_read_only_in_a_battleground(self):
        self.assertIsNone(self.runtime("Orgrimmar", False).eval('registered.CHAT_MSG_MONSTER_YELL'))
        self.assertTrue(self.runtime("Alterac Valley", True).eval('registered.CHAT_MSG_MONSTER_YELL'))

    def test_a_captured_flag_starts_its_return_row(self):
        lua = self.runtime("Warsong Gulch", True)
        lua.execute('local f = AutoBG_TimersEventFrame; f.scripts.OnEvent(f, "CHAT_MSG_BG_SYSTEM_ALLIANCE", "Tester captured the Horde flag!")')
        self.assertEqual(lua.eval('AutoBG_WSGFlagFrame.rows[1].labelFs.text'), "Horde Flag")
        self.assertEqual(lua.eval('AutoBG_WSGFlagFrame.rows[1].timeFs.text'), "23")

    def test_the_preview_is_never_saved(self):
        lua = self.runtime("Orgrimmar", False)
        lua.execute('AutoBG_Timers_SetPreview(true); AutoBG_Timers_UpdateVisibility()')
        self.assertTrue(lua.eval('AutoBG_NodeFrame.shown'))
        self.assertIsNone(lua.eval('AutoBG_Settings.TestAllTimers'))


class EnemyFrameEventTests(unittest.TestCase):
    def runtime(self):
        import test_targets_guid_events as tge
        lua = tge.runtime()
        lua.execute('clock = 1000; function GetTime() return clock end')
        return lua, tge

    def test_unit_spellcast_succeeded_is_not_registered(self):
        # UNIT_CASTEVENT already reports every cast, instants included.
        import test_targets_guid_events as tge
        from wowlua import LuaRuntime
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute(tge.BASE + 'unitEvents = {}')
        lua.execute('''local w = getmetatable(CreateFrame("Frame")).__index
            function w:RegisterUnitEvent(e) unitEvents[e] = true end''')
        tge.addon_loader.load(lua, tge.TARGETS, "AutoBG_Targets.lua")
        lua.execute('AutoBG_Targets.scripts.OnEvent(AutoBG_Targets, "PLAYER_LOGIN")')
        lua.execute('AutoBG_Targets.scripts.OnEvent(AutoBG_Targets, "UPDATE_BATTLEFIELD_STATUS")')
        self.assertTrue(lua.eval('unitEvents.UNIT_AURA_DELTA'))
        self.assertIsNone(lua.eval('unitEvents.UNIT_SPELLCAST_SUCCEEDED'))

    def test_a_creatures_swings_are_looked_up_once(self):
        lua, tge = self.runtime()
        lua.execute('''nameCalls = 0
            local unitName = UnitName
            function UnitName(u) nameCalls = nameCalls + 1; return unitName(u) end''')
        for _ in range(5):
            tge.fire(lua, "UNIT_CASTEVENT", "0xF130000000000077", "", "MAINHAND", 0, 0)
        self.assertEqual(lua.eval('nameCalls'), 0)  # not a player GUID: no name asked
        lua.execute('guidNames["0x0000000000000099"] = "Stranger"')
        for _ in range(5):
            tge.fire(lua, "UNIT_CASTEVENT", "0x0000000000000099", "", "MAINHAND", 0, 0)
        self.assertEqual(lua.eval('nameCalls'), 1)

    def test_potion_stealth_ends_on_the_half_second_ticker(self):
        lua, tge = self.runtime()
        tge.fire(lua, "BUFF_ADDED_OTHER", tge.GROM, 1, 11392, 1, 60, 5, 0)
        self.assertEqual(tge.row_text(lua), "|cff00ffffINVIS POT|r")
        lua.execute('clock = clock + 19; for _, fn in ipairs(tickers) do fn() end')
        self.assertEqual(tge.row_text(lua), "100%")


class SpyEventTests(unittest.TestCase):
    def test_unit_spellcast_succeeded_is_not_registered(self):
        from wowlua import LuaRuntime
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute(spy.BASE + 'unitEvents = {}')
        lua.execute('''local w = getmetatable(CreateFrame("Frame")).__index
            function w:RegisterUnitEvent(e) unitEvents[e] = true end''')
        spy.addon_loader.load(lua, spy.SPY, "AutoBG_Spy.lua")
        self.assertTrue(lua.eval('unitEvents.UNIT_AURA_DELTA'))
        self.assertIsNone(lua.eval('unitEvents.UNIT_SPELLCAST_SUCCEEDED'))

    def test_a_friendly_players_casts_never_list_them(self):
        lua = spy.runtime()
        lua.execute('function UnitCanAttack(_, u) return u ~= "0x0000000000000003" end; names["0x0000000000000003"] = "Friend"')
        spy.fire(lua, "UNIT_CASTEVENT", "0x0000000000000003", "0x0000000000000000", "CAST", 1234, 0)
        lua.execute('AutoBG_Spy:RenderRows()')
        self.assertIsNone(lua.eval('AutoBG_Settings.Spy.Stats and AutoBG_Settings.Spy.Stats.friend'))
        self.assertNotEqual(lua.eval('AutoBG_SpyRow1.targetName'), "Friend")


if __name__ == "__main__":
    unittest.main()
