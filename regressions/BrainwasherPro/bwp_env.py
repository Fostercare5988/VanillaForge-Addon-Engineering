"""The BrainwasherPro regressions on the shared game model (wowkit).

Loads the files the selected addon's TOC lists, in order. One option list
drives both gossip shapes: the stock GossipTitleButtonN widgets (1.5) and
ClassicAPI C_GossipInfo.GetOptions/SelectOption (2.0). The mocks do not prove
the device's real option text, the server's confirmations or the timing of a
talent swap.
"""
from pathlib import Path
import os
import wowkit

ROOT = Path(os.environ["VANILLAFORGE_ADDON_ROOT"])

MOCK = r'''
CLASSIC_API_VERSION = 11711
YES, NO, NUMGOSSIPBUTTONS = "Yes", "No", 32
messages, fonts, selected, calls = chat, {}, {}, {}
tooltip = {}
GameTooltip = {
    SetOwner = function() tooltip = {} end,
    SetText = function(_, t) table.insert(tooltip, t) end,
    AddLine = function(_, t) table.insert(tooltip, t) end,
    Show = function() end, Hide = function() end,
}
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
-- 6 pixels per visible character; colour codes take no room.
function Widget:GetStringWidth()
    local t = string.gsub(string.gsub(self.text or "", "|c%x%x%x%x%x%x%x%x", ""), "|r", "")
    return string.len(t) * 6
end
local createFontString = Widget.CreateFontString
function Widget:CreateFontString(name) local f = createFontString(self, name); table.insert(fonts, f); return f end
function Widget:Click() run(self, "OnClick") end
function click(button, mouse) if button and button.shown and button:IsEnabled() then run(button, "OnClick", mouse or "LeftButton") end end
function shownText()
    local out = {}
    for _, f in ipairs(fonts) do if f.text and f.shown then table.insert(out, f.text) end end
    return table.concat(out, "\n")
end
function count(kind) local n = 0; for _, w in ipairs(widgets) do if w.kind == kind then n = n + 1 end end; return n end

-- Timers -----------------------------------------------------------------
now = 0
function advance(dt) now = now + (dt or 0); runTimers() end

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
        -- Wording read in play on OctoWoW, 2026-10-21.
        { id = 90, name = "Reset my talents. (1g0s0c)" },
        { id = 11, name = "Save 1st Specialization." },
        { id = 22, name = "Activate 2nd Specialization  (32/0/19)" },
        { id = 12, name = "Save 2nd Specialization." },
        { id = 33, name = "Buy 3rd Specialization tab for 100 gold." },
        { id = 44, name = "Buy 4th Specialization tab for 300 gold." },
    }
end

-- ActionBarProfiles -------------------------------------------------------
abpLoaded = {}
function ABP_GetProfileNames() return { "PvE", "PvP" } end
function ABP_LoadProfileByName(name) table.insert(abpLoaded, name); return true end
'''


def load(setup=""):
    lua = wowkit.runtime()
    lua.execute(MOCK)
    lua.execute(setup)
    lua.execute("addonNS = {}; __addon_ns = addonNS")
    wowkit.load_files(lua, ROOT, wowkit.toc_files(ROOT), "BrainwasherPro")
    lua.execute('fire("ADDON_LOADED", "BrainwasherPro"); advance(0)')
    return lua
