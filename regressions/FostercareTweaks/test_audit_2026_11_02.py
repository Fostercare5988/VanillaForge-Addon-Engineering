"""FostercareTweaks audit, 2026-11-02 (.private/audit-FostercareTweaks-2026-11-02.md).

Bugs (each fails on 192e14d):
- The target cast bar wrote its texture paths with one backslash per separator.
  Lua 5.0 drops an unknown escape's backslash, so the fill, the background and
  the spark named files that do not exist.
- The party grid gave the leader's crown only to the player: a party member
  who led never showed it, and a leader change did not read the roster again.
- Defaults.lua still carried the retired "WorldMap Window" switch, so a new
  character's first login switched the account's world map to windowed.

Old code and hot paths: three chat AddMessage wrappers, raid health events
that rewrote name and class and built text every time, aura deltas of every
nameplate and mark token, world map coordinates resolved by name with a table
every 0.1 s, a closure per Extra Rows refresh, unread module fields, aliases
and vararg wrappers. Options: nine switches every character leaves on, and
developer slash commands.

Every test fails on 192e14d except SlashCommands.test_the_documented_commands_stay
(a control). Widget mocks record our calls; drawing stays an in-game check.
"""
import re
import sys
import unittest
from pathlib import Path
from wowlua import LuaRuntime

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

from test_audit_2026_10_25 import source
from test_audit_2026_10_26 import RAID_ROSTER, runtime
from test_audit_2026_11_01 import CORE_PRELUDE
from test_event_fanout import BASE, ROOT
from test_unitframe_hot_paths import RAID, WIDGETS, raid_runtime, slice

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
        lua.execute(source("Core.lua") + "\nif FostercareTweaks then FostercareTweaks.ActionBars = { Initialize = function() end } end")
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


# Old code and hot paths (each fails on 192e14d).

class ChatHasOneWrapper(unittest.TestCase):
    """Links, timestamps and class colours each wrapped AddMessage: three calls
    and three wrappers per chat line. One wrapper now runs their filters."""

    def setUp(self):
        lua = self.lua = runtime()
        lua.execute(r'''
            NUM_CHAT_WINDOWS = 2
            got = {}
            ChatFrame1 = { AddMessage = function(_, text) got[1] = text end }
            ChatFrame2 = { combat = true, AddMessage = function(_, text) got[2] = text end }
            native2 = ChatFrame2.AddMessage
            function FT.IsCombatChatFrame(cf) return cf.combat == true end
            function FT.GetPlayerClass(name) return name == "Jaina" and "MAGE" or nil end
            FT.rgbhex = function() return "|cff3fc7eb" end
            RAID_CLASS_COLORS = { MAGE = {} }
            function date() return "[12:00:00] " end
            function SetItemRef() end
        ''')
        lua.execute(source("mods/chat-tweaks.lua"))
        lua.execute('FT.mods["Chat Hyperlinks"]:enable(); wrapped = ChatFrame1.AddMessage')
        lua.execute('FT.mods["Chat Timestamps"]:enable(); FT.mods["Chat Class Colors"]:enable()')

    def test_one_wrapper_runs_every_filter(self):
        self.assertTrue(self.lua.eval("ChatFrame1.AddMessage == wrapped"))
        self.lua.execute('ChatFrame1:AddMessage("|Hplayer:Jaina|h[Jaina]|h: see www.example.com")')
        line = self.lua.eval("got[1]")
        self.assertTrue(line.startswith("[12:00:00] "), line)
        self.assertIn("|cff3fc7ebJaina", line)
        self.assertIn("|Hurl:www.example.com|h", line)

    def test_combat_log_is_left_alone(self):
        self.assertTrue(self.lua.eval("ChatFrame2.AddMessage == native2"))


class RaidHealthPath(unittest.TestCase):
    def test_health_events_leave_name_and_class_alone(self):
        lua = raid_runtime()
        lua.execute('classes = 0; function UnitClass() classes = classes + 1; return "Mage", "MAGE" end')
        lua.execute('Health(btn); Health(btn); Health(btn)')
        self.assertEqual(lua.eval("classes"), 0)

    def test_the_text_is_built_only_when_its_number_changes(self):
        lua = raid_runtime()
        lua.execute('built = 0; function AbbreviateNumbers(n) built = built + 1; return n end')
        lua.execute('Health(btn); Health(btn); Health(btn)')
        self.assertEqual(lua.eval("built"), 1)
        lua.execute('FT.GetUnitHealthValues = function() return 2500, 4000 end; Health(btn)')
        self.assertEqual(lua.eval("built"), 2)                        # control
        self.assertEqual(lua.eval("btn.healthText.text"), "-1500")

    def test_a_rebuilt_button_writes_its_text_again(self):
        # The test grid writes the text itself; a roster pass after it must not
        # trust the remembered number.
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute(WIDGETS)
        lua.execute(PARTY)
        lua.execute(slice(RAID, "-- Unit events keep a member current. A roster", "-- Roster events come in bursts",
                          "-- force: rebuild every button"))
        lua.execute("groups[1].buttons[1].fctHealthShown = 5; UF:UpdateGroupRoster(true)")
        self.assertIsNone(lua.eval("groups[1].buttons[1].fctHealthShown"))


