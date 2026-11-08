"""FostercareTweaks audit, 2026-10-26 (AV session, /lag and the player's note).

- Auto Dismount: ClassicAPI's autoDismount/autoUnshift/autoStand do it
  (AutoDismountRetired keeps it from coming back).
- Event fan-out: ClassicAPI fires every unit event once per token, including
  nameplateN, markN and focus (docs/API.md, nameplate and mark tokens). The raid
  frames, target auras, energy ticks and target castbar register these events
  unfiltered, so in a battleground they run for every nameplate. In Lua 5.0
  each delivery also builds two tables in FT.SetEventHandler's vararg wrapper
  (docs/LuaCAPI.md, adjust_varargs). frame:RegisterUnitEvent filters in the
  engine.
- Chat Timestamps also stamped the combat log; Reagent Counter asked for the
  same reagent lists on every target or modifier change.

Ten tests fail on 1.5.0 (28a6eea). Three are controls that pass on it and
guard the fix: spell errors stay with ClassicAPI, stealth is never cancelled,
and a stale error does nothing.
Real UI_ERROR_MESSAGE texts, mount and form state and event rates stay
in-game checks.
"""
from pathlib import Path
import os
import unittest
from wowlua import LuaRuntime
# Instrumentation only, not the game's Lua: 5.4's debug.getinfo reports isvararg.
from lupa.lua54 import LuaRuntime as Lua54Runtime  # noqa: wowlua

ROOT = Path(os.environ["VANILLAFORGE_ADDON_ROOT"])


def source(name):
    return (ROOT / name).read_text("utf-8-sig")


# Frames record plain and unit-filtered registrations. fire() delivers an
# event the way the engine would: a RegisterUnitEvent filter drops other units.
BASE = r'''
NOOP = function() end
local W = {}
W.__index = function(_, k)
    local v = rawget(W, k)
    if v ~= nil then return v end
    if string.find(k, "^%u") then return NOOP end
end
function W:GetFont() return "f", 12, "" end
function W:GetWidth() return 36 end
function W:GetHeight() return 36 end
function W:GetFrameLevel() return 1 end
function W:GetNumPoints() return 0 end
function W:GetParent() return rawget(self, "parent") end
function W:GetName() return rawget(self, "name") end
function W:IsShown() return rawget(self, "shown") end
function W:IsVisible() return false end
function W:Show() rawset(self, "shown", true) end
function W:Hide() rawset(self, "shown", false) end
function W:CreateTexture() return setmetatable({}, W) end
function W:CreateFontString() return setmetatable({}, W) end
function W:GetScript(name) local s = rawget(self, "scripts"); return s and s[name] end
function W:SetScript(name, fn) local s = rawget(self, "scripts") or {}; s[name] = fn; rawset(self, "scripts", s) end
function W:RegisterEvent(ev)
    local r = rawget(self, "events") or {}; rawset(self, "events", r)
    if r[ev] == nil then r[ev] = true end
end
function W:RegisterUnitEvent(ev, ...)
    local r = rawget(self, "events") or {}; rawset(self, "events", r)
    local units = {}
    for i = 1, select("#", ...) do units[string.lower(select(i, ...))] = true end
    r[ev] = units
end
function W:UnregisterEvent(ev) local r = rawget(self, "events"); if r then r[ev] = nil end end
function W:UnregisterAllEvents() rawset(self, "events", {}) end
function Widget(props) return setmetatable(props or {}, W) end
frames = {}
function CreateFrame(_, name, parent)
    local f = Widget({ name = name, parent = parent })
    frames[#frames + 1] = f
    if name then _G[name] = f end
    return f
end
handlers = {}
calls = 0
function fire(frame, ev, unit, ...)
    local r = rawget(frame, "events")
    local reg = r and r[ev]
    if not reg then return false end
    if type(reg) == "table" and type(unit) == "string" and not reg[string.lower(unit)] then return false end
    local h = handlers[frame]
    if not h then return false end
    calls = calls + 1
    h(frame, ev, unit, ...)
    return true
end
UIParent, TargetFrame, PlayerFrame = Widget(), Widget(), Widget()
PlayerFrameManaBar = Widget()
Enum = { StatusBarInterpolation = { Immediate = 0 }, StatusBarTimerDirection = { ElapsedTime = 0, RemainingTime = 1 } }
C_DurationUtil = { CreateDuration = function() return { SetTimeSpan = function(self, s, e) self.startTime, self.endTime = s, e end } end }
C_Timer = { After = NOOP, NewTicker = function() return { Cancel = NOOP } end }
FostercareTweaks_Config = { overwrites = {} }
FT = { mods = {}, overwrites = {} }
FostercareTweaks = FT
function FT:register(m) self.mods[m.title] = m; return m end
function FT.SetEventHandler(frame, fn) handlers[frame] = fn end
function FT.IsEnabled(key, default)
    local v = FostercareTweaks_Config[key]
    if v == nil then return default ~= false end
    return v == 1
end
function FT.GetNumber(_, default) return default end
FT.hooksecurefunc, FT.HookScript, hooksecurefunc = NOOP, NOOP, NOOP
FT.RestoreFramePosition, FT.RegisterFrameMover = NOOP, NOOP
TargetofTargetFrame = { IsShown = function() return false end }
function UnitGUID(u) return "0x" .. u end
function UnitIsUnit(a, b) return a == b or (a == "raid5" and b == "target") end
function UnitExists() return true end
function UnitIsDeadOrGhost() return false end
function UnitPowerType() return 3 end
function UnitMana() return 50 end
function UnitManaMax() return 100 end
function GetTime() return 100 end
function table.wipe(t) for k in pairs(t) do t[k] = nil end return t end
'''


