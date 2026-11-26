"""ThreatMeter 1.0 (written new, 2026-11-26) on the shared game model (wowkit).

The game is modelled as the docs give it: ClassicAPI's PLAYER_IN_COMBAT_CHANGED
(inCombat), GROUP_ROSTER_UPDATE, frame:RegisterUnitEvent, C_ClassColor (one shared
colour per class), AbbreviateNumbers (rounded down, one decimal below ten of a unit),
statusBar:SetValue(value, interpolation) and the animation groups (docs/API.md); the
stock unit, group and chat calls are the client's. The server's side of the threat
protocol (Threat.lua's header) is test data: `answer(body)` is the server's reply, and
what the real server puts in it is UNVERIFIED beyond the old addon's play (2026-11-08).

Frames are the kit's stubs: they record sizes, texts, colours and values, so these
tests prove the logic and the UI writes, not the drawing.
"""
import os
from pathlib import Path

import wowkit

ROOT = Path(os.environ["VANILLAFORGE_ADDON_ROOT"])

MOCK = r'''
CLASSIC_API_VERSION = 12309
STANDARD_TEXT_FONT = "Fonts\\FRIZQT__.TTF"
Enum = { StatusBarInterpolation = { Immediate = 0, ExponentialEaseOut = 1 } }
function AbbreviateNumbers(n)
    if n >= 10000 then return math.floor(n / 1000) .. "K" end
    if n >= 1000 then return string.format("%gK", math.floor(n / 100) / 10) end
    return tostring(n)
end
GameTooltip = newWidget("GameTooltip", "GameTooltip")

-- The server's side: what is asked, and the warning's sound and flash.
sent = {}
function SendAddonMessage(prefix, msg, channel) sent[#sent + 1] = { prefix = prefix, msg = msg, channel = channel } end
sounds, flashes = 0, 0
function PlaySoundFile(file, channel) sounds = sounds + 1; lastSound = file; return true end
function FlashClientIcon() flashes = flashes + 1 end

-- The group, the player and the target.
raid, party, playerCombat = 0, 2, false
target = { exists = true, name = "Onyxia", kind = "worldboss", dead = false, player = false, enemy = true, combat = true }
units = { player = { name = "Me", class = "ROGUE" }, party1 = { name = "Tank", class = "WARRIOR" },
          party2 = { name = "Healer", class = "PRIEST" } }
roster = 0 -- how often a group member's name was read
function IsInRaid() return raid > 0 end
function IsInGroup() return raid > 0 or party > 0 end
function GetNumRaidMembers() return raid end
function GetNumPartyMembers() if raid > 0 then return 0 end return party end
-- A raid of n: Tank, Healer, Me and fillers named R4... (all mages).
function makeRaid(n)
    raid = n
    local names = { "Tank", "Healer", "Me" }
    local classes = { "WARRIOR", "PRIEST", "ROGUE" }
    for i = 1, n do units["raid" .. i] = { name = names[i] or ("R" .. i), class = classes[i] or "MAGE" } end
end
function UnitName(u)
    if u == "target" then if target.exists then return target.name end return nil end
    local x = units[u]
    if x then
        if u ~= "player" then roster = roster + 1 end
        return x.name
    end
end
function UnitClass(u) local x = units[u]; if x then return x.class, x.class end end
function UnitExists(u) if u == "target" then return target.exists and 1 or nil end return units[u] and 1 or nil end
function UnitIsDead(u) if u == "target" and target.dead then return 1 end end
function UnitIsPlayer(u) if u == "target" then return target.player and 1 or nil end return units[u] and 1 or nil end
function UnitCanAttack(a, b) if b == "target" and target.enemy then return 1 end end
function UnitClassification(u) if u == "target" then return target.kind end return "normal" end
function UnitAffectingCombat(u)
    if u == "player" then return playerCombat and 1 or nil end
    if u == "target" and target.exists and target.combat then return 1 end
end
local COLORS = {}
for class, c in pairs({ WARRIOR = { 0.78, 0.61, 0.43 }, PRIEST = { 1, 1, 1 }, ROGUE = { 1, 0.96, 0.41 },
        MAGE = { 0.41, 0.8, 0.94 }, PALADIN = { 0.96, 0.55, 0.73 }, DRUID = { 1, 0.49, 0.04 },
        WARLOCK = { 0.58, 0.51, 0.79 }, HUNTER = { 0.67, 0.83, 0.45 } }) do
    COLORS[class] = { r = c[1], g = c[2], b = c[3], GetRGB = function(self) return self.r, self.g, self.b end }
end
C_ClassColor = { GetClassColor = function(token) return COLORS[token] end }

-- The kit's widgets, with the writes these tests read (fields only: no garbage).
function Widget:SetValue(v, how) self.value, self.how = v, how end
function Widget:SetStatusBarColor(r, g, b) self.r, self.g, self.b = r, g, b end
local kitSetText = Widget.SetText
function Widget:SetText(t) self.writes = (self.writes or 0) + 1; kitSetText(self, t) end
function Widget:CreateAnimationGroup() return newWidget("AnimationGroup", nil, self) end
function Widget:CreateAnimation(kind) return newWidget("Animation", nil, self) end
function Widget:Play() self.plays = (self.plays or 0) + 1 end

handled = {}
local function handler(err) handled[#handled + 1] = tostring(err) end
function geterrorhandler() return handler end

-- Events as the client sends them.
function answer(body) fire("CHAT_MSG_ADDON", "TWT", "TWTv4=" .. body, "RAID", "Tank") end
function fight() playerCombat = true; fire("PLAYER_IN_COMBAT_CHANGED", true) end
function calm() playerCombat = false; fire("PLAYER_IN_COMBAT_CHANGED", false) end
function retarget(name, kind) target.exists, target.name, target.kind = name ~= nil, name, kind or "elite"; fire("PLAYER_TARGET_CHANGED") end

-- What the window shows. The window's status bars in creation order: the pull line,
-- then the 14 rows top to bottom; each bar's texts: name, percent, threat, per second.
local function children(parent, kind)
    local out = {}
    for _, w in ipairs(widgets) do if w.parent == parent and w.kind == kind then out[#out + 1] = w end end
    return out
end
local function describe(bar)
    local t = children(bar, "FontString")
    return { name = t[1].text, pct = t[2].text, threat = t[3].text, tps = t[4].text, value = bar.value, how = bar.how,
             r = bar.r, g = bar.g, b = bar.b, threatShown = t[3].shown, tpsShown = t[4].shown,
             writes = (t[1].writes or 0) + (t[2].writes or 0) + (t[3].writes or 0) + (t[4].writes or 0) }
end
function shownRows()
    local out, bars = {}, children(ThreatMeter_Window, "StatusBar")
    for i = 2, #bars do if bars[i].shown then out[#out + 1] = describe(bars[i]) end end
    return out
end
function pullLine()
    local bar = children(ThreatMeter_Window, "StatusBar")[1]
    if bar.shown then return describe(bar) end
end
function title()
    for _, f in ipairs(children(ThreatMeter_Window, "Frame")) do
        local t = children(f, "FontString")[1]
        if t then return t.text end
    end
end
function badgeText() return children(ThreatMeter_Badge, "FontString")[1].text end
function pulses()
    local n = 0
    for _, w in ipairs(widgets) do if w.kind == "AnimationGroup" then n = n + (w.plays or 0) end end
    return n
end
function closeButton() return children(ThreatMeter_Window, "Button")[1] end
function listening()
    local out = {}
    for _, w in ipairs(widgets) do
        for e in pairs(w.events) do out[#out + 1] = e end
        if w.scripts.OnUpdate then out[#out + 1] = "OnUpdate" end
    end
    table.sort(out)
    return table.concat(out, ",")
end
function liveTimers() local n = 0; for _, t in ipairs(timers) do if not t.cancelled then n = n + 1 end end; return n end
function page() return settingsWindow.find("ThreatMeter") end
function ns() return __addon_ns end
'''

