"""BattleText 1.0 (written new, 2026-11-22) on the shared game model (wowkit).

The game is modelled as ClassicAPI documents it (docs/API.md):

* Animation groups (### region:CreateAnimationGroup, "AnimationGroup",
  "Animation", "Path and ControlPoint"): a group lasts as long as its longest
  startDelay + duration + endDelay; `Play` on a playing group changes nothing;
  `GetProgress` is elapsed / duration while it plays; at the end its progress
  goes back to 0 and OnFinished runs, unless it loops (REPEAT starts again);
  `Stop` runs OnStop, not OnFinished; `StopAnimating` stops every group of the
  region and of every region inside it. The clock is the kit's: `step(dt)`
  moves every playing group by dt after the timers. Nothing is drawn, so the
  values an animation would apply are not modelled, only its timing.
* The combat log (### COMBAT_LOG_EVENT_UNFILTERED / COMBAT_LOG_EVENT,
  ### CombatLogGetCurrentEventInfo, ### CombatLogAddFilter): `cleu(sub,
  source, dest, ...)` fires COMBAT_LOG_EVENT with the 11 common values and the
  rest; the filter calls are recorded, not applied.
* Units, spells, factions and players by GUID with the returns their doc
  headings give.

Animation groups live here, not in wowkit.py: the spec (BattleText.md 4.6)
keeps the kit unchanged while other builds run. ThreatMeter's env has a
smaller stub of the same API.
"""
from pathlib import Path
import os
import wowkit

ROOT = Path(os.environ["VANILLAFORGE_ADDON_ROOT"])

