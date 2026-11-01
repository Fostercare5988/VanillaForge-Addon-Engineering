"""Spy encounter stats, 2026-11-01.

!ErrorLog (2026-10-31, The Hinterlands): AutoBG_Spy.lua:121 "attempt to compare
number with nil". The saved-enemy count was taken only when a NEW enemy was
recorded, so a first encounter of the session with an already known enemy
compared nil with the limit.
"""
import os
import unittest
from pathlib import Path
from lupa.lua51 import LuaRuntime

ROOT = Path(os.environ["VANILLAFORGE_ADDON_ROOT"])
SPY = (ROOT / "AutoBG_Spy.lua").read_text("utf-8-sig")


class NoteEncounterTests(unittest.TestCase):
    def runtime(self):
        lua = LuaRuntime(unpack_returned_tuples=True)
        start = SPY.index("local STATS_LIMIT, STATS_KEEP")
        end_ = SPY.index("local function Ago")
        lua.execute('''
            stats = { ["known"] = { first = 1, seen = 3, last = 5 } }
            function SavedList() return stats end
            function time() return 100 end
            function GetRealZoneText() return "Test" end
        ''' + SPY[start:SPY.index("\n", start)] + "\n" +
            SPY[SPY.index("local statsSize"):end_] + "\nNote = NoteEncounter\n")
        return lua

    def test_a_known_enemy_first_in_the_session_does_not_error(self):
        lua = self.runtime()
        entry = lua.eval('Note("Known", "ROGUE", 60)')
        self.assertEqual(entry.seen, 4)

    def test_a_new_enemy_is_added(self):
        lua = self.runtime()
        lua.execute('Note("Fresh", nil, nil)')
        self.assertTrue(lua.eval('stats["fresh"] ~= nil'))


if __name__ == "__main__":
    unittest.main()