# Claude's saved file (NIKORULES, 2026-11-26): the old 1.0.1 keys, ThreatMeter off.
CLAUDE = '''ThreatMeterDB = { badge = true, alphaOut = 1, scale = 1,
  window = { "TOPLEFT", "TOPLEFT", 946.9997761685653, -352.6040989533265 },
  screenGlow = true, locked = false, hideOut = false, sound = true, alphaCombat = 1, enabled = false,
  rowHeight = 25, width = 220, threshold = 80, rows = 14,
  badgePos = { "TOPLEFT", "TOPLEFT", 731.8889990303374, -466.212403790267 }, allEnemies = false }'''

# A fight in the party: the tank, the healer and you (ranged, 600 of 1000).
FIGHT = "Tank:1:1000:100:1;Healer:0:700:70:0;Me:0:600:60:0"


def load(saved="", setup="", world=True, layout=None):
    """The addon after a first login over `saved` (Lua that sets ThreatMeterDB);
    `layout` is the client's layout-cache.txt as {frame: (x, y)}."""
    lua = wowkit.runtime()
    lua.execute(MOCK)
    for name, (x, y) in (layout or {}).items():
        lua.execute('layoutCache["%s"] = { %s, %s }' % (name, x, y))
    lua.execute(setup)
    wowkit.load_addon(lua, ROOT, "ThreatMeter", saved=saved or None)
    if world:
        lua.execute('fire("VARIABLES_LOADED") fire("PLAYER_LOGIN") fire("PLAYER_ENTERING_WORLD") step()')
    return lua


def fight(saved="", setup="", **kw):
    """In combat with the target, the first question sent."""
    lua = load(saved, setup, **kw)
    lua.execute("fight()")
    return lua


def rows(lua):
    """The shown player rows, top to bottom, as dicts."""
    return [dict(r.items()) for r in lua.eval("shownRows()").values()]


def names(lua):
    return [r["name"] for r in rows(lua)]
