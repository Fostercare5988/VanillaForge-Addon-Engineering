"""Audit 2026-10-25: walking into another subzone must not empty the Spy list.

The raid toggle (commit 1ccba8d) made ZONE_CHANGED and ZONE_CHANGED_NEW_AREA
clear the whole list, so an enemy you follow across a subzone border vanishes.
Only entering the world (a loading screen) should start a fresh list.
"""
import unittest

from test_spy_features import GROM, runtime
from test_spy_nearby import advance, fire


class SubzoneTests(unittest.TestCase):
    def test_subzone_change_keeps_the_list(self):
        lua = runtime()
        self.assertEqual(lua.eval('AutoBG_SpyRow1.targetName'), "Grom")
        fire(lua, "ZONE_CHANGED")
        advance(lua, 0)
        self.assertEqual(lua.eval('AutoBG_SpyRow1.targetName'), "Grom")
        self.assertTrue(lua.eval('AutoBG_SpyRow1.shown'))

    def test_new_area_outside_a_raid_keeps_the_list(self):
        lua = runtime()
        fire(lua, "ZONE_CHANGED_NEW_AREA")
        advance(lua, 0)
        self.assertEqual(lua.eval('AutoBG_SpyRow1.targetName'), "Grom")
        self.assertTrue(lua.eval('AutoBG_SpyRow1.shown'))

    def test_entering_a_raid_still_hides_spy(self):
        lua = runtime()
        lua.execute('function IsInInstance() return 1, "raid" end')
        fire(lua, "ZONE_CHANGED_NEW_AREA")
        advance(lua, 0)
        self.assertFalse(lua.eval('AutoBG_Spy.Frame.shown'))
        lua.execute('AutoBG_Spy:RecordEnemy("Grom", "WARRIOR", 60, "%s", 100, nil, nil, "Orc")' % GROM)
        advance(lua, 1)
        self.assertFalse(lua.eval('AutoBG_Spy.Frame.shown'))


if __name__ == "__main__":
    unittest.main()