class MemberEventsOnly(unittest.TestCase):
    def setUp(self):
        lua = self.lua = runtime()
        lua.execute(RAID_ROSTER)
        lua.execute(source("mods/unitframes/raid.lua"))
        lua.execute("UF:EnableRaidFrames(true)")

    def test_aura_changes_of_other_tokens_never_arrive(self):
        fire = self.lua.globals().fire
        frame = self.lua.eval("FCTweaksRaidFrame")
        full = self.lua.eval("{ isFullUpdate = true }")
        for unit in ("nameplate3", "mark2", "focus", "target"):
            self.assertFalse(fire(frame, "UNIT_AURA_DELTA", unit, full), unit)
        self.assertTrue(fire(frame, "UNIT_AURA_DELTA", "raid3", full))     # control

    def test_level_changes_are_not_heard(self):
        # The buttons show no level.
        self.assertFalse(self.lua.globals().fire(self.lua.eval("FCTweaksRaidFrame"), "UNIT_LEVEL", "raid3"))


class WorldMapCoordinates(unittest.TestCase):
    def setUp(self):
        lua = self.lua = runtime()
        lua.execute(r'''
            texts = {}
            local create = CreateFrame
            function CreateFrame(kind, name, parent)
                local f = create(kind, name, parent)
                f.CreateFontString = function()
                    local t = { sets = 0, SetPoint = NOOP }
                    function t:SetText(s) self.value = s; self.sets = self.sets + 1 end
                    texts[name] = t
                    return t
                end
                return f
            end
            WorldMapButton = Widget()
            function WorldMapButton:GetLeft() return 0 end
            function WorldMapButton:GetTop() return 400 end
            function WorldMapButton:GetWidth() return 400 end
            function WorldMapButton:GetHeight() return 400 end
            function WorldMapButton:GetEffectiveScale() return 1 end
            over, px, py = false, 0.4567, 0.123
            function MouseIsOver() return over end
            function GetCursorPosition() return 100, 300 end
            function GetPlayerMapPosition(unit) return px, py end
            arg1 = 0.2
        ''')
        lua.execute(source("mods/worldmap-window.lua"))
        lua.execute('FT.mods["WorldMap Coordinates"]:enable(); tick = FCTweaksWorldMapCursorCoords.scripts.OnUpdate')

    def test_the_shown_map_gives_the_position(self):
        self.lua.execute("tick()")
        self.assertEqual(self.lua.eval("texts.FCTweaksWorldMapPlayerCoords.value"), "|cffffcc00Player: |r45.7 / 12.3")
        self.assertEqual(self.lua.eval("texts.FCTweaksWorldMapCursorCoords.value"), "|cffffcc00Cursor: |rN/A")
        self.lua.execute("over = true; tick()")
        self.assertEqual(self.lua.eval("texts.FCTweaksWorldMapCursorCoords.value"), "|cffffcc00Cursor: |r25.0 / 25.0")

    def test_off_the_shown_map_is_n_a(self):
        self.lua.execute("px, py = 0, 0; tick()")
        self.assertEqual(self.lua.eval("texts.FCTweaksWorldMapPlayerCoords.value"), "|cffffcc00Player: |rN/A")

    def test_an_unchanged_position_writes_nothing(self):
        self.lua.execute("tick(); tick(); tick()")
        self.assertEqual(self.lua.eval("texts.FCTweaksWorldMapPlayerCoords.sets"), 1)


class ExtraRowsQueueOneCallback(unittest.TestCase):
    def setUp(self):
        lua = self.lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute(r'''
            EA, refreshed, callbacks = {}, 0, {}
            function RefreshVisible() refreshed = refreshed + 1 end
            C_Timer = { After = function(_, fn) callbacks[#callbacks + 1] = fn end }
        ''')
        lua.execute(slice(source("ExtraActions.lua"), "-- One callback for every queued refresh", "local function SyncOwner")
                    + "\nQueue = QueueRefresh")

    def test_a_burst_is_one_refresh_through_one_function(self):
        self.lua.execute("Queue(); Queue(); Queue(); callbacks[1](); Queue(); callbacks[2]()")
        self.assertEqual(self.lua.eval("#callbacks"), 2)
        self.assertEqual(self.lua.eval("refreshed"), 2)
        self.assertTrue(self.lua.eval("callbacks[1] == callbacks[2]"))

    def test_hidden_rows_drop_a_queued_refresh(self):
        self.lua.execute("Queue(); EA.pending = nil; callbacks[1]()")      # SyncOwner hid the rows
        self.assertEqual(self.lua.eval("refreshed"), 0)