def runtime():
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(BASE)
    return lua


def gameplay(lua):
    lua.execute(r'''
        function UnitClass() return "Druid", "DRUID" end
        function FT.cmatch() end
        ShapeshiftBarFrame = Widget()
        SPELL_FAILED_ONLY_SHAPESHIFT = "Must be in %s" -- the client's GlobalStrings.lua
    ''')
    lua.execute(source("mods/gameplay.lua"))
    for title, mod in list(lua.eval("FT.mods").items()):
        lua.globals().FostercareTweaks_Config[title] = 1 if mod.enabled else 0
        if mod.enable:
            mod.enable(mod)
    return lua


def error_frames(lua):
    return [f for f in lua.eval("frames").values()
            if f.events and f.events["UI_ERROR_MESSAGE"]]


class AutoDismountRetired(unittest.TestCase):
    """2026-11-07: ClassicAPI 1.20.1's autoDismount/autoUnshift/autoStand act
    before attacks, flight masters, NPCs and items, so the UI_ERROR_MESSAGE
    fallback that did it a click late is gone."""

    def test_no_module_and_no_error_listener(self):
        # Auto Stance keeps its own UI_ERROR_MESSAGE frame.
        lua = gameplay(runtime())
        self.assertIsNone(lua.eval('FT.mods["Auto Dismount"]'))
        self.assertIsNone(lua.eval('FCTweaksAutoDismount'))
        self.assertEqual(len(error_frames(lua)), 1)


class NoVarargEventWrapper(unittest.TestCase):
    """Lua 5.0 builds a table for every call of a vararg function."""

    def test_event_delivery_calls_no_vararg_lua_function(self):
        lua = Lua54Runtime(unpack_returned_tuples=True)
        lua.execute(r'''
            NOOP = function() end
            FostercareTweaks = {}
            CreateFrame = function() return { SetScript = NOOP, RegisterEvent = NOOP, UnregisterAllEvents = NOOP } end
            hooksecurefunc = NOOP
            frame = { SetScript = function(self, n, fn) self[n] = fn end, GetScript = function(self, n) return self[n] end }
        ''')
        helpers = source("Helpers.lua")
        lua.execute(helpers[:helpers.index("-- One load watcher")]
                    .replace("local FT = FostercareTweaks", "FT = FostercareTweaks"))
        lua.execute(r'''
            seen = {}
            FT.SetEventHandler(frame, function(f, ev, unit) seen[#seen + 1] = ev .. ":" .. tostring(unit) end)
            varargs = 0
            debug.sethook(function()
                local info = debug.getinfo(2, "Su")
                if info and info.what == "Lua" and info.isvararg then varargs = varargs + 1 end
            end, "c")
            frame.OnEvent(frame, "UNIT_HEALTH", "raid3")
            debug.sethook()
        ''')
        self.assertEqual(lua.eval('seen[1]'), "UNIT_HEALTH:raid3")
        self.assertEqual(lua.eval('varargs'), 0)


