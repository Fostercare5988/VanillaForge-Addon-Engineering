"""Saved keys nothing reads, offline members in a party, and switches that start
other modules (audit 2026-11-13, 1.20.0).

- "Auto Dismount" stayed in eight characters' saved files: its module went on
  2026-11-07 and Core's line that cleared it on 2026-11-08 (find_holes, "Saved but
  no code reads it"). Core now clears every key that no module, number, choice
  or saved table owns, so no retired switch needs a line of its own.
- A party member who went offline kept showing missing health: a party has no
  roster event for it, and UNIT_CONNECTION only dimmed the button.
- The unit frames' core started the energy ticks and the target castbar itself,
  a second time after Core: a hidden connection. Each module starts once and
  applies its own switch.
- Chat History kept its lines under realm and name inside a per-character table.

Each test fails on 6d9937e (1.19.0).
"""
import re
import sys
import unittest
from pathlib import Path

from test_audit_2026_10_25 import source
from test_audit_2026_10_26 import RAID_ROSTER, ROOT, runtime
from test_audit_2026_11_01 import core


def initialize(saved):
    lua = core()
    lua.execute("FT = FostercareTweaks")
    lua.execute(source("Helpers.lua")[source("Helpers.lua").index("-- A switch: its saved value"):
                                      source("Helpers.lua").index("function FT.ClampNumber")])
    lua.execute(r'''
        FT:register({ title = "Chat History", enabled = true })
        FT:register({ title = "Vendor Values", always = true })
    ''')
    lua.execute("FostercareTweaks_Config = " + saved)
    lua.execute("FostercareTweaks:Initialize()")
    return lua


class SavedKeysNothingReadsAreCleared(unittest.TestCase):
    def setUp(self):
        self.lua = initialize(r'''{
            ["Auto Dismount"] = 1, ["WorldMap Window"] = 1, ["Zone Layouts"] = 1,
            ["Center Vertical Actionbar"] = 1, profiles = {},
            ["Chat History"] = 0, ["Vendor Values"] = 1,
            watched = {}, actionbars = { enabled = true }, unitframe_positions = {},
            groupframe_dimensions = {},
            overwrites = { minimap_scale = 1.6, raid_health_format = "percent", old_number = 3 },
        }''')

    def config(self, key):
        return self.lua.eval('FostercareTweaks_Config["%s"]' % key)

    def test_retired_switches_go(self):
        for key in ("Auto Dismount", "WorldMap Window", "Zone Layouts", "Center Vertical Actionbar", "profiles"):
            self.assertIsNone(self.config(key), key)

    def test_switches_and_tables_stay(self):
        self.assertEqual(self.config("Chat History"), 0)
        for key in ("watched", "actionbars", "unitframe_positions", "groupframe_dimensions", "overwrites"):
            self.assertIsNotNone(self.config(key), key)
        self.assertIsNone(self.config("Vendor Values"))        # an always-on module keeps no switch

    def test_numbers_and_choices_stay_and_others_go(self):
        self.assertEqual(self.lua.eval("FostercareTweaks_Config.overwrites.minimap_scale"), 1.6)
        self.assertEqual(self.lua.eval("FostercareTweaks_Config.overwrites.raid_health_format"), "percent")
        self.assertIsNone(self.lua.eval("FostercareTweaks_Config.overwrites.old_number"))

    def test_no_retired_key_has_its_own_line(self):
        self.assertIsNone(re.search(r'FostercareTweaks_Config\["[^"]+"\]\s*=\s*nil', source("Core.lua")))


class ChoicesHaveOneDefault(unittest.TestCase):
    def test_a_cleared_choice_reads_its_default(self):
        lua = initialize("{ overwrites = {} }")
        self.assertEqual(lua.eval('FT.GetOverride("raid_health_format")'), "deficit")
        self.assertEqual(lua.eval('FT.GetOverride("raidmark_position")'), "portrait")

    def test_no_read_passes_a_default(self):
        for path in ROOT.rglob("*.lua"):
            self.assertIsNone(re.search(r'GetOverride\("[^"]+",', path.read_text("utf-8-sig")), path.name)


class DefaultsShipOnlyWhatTheAddonReads(unittest.TestCase):
    def test_every_default_is_read_and_no_watched_aura_ships(self):
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
        from export_defaults import kept_keys
        kept = kept_keys(ROOT)
        text = source("Defaults.lua")
        top = re.findall(r'^    (?:\["([^"]+)"\]|(\w+)) = ', text, re.M)
        names = [a or b for a, b in top]
        self.assertTrue(names)
        self.assertEqual([n for n in names if n not in kept], [])
        self.assertNotIn("watched", names)
        self.assertNotIn("watch_", text)

    def test_defaults_are_the_authors_current_borders(self):
        # The author turned buff borders on and castbar borders back on after 2026-11-02.
        text = source("Defaults.lua")
        self.assertIn('["Show Buff Borders"] = 1', text)
        self.assertIn('["Borderless Castbars"] = 0', text)


