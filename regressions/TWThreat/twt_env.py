"""The TWThreat regressions on the shared game model (wowkit), 2026-11-07.

Loads the real TWThreat.lua against widget mocks. Every XML frame (TWTMain,
TWThreatN bars, TMEF rows, the target indicator) is a permissive stub that
records sizes, colours, text and anchors, so these tests prove the logic and the
UI writes, not drawing. `step(dt)` advances GetTime() and runs every visible
OnUpdate script, the way the client does once per frame.
"""
import os
from pathlib import Path
import wowkit

ROOT = Path(os.environ["VANILLAFORGE_ADDON_ROOT"])
SOURCE = (ROOT / "TWThreat.lua").read_text("utf-8-sig")
XML = (ROOT / "TWThreat.xml").read_text("utf-8-sig")

MOCK = r'''
now = 100.0
function time() return math.floor(now) end
SUPERWOW_VERSION = "2.2"
CLASSIC_API_VERSION = 12004
sent = {}
function SendAddonMessage(prefix, msg, channel) sent[#sent + 1] = { prefix = prefix, msg = msg, channel = channel } end
sounds = 0
function PlaySoundFile() sounds = sounds + 1 end
function FlashClientIcon() end
function AbbreviateNumbers(n) return tostring(n) end
function GetScreenWidth() return 1920 end
function GetScreenHeight() return 1080 end
function HideUIPanel() end

raid, party, combat, targetCombat = 0, 4, false, true
target = { exists = true, name = "Boss", classification = "worldboss" }
function GetNumRaidMembers() return raid end
function GetNumPartyMembers() return party end
function UnitAffectingCombat(u) if u == "player" then return combat end return targetCombat end
function UnitExists(u) return u == "target" and target.exists end
function UnitIsDead() return false end
function UnitIsPlayer() return false end
function UnitClassification() return target.classification end
function UnitName(u) if u == "player" then return "Me" end if u == "target" then return target.name end return nil end
playerClass = "ROGUE"
function UnitClass(u) if u == "player" then return playerClass, playerClass end return "Warrior", "WARRIOR" end
function GetNumTalentTabs() return 3 end
function GetNumTalents() return 0 end
function GetTalentInfo() return nil end
function GetSpellTabInfo(i) if i <= 4 then return "Tab" .. i, "Interface\\Icons\\Ability_Tab" .. i end end

-- Widgets: the kit's, hidden until shown, with the writes these tests count.
-- fire(frame, script, arg1) runs one script; the kit's event fire is not used here.
function fire(f, script, a1)
    local s = f.scripts[script]
    if not s then return end
    local oldThis, oldArg = this, arg1
    this, arg1 = f, a1
    s(f, a1)
    this, arg1 = oldThis, oldArg
end
local make = newWidget
function newWidget(kind, name, parent)
    local w = make(kind, name, parent)
    w.shown, w.attrs, w.setAlpha = false, {}, 0
    return w
end
function widget(name) return newWidget("Frame", name) end
function Widget:SetWidth(v) self.width = v; self.widthWrites = (self.widthWrites or 0) + 1 end
function Widget:SetAlpha(a) self.alpha = a; self.setAlpha = self.setAlpha + 1 end
function Widget:GetEffectiveScale() return self:GetScale() end
function Widget:SetText(t) self.text = t; self.textWrites = (self.textWrites or 0) + 1 end
function Widget:SetNormalTexture(t) self.normal = t end
function Widget:SetValue(v) self.value = v; fire(self, "OnValueChanged") end
function Widget:SetPoint(p, a, b, c, d) self.point = { p, a, b, c, d }; self.pointWrites = (self.pointWrites or 0) + 1 end
function Widget:SetAttribute(k, v) self.attrs[k] = v end
function Widget:GetAttribute(k) return self.attrs[k] end
function Widget:SetFont(f, s, o) self.font = f; self.fontWrites = (self.fontWrites or 0) + 1 end
function Widget:GetLeft() return 10 end
function Widget:GetTop() return 500 end
function Widget:CreateAnimationGroup()
    local g = widget()
    g.playing = false
    function g:Play() self.playing = true; self.plays = (self.plays or 0) + 1; fire(self, "OnPlay") end
    function g:Stop() self.playing = false end
    function g:IsPlaying() return self.playing end
    function g:Finish() self.playing = false; fire(self, "OnFinished") end
    function g:CreateAnimation() return widget() end
    self.groups = self.groups or {}
    self.groups[#self.groups + 1] = g
    return g
end
TargetFrame = widget("TargetFrame"); TargetFrame.shown = true
GameMenuFrame = widget("GameMenuFrame")
GameTooltip = widget("GameTooltip")

-- XML frames: any TWT*/TMEF* name that the file reads becomes a stub on first use.
setmetatable(_G, { __index = function(t, k)
    if type(k) == "string" and not string.find(k, "^TWT_")
            and (string.find(k, "^TWT") or string.find(k, "^TMEF") or string.find(k, "^Font_") or k == "pps") then
        return widget(k)
    end
end })
C_Timer = {}
timers = {}
function C_Timer.NewTicker(interval, cb)
    local t = { interval = interval, callback = cb, cancelled = false }
    function t:Cancel() self.cancelled = true end
    timers[#timers + 1] = t
    return t
end
function C_Timer.NewTimer(d, cb) return C_Timer.NewTicker(d, cb) end
function C_Timer.After(d, cb) C_Timer.NewTicker(d, cb) end

-- Helpers ---------------------------------------------------------------------
function step(dt)
    now = now + dt
    for _, w in ipairs(widgets) do
        if w.shown and w.scripts.OnUpdate then fire(w, "OnUpdate", dt) end
    end
end
function run(seconds, fps)
    local dt = 1 / (fps or 60)
    local n = math.floor(seconds / dt + 0.5)
    for i = 1, n do step(dt) end
end
function event(name, a1, a2, a3, a4)
    local oldEvent, o1, o2, o3, o4 = _G.event, arg1, arg2, arg3, arg4
    local oldThis = this
    _G.event, arg1, arg2, arg3, arg4, this = name, a1, a2, a3, a4, TWThreatCore
    TWThreatCore.scripts.OnEvent(TWThreatCore, name, a1, a2, a3, a4)
    _G.event, arg1, arg2, arg3, arg4, this = oldEvent, o1, o2, o3, o4, oldThis
end
function tick()
    local live
    for _, t in ipairs(timers) do if not t.cancelled and t.interval < 5 then live = t end end
    assert(live, "no live query ticker")
    live.callback()
end
function packet(body) event("CHAT_MSG_ADDON", "TWT", "TWTv4=" .. body, "RAID", "Me") end
function bars()
    -- The visible threat bars, keyed by the player name they show.
    local out = {}
    for i = 1, 40 do
        local f = rawget(_G, "TWThreat" .. i)
        if f and f.shown then
            local nameText = rawget(_G, "TWThreat" .. i .. "Name")
            local name = nameText and nameText.text and string.gsub(nameText.text, "^|c%x%x%x%x%x%x%x%x", "")
            if name then out[name] = { frame = f, bg = rawget(_G, "TWThreat" .. i .. "BG"), index = i } end
        end
    end
    return out
end
function width(name) local b = bars()[name]; return b and b.bg.width end
function startFight()
    combat = true
    event("PLAYER_REGEN_DISABLED")
    tick()            -- picks up the target
    tick()            -- first query for it
end
'''


def load(config="{}", setup=""):
    lua = wowkit.runtime()
    lua.execute(MOCK)
    lua.execute(setup)
    lua.execute("TWT_CONFIG = " + config)
    lua.execute(SOURCE, "TWThreat.lua")
    lua.execute('event("ADDON_LOADED", "TWThreat")')
    return lua
