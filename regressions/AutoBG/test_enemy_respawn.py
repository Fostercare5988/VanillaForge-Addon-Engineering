"""A dead enemy's row counts down to the spirit healer's next wave (2026-11-13).

BattleGroundEnemies shows when a dead enemy comes back; AutoBG's rows said
only "DEAD". The row now reads "DEAD 21" (ClassicAPI's duration text binding,
"~" while the wave is a guess) and comes back at full health at the wave,
unless the corpse is still in sight. Fails on AutoBG 6623680: the row says
"DEAD" and stays dead. Whether OctoWoW revives every graveyard on one wave, and
that the living cannot see ghosts, are in-game checks.
"""
import unittest
from wowlua import LuaRuntime

import addon_loader
from clock_mock import CLOCK
import test_targets_guid_events as tge

GROM = tge.GROM
DEAD = "|cffff4040DEAD|r"

STUBS = r'''
-- Timers.lua's wave: one every 30 s from SYNC; WAVE_SYNCED once one is seen.
SYNC, WAVE_SYNCED = 991, true
function AutoBG_NextSpiritWave()
    local n = GetTime()
    return SYNC + 30 * (math.floor((n - SYNC) / 30) + 1), WAVE_SYNCED
end
inSight, corpse = false, false
function UnitExists(u) return u == "player" or (u == "target" and target ~= nil) or (u == "0x0000000000000042" and inSight) end
function UnitIsDeadOrGhost(u) return u == "0x0000000000000042" and corpse or nil end
'''


def runtime(arena=False):
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(tge.BASE)
    lua.execute(CLOCK)
    lua.execute(STUBS)
    if arena:
        lua.execute('function AutoBG_IsArenaZone() return true end')
    addon_loader.load(lua, tge.TARGETS, "AutoBG_Targets.lua")
    for event in ("PLAYER_LOGIN", "UPDATE_BATTLEFIELD_STATUS"):
        lua.execute('AutoBG_Targets.scripts.OnEvent(AutoBG_Targets, "%s")' % event)
    lua.execute('inSight = true; target = "Grom"; AutoBG_Targets.scripts.OnEvent(AutoBG_Targets, "PLAYER_TARGET_CHANGED"); target = nil; inSight = false')
    return lua


def text_at(lua, now):
    lua.execute('NOW = %s; __frame()' % now)
    return tge.row_text(lua)


class EnemyRespawnTests(unittest.TestCase):
    def test_dead_enemy_counts_down_to_the_wave(self):
        lua = runtime()
        tge.fire(lua, "UNIT_DIED", GROM)
        self.assertEqual(text_at(lua, 1000), DEAD + " 21")
        self.assertEqual(text_at(lua, 1010.5), DEAD + " 11")

    def test_a_guessed_wave_is_marked(self):
        lua = runtime()
        lua.execute('WAVE_SYNCED = false')
        tge.fire(lua, "UNIT_DIED", GROM)
        self.assertEqual(text_at(lua, 1000), DEAD + " ~21")

    def test_an_unseen_enemy_is_back_at_the_wave(self):
        lua = runtime()
        tge.fire(lua, "UNIT_DIED", GROM)
        text_at(lua, 1000)
        self.assertEqual(text_at(lua, 1021.2), "100%")
        self.assertFalse(lua.eval('AutoBG_TargetButton1.respawnClock:IsEnabled()'))

    def test_a_corpse_in_sight_waits_for_the_next_wave(self):
        lua = runtime()
        tge.fire(lua, "UNIT_DIED", GROM)
        text_at(lua, 1000)
        lua.execute('inSight, corpse = true, true')
        self.assertEqual(text_at(lua, 1021.2), DEAD + " 30")
        self.assertEqual(text_at(lua, 1040), DEAD + " 11")

    def test_a_guessed_wave_revives_nobody(self):
        lua = runtime()
        lua.execute('WAVE_SYNCED = false')
        tge.fire(lua, "UNIT_DIED", GROM)
        text_at(lua, 1000)
        self.assertEqual(text_at(lua, 1021.2), DEAD + " ~30")

    def test_a_wave_that_moved_resets_the_clock_without_reviving(self):
        lua = runtime()
        tge.fire(lua, "UNIT_DIED", GROM)
        text_at(lua, 1000)
        lua.execute('SYNC = 1001')  # Timers saw the real wave: 1031, not 1021
        self.assertEqual(text_at(lua, 1021.2), DEAD + " 10")
        self.assertEqual(text_at(lua, 1031.2), "100%")

    def test_arena_rows_have_no_respawn(self):
        lua = runtime(arena=True)
        tge.fire(lua, "UNIT_DIED", GROM)
        self.assertEqual(text_at(lua, 1000), DEAD)

    def test_seen_alive_again_gives_the_text_back(self):
        lua = runtime()
        tge.fire(lua, "UNIT_DIED", GROM)
        text_at(lua, 1000)
        lua.execute('health.hp = 2000')
        tge.fire(lua, "UNIT_HEALTH_GUID", GROM, 0, 0, 0, 0, 0, 0)
        self.assertEqual(text_at(lua, 1005), "50%")
        self.assertFalse(lua.eval('AutoBG_TargetButton1.respawnClock:IsEnabled()'))

    def test_leaving_the_battleground_stops_the_clocks(self):
        lua = runtime()
        tge.fire(lua, "UNIT_DIED", GROM)
        text_at(lua, 1000)
        lua.execute('function GetBattlefieldStatus() return "none" end')
        tge.fire(lua, "UPDATE_BATTLEFIELD_STATUS", 0)
        lua.execute('AutoBG_Targets:BattlefieldScoreUpdate(true)')
        self.assertFalse(lua.eval('AutoBG_TargetButton1.respawnClock:IsEnabled()'))


if __name__ == '__main__':
    unittest.main()
