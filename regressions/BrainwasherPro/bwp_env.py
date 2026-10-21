"""Shared Lua 5.1 environment for the BrainwasherPro regressions.

Loads the files the selected addon's TOC lists, in order. One option list
drives both gossip shapes: the stock GossipTitleButtonN widgets (1.5) and
ClassicAPI C_GossipInfo.GetOptions/SelectOption (2.0). The mocks do not prove
the device's real option text, the server's confirmations or the timing of a
talent swap.
"""
from pathlib import Path
import os
import re
from lupa.lua51 import LuaRuntime

ROOT = Path(os.environ["VANILLAFORGE_ADDON_ROOT"])

MOCK = r'''
math.mod = math.mod or math.fmod
table.getn = table.getn or function(t) return #t end
function table.wipe(t) for k in pairs(t) do t[k] = nil end return t end
getglobal = function(n) return _G[n] end
tinsert, tremove = table.insert, table.remove
CLASSIC_API_VERSION = 11600
YES, NO, NUMGOSSIPBUTTONS = "Yes", "No", 32
messages, widgets, fonts, selected, calls = {}, {}, {}, {}, {}
DEFAULT_CHAT_FRAME = { AddMessage = function(_, m) table.insert(messages, m) end }
SlashCmdList, UISpecialFrames = {}, {}
GameTooltip = { SetOwner = function() end, SetText = function() end, Show = function() end, Hide = function() end }
inCombat, talents = false, { 0, 0, 0 }
function UnitAffectingCombat() return inCombat end
function GetTalentTabInfo(tab) return "Tab" .. tab, "Icon", talents[tab] end
function GetTalentInfo() end
function GetAddOnMetadata(_, key) if key == "Version" then return "test" end end
function CloseGossip() selected.closed = true end
numIcons = 600
function GetNumMacroIcons() return numIcons end
function GetMacroIconInfo(i) calls.icon = (calls.icon or 0) + 1; return "Interface\\Icons\\Icon" .. i end

-- Widgets ----------------------------------------------------------------
local Widget = {}
local mt = { __index = function(_, k)
    local m = Widget[k]; if m then return m end
    if type(k) == "string" and string.find(k, "^[A-Z]") then return function() end end
end }
function newWidget(kind, name)
    local w = setmetatable({ kind = kind, name = name, scripts = {}, events = {}, shown = true, alpha = 1, scale = 1 }, mt)
    if name then _G[name] = w end
    table.insert(widgets, w)
    return w
end
function run(w, script, ...)
    local f = w.scripts[script]
    if f then local old = this; this = w; f(w, ...); this = old end
end
function Widget:SetScript(k, f) self.scripts[k] = f end
function Widget:GetScript(k) return self.scripts[k] end
function Widget:RegisterEvent(e) self.events[e] = true end
function Widget:UnregisterEvent(e) self.events[e] = nil end
function Widget:Show() if not self.shown then self.shown = true; run(self, "OnShow") end end
function Widget:Hide() if self.shown then self.shown = false; run(self, "OnHide") end end
function Widget:IsShown() return self.shown end
function Widget:IsVisible() return self.shown end
function Widget:GetName() return self.name end
function Widget:Enable() self.disabled = false end
function Widget:Disable() self.disabled = true end
function Widget:GetText() return self.text end
function Widget:SetText(v) self.text = v; if self.font then self.font:SetText(v) end end
function Widget:SetFontString(f) self.font = f end
function Widget:GetFontString() return self.font end
function Widget:SetAlpha(v) self.alpha = v end
function Widget:GetAlpha() return self.alpha end
function Widget:SetScale(v) self.scale = v end
function Widget:GetScale() return self.scale end
function Widget:SetTexture(v) self.texture = v end
function Widget:GetTexture() return self.texture end
function Widget:CreateFontString() local f = newWidget("FontString"); table.insert(fonts, f); return f end
function Widget:CreateTexture() return newWidget("Texture") end
function Widget:Click() run(self, "OnClick") end
function CreateFrame(kind, name) return newWidget(kind, name) end
UIParent = newWidget("Frame", "UIParent")

function fire(ev, a1)
    for _, w in ipairs(widgets) do
        if w.events[ev] and w.scripts.OnEvent then event, arg1 = ev, a1; run(w, "OnEvent") end
    end
end
function click(button, mouse) if button and button.shown and not button.disabled then arg1 = mouse or "LeftButton"; run(button, "OnClick") end end
function shownText()
    local out = {}
    for _, f in ipairs(fonts) do if f.text and f.shown then table.insert(out, f.text) end end
    return table.concat(out, "\n")
end
function count(kind) local n = 0; for _, w in ipairs(widgets) do if w.kind == kind then n = n + 1 end end; return n end

-- Timers -----------------------------------------------------------------
now, timers = 0, {}
C_Timer = { After = function(s, f) table.insert(timers, { at = now + s, fn = f }) end }
function advance(dt)
    now = now + (dt or 0)
    local ran = true
    while ran do
        ran = false
        for i, t in ipairs(timers) do
            if t.at <= now then table.remove(timers, i); t.fn(); ran = true; break end
        end
    end
end

-- Popups -----------------------------------------------------------------
StaticPopupDialogs, popups = {}, {}
function StaticPopup_Show(which, a1, a2)
    local info = StaticPopupDialogs[which]
    local dialog = { which = which, text = string.format(info.text, a1 or "", a2 or "") }
    popups[which] = dialog
    return dialog
end
function StaticPopup_Hide(which) popups[which] = nil end
function accept(which)
    local dialog = popups[which]
    if not dialog then return false end
    popups[which] = nil
    StaticPopupDialogs[which].OnAccept(dialog.data, dialog.data2)
    return true
end

-- Gossip -----------------------------------------------------------------
GossipFrame = newWidget("Frame", "GossipFrame")
GossipFrameNpcNameText = newWidget("FontString", "GossipFrameNpcNameText")
options = {}
for i = 1, 32 do
    local b = newWidget("Button", "GossipTitleButton" .. i)
    b.shown = false
    b.scripts.OnClick = function() table.insert(selected, options[i].id) end
end
function talk(npc, list)
    options = list
    GossipFrameNpcNameText.text = npc
    GossipFrame.shown = true
    for i = 1, 32 do
        local b = _G["GossipTitleButton" .. i]
        b.shown = list[i] ~= nil
        b.text = list[i] and list[i].name
    end
    fire("GOSSIP_SHOW"); advance(0)
end
function leave() GossipFrame.shown = false; fire("GOSSIP_CLOSED"); advance(0) end
C_GossipInfo = {
    GetOptions = function()
        local out = {}
        for i, o in ipairs(options) do out[i] = { gossipOptionID = o.id, name = o.name, flags = o.flags or 0, orderIndex = i, icon = 0 } end
        return out
    end,
    SelectOption = function(id) table.insert(selected, id) end,
}
DEVICE = "Goblin Brainwashing Device"
function deviceMenu()
    return {
        { id = 11, name = "Save 1st Specialization" },
        { id = 12, name = "Save 2nd Specialization" },
        { id = 22, name = "Activate 2nd Specialization" },
        { id = 33, name = "Buy 3rd Specialization for 100 gold" },
        { id = 44, name = "Buy 4th Specialization for 300 gold" },
        { id = 90, name = "Reset my talents for 5 gold" },
    }
end

-- ActionBarProfiles -------------------------------------------------------
abpLoaded = {}
function ABP_GetProfileNames() return { "PvE", "PvP" } end
function ABP_LoadProfileByName(name) table.insert(abpLoaded, name); return true end
'''

LUA50_FOR = re.compile(r"(for\s+[\w\s,]+\s+in\s+)([A-Za-z_][\w.]*)(\s+do)")


def _sources():
    toc = (ROOT / "BrainwasherPro.toc").read_text("utf-8-sig")
    for line in toc.splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            yield line, (ROOT / line).read_text("utf-8-sig")


def load(setup=""):
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(MOCK)
    lua.execute(setup)
    lua.execute("addonNS = {}")
    chunk = lua.eval("function(src, name) return assert(loadstring(src, name)) end")
    for name, src in _sources():
        src = LUA50_FOR.sub(lambda m: m.group(1) + "pairs(" + m.group(2) + ")" + m.group(3), src)
        chunk(src, "@" + name)("BrainwasherPro", lua.eval("addonNS"))
    lua.execute('fire("ADDON_LOADED", "BrainwasherPro"); advance(0)')
    return lua
