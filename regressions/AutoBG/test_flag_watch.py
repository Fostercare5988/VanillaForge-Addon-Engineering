"""Flag watch: an enemy who comes into sight at a flag their team does not hold
and stands there, that is out of stealth onto the flag.

An opening started from stealth sends no cast to the client (2026-10-22: a druid
out of Prowl opened the Blacksmith with no cast bar), so the watch uses
positions. The complete AutoBG_FlagWatch.lua runs with a mocked roster and
UnitPosition; real flag spots, the "Opening" spell name and the look of the
alert stay in-game checks.
"""
from pathlib import Path
import os
import unittest
from lupa.lua51 import LuaRuntime

ROOT = Path(os.environ["VANILLAFORGE_ADDON_ROOT"])
WATCH = (ROOT / "AutoBG_FlagWatch.lua").read_text("utf-8-sig")
BALLOON = "0x0000000000000007"

SETUP = r'''
local Frame = {}
function Frame:RegisterEvent() end
function Frame:UnregisterEvent() end
function Frame:SetScript(_, fn) self.onEvent = fn end
function CreateFrame() return setmetatable({}, { __index = Frame }) end
tick = nil
C_Timer = { NewTicker = function(_, fn) tick = fn; return { Cancel = function() tick = nil end } end }
now = 100
function GetTime() return now end
function IsInInstance() return 1, "pvp" end
function GetRealZoneText() return "Arathi Basin" end
function UnitFactionGroup() return "Alliance" end
function UnitGUID(u) if u == "player" then return "0x0000000000000001" end end
function UnitName(u) if u == "player" then return "Tester" end end
function GetNumRaidMembers() return 0 end
function UnitIsDeadOrGhost() return nil end
function PlaySound() end
function SpellInfo() return "Opening" end
pos = { player = { 0, 0 } }
function UnitPosition(u)
    local p = pos[u]
    if p then return p[1], p[2], 0, 529 end
end
AutoBG_Settings = {}
opening, alerts = {}, {}
AutoBG_Targets = {
    EnemyCount = function() return 1 end,
    GetEnemy = function() return "Balloon", "0x0000000000000007", "DRUID" end,
    GetGUID = function(name) if name == "Balloon" then return "0x0000000000000007" end end,
    SetOpening = function(name, node) opening[name] = node end,
}
learned = {}
AutoBG_FlagAlert = {
    Show = function(_, name, _, _, node) table.insert(alerts, "Opening " .. node .. " " .. name) end,
    LearnOpening = function(_, id) table.insert(learned, id) end,
}
'''


def runtime():
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(SETUP)
    lua.execute(WATCH)
    lua.execute('AutoBG_FlagWatchFrame = AutoBG_FlagWatch; AutoBG_FlagWatch.onEvent(AutoBG_FlagWatch, "PLAYER_ENTERING_WORLD")')
    return lua


def learn_blacksmith(lua):
    """You assault the Blacksmith standing at (50, 50)."""
    lua.execute('pos.player = { 50, 50 }')
    lua.execute('AutoBG_FlagWatch:OnNodeMessage("Blacksmith", "Tester has assaulted the Blacksmith!", "Alliance")')


def ticks(lua, n):
    for _ in range(n):
        lua.execute('now = now + 0.25; tick()')