class OfflinePartyMemberSaysOff(unittest.TestCase):
    def setUp(self):
        lua = self.lua = runtime()
        lua.execute(RAID_ROSTER)
        lua.execute(r'''
            local W = getmetatable(Widget())
            function W:SetText(t) rawset(self, "text", t) end
            function W:GetText() return rawget(self, "text") end
            members = 0
            function GetNumPartyMembers() return 2 end
            function UnitIsPartyLeader() return false end
            connected = {}
            function UnitIsConnected(u) return connected[u] ~= false end
            function FT.GetUnitHealthValues() return 60, 100 end
        ''')
        lua.execute(source("mods/unitframes/raid.lua"))
        lua.execute("UF:EnableRaidFrames(true); UF:UpdateGroupRoster(true)")

    def text(self, unit):
        return self.lua.eval('(function() for _, b in pairs(frames) do if b.unit == "%s" then '
                             'return b.healthText:GetText() end end end)()' % unit)

    def test_going_offline_and_back(self):
        self.assertEqual(self.text("party2"), "-40")
        self.lua.execute('connected.party2 = false; fire(FCTweaksRaidFrame, "UNIT_CONNECTION", "party2", false)')
        self.assertEqual(self.text("party2"), "|cff888888Off|r")
        self.assertEqual(self.text("party1"), "-40")
        self.lua.execute('connected.party2 = true; fire(FCTweaksRaidFrame, "UNIT_CONNECTION", "party2", true)')
        self.assertEqual(self.text("party2"), "-40")


class EachModuleStartsItself(unittest.TestCase):
    def test_unit_frame_core_starts_no_other_module(self):
        text = source("mods/unitframes/core.lua")
        for other in ("Show Energy Ticks", "Enemy Castbars", "RefreshEnergyTick", "RefreshTargetCastbar"):
            self.assertNotIn(other, text)
        self.assertNotIn("RefreshTargetCastbar", source("mods/target-castbar.lua"))

    def test_energy_ticks_switch_applies_live(self):
        lua = runtime()
        lua.execute(source("mods/unitframe-energytick.lua"))
        lua.execute('PlayerFrameManaBar.GetEffectiveScale = function() return 1 end; PlayerFrameManaBar.IsVisible = function() return true end')
        lua.execute('FostercareTweaks_Config["Show Energy Ticks"] = 1; FT.mods["Show Energy Ticks"]:apply(true)')
        self.assertIsNotNone(lua.eval("FCTweaksEnergyTick"))
        self.assertTrue(lua.eval("FCTweaksEnergyTick.running"))
        lua.execute('FostercareTweaks_Config["Show Energy Ticks"] = 0; FT.mods["Show Energy Ticks"]:apply(false)')
        self.assertFalse(lua.eval("FCTweaksEnergyTick.running"))
        self.assertIn('Live("Show Energy Ticks")', source("Settings.lua"))


class ChatHistoryIsTheCharactersOwn(unittest.TestCase):
    def history(self, cache):
        lua = runtime()
        lua.execute(r'''
            NUM_CHAT_WINDOWS = 1
            function FT.IsCombatChatFrame() return false end
            FT.rgbhex = function() return "|cff999999" end
            function GetRealmName() return "R" end
            function UnitName() return "P" end
            msgs = {}
            ChatFrame1 = {}
            function ChatFrame1:BackFillMessage(text) table.insert(msgs, 1, text) end
            function ChatFrame1:GetNumMessages() return #msgs end
            function ChatFrame1:GetMessageInfo(i) return msgs[i], 1, 1, 1 end
        ''')
        lua.execute("FostercareTweaks_Cache = " + cache)
        lua.execute(source("mods/chat-tweaks.lua"))
        lua.execute('FT.mods["Chat History"]:enable()')
        return lua

    def test_old_lines_move_once_and_the_nesting_goes(self):
        lua = self.history('{ chathistory = { R = { P = { [1] = { "|cff999999old" } } }, Other = {} } }')
        self.assertEqual(lua.eval("msgs[1]"), "|cff999999old")
        self.assertIsNone(lua.eval("FostercareTweaks_Cache.chathistory"))
        self.assertEqual(lua.eval("FostercareTweaks_Cache.chat[1][1]"), "|cff999999old")

    def test_a_new_character_starts_empty(self):
        lua = self.history("{}")
        self.assertEqual(lua.eval("#msgs"), 0)
        self.assertIsNotNone(lua.eval("FostercareTweaks_Cache.chat"))


if __name__ == "__main__":
    unittest.main()
