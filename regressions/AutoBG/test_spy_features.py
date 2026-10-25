"""Spy distance, health bars, kill on sight, ignore list and encounter statistics.

The complete AutoBG_Spy.lua runs with the Spy Nearby mocks. UnitXP distance and
unit health are stubbed per GUID; real distances, sounds and chat output stay
in-game checks.
"""
import unittest

from test_spy_nearby import advance, fire, runtime as spy_runtime

GROM = "0x0000000000000001"
EXTRA = r'''
yardsByGUID, healthByGUID, sounds = {}, {}, {}
function UnitDistanceSquared(u) local d = yardsByGUID[u]; if not d then return 0, false end return d * d, true end
function UnitHealth(u) return healthByGUID[u] or 100 end
function UnitHealthMax() return 100 end
function PlaySound(name) table.insert(sounds, name) end
function click(row, button) row.scripts.OnClick(row, button or "LeftButton") end
'''


def runtime():
    lua = spy_runtime()
    lua.execute(EXTRA)
    return lua


def meet_again(lua, name="Grom", guid=GROM, later=200):
    """A fresh encounter: the old row expired and two minutes passed."""
    lua.execute('visible = false')
    advance(lua, 40)
    lua.execute('visible = true; now = now + %d; clock = clock + %d' % (later, later))
    lua.execute('AutoBG_Spy:RecordEnemy("%s", "WARRIOR", 60, "%s", 100, nil, nil, "Orc")' % (name, guid))
    advance(lua, 0)


class DistanceAndHealthTests(unittest.TestCase):
    def test_row_shows_distance_and_a_health_sized_bar(self):
        lua = runtime()
        lua.execute('yardsByGUID["%s"] = 23; healthByGUID["%s"] = 50' % (GROM, GROM))
        advance(lua, 1)
        self.assertEqual(lua.eval('AutoBG_SpyRow1.Yards.text'), "23y")
        self.assertEqual(lua.eval('AutoBG_SpyRow1.StatusBar.width'), lua.eval('AutoBG_SpyRow1.width') / 2)

    def test_unseen_enemy_has_no_distance(self):
        lua = runtime()
        lua.execute('yardsByGUID["%s"] = 23' % GROM)
        advance(lua, 1)
        lua.execute('visible = false')
        advance(lua, 1)
        self.assertEqual(lua.eval('AutoBG_SpyRow1.Yards.text'), "")


class ListTests(unittest.TestCase):
    def test_shift_click_marks_kill_on_sight_and_it_warns_on_the_next_encounter(self):
        lua = runtime()
        lua.execute('shift = true; click(AutoBG_SpyRow1); shift = false')
        self.assertTrue(lua.eval('AutoBG_Spy:IsKoS("Grom")'))
        self.assertTrue(lua.eval('AutoBG_SpyRow1.kos'))
        lua.execute('sounds = {}')
        meet_again(lua)
        self.assertIn("RaidWarning", list(lua.eval('sounds').values()))

    def test_ctrl_click_ignores_and_the_command_undoes_it(self):
        lua = runtime()
        lua.execute('ctrl = true; click(AutoBG_SpyRow1); ctrl = false')
        self.assertFalse(lua.eval('AutoBG_SpyRow1.shown'))
        lua.execute('AutoBG_Spy:RecordEnemy("Grom", "WARRIOR", 60, "%s", 100, nil, nil, "Orc")' % GROM)
        advance(lua, 0)
        self.assertFalse(lua.eval('AutoBG_SpyRow1.shown'))
        self.assertTrue(lua.eval('AutoBG_Spy:HandleCommand("ignore grom")'))
        self.assertFalse(lua.eval('AutoBG_Spy:IsIgnored("Grom")'))

    def test_lists_are_saved_by_lower_case_name(self):
        lua = runtime()
        lua.execute('AutoBG_Spy:HandleCommand("kos Thrall")')
        self.assertEqual(lua.eval('AutoBG_Settings.Spy.KoS.thrall'), "Thrall")

    def test_spy_disabled_in_raids(self):
        lua = runtime()
        lua.execute('function IsInInstance() return 1, "raid" end')
        fire(lua, "ZONE_CHANGED_NEW_AREA")
        self.assertTrue(lua.eval('AutoBG_Spy:IsRaidDisabled()'))
        self.assertFalse(lua.eval('AutoBG_Spy.Frame.shown'))
        lua.execute('AutoBG_Spy:RecordEnemy("Grom", "WARRIOR", 60, "%s", 100, nil, nil, "Orc")' % GROM)
        advance(lua, 1)
        self.assertFalse(lua.eval('AutoBG_Spy.Frame.shown'))
        self.assertTrue(lua.eval('AutoBG_Spy:HandleCommand("raids")'))
        self.assertFalse(lua.eval('AutoBG_Settings.Spy.DisableInRaids'))
        self.assertFalse(lua.eval('AutoBG_Spy:IsRaidDisabled()'))


class StatisticsTests(unittest.TestCase):
    def test_each_new_encounter_is_counted_with_zone(self):
        lua = runtime()
        self.assertEqual(lua.eval('AutoBG_Settings.Spy.Stats.grom.seen'), 1)
        lua.execute('zoneName = "Durotar"')
        meet_again(lua)
        self.assertEqual(lua.eval('AutoBG_Settings.Spy.Stats.grom.seen'), 2)
        self.assertEqual(lua.eval('AutoBG_Settings.Spy.Stats.grom.zone'), "Durotar")

    def test_repeat_sightings_in_one_encounter_count_once(self):
        lua = runtime()
        for _ in range(3):
            lua.execute('AutoBG_Spy:RecordEnemy("Grom", "WARRIOR", 60, "%s", 100, nil, nil, "Orc")' % GROM)
        self.assertEqual(lua.eval('AutoBG_Settings.Spy.Stats.grom.seen'), 1)

    def test_stats_command_prints_the_most_met(self):
        lua = runtime()
        lua.execute('printed = {}; AutoBG_Spy:HandleCommand("stats")')
        lines = list(lua.eval('printed').values())
        self.assertIn("1 enemies met 1 times", lines[0])
        self.assertIn("Grom", lines[1])


if __name__ == '__main__':
    unittest.main()
