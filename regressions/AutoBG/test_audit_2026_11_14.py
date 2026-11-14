"""Audit 2026-11-14: the arena sweep, the settings window and the retired options.

The complete AutoBG files run under the game's Lua with the suites' widget
stand-ins. Looks, clicks in the client and AddOn Options' own frames stay
in-game checks.
"""
import unittest
from wowlua import LuaRuntime

import addon_loader
from test_targets_guid_events import BASE as TARGETS_BASE, TARGETS

# An arena, your team of two in a raid group, two enemies the UnitXP cycle
# steps through (it selects the next enemy and returns true).
ARENA_WORLD = r'''
ARENA = "Arena"
function AutoBG_IsArenaZone() return true end
function GetBattlefieldStatus() return "none" end
function GetNumBattlefieldScores() return 0 end
raidSize = 2
ENEMIES = { { guid = "0x00000000000000A1", name = "Kael" }, { guid = "0x00000000000000A2", name = "Morg" } }
local function Enemy(u)
    if u == "target" then
        for _, e in ipairs(ENEMIES) do if e.name == target then return e end end
        return nil
    end
    for _, e in ipairs(ENEMIES) do if e.guid == u then return e end end
end
steps, cursor = 0, 0
function UnitXP(unit, verb)
    steps = steps + 1
    cursor = cursor % #ENEMIES + 1
    target = ENEMIES[cursor].name
    return true
end
function ClearTarget() target = nil end
function UnitExists(u) return u == "player" or Enemy(u) ~= nil end
function UnitGUID(u) local e = Enemy(u); return e and e.guid end
function UnitName(u) if u == "player" then return "Tester" end local e = Enemy(u); return e and e.name end
'''


def arena():
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(TARGETS_BASE)
    lua.execute(ARENA_WORLD)
    addon_loader.load(lua, TARGETS, "AutoBG_Targets.lua")
    for event in ("PLAYER_LOGIN", "UPDATE_BATTLEFIELD_STATUS"):
        lua.execute('AutoBG_Targets.scripts.OnEvent(AutoBG_Targets, "%s")' % event)
    return lua


def run_tickers(lua):
    lua.execute('for _, fn in ipairs(tickers) do fn() end')


class ArenaSweep(unittest.TestCase):
    """2026-11-14 /lag on Claude, Sunstrider Court: the sweep (Targets.lua:1030)
    ran 88 times for 597 ms, every second, moving your target through every
    enemy even with the whole team listed."""

    def test_the_sweep_finds_the_team(self):
        lua = arena()
        run_tickers(lua)
        self.assertEqual(lua.eval('AutoBG_Targets.EnemyCount()'), 2)
        self.assertIsNone(lua.eval('target'))          # your empty target is given back

    def test_the_sweep_rests_once_the_whole_team_is_listed(self):
        lua = arena()
        run_tickers(lua)
        lua.execute('steps = 0')
        run_tickers(lua)
        self.assertEqual(lua.eval('steps'), 0)

    def test_the_sweep_goes_on_while_an_enemy_is_missing(self):
        lua = arena()
        lua.execute('ENEMIES[2].hidden = ENEMIES[2]; table.remove(ENEMIES, 2)')   # in stealth
        run_tickers(lua)
        self.assertEqual(lua.eval('AutoBG_Targets.EnemyCount()'), 1)
        lua.execute('steps = 0; table.insert(ENEMIES, { guid = "0x00000000000000A2", name = "Morg" })')
        run_tickers(lua)
        self.assertGreater(lua.eval('steps'), 0)
        self.assertEqual(lua.eval('AutoBG_Targets.EnemyCount()'), 2)


if __name__ == "__main__":
    unittest.main()
