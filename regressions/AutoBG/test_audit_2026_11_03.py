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


if __name__ == "__main__":
    unittest.main()
