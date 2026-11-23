"""AutoBG 1.0 (written new, 2026-11-22) on the shared game model (wowkit).

The world is modelled as the docs describe it: units by GUID, named by tokens
and GUID literals (### Unit tokens (GUID literals)); GUID registrations
(### frame:RegisterGUIDEvent, in the kit); auras with instance IDs
(### UNIT_AURA_DELTA, ### C_UnitAuras.GetAuraDataByAuraInstanceID); casts in
GetTime() milliseconds (### C_Spell.UnitCastingInfo); positions in the
C_PlayerInfo shape (### UnitPosition); the battlefield queue calls of the
client's FrameXML (BattlefieldFrame.lua, OctoWoW's Minimap.lua and
Turtle_ArenaUI.lua); duration objects, text bindings and rule formatters
(### C_DurationUtil.*, ### C_StringUtil.CreateNumericRuleFormatter) with their
text worked out when a test asks (`clock(fontString)`); unit buttons' click
verbs (### frame:SetAttribute ... unit-frame mouseover). Nothing is drawn.
"""
from pathlib import Path
import os
import wowkit

ROOT = Path(os.environ["VANILLAFORGE_ADDON_ROOT"])

MOCK = r'''
CLASSIC_API_VERSION = 12404
function GetNampowerVersion() return 4, 6, 2 end
UNKNOWNOBJECT = "Unknown"
RAID_CLASS_COLORS = {}
for _, c in ipairs({ "WARRIOR", "ROGUE", "MAGE", "PRIEST", "PALADIN", "DRUID", "HUNTER", "WARLOCK", "SHAMAN" }) do
    RAID_CLASS_COLORS[c] = { r = 0.5, g = 0.5, b = 0.5 }
end
RAID_CLASS_COLORS.ROGUE = { r = 1, g = 0.96, b = 0.41 }
Enum = {
    StatusBarTimerDirection = { ElapsedTime = 0, RemainingTime = 1 },
    StatusBarInterpolation = { Immediate = 0, ExponentialEaseOut = 1 },
    NumericRuleFormatRounding = { Nearest = 0, Up = 1, Down = 2 },
    DurationTextBindingProperty = { RemainingDuration = 0, RemainingPercent = 1, ElapsedDuration = 2 },
}
log = {}
function note(what) log[#log + 1] = what end
function said(pattern)
    for _, l in ipairs(log) do if string.find(l, pattern) then return true end end
    return false
end
function count(pattern)
    local n = 0
    for _, l in ipairs(log) do if string.find(l, pattern) then n = n + 1 end end
    return n
end
function heard(pattern)
    for _, l in ipairs(chat) do if string.find(l, pattern) then return l end end
end

-- A working hooksecurefunc: the hook runs after the function.
function hooksecurefunc(name, fn)
    local old = _G[name]
    _G[name] = function(a, b, c, d) local r = old and old(a, b, c, d); fn(a, b, c, d); return r end
end

-- Widgets: what the addon writes.
function Widget:SetStatusBarColor(r, g, b) self.barColor = { r, g, b } end
function Widget:SetTimerDuration(d, _, direction) self.timer, self.direction = d, direction end
function Widget:SetCooldown(start, duration) self.cdStart, self.cdDuration = start, duration; note("SetCooldown") end
function Widget:Clear() self.cdStart, self.cdDuration = nil, nil end
-- A cooldown's countdown: its formatter, and its own font string (### CreateFrame("Cooldown")).
function Widget:SetCountdownFormatter(f) self.countdownFormatter = f end
function Widget:GetCountdownFontString()
    self.countdownText = self.countdownText or self:CreateFontString(nil, "OVERLAY")
    return self.countdownText
end
function Widget:SetTexture(path, g, b) self.texture = path end
function Widget:SetAttribute(k, v) self.attrs = self.attrs or {}; self.attrs[string.lower(k)] = v end
function Widget:GetAttribute(k) return self.attrs and self.attrs[string.lower(k)] end
-- A click resolves the verb as the unit buttons do; an unknown verb reaches OnClick.
function Widget:Click(button)
    local n = button == "RightButton" and 2 or 1
    local prefix = (ctrl and "ctrl-" or "") .. (shift and "shift-" or "")
    local verb = self:GetAttribute(prefix .. "type" .. n) or self:GetAttribute("type" .. n)
    local unit = self:GetAttribute("unit")
    if (verb == "target" or verb == "focus") and unit then
        note(verb .. ":" .. tostring(UnitName(unit)))
        if verb == "target" then setTarget(resolve(unit)) else focusGUID = resolve(unit); fire("PLAYER_FOCUS_CHANGED") end
    else
        -- ClassicAPI's chained OnClick hands a click with no verb to the frame's own
        -- handler with no arguments (seen in play 2026-11-23: self and button nil);
        -- GetMouseButtonClicked names the button while it runs.
        local f = self.scripts.OnClick
        if f then
            local outer = clicked
            clicked = button or "LeftButton"
            f()
            clicked = outer
        end
    end
end
function GetMouseButtonClicked() return clicked end
ctrl, shift = false, false
function IsControlKeyDown() return ctrl end
function IsShiftKeyDown() return shift end

-- Durations, bindings and formatters.
local Duration = {}
Duration.__index = Duration
function Duration:SetTimeSpan(s, e) self.s, self.e = s, math.max(s, e) end
function Duration:GetRemainingDuration() return math.max(0, (self.e or 0) - math.max(now, self.s or 0)) end
function Duration:GetElapsedDuration() return math.min((self.e or 0) - (self.s or 0), math.max(0, now - (self.s or 0))) end
C_DurationUtil = {}
function C_DurationUtil.CreateDuration() return setmetatable({ s = 0, e = 0 }, Duration) end
local function round(v, step, mode)
    if not step or step <= 0 then return v end
    local q = v / step
    if mode == 1 then q = math.ceil(q - 1e-9) elseif mode == 2 then q = q >= 0 and math.floor(q) or math.ceil(q)
    else q = math.floor(q + 0.5) end
    return q * step
end
local Formatter = {}
Formatter.__index = Formatter
function Formatter:SetBreakpoints(b) self.b = b end
function Formatter:FormatNumber(n)
    local best
    for _, bp in ipairs(self.b) do if bp.threshold <= n and (not best or bp.threshold > best.threshold) then best = bp end end
    if not best then return tostring(n) end
    local v = round(n, best.step, best.rounding)
    if not best.components then return string.format(best.format, math.floor(v)) end
    local vals = {}
    for i, c in ipairs(best.components) do
        local x = v
        if c.div then x = x / c.div end
        if c.mod then x = math.fmod(x, c.mod) end
        vals[i] = math.floor(round(x, c.step, c.rounding))
    end
    return string.format(best.format, unpack(vals))
end
C_StringUtil = { CreateNumericRuleFormatter = function() return setmetatable({ b = {} }, Formatter) end }
local Binding = {}
Binding.__index = Binding
bindings = {}
function Binding:SetFontString(fs) self.fs = fs; bindings[fs] = self end
function Binding:SetDuration(d) self.d = d end
function Binding:SetFormatter(f) self.f, self.format = f, nil end
function Binding:SetTextFormat(fmt, comps) self.format, self.comps = fmt, comps end
function Binding:SetEnabled(on) self.on = on end
function Binding:GetFormattedText()
    local d = self.d
    if not self.format then return self.f:FormatNumber(d:GetRemainingDuration()) end
    local i = 0
    return (string.gsub(self.format, "{}", function()
        i = i + 1
        local c = self.comps[i]
        return c.formatter:FormatNumber(c.property == 2 and d:GetElapsedDuration() or d:GetRemainingDuration())
    end))
end
function C_DurationUtil.CreateDurationTextBinding() return setmetatable({}, Binding) end
-- The text a font string shows now: its binding's while enabled, else its own.
function clock(fs)
    local b = bindings[fs]
    if b and b.on then return b:GetFormattedText() end
    return fs.text
end

-- Units: by GUID, named by tokens and GUID literals.
units, tokens = {}, {}
function resolve(u)
    if not u then return nil end
    if tokens[u] then return tokens[u] end
    if units[u] then return u end
    for g, d in pairs(units) do if d.name == u and d.inGroup then return g end end
end
local function d(u) local g = resolve(u); return g and units[g] end
function unit(guid, t)
    t.guid, t.hp, t.max = guid, t.hp or 100, t.max or 100
    if t.visible == nil then t.visible = true end
    t.auras = t.auras or {}
    units[guid] = t
    return t
end
me = unit("0x0000000000000001", { name = "Claude", class = "ROGUE", player = true, faction = "Horde", inGroup = true })
tokens.player = me.guid
function UnitGUID(u) return resolve(u) end
function UnitExists(u) if d(u) then return 1 end end
function UnitName(u) local x = d(u); return x and x.name end
function UnitClass(u) local x = d(u); if x and x.class then return string.lower(x.class), x.class end end
function UnitRace(u) local x = d(u); if x and x.race then return x.race, x.race end end
function UnitLevel(u) local x = d(u); return x and (x.level or 60) end
function UnitIsPlayer(u) local x = d(u); if x and x.player then return 1 end end
function UnitCanAttack(_, u) local x = d(u); if x and x.enemy then return 1 end end
function UnitFactionGroup(u) local x = d(u); return x and x.faction end
function UnitHealth(u) local x = d(u); return x and x.hp or 0 end
function UnitHealthMax(u) local x = d(u); return x and x.max or 0 end
function UnitIsDeadOrGhost(u) local x = d(u); if x and (x.dead or x.ghost) then return 1 end end
function UnitIsGhost(u) local x = d(u); if x and x.ghost then return 1 end end
function UnitIsVisible(u) local x = d(u); if x and x.visible then return 1 end end
function UnitIsAFK() return afk end
function UnitInRaid(u) local x = d(u); if x and x.inGroup and x ~= me and raid then return 1 end end
function UnitInParty(u) local x = d(u); if x and x.inGroup and x ~= me then return 1 end end
function UnitTokenFromName(name)
    for g, x in pairs(units) do
        if x.name == name and x.visible then
            if x == me then return "player" end
            return g
        end
    end
end
function UnitPower(u) local x = d(u); return x and x.power or 0 end
function UnitPowerMax(u) local x = d(u); return x and 100 or 0 end
function UnitPowerType(u) local x = d(u); return x and x.powerType or 0 end
function UnitIsMinion(u) local x = d(u); if x and x.owner then return 1 end end
function UnitOwnerGUID(u) local x = d(u); return x and x.owner end
function UnitCreatureType(u) local x = d(u); return x and x.creature end
function GetRaidTargetIndex(u) local x = d(u); return x and x.mark end
function SetRaidTargetIconTexture(t, i) t.markIndex = i end
function UnitDistanceSquared(u)
    local x = d(u)
    if x and x.visible and x.yards then return x.yards * x.yards, true end
    return 0, false
end
-- A unit's pos is { x, y }; UnitPosition returns posY first (### UnitPosition(unit)).
C_PlayerInfo = { UnitPosition = function(u) local x = d(u); if x and x.visible and x.pos then return x.pos[2], x.pos[1], 0, 529 end end }
raid, afk = false, nil
function GetNumRaidMembers() return raid and 10 or 0 end
function GetNumPartyMembers() return partySize or 0 end
targetGUID, focusGUID = nil, nil
function setTarget(g) targetGUID = g; tokens.target = g; fire("PLAYER_TARGET_CHANGED") end
function UnitXP(u, what)
    assert(u == "target" and what == "nextEnemyInCycle")
    for g, x in pairs(units) do
        if x.enemy and x.player and x.visible and not x.cycled then x.cycled = true; setTarget(g); return true end
    end
    return false
end
function ClearTarget() note("ClearTarget"); targetGUID, tokens.target = nil, nil end

-- Auras: instance IDs; the spell IDs and names a test gives.
local nextID = 0
function aura(guid, spellId, name, filter)
    nextID = nextID + 1
    local a = { spellId = spellId, name = name or ("Spell" .. spellId), auraInstanceID = nextID, applications = 1,
        harmful = filter == "HARMFUL", expirationTime = 0 }
    table.insert(units[guid].auras, a)
    return nextID
end
local function find(u, id)
    for _, a in ipairs(units[resolve(u)].auras) do if a.auraInstanceID == id then return a end end
end
C_UnitAuras = {
    GetAuraDataByAuraInstanceID = function(u, id, buf)
        local a = find(u, id)
        if not a then return nil end
        for k, v in pairs(a) do buf[k] = v end
        return buf
    end,
    GetAuraDataBySpellName = function(u, name, filter)
        local x = d(u)
        for _, a in ipairs(x and x.auras or {}) do
            if a.name == name and (filter ~= "HARMFUL" or a.harmful) then return a end
        end
    end,
    GetAuraSlots = function(u, filter, _, _, t)
        local n = 0
        for i, a in ipairs(d(u).auras) do if not a.harmful then n = n + 1; t[n] = i end end
        for i = n + 1, #t do t[i] = nil end
        t.n = n
        return nil, n
    end,
    GetAuraDataBySlot = function(u, slot) return d(u).auras[slot] end,
}
function removeAura(guid, id)
    for i, a in ipairs(units[guid].auras) do if a.auraInstanceID == id then table.remove(units[guid].auras, i) end end
end
-- An aura change as the engine reports it to GUID registrations.
function auraEvent(guid, added, removed)
    fireGUID("UNIT_AURA_DELTA", guid, { addedAuraInstanceIDs = added, removedAuraInstanceIDs = removed })
end

-- Casts and spells.
C_Spell = {
    UnitCastingInfo = function(u) local c = d(u) and d(u).cast
        if c and not c.channel then return c.name, c.name, c.icon, c.from * 1000, c.to * 1000, false, nil, c.locked or false, c.spell end end,
    UnitChannelInfo = function(u) local c = d(u) and d(u).cast
        if c and c.channel then return c.name, c.name, c.icon, c.from * 1000, c.to * 1000, false, c.locked or false, c.spell end end,
}
function GetSpellInfo(id) return "Spell" .. id, nil, "Icon" .. id end

-- The battlefield: three queues, the battlemaster window, the scoreboard.
MAX_BATTLEFIELD_QUEUES = 3
OCTO_BG_ROW_XF_ID, OCTO_BG_ROW_FX_ID = 9001, 9002
queues = { {}, {}, {} } -- { status, map, instance, waited, estimate, expires }
function GetBattlefieldStatus(i) local q = queues[i]; return q.status or "none", q.map, q.instance or 0 end
function GetBattlefieldTimeWaited(i) return queues[i].waited or 0 end
function GetBattlefieldEstimatedWaitTime(i) return queues[i].estimate or 0 end
function GetBattlefieldPortExpiration(i) return queues[i].expires or 0 end
function OctoBGQueueName(map, id) return map .. (id == 9001 and " (Cross-Faction)" or "") end
battlemaster = { 0, 9001, 9002 } -- the instance number of each row
shownBattlefield = nil
function GetBattlefieldInfo() return shownBattlefield end
function GetNumBattlefields() return #battlemaster - 1 end
function GetBattlefieldInstanceInfo(k) return battlemaster[k + 1] end
function SetSelectedBattlefield(k) note("select:" .. k) end
function JoinBattlefield(k) note("join:" .. k) end
function CloseBattlefield() note("close") end
function JoinBattlegroundQueue(kind) note("request:" .. kind) end
function JoinArenaQueue(kind) note("arena:" .. kind) end
function LeaveArenaQueue() note("leaveArena") end
function AcceptBattlefieldPort(i, accept) note("port:" .. i .. ":" .. tostring(accept)) end
function HideUIPanel(f) f:Hide() end
BattlefieldFrame = CreateFrame("Frame", "BattlefieldFrame")
BattlefieldFrame:Hide()
winner = nil
function GetBattlefieldWinner() return winner end
function LeaveBattlefield() note("LeaveBattlefield") end
function SpellStopCasting() note("SpellStopCasting") end
function SpellStopTargeting() note("SpellStopTargeting") end
soulstone = nil
function HasSoulstone() return soulstone end
function RepopMe() note("RepopMe") end
function StaticPopup_Hide(which) note("hide:" .. which) end
function PlaySound(s) note("sound:" .. s) end
function FlashClientIcon() note("flash") end
function SendChatMessage(text, channel) note("say:" .. channel .. ":" .. text) end
UIErrorsFrame = { AddMessage = function(_, text) note("error:" .. text) end }
GameTooltip = CreateFrame("Frame", "GameTooltip")
SettingsPanel = CreateFrame("Frame", "SettingsPanel")
SettingsPanel:Hide()
scores = {} -- { name, faction (0 Horde, 1 Alliance), race, class }
function GetNumBattlefieldScores() return #scores end
function GetBattlefieldScore(i)
    local s = scores[i]
    if s then return s[1], 0, 0, 0, 0, s[2], 0, s[3], s[4] end
end
function RequestBattlefieldScoreData() note("RequestScores") end
cvars = {}
function GetCVar(name) return cvars[name] end
function SetCVar(name, value) cvars[name] = tostring(value) end
MAX_WORLDSTATE_SCORE_BUTTONS = 3
WorldStateScoreScrollFrame = CreateFrame("Frame")
function FauxScrollFrame_GetOffset() return 0 end
for i = 1, 3 do CreateFrame("Frame", nil):CreateFontString("WorldStateScoreButton" .. i .. "NameButtonName", "OVERLAY", "x") end
function WorldStateScoreFrame_Update() end
worldStates = {}
function GetNumWorldStateUI() return #worldStates end
-- state, text, icon, ... as the client's WorldStateFrame.lua:39 reads them (the text second).
function GetWorldStateUIInfo(i) if worldStates[i] then return 0, worldStates[i], "Interface\WorldStateFrame\HordeFlag" end end
healerTime = 0
function GetAreaSpiritHealerTime() return healerTime end

-- The zone.
zone = { name = "Orgrimmar", kind = "none", map = 1, inside = false }
function GetInstanceInfo() return zone.name, zone.kind, 1, "Normal", 40, 0, false, zone.map, 40 end
function IsInInstance() return zone.inside and 1 or nil, zone.kind end
function IsActiveBattlefieldArena() return zone.arena end
function GetRealZoneText() return zone.name end
local MAPS = { ["Warsong Gulch"] = 489, ["Arathi Basin"] = 529, ["Alterac Valley"] = 30 }
function enter(name, arena)
    if name then
        zone = { name = name, kind = "pvp", map = MAPS[name] or 0, inside = true, arena = arena }
    else
        zone = { name = "Orgrimmar", kind = "none", map = 1, inside = false }
    end
    fire("PLAYER_ENTERING_WORLD")
    fire("ZONE_CHANGED_NEW_AREA")
    step()
end
function line(text, event) fire(event or "CHAT_MSG_BG_SYSTEM_NEUTRAL", text) end

-- An enemy player in view, with a GUID; seen on a plate.
local plateN = 0
function enemy(guid, t)
    t.player, t.enemy = true, true
    t.faction = t.faction or "Alliance"
    return unit(guid, t)
end
function plate(guid)
    plateN = plateN + 1
    tokens["nameplate" .. plateN] = guid
    fire("NAME_PLATE_UNIT_ADDED", "nameplate" .. plateN)
    step()
    return "nameplate" .. plateN
end
function liveTimers() local n = 0; for _, t in ipairs(timers) do if not t.cancelled then n = n + 1 end end; return n end
function onUpdates() local n = 0; for _, w in ipairs(widgets) do if w.scripts.OnUpdate then n = n + 1 end end; return n end
function row(i, size) return _G["AutoBG_TargetsMainFrame" .. (size or 10)].rows[i] end
'''


def load(saved=None, setup="", world=True, cache=None):
    """The addon over `saved` (Lua that sets AutoBGDB); with `world`, a first
    login: the client puts the frames of `cache` (name -> (x, y)) back at the
    first step, after PLAYER_ENTERING_WORLD."""
    lua = wowkit.runtime()
    lua.execute(MOCK)
    for name, (x, y) in (cache or {}).items():
        lua.execute(f'layoutCache["{name}"] = {{ {x}, {y} }}')
    lua.execute(setup)
    wowkit.load_addon(lua, ROOT, "AutoBG", saved=saved)
    if world:
        lua.execute('fire("VARIABLES_LOADED") fire("PLAYER_LOGIN") fire("PLAYER_ENTERING_WORLD") step()')
    return lua


def ns(lua, path):
    return lua.eval("__addon_ns." + path)
