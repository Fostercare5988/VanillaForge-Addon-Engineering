"""Specs 1.0 (written new, 2026-11-22) on the shared game model (wowkit).

The device is modelled by its option texts (read in play on OctoWoW, 2026-10-21,
from the old addon) through ClassicAPI's C_GossipInfo (API.md "C_GossipInfo.GetOptions()");
the gossip window is the stock GossipFrame with its greeting scroll frame
(FrameXML GossipFrame.xml); popups are the stock StaticPopup's (`StaticPopup_Show`
with a 4th `data` argument, the edit-box dialog's children named `<dialog>EditBox`).
The menu system and the icon provider are stand-ins that run the generator and the
mixin's four calls.

What the kit should model (this suite stubs it): `SetEnabled` on buttons; the
stock StaticPopup (Show with data, Hide, the dialog's edit box); `GameTooltip`;
`MenuUtil.CreateContextMenu` and a menu description (CreateTitle, CreateButton,
CreateRadio); `IconDataProviderMixin` with `CreateAndInitFromMixin`;
`fontstring:SetMaxLines`/`IsTruncated`; `UnitAffectingCombat`; the talent calls
(`GetNumTalents`, `GetTalentInfo`, `GetTalentTabInfo`) and C_GossipInfo.
The mocks do not prove drawing, the server's replies or the timing of a swap.
"""
from pathlib import Path
import os
import wowkit

ROOT = Path(os.environ["VANILLAFORGE_ADDON_ROOT"])

