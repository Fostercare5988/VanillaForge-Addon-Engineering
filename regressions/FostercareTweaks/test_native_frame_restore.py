"""Suppressing then restoring Blizzard unit frames keeps native events (P2-2).

Native sets come from the deployed 1.12 FrameXML: PlayerFrame_OnLoad,
TargetFrame_OnLoad, UnitFrame_Initialize, UnitFrameHealthBar_Initialize and
UnitFrameManaBar_Initialize (archived pane-stutter-2026-10-11 native-fanout copy).
"""
from pathlib import Path
import os
import re
import unittest
from lupa.lua51 import LuaRuntime

SOURCE = (Path(os.environ["VANILLAFORGE_ADDON_ROOT"]) /
          "mods/unitframes/core.lua").read_text("utf-8-sig")

# Extracted by tools/extract_framexml.py; Blizzard code stays in .private.
FRAMEXML = Path(os.environ.get("VANILLAFORGE_FRAMEXML",
                               Path(__file__).resolve().parents[2] / ".private" / "framexml")) / "Interface" / "FrameXML"

UNIT_FRAME = ["UNIT_NAME_UPDATE", "UNIT_PORTRAIT_UPDATE", "UNIT_DISPLAYPOWER"]
HEALTH_BAR = ["UNIT_HEALTH", "UNIT_MAXHEALTH"]
MANA_BAR = ["UNIT_MANA", "UNIT_RAGE", "UNIT_FOCUS", "UNIT_ENERGY", "UNIT_HAPPINESS",
            "UNIT_MAXMANA", "UNIT_MAXRAGE", "UNIT_MAXFOCUS", "UNIT_MAXENERGY",
            "UNIT_MAXHAPPINESS", "UNIT_DISPLAYPOWER"]
NATIVE = {
    "PlayerFrame": UNIT_FRAME + [
        "UNIT_LEVEL", "UNIT_COMBAT", "UNIT_FACTION", "UNIT_MAXMANA",
        "PLAYER_ENTERING_WORLD", "PLAYER_ENTER_COMBAT", "PLAYER_LEAVE_COMBAT",
        "PLAYER_REGEN_DISABLED", "PLAYER_REGEN_ENABLED", "PLAYER_UPDATE_RESTING",
        "PARTY_MEMBERS_CHANGED", "PARTY_LEADER_CHANGED", "PARTY_LOOT_METHOD_CHANGED",
        "RAID_ROSTER_UPDATE", "PLAYTIME_CHANGED"],
    "PlayerFrameHealthBar": HEALTH_BAR,
    "PlayerFrameManaBar": MANA_BAR,
    "TargetFrame": UNIT_FRAME + [
        "PLAYER_ENTERING_WORLD", "PLAYER_TARGET_CHANGED", "UNIT_HEALTH", "UNIT_LEVEL",
        "UNIT_FACTION", "UNIT_CLASSIFICATION_CHANGED", "UNIT_AURA",
        "PLAYER_FLAGS_CHANGED", "PARTY_MEMBERS_CHANGED", "RAID_TARGET_UPDATE"],
    "TargetFrameHealthBar": HEALTH_BAR,
    "TargetFrameManaBar": MANA_BAR,
    "ComboFrame": ["PLAYER_TARGET_CHANGED", "PLAYER_COMBO_POINTS"],
}


def runtime():
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute('''
        local Frame = {}
        Frame.__index = Frame
        function Frame:RegisterEvent(e) self.events[e] = true end
        function Frame:UnregisterAllEvents() self.events = {} end
        function Frame:IsEventRegistered(e) return self.events[e] == true end
        function Frame:Show() self.shown = true end
        function Frame:Hide() self.shown = false end
        function Frame:IsShown() return self.shown end
        function NewFrame(name)
            local f = setmetatable({ events = {}, shown = true }, Frame)
            _G[name] = f
            return f
        end
        function UnitExists() return true end
        PlayerFrame_Update, TargetFrame_Update, TargetFrame_CheckDead = function() end, function() end, function() end
        ComboPointsFrame_OnEvent = function() end
    ''')
    for name, events in NATIVE.items():
        lua.execute('local f = NewFrame(...)', name)
        for e in events:
            lua.execute('local n, e = ...; _G[n].events[e] = true', name, e)
    start = SOURCE.find('local NATIVE_FRAME_EVENTS')
    if start < 0:
        start = SOURCE.index('function UF:SuppressPlayerFrame()')
    body = SOURCE[start:SOURCE.index('function UF:SuppressPartyFrames()')]
    lua.execute('UF = {}\n' + body)
    return lua


def registered(lua, name):
    return set(lua.eval('_G["%s"].events' % name).keys())


class NativeFrameRestoreTests(unittest.TestCase):
    def check_round_trip(self, suppress, restore, names, calls=1):
        lua = runtime()
        lua.execute(('UF:%s(); ' % suppress) * calls + 'UF:%s()' % restore)
        for name in names:
            self.assertEqual(registered(lua, name), set(NATIVE[name]),
                             "%s events changed by suppress/restore" % name)

    def test_target_frame_round_trip_keeps_native_events(self):
        self.check_round_trip("SuppressTargetFrame", "RestoreTargetFrame",
                              ["TargetFrame", "TargetFrameHealthBar", "TargetFrameManaBar", "ComboFrame"])

    def test_player_frame_round_trip_keeps_native_events(self):
        self.check_round_trip("SuppressPlayerFrame", "RestorePlayerFrame",
                              ["PlayerFrame", "PlayerFrameHealthBar", "PlayerFrameManaBar"])

    def test_repeated_suppression_keeps_native_snapshot(self):
        self.check_round_trip("SuppressTargetFrame", "RestoreTargetFrame",
                              ["TargetFrame", "TargetFrameManaBar"], calls=2)

    def test_restore_without_suppression_leaves_native_events(self):
        lua = runtime()
        lua.execute('UF:RestorePlayerFrame(); UF:RestoreTargetFrame()')
        for name in NATIVE:
            self.assertEqual(registered(lua, name), set(NATIVE[name]), name)


def registered_in(text, function=None):
    """RegisterEvent names in one Lua function body, or in a whole file."""
    if function:
        start = text.index("function %s(" % function)
        text = text[start:text.index("\nend", start)]
    return re.findall(r'RegisterEvent\("([A-Z_]+)"\)', text)


@unittest.skipUnless(FRAMEXML.is_dir(), "Run tools/extract_framexml.py --client <client-root> first")
class NativeEventProvenanceTests(unittest.TestCase):
    def test_native_sets_match_the_deployed_framexml(self):
        def read(name):
            return (FRAMEXML / name).read_text("utf-8-sig")
        unit = read("UnitFrame.lua")
        self.assertEqual(registered_in(unit, "UnitFrame_Initialize"), UNIT_FRAME)
        self.assertEqual(registered_in(unit, "UnitFrameHealthBar_Initialize"), HEALTH_BAR)
        self.assertEqual(registered_in(unit, "UnitFrameManaBar_Initialize"), MANA_BAR)
        self.assertEqual(UNIT_FRAME + registered_in(read("PlayerFrame.lua"), "PlayerFrame_OnLoad"),
                         NATIVE["PlayerFrame"])
        self.assertEqual(UNIT_FRAME + registered_in(read("TargetFrame.lua"), "TargetFrame_OnLoad"),
                         NATIVE["TargetFrame"])
        self.assertEqual(registered_in(read("ComboFrame.xml")), NATIVE["ComboFrame"])


if __name__ == '__main__':
    unittest.main()
