"""Nameplates 1.0 (written new, 2026-11-22) on the shared game model (wowkit).

The game is modelled as ClassicAPI documents it (docs/API.md): a default plate
is a frame whose first child is the health bar and whose regions are, in the
order the old addon found in play, border, glow, name, level, skull and raid
icon (### Reading region content from a default nameplate); the units behind
the plate tokens, their health, auras (### C_UnitAuras.UnitAura, GetAuraSlots'
fill form, UnitAuraBySlot), casts (### C_Spell.UnitCastingInfo /
UnitChannelInfo, times in GetTime() milliseconds) and spells
(### C_Spell.GetSpellInfo, ### GetSpellBaseCooldown). Cooldown, duration and
formatter objects record what they are given. Nothing is drawn.

What the kit could model for every suite (this file stubs it, wowkit.py is
not edited while other builds run): frame levels, StatusBar colour and
SetTimerDuration, Cooldown frames (SetCooldown, Clear, OnCooldownDone),
C_DurationUtil and C_StringUtil formatters, the Enum tables, and default
nameplates with plate tokens (NAME_PLATE_UNIT_ADDED / _REMOVED).
"""
from pathlib import Path
import os
import wowkit

ROOT = Path(os.environ["VANILLAFORGE_ADDON_ROOT"])