class OldCodeIsGone(unittest.TestCase):
    def test_modules_carry_no_unread_fields(self):
        for path in sorted((ROOT / "mods").rglob("*.lua")):
            text = path.read_text("utf-8-sig")
            self.assertNotRegex(text, r'\b(description|category) = "', path.name)
        self.assertNotIn("mod.category", source("Core.lua"))

    def test_no_aliases_for_client_functions(self):
        helpers = source("Helpers.lua")
        for alias in ("FT.hooksecurefunc =", "FT.Abbreviate =", "FT.TimeConvert ="):
            self.assertNotIn(alias, helpers)
        self.assertNotIn("UF.GetUnitHealthValues =", source("mods/unitframes/core.lua"))

    def test_native_group_wrappers_take_fixed_arguments(self):
        # Lua 5.0 builds a table for every call of a ... function.
        self.assertNotIn("function(...)", source("mods/unitframes/native-group.lua"))

    def test_one_chat_file(self):
        self.assertFalse((ROOT / "mods/chat-class-colors.lua").exists())
        self.assertNotIn("chat-class-colors", source("FostercareTweaks.toc"))


# Options (each fails on 192e14d).

RETIRED = {"Sell Junk": "mods/sell-junk.lua", "Vendor Values": "mods/vendor-values.lua",
           "Item Rarity Borders": "mods/item-colors.lua", "Equip Compare": "mods/equip-compare.lua",
           "Chat Hyperlinks": "mods/chat-tweaks.lua", "WorldMap Coordinates": "mods/worldmap-window.lua",
           "WorldMap Class Colors": "mods/worldmap-window.lua", "Real Health Numbers": "mods/health-numbers.lua",
           "Clear Raid Target Marks": "mods/raid-target-marks.lua"}


class SwitchesEveryoneLeavesOn(unittest.TestCase):
    """All ten characters had these on; none has a reason to turn them off."""

    def test_they_are_always_on_and_have_no_switch(self):
        settings = source("Settings.lua")
        for title, path in RETIRED.items():
            self.assertRegex(source(path), r'title = "%s",\s*always = true,' % re.escape(title), title)
            self.assertNotIn('"%s"' % title, settings, title)

    def test_their_saved_switch_is_cleared_and_they_start(self):
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute((CORE_PRELUDE % "2.2").replace("FostercareTweaks_Config = { overwrites = {} }",
                                                     'FostercareTweaks_Config = { overwrites = {}, ["Vendor Values"] = 0 }'))
        lua.execute(source("Core.lua") + "\nif FostercareTweaks then FostercareTweaks.ActionBars = { Initialize = function() end } end")
        lua.execute(source("mods/vendor-values.lua").split("module.enable =")[0]
                    + "started = 0; module.enable = function() started = started + 1 end")
        lua.execute("FostercareTweaks:Initialize()")
        self.assertIsNone(lua.eval('FostercareTweaks_Config["Vendor Values"]'))
        self.assertEqual(lua.eval("started"), 1)

    def test_the_window_says_what_is_always_on(self):
        self.assertIn("Always on: sell prices, Shift to compare", source("Settings.lua"))


class SlashCommands(unittest.TestCase):
    def setUp(self):
        lua = self.lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute((CORE_PRELUDE % "2.2") + r'''
            function strsplittable(sep, str)
                local t = {}
                for w in string.gmatch(str, "[^" .. sep .. "]+") do t[#t + 1] = w end
                return t
            end
            function ReloadUI() reloaded = true end
        ''')
        lua.execute(source("Core.lua") + "\nif FostercareTweaks then FostercareTweaks.ActionBars = { Initialize = function() end } end")
        lua.execute(r'''
            opened, resized = {}, 0
            FostercareTweaks.OpenSettings = function(page) opened[#opened + 1] = page or "toggle" end
            FostercareTweaks.UnitFrames = {
                ApplyGroupDimensions = function() resized = resized + 1 end,
                GetGroupDimensions = function() return { width = 64, height = 34, scale = 1 } end,
                ToggleRaidTest = function() raidTest = true end }
            slash = SlashCmdList["FOSTERCARETWEAKS"]
        ''')

    def test_pages_and_the_window(self):
        self.lua.execute('slash(""); slash("UF"); slash("raid"); slash("bars"); slash("options")')
        self.assertEqual(list(self.lua.eval("opened").values()), ["toggle", "unit", "raid", "bars", "toggle"])

    def test_developer_commands_are_gone(self):
        # The window has these sliders; /ft <key> <value> wrote any setting unchecked.
        self.lua.execute('slash("groupsize 80 40"); slash("groupscale 2"); slash("raid_buff_count 8"); slash("reset")')
        self.assertEqual(self.lua.eval("resized"), 0)
        self.assertIsNone(self.lua.eval("FostercareTweaks_Config.overwrites.raid_buff_count"))
        self.assertIsNone(self.lua.eval("reloaded"))

    def test_the_documented_commands_stay(self):
        self.lua.execute('slash("testraid")')
        self.assertTrue(self.lua.eval("raidTest"))
        self.lua.execute('FostercareTweaks_Config.unitframe_positions = {}; slash("resetuf")')
        self.assertIsNone(self.lua.eval("FostercareTweaks_Config.unitframe_positions"))
        self.assertTrue(self.lua.eval("reloaded"))


if __name__ == "__main__":
    unittest.main()
