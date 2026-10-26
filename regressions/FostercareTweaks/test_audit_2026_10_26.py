"""FostercareTweaks audit, 2026-10-26 (AV session, /lag and the player's note).

- Auto Dismount: e813b8c handed it to ClassicAPI's autoDismount/autoUnshift/
  autoStand. Those act only before a spell cast (ClassicAPI docs/API.md, "Cast
  settings"), so melee attack, flight masters, talking to NPCs and items in a
  form no longer dismount or leave the form. The player misses it.
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
from lupa.lua51 import LuaRuntime
from lupa.lua54 import LuaRuntime as Lua54Runtime

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
        mounted, form, stealthed = false, 0, false
        dismounts, cancels, stands = 0, 0, 0
        function IsMounted() return mounted end
        function Dismount() dismounts = dismounts + 1 end
        function GetShapeshiftFormID() return form end
        function IsStealthed() return stealthed end
        function CancelShapeshiftForm() cancels = cancels + 1 end
        function SitOrStand() stands = stands + 1 end
        function UnitClass() return "Druid", "DRUID" end
        function FT.cmatch() end
        CastingBarFrame, ShapeshiftBarFrame = Widget(), Widget()
    ''')
    for key, text in (
        ("SPELL_FAILED_NOT_MOUNTED", "You are mounted"),
        ("SPELL_FAILED_NOT_SHAPESHIFT", "You are in shapeshift form"),
        ("SPELL_FAILED_NOT_STANDING", "You must be standing to do that"),
        ("ERR_ATTACK_MOUNTED", "Can't attack while mounted."),
        ("ERR_TAXIPLAYERALREADYMOUNTED", "You are already mounted! Dismount first."),
        ("ERR_TAXIPLAYERSHAPESHIFTED", "You can't take a taxi while shapeshifted!"),
        ("ERR_CANT_INTERACT_SHAPESHIFTED", "Can't speak while shapeshifted."),
        ("ERR_NO_ITEMS_WHILE_SHAPESHIFTED", "Can't use items while shapeshifted."),
        ("SPELL_FAILED_ONLY_SHAPESHIFT", "Must be in %s"),
    ):  # texts from the client's GlobalStrings.lua
        lua.execute('%s = "%s"' % (key, text))
    lua.execute(source("mods/gameplay.lua"))
    for title, mod in list(lua.eval("FT.mods").items()):
        lua.globals().FostercareTweaks_Config[title] = 1 if mod.enabled else 0
        if mod.enable:
            mod.enable(mod)
    return lua


def error_frames(lua):
    return [f for f in lua.eval("frames").values()
            if f.events and f.events["UI_ERROR_MESSAGE"]]


def ui_error(lua, message):
    for frame in error_frames(lua):
        lua.globals().fire(frame, "UI_ERROR_MESSAGE", message)


class AutoDismountFallback(unittest.TestCase):
    def setUp(self):
        self.lua = gameplay(runtime())

    def test_melee_attack_while_mounted_dismounts(self):
        self.lua.execute('mounted = true')
        ui_error(self.lua, "Can't attack while mounted.")
        self.assertEqual(self.lua.eval('dismounts'), 1)

    def test_flight_master_while_mounted_dismounts(self):
        self.lua.execute('mounted = true')
        ui_error(self.lua, "You are already mounted! Dismount first.")
        self.assertEqual(self.lua.eval('dismounts'), 1)

    def test_npc_and_items_in_a_form_leave_it(self):
        self.lua.execute('form = 5')
        ui_error(self.lua, "Can't speak while shapeshifted.")
        ui_error(self.lua, "Can't use items while shapeshifted.")
        self.assertEqual(self.lua.eval('cancels'), 2)

    def test_stealth_is_never_cancelled(self):
        # CancelShapeshiftForm also cancels Stealth (ClassicAPI docs).
        self.lua.execute('form, stealthed = 0, true')
        ui_error(self.lua, "Can't speak while shapeshifted.")
        self.assertEqual(self.lua.eval('cancels'), 0)

    def test_spell_errors_stay_with_classicapi(self):
        # Control (passes on 1.5.0): casts belong to the autoDismount /
        # autoUnshift / autoStand settings, so nothing acts twice.
        self.lua.execute('mounted, form = true, 5')
        for text in ("You are mounted", "You are in shapeshift form", "You must be standing to do that"):
            ui_error(self.lua, text)
        self.assertEqual(self.lua.eval('dismounts + cancels + stands'), 0)

    def test_stale_error_does_nothing(self):
        # The error arrives after the player already dismounted or left the form.
        ui_error(self.lua, "Can't attack while mounted.")
        ui_error(self.lua, "Can't speak while shapeshifted.")
        self.assertEqual(self.lua.eval('dismounts + cancels'), 0)


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
        for ev in ("UNIT_HEALTH", "UNIT_MANA", "UNIT_AURA", "UNIT_MAXHEALTH"):
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
        lua.execute(source("mods/unitframes/auras.lua"))
        lua.execute('UF.Auras.UpdateBlizzTargetAuras = NOOP')
        frame = lua.eval('FCTweaksAuraEventFrame')
        fire = lua.globals().fire
        self.assertFalse(fire(frame, "UNIT_AURA", "nameplate1"))
        # The target is also raid5: its own "target" event already rescans it.
        self.assertFalse(fire(frame, "UNIT_AURA", "raid5"))
        self.assertTrue(fire(frame, "UNIT_AURA", "target"))

    def test_energy_ticks_listen_to_the_player_only(self):
        lua = runtime()
        lua.execute('FostercareTweaks_Config["Show Energy Ticks"] = 0')
        lua.execute(source("mods/unitframe-energytick.lua"))
        lua.execute('FT.mods["Show Energy Ticks"]:enable()')
        frame = lua.eval('FCTweaksEnergyTick')
        fire = lua.globals().fire
        for ev in ("UNIT_MANA", "UNIT_ENERGY", "UNIT_DISPLAYPOWER"):
            self.assertFalse(fire(frame, ev, "raid7"), ev)
            self.assertFalse(fire(frame, ev, "nameplate2"), ev)
        self.assertTrue(fire(frame, "UNIT_ENERGY", "player"))

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
        ct = source("mods/chat-tweaks.lua")
        lua.execute(ct[ct.index("do\n-- Adds timestamps"):])
        lua.execute(r'''
            local m = FT.mods["Chat Timestamps"]; m.config = {}; m:enable()
            ChatFrame1:AddMessage("hello")
            ChatFrame2:AddMessage("Grunt hits you for 12.")
        ''')
        self.assertEqual(lua.eval('got[2]'), "Grunt hits you for 12.")
        self.assertIn("18:21:57", lua.eval('got[1]'))


class ReagentListsAskedOnce(unittest.TestCase):
    """GetSpellReagents returns a new table per call; Spell.dbc never changes."""

    def test_macro_rescans_reuse_the_reagent_answer(self):
        lua = runtime()
        lua.execute(r'''
            NUM_ACTIONBAR_BUTTONS = 12
            asked = 0
            C_Spell = { GetSpellReagents = function() asked = asked + 1; return { { itemID = 17020, count = 1 } } end,
                GetSpellCastCount = function() return 5 end }
            function GetActionInfo(slot) if slot <= 10 then return "macro", slot end end
            function GetMacroSpell() return "Arcane Brilliance", "Rank 1", 23028 end
        ''')
        lua.execute(source("mods/actionbar-reagents.lua"))
        lua.execute(r'''
            FT.mods["Reagent Counter"]:enable()
            local frame = FCTweaksReagentCount
            for i = 1, 50 do fire(frame, "MODIFIER_STATE_CHANGED", "LSHIFT", i % 2) end
        ''')
        self.assertEqual(lua.eval('asked'), 1)


if __name__ == "__main__":
    unittest.main()
