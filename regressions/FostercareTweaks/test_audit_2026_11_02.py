"""FostercareTweaks audit, 2026-11-02 (.private/audit-FostercareTweaks-2026-11-02.md).

Bugs (each fails on 192e14d):
- The target cast bar wrote its texture paths with one backslash per separator.
  Lua 5.0 drops an unknown escape's backslash, so the fill, the background and
  the spark named files that do not exist.
- The party grid gave the leader's crown only to the player: a party member
  who led never showed it, and a leader change did not read the roster again.
- Defaults.lua still carried the retired "WorldMap Window" switch, so a new
  character's first login switched the account's world map to windowed.

Widget mocks record our calls; drawing stays an in-game check.
"""
import re
import sys
import unittest
from pathlib import Path
from lupa.lua51 import LuaRuntime

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

from test_audit_2026_10_25 import source
from test_audit_2026_11_01 import CORE_PRELUDE
from test_event_fanout import BASE, ROOT
from test_unitframe_hot_paths import RAID, WIDGETS, slice

BS = chr(92)


class TexturePathsKeepTheirBackslashes(unittest.TestCase):
    def test_the_target_cast_bar_names_real_textures(self):
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute(BASE + r'''
            paths = {}
            local create = CreateFrame
            function CreateFrame(kind, name)
                local f = create(kind, name)
                f.SetStatusBarTexture = function(_, p) paths.fill = p end
                f.SetBackdrop = function(_, b) paths.background = b.bgFile end
                f.CreateTexture = function()
                    return setmetatable({ SetTexture = function(_, p) paths.texture = p end }, getmetatable(f))
                end
                return f
            end
            TargetFrame = CreateFrame("Frame", "TargetFrame")
        ''')
        lua.execute((ROOT / "mods/target-castbar.lua").read_text("utf-8-sig"))
        self.assertEqual(lua.eval("paths.fill"), "Interface%sTargetingFrame%sUI-StatusBar" % (BS, BS))
        self.assertEqual(lua.eval("paths.background"), "Interface%sButtons%sWHITE8X8" % (BS, BS))
        self.assertEqual(lua.eval("paths.texture"), "Interface%sCastingBar%sUI-CastingBar-Spark" % (BS, BS))

    def test_no_string_in_the_addon_loses_a_backslash(self):
        # The kind: any "..." literal with an escape Lua 5.0 does not know.
        literal = re.compile(r'"((?:[^"\\\n]|\\.)*)"')
        known = set(BS + "\"'abfnrtv0123456789")
        found = []
        for path in sorted(ROOT.rglob("*.lua")):
            for number, line in enumerate(path.read_text("utf-8-sig").splitlines(), 1):
                for text in literal.findall(line):
                    if any(c not in known for c in re.findall(r'\\(.)', text)):
                        found.append("%s:%d %s" % (path.relative_to(ROOT), number, text))
        self.assertEqual(found, [])


PARTY = r'''
    raidFrame, testMode = W(), false
    unitToButton, groupCounters = {}, {}
    function wipe(t) for k in pairs(t) do t[k] = nil end end
    groups = {}
    for g = 1, 8 do
        local group = W({ title = W(), buttons = {} })
        for m = 1, 5 do group.buttons[m] = W({ buffBadges = {}, debuffBadges = {} }) end
        groups[g] = group
    end
    RAID_UNITS = {}
    function GetNumRaidMembers() return 0 end
    function GetNumPartyMembers() return 2 end
    leader = "party1"
    function UnitIsPartyLeader(u) return u == leader end
    names = { player = "Me", party1 = "Ann", party2 = "Bob" }
    function UnitName(u) return names[u] end
    function UnitIsConnected() return 1 end
    function SetUnit(b, unit) b.unit = unit end
    rebuilt = 0
    function UpdateButtonAll() rebuilt = rebuilt + 1 end
    function LayoutRaidGroups() end
    FT = { NormalizeClass = function(c) return c end }
    UF = { Auras = { ResetAuraButton = function() end } }
    function UF:GetGroupDimensions() return { enabled = true } end
'''


class PartyLeaderCrown(unittest.TestCase):
    def setUp(self):
        lua = self.lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute(WIDGETS)
        lua.execute(PARTY)
        lua.execute(slice(RAID, "-- Unit events keep a member current. A roster", "-- Roster events come in bursts",
                          "-- force: rebuild every button"))

    def test_a_party_member_who_leads_wears_the_crown(self):
        self.lua.execute("UF:UpdateGroupRoster()")
        self.assertEqual(self.lua.eval("groups[1].buttons[2].rank"), 2)   # party1
        self.assertEqual(self.lua.eval("groups[1].buttons[1].rank"), 0)   # the player follows

    def test_a_new_leader_moves_the_crown(self):
        self.lua.execute('UF:UpdateGroupRoster(); rebuilt = 0; leader = "player"; UF:UpdateGroupRoster()')
        self.assertEqual(self.lua.eval("groups[1].buttons[1].rank"), 2)
        self.assertEqual(self.lua.eval("groups[1].buttons[2].rank"), 0)
        self.assertEqual(self.lua.eval("rebuilt"), 2)                       # only those two

    def test_a_leader_change_reads_the_roster(self):
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute(WIDGETS + r'''
            timers, unitToButton = {}, {}
            C_Timer = { After = function(_, fn) timers[#timers + 1] = fn end }
            UF = { UpdateGroupRoster = function() end }
            function RefreshAggro() end
        ''')
        lua.execute(slice(RAID, "local rosterPending", "-- 8. Test Mode", "local rosterPending").rstrip("-\n")
                    + "\nHandler = RaidFrame_OnEvent")
        lua.execute('Handler(nil, "PARTY_LEADER_CHANGED")')
        self.assertEqual(lua.eval("#timers"), 1)


class NewCharacterKeepsTheMap(unittest.TestCase):
    def initialize(self):
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute((CORE_PRELUDE % "2.2").replace("FostercareTweaks_Config = { overwrites = {} }", ""))
        lua.execute(source("Defaults.lua"))
        lua.execute(source("Core.lua"))
        lua.execute('''
            minimized, WORLDMAP_WINDOWED = 0, 0
            function WorldMapFrame_Minimize() minimized = minimized + 1 end
            FostercareTweaks:Initialize()
        ''')
        return lua

    def test_the_first_login_leaves_the_world_map_alone(self):
        lua = self.initialize()
        self.assertEqual(lua.eval("WORLDMAP_WINDOWED"), 0)
        self.assertEqual(lua.eval("minimized"), 0)

    def test_retired_switches_are_not_shipped(self):
        # The kind: whatever the addon retires (always-on modules, keys Core.lua
        # clears) never reaches a new character. Run tools/export_defaults.py
        # again after retiring a switch.
        from export_defaults import retired_keys
        retired = retired_keys(ROOT)
        self.assertIn("WorldMap Window", retired)
        self.assertIn("Blizzard Aura Controls", retired)
        text = source("Defaults.lua")
        self.assertEqual(sorted(k for k in retired if '["%s"]' % k in text), [])


if __name__ == "__main__":
    unittest.main()