MOCK = r'''
CLASSIC_API_VERSION = 12404
-- GlobalStrings.lua of the 1.12.1 client (extracted FrameXML).
ABSORB_TRAILER, BLOCK_TRAILER, RESIST_TRAILER = " (%d absorbed)", " (%d blocked)", " (%d resisted)"
CRUSHING_TRAILER, GLANCING_TRAILER = " (crushing)", " (glancing)"
COMBATLOG_HONORAWARD = "You have been awarded %d honor points."
COMBATLOG_HONORGAIN = "%s dies, honorable kill Rank: %s (Estimated Honor Points: %d)"
SKILL_RANK_UP = "Your skill in %s has increased to %d."
MAX_COMBO_POINTS = 5 -- FrameXML TargetFrame.lua:1
COMBATLOG_FILTER_ME = 0x511
COMBATLOG_OBJECT_TYPE_PLAYER, COMBATLOG_OBJECT_TYPE_NPC = 0x400, 0x800
bit = { band = function(a, b)
    local r, p = 0, 1
    while a > 0 and b > 0 do
        if a % 2 == 1 and b % 2 == 1 then r = r + p end
        a, b, p = math.floor(a / 2), math.floor(b / 2), p * 2
    end
    return r
end }

handled = {}
local function onError(err) handled[#handled + 1] = tostring(err) end
function geterrorhandler() return onError end

-- What the addon writes on its lines.
function Widget:SetFont(font, size, flags) self.font, self.fontSize, self.outline = font, size, flags end
-- Colours and anchors in reused tables (the kit's make one per call): a garbage
-- test measures the addon.
function Widget:SetTextColor(r, g, b)
    local c = self.color or {}
    c[1], c[2], c[3], c[4] = r, g, b, nil
    self.color = c
end
function Widget:SetVertexColor(r, g, b, a)
    local c = self.color or {}
    c[1], c[2], c[3], c[4] = r, g, b, a
    self.color = c
end
function Widget:ClearAllPoints()
    local pts = self.points
    for i = #pts, 1, -1 do self.spare = pts[i]; pts[i] = nil end
end
function Widget:SetPoint(a, b, c, d, e)
    local pt = self.spare or {}
    self.spare = nil
    pt[1], pt[2], pt[3], pt[4], pt[5] = a, b, c, d, e
    self.points[#self.points + 1] = pt
end
said = {}
function Widget:SetText(text)
    self.text = text
    if self.kind == "FontString" and self.font then said[#said + 1] = self end
end
function forget() for i = #said, 1, -1 do said[i] = nil end end

-- Animation groups: timing only.
groups = {}
local Group, Anim, Point = {}, {}, {}
local GroupMeta, AnimMeta, PointMeta = { __index = Group }, { __index = Anim }, { __index = Point }
function Widget:CreateAnimationGroup()
    local g = setmetatable({ region = self, anims = {}, scripts = {}, elapsed = 0, plays = 0, looping = "NONE" }, GroupMeta)
    groups[#groups + 1] = g
    return g
end
function Widget:StopAnimating()
    for _, g in ipairs(groups) do
        local r = g.region
        while r and r ~= self do r = r.parent end
        if r == self and g.playing then g:Stop() end
    end
end
function Group:SetScript(s, f) self.scripts[s] = f end
function Group:GetScript(s) return self.scripts[s] end
function Group:SetLooping(l) self.looping = l end
function Group:SetIgnoreFramerateThrottle(on) self.unthrottled = on end
function Group:CreateAnimation(kind)
    local a = setmetatable({ kind = kind, group = self, duration = 0, delay = 0, points = {} }, AnimMeta)
    self.anims[#self.anims + 1] = a
    return a
end
function Group:GetDuration()
    local d = 0
    for _, a in ipairs(self.anims) do if a.delay + a.duration > d then d = a.delay + a.duration end end
    return d
end
function Group:Play()
    if self.playing then return end
    self.playing, self.elapsed, self.plays = true, 0, self.plays + 1
end
function Group:Stop()
    if not self.playing then return end
    self.playing, self.elapsed = false, 0
    if self.scripts.OnStop then self.scripts.OnStop(self, true) end
end
function Group:IsPlaying() return self.playing and true or false end
function Group:GetProgress()
    local d = self:GetDuration()
    if not self.playing or d == 0 then return 0 end
    return self.elapsed / d
end
function Group:GetAnimations() return unpack(self.anims) end
function Anim:SetDuration(d) self.duration = d end
function Anim:SetStartDelay(d) self.delay = d end
function Anim:SetTarget(r) self.target = r; return true end
function Anim:SetFromAlpha(a) self.from = a end
function Anim:SetToAlpha(a) self.to = a end
function Anim:SetOffset(x, y) self.x, self.y = x, y end
function Anim:SetScaleFrom(x, y) self.scaleFrom = x end
function Anim:SetScaleTo(x, y) self.scaleTo = x end
function Anim:CreateControlPoint()
    local p = setmetatable({}, PointMeta)
    self.points[#self.points + 1] = p
    return p
end
function Point:SetOffset(x, y) self.x, self.y = x, y end
local function animate(dt)
    for _, g in ipairs(groups) do
        if g.playing then
            g.elapsed = g.elapsed + dt
            local d = g:GetDuration()
            if g.elapsed >= d then
                if g.looping == "REPEAT" and d > 0 then
                    g.elapsed = g.elapsed % d
                else
                    g.playing, g.elapsed = false, 0
                    if g.scripts.OnFinished then g.scripts.OnFinished(g, false) end
                end
            end
        end
    end
end
local kitStep = step
function step(dt) kitStep(dt); animate(dt or 0) end
function playing() local n = 0; for _, g in ipairs(groups) do if g.playing then n = n + 1 end end; return n end

-- The world.
ME, playerClass = "0xME", "ROGUE"
targetGUID, combo = nil, 0
xp, xpMax = 1000, 5000
health, healthMax, mana, manaMax = 3000, 3000, 2000, 2000
function UnitGUID(u) if u == "player" then return ME end if u == "target" then return targetGUID end end
function UnitClass(u) if u == "player" then return playerClass, playerClass end end
function UnitXP() return xp end
function UnitXPMax() return xpMax end
function UnitHealth(u) assert(u == "player"); return health end
function UnitHealthMax(u) assert(u == "player"); return healthMax end
function UnitPower(u, t) assert(u == "player" and t == 0); return mana end
function UnitPowerMax(u, t) assert(u == "player" and t == 0); return manaMax end
function GetComboPoints(a, b) assert(a == "player" and b == "target"); return targetGUID and combo or 0 end
players = {}  -- GUID -> class file name (### GetPlayerInfoByGUID; nil is a cache miss)
function GetPlayerInfoByGUID(guid)
    local class = players[guid]
    if class then return class, class, "Human", "Human", 2, "Someone", "" end
end
local hex = { MAGE = "ff69ccf0", PRIEST = "ffffffff", WARRIOR = "ffc79c6e" }
C_ClassColor = { GetClassColor = function(class)
    if hex[class] then return { GenerateHexColorMarkup = function() return "|c" .. hex[class] end } end
end }
factions = { [72] = "Stormwind" }
function GetFactionInfoByID(id) return factions[id] end

-- Spells: icons by ID, the spellbook by name, the reactive state by name.
icons = { [133] = "Interface\\Icons\\Spell_Fire_FlameBolt", [116] = "Interface\\Icons\\Spell_Frost_FrostBolt",
    [8512] = "Interface\\Icons\\Spell_Nature_Windfury", [12536] = "Interface\\Icons\\Spell_Shadow_ManaBurn",
    [2457] = "Interface\\Icons\\Ability_Warrior_OffensiveStance" }
known = {}    -- name -> icon, the spells in your book
reactive = {} -- name -> { ready, comboTargetGUID }
C_Spell = {
    GetSpellTexture = function(id) return icons[id] end,
    IsSpellReactiveReady = function(name)
        local r = reactive[name]
        if not known[name] then return false end
        if r then return r[1], r[2] end
        return false
    end,
}
spellNames = { [2457] = "Battle Stance" }
function GetSpellInfo(x)
    if type(x) == "number" then return spellNames[x], nil, icons[x] end
    if known[x] then return x, "Rank 1", known[x], 0, false, 0, 0, 0, 0, 1 end
end

-- The combat log.
filters = {}
function CombatLogResetFilter() filters = {}; filters.resets = (filters.resets or 0) + 1 end
function CombatLogAddFilter(events, source, dest) filters[#filters + 1] = { events = events, source = source, dest = dest } end
local current, currentN = {}, 0
function CombatLogGetCurrentEventInfo() return unpack(current, 1, currentN) end
-- One event: sub, source { guid, name, flags }, dest { guid, name, flags }, then the prefix and suffix values.
function cleu(sub, src, dst, ...)
    src, dst = src or {}, dst or {}
    current[1], current[2], current[3] = 1000.5, sub, src[1] == nil
    current[4], current[5], current[6], current[7] = src[1], src[2], src[3] or 0, 0
    current[8], current[9], current[10], current[11] = dst[1], dst[2], dst[3] or 0, 0
    local n = select("#", ...)
    for i = 1, n do current[11 + i] = select(i, ...) end
    for i = 12 + n, 30 do current[i] = nil end
    currentN = 11 + n
    fire("COMBAT_LOG_EVENT")
    currentN = 0
end
you = { ME, "Claude", 0x511 }
mob = { "0xMOB", "Defias Thug", 0xa48 }
mob2 = { "0xMOB2", "Defias Pillager", 0xa48 }
priest = { "0xPRIEST", "Halfwit", 0x512 }

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
    return "," .. table.concat(unique, ",") .. ","
end
function listensFor(e, unit)
    for _, w in ipairs(widgets) do if receives(w, e, unit) then return true end end
    return false
end
function liveTimers() local n = 0; for _, t in ipairs(timers) do if not t.cancelled then n = n + 1 end end; return n end

-- The lines: which area a font string is in, and what each area says.
function areaOf(w)
    local f = w.parent and w.parent.parent
    for name, a in pairs(__addon_ns.areas) do if a.frame == f then return name end end
end
-- The texts said since the last forget(), "|"-joined; with an area, only that area's.
function texts(area)
    local out = {}
    for _, w in ipairs(said) do
        if not area or areaOf(w) == area then out[#out + 1] = w.text end
    end
    return table.concat(out, "|")
end
function last() return said[#said] end
-- The line a font string belongs to.
function lineOf(w)
    for _, a in pairs(__addon_ns.areas) do
        for i = 1, 10 do
            if a.lines[i] and a.lines[i].text == w then return a.lines[i] end
            if a.crits[i] and a.crits[i].text == w then return a.crits[i] end
        end
    end
end
'''


def load(saved=None, setup="", world=True):
    """The addon loaded over `saved` (Lua that sets BattleTextDB); with `world`,
    the login events have fired, as at a first login (no /reload)."""
    lua = wowkit.runtime()
    lua.execute(MOCK)
    lua.execute(setup)
    wowkit.load_addon(lua, ROOT, "BattleText", saved=saved)
    if world:
        lua.execute('fire("SPELLS_CHANGED") fire("VARIABLES_LOADED") fire("PLAYER_LOGIN") '
                    'fire("PLAYER_ENTERING_WORLD") step()')
    return lua


# Claude's 2.4.3 saved file, as it is on disk (2026-11-22), shortened to its kinds of keys.
CLAUDE_243 = r'''
BattleTextDB = {
    ["UserDisabled"] = false,
    ["Profiles"] = {
        ["Default"] = {
            ["AnimationStep"] = 1.5,
            ["ShowAllManaGains"] = false,
            ["Triggers"] = { ["TRIGGER_RIPOSTE"] = { ["EventSettings"] = { ["Show"] = false } } },
            ["DisplaySettings"] = { ["Incoming"] = { ["FrameOffsets"] = { ["x"] = -159, ["y"] = -46 } } },
        },
    },
}
'''