class UnitEventsReachOnlyTheirUnits(unittest.TestCase):
    """Nameplate, mark and focus copies of unit events never reach these handlers."""

    def test_raid_frames_ignore_nameplates(self):
        lua = runtime()
        lua.execute(r'''
            UF = { Auras = { CreateAuraButton = function() return Widget() end, ResetAuraButton = NOOP } }
            FT.UnitFrames = UF
            function UF:CreateBar() return Widget() end
            FT.RegisterFrameMover = NOOP
            function FT.ClampNumber(v, d, lo, hi) return math.max(lo, math.min(hi, tonumber(v) or d)) end
        ''')
        lua.execute(source("mods/unitframes/raid.lua"))
        lua.execute('UF:EnableRaidFrames(true)')
        raid = lua.eval('FCTweaksRaidFrame')
        fire = lua.globals().fire
        for ev in ("UNIT_HEALTH", "UNIT_POWER_UPDATE", "UNIT_AURA", "UNIT_MAXHEALTH"):
            self.assertFalse(fire(raid, ev, "nameplate3"), ev)
            self.assertFalse(fire(raid, ev, "mark8"), ev)
        # Control: raid members still arrive.
        self.assertTrue(fire(raid, "UNIT_HEALTH", "raid40"))
        self.assertTrue(fire(raid, "UNIT_HEALTH", "party4"))

    def test_target_auras_listen_to_player_and_target_only(self):
        lua = runtime()
        lua.execute(r'''
            UF = {}
            FT.UnitFrames = UF
        ''')
        lua.execute(AuraCountdownIsNative.FORMATTER + "FT.Countdown = C_StringUtil.CreateNumericRuleFormatter()")
        lua.execute(source("mods/unitframes/auras.lua"))
        # RegisterUnitEvent filters every event whose first argument is a
        # unit (ClassicAPI docs), UNIT_AURA_DELTA too.
        lua.execute('reads = 0; UF.Auras.UpdateBlizzTargetAuras = function() reads = reads + 1 end')
        frame = lua.eval('FCTweaksAuraEventFrame')
        fire = lua.globals().fire
        full = lua.eval('{ isFullUpdate = true }')
        fire(frame, "UNIT_AURA_DELTA", "nameplate1", full)
        # The target is also raid5: its own "target" event already rescans it.
        fire(frame, "UNIT_AURA_DELTA", "raid5", full)
        self.assertEqual(lua.eval('reads'), 0)
        fire(frame, "UNIT_AURA_DELTA", "target", full)
        self.assertEqual(lua.eval('reads'), 1)

    def test_energy_ticks_listen_to_the_player_only(self):
        lua = runtime()
        lua.execute('FostercareTweaks_Config["Show Energy Ticks"] = 0')
        lua.execute(source("mods/unitframe-energytick.lua"))
        lua.execute('FT.mods["Show Energy Ticks"]:enable()')
        frame = lua.eval('FCTweaksEnergyTick')
        fire = lua.globals().fire
        for ev in ("UNIT_POWER_UPDATE", "UNIT_DISPLAYPOWER"):
            self.assertFalse(fire(frame, ev, "raid7"), ev)
            self.assertFalse(fire(frame, ev, "nameplate2"), ev)
        self.assertTrue(fire(frame, "UNIT_POWER_UPDATE", "player"))

    def test_target_castbar_skips_other_casters_and_swings(self):
        lua = runtime()
        lua.execute(r'''
            C_Spell = { UnitCastingInfo = NOOP, UnitChannelInfo = NOOP }
        ''')
        lua.execute(source("mods/target-castbar.lua"))
        lua.execute('FT.mods["Enemy Castbars"]:enable()')
        frame = lua.eval('FCTweaksTargetCastbarEvents')
        fire = lua.globals().fire
        # SuperWoW's UNIT_CASTEVENT fires for every nearby cast and swing;
        # UNIT_SPELLCAST_* already fire for the "target" token.
        self.assertFalse(fire(frame, "UNIT_CASTEVENT", "0xF130001", "0x2", "MAINHAND", 6603, 0))
        self.assertFalse(fire(frame, "UNIT_SPELLCAST_START", "nameplate4"))
        self.assertTrue(fire(frame, "UNIT_SPELLCAST_START", "target"))