MOCK = r'''
CLASSIC_API_VERSION = 12302
YES, NO, ACCEPT, CANCEL = "Yes", "No", "Accept", "Cancel"
calls = {}
local function record(name, value) calls[name] = calls[name] or {}; table.insert(calls[name], value) end
function count(name) return calls[name] and #calls[name] or 0 end
function last(name) local list = calls[name]; return list and list[#list] end
function forget() calls = {} end

function Widget:SetEnabled(on) self.enabled = on and true or false end
function Widget:SetMaxLines(n) self.maxLines = n end
function Widget:SetBackdrop() end
function Widget:SetBackdropColor() end
function Widget:SetFrameLevel(n) self.level = n end
function Widget:GetFrameLevel() return self.level or 1 end
function click(w) run(w, 'OnClick', 'LeftButton') end

GameTooltip = {
    lines = {},
    SetOwner = function(self) self.lines = {} end,
    SetText = function(self, t) table.insert(self.lines, t) end,
    AddLine = function(self, t) table.insert(self.lines, t) end,
    Show = function() end, Hide = function() end,
}

-- Combat and talents: ranks[tab] is a list of ranks; tab points are their sum.
inCombat = false
function UnitAffectingCombat() return inCombat end
ranks = { {}, {}, {} }
function setBuild(a, b, c) ranks = { a, b, c } end
function GetNumTalents(tab) return #ranks[tab] end
function GetTalentInfo(tab, i) return 'T' .. tab .. i, 'icon', 1, i, ranks[tab][i], 5 end
function GetTalentTabInfo(tab)
    local sum = 0
    for _, r in ipairs(ranks[tab]) do sum = sum + r end
    return 'Tree' .. tab, 'Interface\\Icons\\Tree' .. tab, sum
end
-- A build of n points in a tree: n talents of rank 1 (one digit each).
function points(n) local t = {} for i = 1, n do t[i] = 1 end return t end

-- The stock popups: Show keeps the text, the data and the edit box.
StaticPopupDialogs = {}
popups = {}
function StaticPopup_Show(which, a1, a2, data)
    local info = StaticPopupDialogs[which]
    local dialog = newWidget('Frame', 'StaticPopup_' .. which)
    local box = newWidget('EditBox', dialog.name .. 'EditBox', dialog)
    local accept = newWidget('Button', nil, dialog)
    dialog.text, dialog.data, dialog.accept, dialog.box = string.format(info.text, a1 or '', a2 or ''), data, accept, box
    popups[which] = dialog
    if info.OnShow then this = dialog; info.OnShow(data) end
    return dialog
end
function StaticPopup_Hide(which) popups[which] = nil end
-- The player presses Accept / Yes, or Enter in the edit box.
function accept(which)
    local d = popups[which]
    if not d then return false end
    popups[which] = nil
    this = d.accept
    StaticPopupDialogs[which].OnAccept(d.data, d.data2)
    return true
end
function enter(which, text)
    local d = popups[which]
    d.box:SetText(text)
    this = d.box
    StaticPopupDialogs[which].EditBoxOnEnterPressed(d.data)
    popups[which] = nil
end

-- The gossip window as GossipFrame.xml makes it, and the device's menu.
GossipFrame = newWidget('Frame', 'GossipFrame'); GossipFrame.shown = false
GossipGreetingScrollFrame = newWidget('ScrollFrame', 'GossipGreetingScrollFrame', GossipFrame)
options, selected = {}, {}
C_GossipInfo = {
    GetOptions = function()
        local out = {}
        for i, o in ipairs(options) do out[i] = { gossipOptionID = o[1], name = o[2], flags = 0, orderIndex = i } end
        return out
    end,
    SelectOption = function(id) table.insert(selected, id) end,
}
function talk(list)
    options = list
    GossipFrame:Show(); GossipGreetingScrollFrame:Show()
    fire('GOSSIP_SHOW')
end
function leave() GossipFrame:Hide(); fire('GOSSIP_CLOSED') end
-- Wording read in play, 2026-10-21 (the old addon's header).
function device(splits, extra)
    local list, ord = {}, { '1st', '2nd', '3rd', '4th', '5th' }
    list[#list + 1] = { 90, 'Reset my talents. (1g0s0c)' }
    for slot, s in ipairs(splits) do
        list[#list + 1] = { 10 + slot, 'Save ' .. ord[slot] .. ' Specialization.' }
        list[#list + 1] = { 20 + slot, 'Activate ' .. ord[slot] .. ' Specialization  (' .. s .. ')' }
    end
    local n = #splits + 1
    list[#list + 1] = { 30 + n, 'Buy ' .. ord[n] .. ' Specialization tab for 200 gold.' }
    return list
end
CLAUDE = { '41/10/0', '32/0/19', '41/10/0' }

-- ActionBars' public table (its Profiles.lua).
barsLoaded, profiles = {}, { 'PVE', 'pvp', 'pveBWL' }
ActionBars = {
    GetProfileNames = function() return profiles end,
    LoadProfile = function(name) table.insert(barsLoaded, name); return true end,
}

-- MenuUtil: the generator runs on a description that records what it was given.
local Desc = {}
Desc.__index = Desc
local function desc(kind, text, f, selected)
    return setmetatable({ kind = kind, text = text, f = f, isOn = selected, items = {} }, Desc)
end
function Desc:CreateTitle(t) local d = desc('title', t); table.insert(self.items, d); return d end
function Desc:CreateButton(t, f) local d = desc('button', t, f); table.insert(self.items, d); return d end
function Desc:CreateRadio(t, sel, f) local d = desc('radio', t, f, sel); table.insert(self.items, d); return d end
function Desc:item(text) for _, d in ipairs(self.items) do if d.text == text then return d end end end
menu = nil
MenuUtil = { CreateContextMenu = function(owner, generator)
    menu = desc('root')
    generator(owner, menu)
end }

-- ClassicAPI's icon provider: the spellbook's icons first, then 500 more.
released = 0
IconDataProviderExtraType = { Spellbook = 1 }
IconDataProviderMixin = {
    GetNumIcons = function() return 3 + 500 end,
    GetIconByIndex = function(self, i)
        if i == 1 then return 'Interface\\Icons\\INV_Misc_QuestionMark' end
        if i <= 4 then return 'Interface\\Icons\\Book' .. i end
        if i <= 503 then return 'INTERFACE\\ICONS\\Base' .. i end
    end,
    Release = function() released = released + 1 end,
}
function CreateAndInitFromMixin(mixin) return mixin end

-- Which frames listen to what, and every OnUpdate.
function listening()
    local out = {}
    for _, w in ipairs(widgets) do
        for e in pairs(w.events) do out[#out + 1] = e end
        if w.scripts.OnUpdate then out[#out + 1] = 'OnUpdate' end
    end
    table.sort(out)
    return table.concat(out, ',')
end
function liveTimers() local n = 0; for _, t in ipairs(timers) do if not t.cancelled then n = n + 1 end end; return n end
function say() return table.concat(chat, '\n') end
'''

# Claude's saved slots (the real file, minus the splits the device sends).
CLAUDE_SAVED = '''SpecsDB = {
  current = 2,
  [1] = { name = "PVE ASSA", icon = "Interface\\\\Icons\\\\Ability_Rogue_DualWeild", bars = "PVE" },
  [2] = { name = "PVP ASSA", icon = "Interface\\\\Icons\\\\Ability_Rogue_Garrote", bars = "pvp",
          build = "%s" },
  [3] = { name = "BWL", icon = "Interface\\\\Icons\\\\Spell_Shadow_DeathScream", bars = "PVE" },
}'''
# A build of 32/0/19 points: the first tree 32 talents of rank 1, the third 19.
BUILD_32_0_19 = "1" * 32 + "-" + "-" + "1" * 19


def load(saved="", setup="", world=True):
    """The addon loaded over `saved` (Lua that sets SpecsDB); with `world`, the
    login events have fired."""
    lua = wowkit.runtime()
    lua.execute(MOCK)
    lua.execute(setup)
    wowkit.load_addon(lua, ROOT, "Specs", saved=saved or None)
    if world:
        lua.execute('fire("VARIABLES_LOADED") fire("PLAYER_LOGIN") fire("PLAYER_ENTERING_WORLD") step()')
    return lua
