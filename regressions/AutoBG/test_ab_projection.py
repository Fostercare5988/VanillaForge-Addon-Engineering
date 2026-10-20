"""Arathi Basin score projection: ties, hold/need wording and pending captures.

AutoBG_Timers.lua runs whole under Lua 5.1 with generic widget mocks. The
projection is driven through its real path: world-state text, BG system
messages and the timer update. Tick rates are the vanilla values the addon
assumes; OctoWoW rates remain an in-game check.
"""
from pathlib import Path
import os
import unittest
from lupa.lua51 import LuaRuntime

from test_timer_bars import BASE, TIMERS

AB = r'''
AutoBG_Settings.TestAllTimers = false
AutoBG_Settings.ABProjection = true
function GetRealZoneText() return "Arathi Basin" end
function IsInInstance() return 1, "pvp" end
function UnitFactionGroup() return "Horde" end
function UnitName() return "Tester" end
function GetNumRaidMembers() return 0 end
worldState = {}
function GetNumWorldStateUI() return 2 end
function GetWorldStateUIInfo(i) return 0, 0, worldState[i] end
function SetScores(aBases, aRes, hBases, hRes)
    worldState[1] = "Bases: " .. aBases .. "  Resources: " .. aRes .. "/2000"
    worldState[2] = "Bases: " .. hBases .. "  Resources: " .. hRes .. "/2000"
    local f = AutoBG_TimersEventFrame
    f.scripts.OnEvent(f, "UPDATE_WORLD_STATES")
end
'''


def runtime(a_bases, a_res, h_bases, h_res, messages=()):
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(BASE)
    lua.execute(AB)
    lua.execute(TIMERS)
    lua.execute('local f = AutoBG_TimersEventFrame; f.scripts.OnEvent(f, "PLAYER_ENTERING_WORLD")')
    lua.execute('SetScores(%d, %d, %d, %d)' % (a_bases, a_res, h_bases, h_res))
    for event, text in messages:
        lua.execute('local f = AutoBG_TimersEventFrame; f.scripts.OnEvent(f, %r, %r)' % (event, text))
    lua.execute('AutoBG_Timers_UpdateVisibility()')
    return lua


def shown(lua):
    frame = 'AutoBG_ABProjectionFrame'
    return {key: lua.eval('%s.%s.text' % (frame, key)) or '' for key in ('r1Status', 'r1Score', 'r2Bases', 'r2Score')}


class ABProjectionTests(unittest.TestCase):
    def test_equal_finish_times_show_a_tie_not_a_stale_win(self):
        # The reported screenshot: 3 bases need 510 (51 ticks x 6 s), 2 bases
        # need 340 (34 ticks x 9 s). Both reach 2000 after 306 s.
        text = shown(runtime(3, 1490, 2, 1660))
        self.assertIn('Tie 05:06', text['r1Status'])
        self.assertNotIn('Win', text['r1Status'])
        self.assertIn('Need 3 Bases', text['r2Bases'])

    def test_winning_side_is_told_how_many_bases_to_hold(self):
        # Horde: 500 left at 3 bases. Holding 2 still wins (450 s vs 600 s).
        text = shown(runtime(2, 1000, 3, 1500))
        self.assertIn('Win', text['r1Status'])
        self.assertIn('Hold 2 Bases', text['r2Bases'])

    def test_losing_side_is_told_how_many_bases_it_needs(self):
        text = shown(runtime(3, 1500, 2, 1000))
        self.assertIn('Loss', text['r1Status'])
        self.assertIn('Need 4 Bases', text['r2Bases'])

    def test_final_scores_name_their_faction(self):
        text = shown(runtime(2, 1000, 3, 1500))
        self.assertTrue(text['r1Score'].endswith('A 1330'), text['r1Score'])
        self.assertTrue(text['r2Score'].endswith('H 2000'), text['r2Score'])

    def test_assaulted_node_is_not_taken_from_the_defender_twice(self):
        # Horde assaulted an Alliance node: the Alliance count already dropped
        # 3 -> 2. When the capture completes Horde gains it; the Alliance keeps 2.
        # 60 s at 2 v 2 -> 1066.7 each; Horde then needs 560 s at 3 bases while
        # the Alliance earns 10/9 s -> 1688.9, shown as 1680 (old code: 1530).
        text = shown(runtime(2, 1000, 2, 1000, [
            ('CHAT_MSG_BG_SYSTEM_HORDE', 'Tester has assaulted the stables!'),
        ]))
        self.assertIn('Win 10:20', text['r1Status'])
        self.assertTrue(text['r1Score'].endswith('A 1680'), text['r1Score'])

    def test_neutral_claim_does_not_take_a_base_from_the_other_side(self):
        # Alliance claims a neutral node while each side holds one base. Horde
        # keeps its base: 0.833/s for 60 s + Alliance at 2 bases afterwards.
        text = shown(runtime(1, 1000, 1, 1000, [
            ('CHAT_MSG_BG_SYSTEM_ALLIANCE', 'Someone claims the farm! If left unchallenged, the Alliance will control it in 1 minute!'),
        ]))
        # Alliance: 1050 after 60 s, 950 left at 10/9 s -> 855 s more (915 s).
        # Horde: 1050 + 0.833 * 855 = 1762.5 -> 1760 (old code: Horde 0 bases, 1050).
        self.assertIn('Loss 15:15', text['r1Status'])
        self.assertTrue(text['r2Score'].endswith('H 1760'), text['r2Score'])


if __name__ == '__main__':
    unittest.main()