class ChatTimestampsSkipCombatLog(unittest.TestCase):
    """Combat lines are unique: a stamp built a new ~110 B string per line, in a
    window the other chat modules already leave alone."""

    def test_combat_window_stays_unstamped(self):
        lua = runtime()
        lua.execute(r'''
            NUM_CHAT_WINDOWS = 2
            got = {}
            ChatFrame1 = { AddMessage = function(_, msg) got[1] = msg end }
            ChatFrame2 = { combat = true, AddMessage = function(_, msg) got[2] = msg end }
            function FT.IsCombatChatFrame(cf) return cf.combat == true end
            FT.rgbhex = function() return "|cffcccccc" end
            function date() return "18:21:57" end
        ''')
        lua.execute(source("mods/chat-tweaks.lua"))
        lua.execute(r'''
            local m = FT.mods["Chat Timestamps"]; m.config = {}; m:enable()
            ChatFrame1:AddMessage("hello")
            ChatFrame2:AddMessage("Grunt hits you for 12.")
        ''')
        self.assertEqual(lua.eval('got[2]'), "Grunt hits you for 12.")
        self.assertIn("18:21:57", lua.eval('got[1]'))


RAID_ROSTER = r'''
    UF = { Auras = { CreateAuraButton = function() return Widget() end, ResetAuraButton = NOOP,
        UpdateAuraTiming = NOOP, StyleBorder = NOOP },
        ClassColors = { ROGUE = { r = 1, g = 1, b = 0 } }, PowerColors = { [0] = { r = 0, g = 0, b = 1 } } }
    FT.UnitFrames = UF
    function UF:CreateBar() return Widget() end
    function UF.SetFontSize() end
    function UF:IsRaidShowHoT() return true end
    function UF:IsRaidShowDebuffs() return true end
    function UF:IsRaidShowAggro() return false end
    function UF:GetRaidHealthFormat() return "deficit" end
    function FT.GetUnitHealthValues() return 100, 100 end
    FT.RegisterFrameMover = NOOP
    function FT.ClampNumber(v, d, lo, hi) return math.max(lo, math.min(hi, tonumber(v) or d)) end
    function FT.NormalizeClass(c) return c end
    function AbbreviateNumbers(n) return n end
    timers = {}
    C_Timer.After = function(_, fn) timers[#timers + 1] = fn end
    function runTimers() local t = timers; timers = {}; for _, fn in ipairs(t) do fn() end end
    members, ranks = 40, {}
    function GetNumRaidMembers() return members end
    function GetNumPartyMembers() return 0 end
    function GetRaidRosterInfo(i)
        return "Member" .. i, ranks[i] or 0, math.floor((i - 1) / 5) + 1, 60, "Rogue", "ROGUE", "AV", 1
    end
    rebuilds = 0
    function UnitClass() rebuilds = rebuilds + 1; return "Rogue", "ROGUE" end
    UNKNOWNOBJECT = "Unknown"
    function UnitName() return "x" end
    function UnitIsConnected() return true end
    function UnitIsGhost() return false end
    function UnitManaMax() return 100 end
    function UnitPowerType() return 3 end
    function UnitInRange() return true end
    function UnitCanAttack() return false end
    function GetRaidTargetIndex() end
    C_UnitAuras = { GetAuraSlots = function() return nil, 0 end }
    FT.GetRaidMarkSettings = function() return 14, "portrait" end
'''