class FlagWatchTests(unittest.TestCase):
    def test_enemy_standing_at_the_flag_warns_once(self):
        lua = runtime()
        learn_blacksmith(lua)
        lua.execute('pos["%s"] = { 52, 49 }' % BALLOON)
        ticks(lua, 4)
        self.assertEqual(list(lua.eval('alerts').values()), ["Opening Blacksmith Balloon"])
        self.assertEqual(lua.eval('opening.Balloon'), "Blacksmith")

    def test_stealthed_or_moving_enemy_does_not_warn(self):
        lua = runtime()
        learn_blacksmith(lua)
        ticks(lua, 3)  # no position: still in Prowl
        for step in range(4):
            lua.execute('pos["%s"] = { 52 + %d, 49 }' % (BALLOON, step * 2))
            ticks(lua, 1)
        self.assertEqual(len(lua.eval('alerts')), 0)

    def test_flag_their_team_holds_does_not_warn(self):
        lua = runtime()
        learn_blacksmith(lua)
        lua.execute('AutoBG_FlagWatch:OnNodeMessage("Blacksmith", "The Horde has taken the Blacksmith!", "Horde")')
        lua.execute('pos["%s"] = { 52, 49 }' % BALLOON)
        ticks(lua, 4)
        self.assertEqual(len(lua.eval('alerts')), 0)

    def test_their_assault_clears_the_row_mark(self):
        lua = runtime()
        learn_blacksmith(lua)
        lua.execute('pos["%s"] = { 52, 49 }' % BALLOON)
        ticks(lua, 4)
        lua.execute('AutoBG_FlagWatch:OnNodeMessage("Blacksmith", "Balloon has assaulted the Blacksmith!", "Horde")')
        self.assertIsNone(lua.eval('opening.Balloon'))

    def test_spots_are_saved_per_map_and_averaged(self):
        lua = runtime()
        learn_blacksmith(lua)
        lua.execute('pos["%s"] = { 54, 54 }' % BALLOON)
        lua.execute('AutoBG_FlagWatch:OnNodeMessage("Blacksmith", "Balloon has assaulted the Blacksmith!", "Horde")')
        self.assertEqual(lua.eval('AutoBG_Settings.FlagSpots[529].Blacksmith.y'), 52)
        # A sample far away is not this flag.
        lua.execute('pos["%s"] = { 300, 300 }' % BALLOON)
        lua.execute('AutoBG_FlagWatch:OnNodeMessage("Blacksmith", "Balloon has defended the Blacksmith!", "Horde")')
        self.assertEqual(lua.eval('AutoBG_Settings.FlagSpots[529].Blacksmith.n'), 2)

    def test_any_opening_cast_teaches_the_spell_once(self):
        lua = runtime()
        lua.execute('AutoBG_FlagWatch.onEvent(AutoBG_FlagWatch, "UNIT_CASTEVENT", "%s", nil, "START", 90001, 5000)' % BALLOON)
        lua.execute('AutoBG_FlagWatch.onEvent(AutoBG_FlagWatch, "UNIT_CASTEVENT", "%s", nil, "CAST", 90001, 0)' % BALLOON)
        self.assertEqual(list(lua.eval('learned').values()), [90001])

    def test_revived_enemy_at_stale_death_spot_does_not_warn(self):
        """2026-10-25: enemies revived at the Lumber Mill graveyard set off
        "Opening Gold Mine", where they had died. The client keeps a ghost's
        last spot until they move."""
        lua = runtime()
        learn_blacksmith(lua)
        lua.execute('pos["%s"] = { 52, 49 }' % BALLOON)
        lua.execute('function UnitIsDeadOrGhost() return 1 end')
        ticks(lua, 3)
        lua.execute('function UnitIsDeadOrGhost() return nil end')
        ticks(lua, 6)  # alive again, client still shows the death spot
        self.assertEqual(len(lua.eval('alerts')), 0)
        # Stealthing again and coming out at the flag warns as usual.
        lua.execute('pos["%s"] = nil' % BALLOON)
        ticks(lua, 2)
        lua.execute('pos["%s"] = { 53, 50 }' % BALLOON)
        ticks(lua, 3)
        self.assertEqual(list(lua.eval('alerts').values()), ["Opening Blacksmith Balloon"])

    def test_enemy_walking_up_in_sight_does_not_warn(self):
        """2026-10-25: standing still near a flag is just as often fighting or
        waiting. A visible opener shows on their enemy frame's cast bar."""
        lua = runtime()
        learn_blacksmith(lua)
        for step in range(4):
            lua.execute('pos["%s"] = { 60 - %d, 49 }' % (BALLOON, step * 2))
            ticks(lua, 1)
        ticks(lua, 6)  # now standing at the flag
        self.assertEqual(len(lua.eval('alerts')), 0)

    def test_enemy_out_of_stealth_who_runs_on_does_not_warn(self):
        lua = runtime()
        learn_blacksmith(lua)
        lua.execute('pos["%s"] = { 52, 49 }' % BALLOON)
        ticks(lua, 1)
        lua.execute('pos["%s"] = { 54, 49 }' % BALLOON)
        ticks(lua, 1)
        lua.execute('pos["%s"] = { 55, 49 }' % BALLOON)
        ticks(lua, 4)
        self.assertEqual(len(lua.eval('alerts')), 0)

    def test_switch_off_stops_warnings(self):
        lua = runtime()
        learn_blacksmith(lua)
        lua.execute('AutoBG_Settings.Targets = { FlagWatch = false }')
        lua.execute('pos["%s"] = { 52, 49 }' % BALLOON)
        ticks(lua, 4)
        self.assertEqual(len(lua.eval('alerts')), 0)


if __name__ == '__main__':
    unittest.main()
