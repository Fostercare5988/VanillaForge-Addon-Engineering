"""The ThreatMeter regressions on the shared game model (wowkit).

Loads the real files named in ThreatMeter.toc, in order, against the kit's widgets
and timers. Frames are the kit's permissive stubs: they record sizes, text, colours
and values, so these tests prove the logic and the UI writes, not drawing. Native
behaviour (the eased fill, the animation, the sound) and the server's answers stay
in-game checks.
"""
import os
from pathlib import Path

import wowkit

ROOT = Path(os.environ["VANILLAFORGE_ADDON_ROOT"])

MOCK = r'''
CLASSIC_API_VERSION = 11711
Enum = { StatusBarInterpolation = { Immediate = 0, ExponentialEaseOut = 1 } }
function GetAddOnMetadata() return "1.0.0" end
function AbbreviateNumbers(n) return tostring(n) end
function HideUIPanel() end
InterfaceOptionsFrame = newWidget("Frame", "InterfaceOptionsFrame"); InterfaceOptionsFrame.shown = false
GameMenuFrame = newWidget("Frame", "GameMenuFrame"); GameMenuFrame.shown = false
GameTooltip = newWidget("Frame", "GameTooltip")

-- The server side of the protocol.
sent = {}
function SendAddonMessage(prefix, msg, channel) sent[#sent + 1] = { prefix = prefix, msg = msg, channel = channel } end
sounds, flashes = 0, 0
function PlaySoundFile() sounds = sounds + 1 end
function FlashClientIcon() flashes = flashes + 1 end

-- The group, the player and the target.
raid, party, combat, targetCombat = 0, 4, false, true
target = { exists = true, name = "Boss", classification = "worldboss", dead = false, player = false, attackable = true }
playerClass = "ROGUE"
function IsInRaid() return raid > 0 end
function IsInGroup() return raid > 0 or party > 0 end
function GetNumRaidMembers() return raid end
function GetNumPartyMembers() return party end
function UnitAffectingCombat(u) if u == "player" then return combat end return targetCombat end
function UnitExists(u) return u == "target" and target.exists end
function UnitIsDead() return target.dead end
function UnitIsPlayer() return target.player end
function UnitCanAttack() return target.attackable end
function UnitClassification() return target.classification end
roster = { Tank = "WARRIOR", A = "MAGE", B = "PRIEST", Me = "ROGUE" }
unitNames = { player = "Me", target = "Boss", party1 = "Tank", party2 = "A", party3 = "B" }
function UnitName(u) if u == "target" then return target.name end return unitNames[u] end
function UnitClass(u)
    local n = unitNames[u]
    if u == "player" then return playerClass, playerClass end
    if n and roster[n] then return roster[n], roster[n] end
end
local colors = { WARRIOR = { 0.78, 0.61, 0.43 }, MAGE = { 0.41, 0.8, 0.94 }, PRIEST = { 1, 1, 1 }, ROGUE = { 1, 0.96, 0.41 } }
C_ClassColor = { GetClassColor = function(token)
    local c = colors[token] or { 0.6, 0.6, 0.6 }
    return { GetRGBA = function() return c[1], c[2], c[3], 1 end }
end }

-- The kit's widgets, with the writes these tests read.
function Widget:SetValue(v, interpolation) self.value, self.interpolation = v, interpolation end
function Widget:CreateFontString(name, layer, template)
    local w = newWidget("FontString", name, self)
    w.template = template
    return w
end
-- The client refuses text on a font string that has no font.
function Widget:SetText(t)
    if self.kind == "FontString" and not self.font and not self.template then error("SetText(): Font not set") end
    self.text = t; self.textWrites = (self.textWrites or 0) + 1 end
function Widget:SetStatusBarColor(r, g, b, a) self.barColor = { r, g, b, a } end
function Widget:SetFont(f, s, o) self.font, self.fontSize = f, s end
function Widget:StartMoving() self.moving = true end
function Widget:StopMovingOrSizing() self.moving = false end
function Widget:CreateAnimationGroup()
    local g = newWidget("AnimationGroup")
    g.plays = 0
    function g:Play() self.plays = self.plays + 1 end
    function g:Stop() end
    function g:CreateAnimation() return newWidget("Animation") end
    return g
end

handled = {}
function geterrorhandler() return function(err) handled[#handled + 1] = tostring(err) end end

-- Events as the client sends them. (The kit keeps the running event in `event`.)
function ev(name, a1, a2, a3, a4) fire(name, a1, a2, a3, a4) end
function answer(body) ev("CHAT_MSG_ADDON", "TWT", "TWTv4=" .. body, "RAID", "Me") end

-- What the window shows. barRows(): the shown player bars top to bottom; footRow():
-- the Pull aggro line (the first bar made); title(): the window's title text.
local function texts(bar)
    local out = {}
    for _, w in ipairs(widgets) do
        if w.kind == "FontString" and w.parent == bar then out[#out + 1] = w end
    end
    return out
end
local function bars()
    local out = {}
    for _, w in ipairs(widgets) do
        if w.kind == "StatusBar" and w.parent == ThreatMeter_Window then out[#out + 1] = w end
    end
    return out
end
local function describe(bar)
    local t = texts(bar)
    local y = bar.points[#bar.points]
    return { name = t[1].text, tps = t[2].text, threat = t[3].text, perc = t[4].text, nameColor = t[1].color,
             value = bar.value, interpolation = bar.interpolation, color = bar.barColor, y = y and y[5],
             writes = (t[1].textWrites or 0) + (t[2].textWrites or 0) + (t[3].textWrites or 0) + (t[4].textWrites or 0),
             tpsShown = t[2].shown, threatShown = t[3].shown, bar = bar }
end
function barRows()
    local out = {}
    local all = bars()
    for i = 2, #all do if all[i].shown then out[#out + 1] = describe(all[i]) end end
    table.sort(out, function(a, b) return a.y > b.y end)
    return out
end
function footRow()
    local foot = bars()[1]
    if foot.shown then return describe(foot) end
end
function title()
    for _, w in ipairs(widgets) do
        if w.kind == "FontString" and w.parent == ThreatMeter_Window then return w.text end
    end
end
function badge() return ThreatMeter_Badge end
function badgeText()
    for _, w in ipairs(widgets) do
        if w.kind == "FontString" and w.parent == ThreatMeter_Badge then return w.text end
    end
end
function startFight()
    combat = true
    ev("PLAYER_REGEN_DISABLED")
end
function endFight()
    combat = false
    ev("PLAYER_REGEN_ENABLED")
end
function ns() return __addon_ns end
'''


def load(saved="", setup=""):
    lua = wowkit.runtime()
    lua.execute(MOCK)
    lua.execute(setup)
    if saved:
        lua.execute("ThreatMeterDB = " + saved)
    wowkit.load_addon(lua, ROOT, "ThreatMeter")
    lua.execute('ev("ADDON_LOADED", "ThreatMeter")')
    return lua