class RaidRosterRebuildsOnlyChanges(unittest.TestCase):
    """AV: roster events arrive in bursts and rarely change who sits where."""

    def setUp(self):
        self.lua = runtime()
        self.lua.execute(RAID_ROSTER)
        self.lua.execute(source("mods/unitframes/raid.lua"))
        self.lua.execute('UF:EnableRaidFrames(true); UF:UpdateGroupRoster(true); rebuilds = 0')

    def fire_roster(self, times):
        self.lua.execute('for i = 1, %d do fire(FCTweaksRaidFrame, "RAID_ROSTER_UPDATE") end; runTimers()' % times)

    def test_a_burst_is_one_pass_and_an_unchanged_roster_rebuilds_nothing(self):
        self.fire_roster(10)
        self.assertEqual(self.lua.eval('rebuilds'), 0)

    def test_a_changed_member_is_rebuilt(self):
        self.lua.execute('ranks[7] = 1')
        self.fire_roster(3)
        self.assertEqual(self.lua.eval('rebuilds'), 1)

    def test_group_sizes_are_read_without_a_new_table(self):
        self.assertTrue(self.lua.eval('UF:GetGroupDimensions() == UF:GetGroupDimensions()'))


class AuraCountdownIsNative(unittest.TestCase):
    """The aura time is the client's: a Cooldown formatter, no ticker, no per-icon text.

    The formatter mock follows the documented rules (the breakpoint is chosen
    before rounding); it proves our breakpoints and colours, not the engine.
    """

    FORMATTER = r'''
        Enum = { NumericRuleFormatRounding = { Nearest = 0, Up = 1, Down = 2 } }
        local function round(v, step, mode)
            if not step or step <= 0 then return v end
            local q = v / step
            if mode == 1 then q = math.ceil(q - 1e-9) elseif mode == 2 then q = math.floor(q) else q = math.floor(q + 0.5) end
            return q * step
        end
        C_StringUtil = { CreateNumericRuleFormatter = function()
            local f = { points = {} }
            function f:SetBreakpoints(list) self.points = list end
            function f:FormatNumber(n)
                local best
                for _, p in ipairs(self.points) do
                    if n >= p.threshold and (not best or p.threshold > best.threshold) then best = p end
                end
                local v = round(n, best.step, best.rounding)
                if best.components then
                    local c = best.components[1]
                    return string.format(best.format, round(v / c.div, c.step, c.rounding))
                end
                return string.format(best.format, v)
            end
            return f
        end }
    '''

    def formatter(self):
        lua = runtime()
        lua.execute(self.FORMATTER)
        helpers = source("Helpers.lua").replace("\r\n", "\n")
        lua.execute(helpers[helpers.index("do\n    local Up"):helpers.index("local borderDef")])
        return lua

    def test_labels_keep_the_old_colours_and_units(self):
        lua = self.formatter()
        for seconds, text in ((3.24, "|cffff4444" + "3.3|r"), (7.2, "|cffffff33" + "8|r"), (30.1, "|cffffffff" + "31|r"),
                              (125, "|cffffffff" + "3m|r"), (7300, "|cffffffff" + "3h|r"), (90000, "|cffffffff" + "2d|r")):
            self.assertEqual(lua.eval("FT.Countdown:FormatNumber(%s)" % seconds), text, seconds)

    def test_no_ticker_and_no_per_icon_text(self):
        auras = source("mods/unitframes/auras.lua")
        for gone in ("NewTicker", "durationText", "timedButtons", "UpdateAuraTimes"):
            self.assertNotIn(gone, auras)

    def test_timing_starts_the_sweep_once(self):
        lua = runtime()
        auras = source("mods/unitframes/auras.lua").replace("\r\n", "\n")
        lua.execute("function UnitGUID() return '0x1' end")
        lua.execute(auras[auras.index("local function UpdateAuraTiming"):auras.index("Auras.UpdateAuraTiming =")]
                    + "\nTiming = UpdateAuraTiming")
        lua.execute(r'''
            starts = 0
            btn = Widget({ cooldown = Widget({ SetCooldown = function() starts = starts + 1 end, Clear = NOOP }) })
            Timing(btn, "0x1", 5, nil, 20, 1020, 1000)
            Timing(btn, "0x1", 5, nil, 20, 1020, 1005)
        ''')
        self.assertEqual(lua.eval("starts"), 1)
        self.assertEqual(lua.eval("btn.expirationTime"), 1020)


if __name__ == "__main__":
    unittest.main()