MOCK = r'''
CLASSIC_API_VERSION = 12302
STANDARD_TEXT_FONT = "Fonts\\FRIZQT__.TTF"
RAID_CLASS_COLORS = {
    ROGUE = { r = 1, g = 0.96, b = 0.41 }, MAGE = { r = 0.41, g = 0.8, b = 0.94 },
    WARRIOR = { r = 0.78, g = 0.61, b = 0.43 }, PALADIN = { r = 0.96, g = 0.55, b = 0.73 },
}
Enum = {
    StatusBarTimerDirection = { ElapsedTime = 0, RemainingTime = 1 },
    StatusBarInterpolation = { Immediate = 0, ExponentialEaseOut = 1 },
    NumericRuleFormatRounding = { Nearest = 0, Up = 1, Down = 2 },
}
calls = {}
function count(name) return calls[name] or 0 end
local function tally(name) calls[name] = (calls[name] or 0) + 1 end
function forget() calls = {} end

-- Widgets: what the addon writes and the tests read back.
function Widget:GetFrameLevel() return self.level or 1 end
function Widget:SetFrameLevel(l) self.level = l end
function Widget:SetStatusBarColor(r, g, b) self.barColor = r .. "," .. g .. "," .. b end
function Widget:SetFont(font, size, flags) self.fontSize, self.noFont = size, nil; if self.native then touch(self, "SetFont") end end
function Widget:SetTexture(path) self.texture = path end
function Widget:SetTimerDuration(d, interpolation, direction) self.timer, self.direction = d, direction; tally("SetTimerDuration") end
function Widget:SetCooldown(start, duration) self.cdStart, self.cdDuration = start, duration; tally("SetCooldown") end
function Widget:Clear() self.cdStart, self.cdDuration = nil, nil end
function Widget:SetCountdownFormatter(f) self.formatter = f end
function Widget:SetMinMaxValues(lo, hi) self.min, self.max = lo, hi end
function Widget:SetValue(v) self.value = v; tally("SetValue") end
function Widget:SetText(text)
    if self.noFont then error("<unnamed>:SetText(): Font not set") end
    self.text = text; tally("SetText")
end
function Widget:SetAlpha(a) self.alpha = a; if self.native then touch(self, "SetAlpha") end end
-- A spy on the game's own regions: what the addon calls on them.
touched = {}
function touch(w, what) touched[#touched + 1] = what end
for _, m in ipairs({ "SetPoint", "SetWidth", "SetHeight", "SetScale", "ClearAllPoints" }) do
    local stock = Widget[m]
    Widget[m] = function(self, a, b, c, d, e)
        if self.native then touch(self, m) end
        if stock then return stock(self, a, b, c, d, e) end
    end
end

C_DurationUtil = { CreateDuration = function()
    return { SetTimeSpan = function(self, s, e) self.from, self.to = s, e end }
end }
C_StringUtil = { CreateNumericRuleFormatter = function()
    return { SetBreakpoints = function(self, b) self.breakpoints = b end }
end }
function AbbreviateNumbers(n)
    if n >= 10000 then return math.floor(n / 1000) .. "K" end
    if n >= 1000 then return math.floor(n / 100) / 10 .. "K" end
    return tostring(n)
end
function SetRaidTargetIconTexture(tex, index) tex.markIndex = index end

-- The world: the player, the target and the units behind the plate tokens.
playerClass, combo, targetGUID = "ROGUE", 0, nil
units = {}  -- "nameplateN" -> { guid, class, player, enemy, hp, max, target (a GUID), mark, auras, cast, channel }
local function guidOf(u)
    if u == "player" then return "0xPLAYER" end
    if u == "target" then return targetGUID end
    local base = string.match(u, "^(nameplate%d+)target$")
    if base then return units[base] and units[base].target end
    return units[u] and units[u].guid
end
function UnitGUID(u) return guidOf(u) end
function UnitExists(u) if guidOf(u) then return 1 end end
function UnitIsUnit(a, b) local x = guidOf(a); if x and x == guidOf(b) then return 1 end end
function UnitClass(u)
    if u == "player" then return "Rogue", playerClass end
    local d = units[u]; if d and d.class then return d.class, d.class end
end
function UnitIsPlayer(u) local d = units[u]; if d and d.player then return 1 end end
function UnitCanAttack(_, u) local d = units[u]; if d and d.enemy then return 1 end end
function UnitHealth(u) local d = units[u]; return d and d.hp or 0 end
function UnitHealthMax(u) local d = units[u]; return d and d.max or 0 end
function GetComboPoints(a, b) assert(a == "player" and b == "target"); return combo end
function GetRaidTargetIndex(u) local d = units[u]; return d and d.mark end

-- Auras: { id, icon, count, duration, expires, mine, cc } in the order the game lists them.
local function aura(a)
    if a then return a.name or "Aura", a.icon, a.count or 1, nil, a.duration or 0, a.expires or 0, nil, false,
        false, a.spell or 1, false, false, a.mine or false, false, 1, a.id end
end
C_UnitAuras = {
    UnitAura = function(u, i, filter)
        assert(i == 1 and filter == "HARMFUL|CROWD_CONTROL")
        tally("UnitAura")
        for _, a in ipairs(units[u] and units[u].auras or {}) do if a.cc then return aura(a) end end
    end,
    GetAuraSlots = function(u, filter, max, token, t)
        assert(filter == "HARMFUL|PLAYER" and type(t) == "table")
        local n = 0
        for i, a in ipairs(units[u] and units[u].auras or {}) do if a.mine then n = n + 1; t[n] = i end end
        for i = n + 1, #t do t[i] = nil end
        t.n = n
        return nil, n
    end,
    UnitAuraBySlot = function(u, slot) return aura(units[u].auras[slot]) end,
}

-- Casts and spells.
spells = {}  -- spellID -> { name, icon, cd (ms) }
C_Spell = {
    UnitCastingInfo = function(u)
        local c = units[u] and units[u].cast
        if c then return c.name, c.name, c.icon, c.from, c.to, false, "Cast-3", c.locked or false, c.spell end
    end,
    UnitChannelInfo = function(u)
        local c = units[u] and units[u].channel
        if c then return c.name, c.name, c.icon, c.from, c.to, false, c.locked or false, c.spell end
    end,
    GetSpellInfo = function(id) local s = spells[id]; if s then return { name = s.name, iconID = s.icon } end end,
}
function GetSpellBaseCooldown(id) local s = spells[id]; return s and s.cd end

-- Plates: frames the game made, reused across units.
plateSize = { 110, 14 }
C_NamePlate = {
    GetNamePlateSize = function() tally("GetNamePlateSize"); return plateSize[1], plateSize[2] end,
    SetNamePlateSize = function(w, h) plateSize = { w, h }; tally("SetNamePlateSize") end,
    GetNamePlateForUnit = function(u)
        if u == "target" then
            for token, d in pairs(units) do if d.guid == targetGUID and d.frame then return d.frame end end
            return
        end
        return units[u] and units[u].frame
    end,
}
function nativePlate()
    local plate = CreateFrame("Frame")
    local bar = CreateFrame("StatusBar", nil, plate)
    local regions = {}
    for i, kind in ipairs({ "Texture", "Texture", "FontString", "FontString", "Texture", "Texture" }) do
        regions[i] = newWidget(kind, nil, plate)
        regions[i].native = true
    end
    bar.native = true
    plate.native = true
    plate.GetChildren = function() return bar end
    plate.GetRegions = function() return unpack(regions) end
    plate.bar, plate.regions = bar, regions
    return plate
end
-- A unit comes into view on a plate frame (a new one unless given).
function show(token, d, frame)
    d.guid = d.guid or ("0x" .. token)
    d.frame = frame or nativePlate()
    units[token] = d
    fire("NAME_PLATE_UNIT_ADDED", token)
    return d.frame
end
function hide(token)
    fire("NAME_PLATE_UNIT_REMOVED", token)
    units[token] = nil
end
function target(token)
    targetGUID = token and units[token] and units[token].guid
    fire("PLAYER_TARGET_CHANGED")
end
-- The addon's parts on a plate frame: the frames and regions it made there.
function made(frame)
    local out = {}
    for _, w in ipairs(widgets) do
        local p = w.parent
        while p and p ~= frame do p = p.parent end
        if p == frame and not w.native then out[#out + 1] = w end
    end
    return out
end

-- Which frames listen to what, and every OnUpdate.
function listening()
    local out = {}
    for _, w in ipairs(widgets) do
        for e in pairs(w.events) do out[#out + 1] = e end
        if w.scripts.OnUpdate then out[#out + 1] = "OnUpdate" end
    end
    table.sort(out)
    local unique, last = {}, nil
    for _, e in ipairs(out) do if e ~= last then unique[#unique + 1] = e; last = e end end
    return table.concat(unique, ",")
end
function liveTimers() local n = 0; for _, t in ipairs(timers) do if not t.cancelled then n = n + 1 end end; return n end
'''


def load(saved=None, setup="", world=True):
    """The addon loaded over `saved` (Lua that sets NameplatesDB); with `world`,
    the login events have fired, as at a first login."""
    lua = wowkit.runtime()
    lua.execute(MOCK)
    lua.execute(setup)
    wowkit.load_addon(lua, ROOT, "Nameplates", saved=saved)
    if world:
        lua.execute('fire("VARIABLES_LOADED") fire("PLAYER_LOGIN") fire("PLAYER_ENTERING_WORLD") step()')
    return lua


def parts(lua, token):
    """The addon's parts of the plate that shows `token`."""
    return lua.eval(f"__addon_ns.byToken['{token}']")


ENEMY_ROGUE = "{ class = 'ROGUE', player = true, enemy = true, hp = 3000, max = 4000 }"
ENEMY_NPC = "{ enemy = true, hp = 72, max = 100 }"
FRIEND = "{ class = 'PALADIN', player = true, hp = 2500, max = 2500 }"
