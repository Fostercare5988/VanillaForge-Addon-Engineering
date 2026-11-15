"""The FostercareBars regressions on the shared game model (wowkit).

The addon is loaded from its TOC with `## LoadSavedVariablesFirst`, so saved
data given to `load(saved=...)` exists when its files run. Its game API is
modelled as ClassicAPI documents it (docs/API.md): GetActionInfo (a set by
its name), GetCursorInfo (a spell as "spell", book slot, "spell", spellID),
FindSpellBookSlotByID, C_Item.GetItemCount and C_Item.PickupItem (equipment
first, then bags; a locked item stays put), the macro calls and
C_EquipmentSet. Popups follow the client's StaticPopup.lua: the first button
hides the popup unless OnAccept returns true, and `data` is the fourth
argument of StaticPopup_Show. FostercareTweaks' ExtraActions is a stand-in
with its documented returns. The mocks do not prove native placement, cursor
behaviour or when the client sends events.
"""
from pathlib import Path
import os
import wowkit

ROOT = Path(os.environ["VANILLAFORGE_ADDON_ROOT"])

MOCK = r'''
CLASSIC_API_VERSION = 12100
bars, spells, spellDB, macros, bags, equipment, sets = {}, {}, {}, {}, {}, {}, {}
calls = {}
local function count(name) calls[name] = (calls[name] or 0) + 1 end
function changes() return (calls.PlaceAction or 0) + (calls.PickupAction or 0) end
function clone(value)
    if type(value) ~= 'table' then return value end
    local copy = {}; for k, v in pairs(value) do copy[k] = clone(v) end; return copy
end
SAVE, CANCEL, YES, NO = 'Save', 'Cancel', 'Yes', 'No'
StaticPopupDialogs = {}
function UnitAffectingCombat() return combat end

-- Action slots hold {kind, id}; a set's id is its name, as GetActionInfo reports it.
local function slotOK(slot) assert(slot >= 1 and slot <= 120, 'invalid action slot') end
function GetActionInfo(slot) slotOK(slot); local a = bars[slot]; if a then return a.kind, a.id end end
function PickupAction(slot) slotOK(slot); count('PickupAction'); cursor, bars[slot] = bars[slot], nil end
function PlaceAction(slot) slotOK(slot); count('PlaceAction'); bars[slot], cursor = cursor, bars[slot] end
function ClearCursor() cursor = nil end
function GetCursorInfo()
    if not cursor then return end
    if cursor.kind == 'spell' then return 'spell', cursor.book, 'spell', cursor.id end
    return cursor.kind, cursor.id
end

-- Spells: the player's book in order.
function learn(id, name)
    spells[#spells + 1] = id; spellDB[id] = name or ('Spell ' .. id)
end
function GetSpellInfo(id) return spellDB[id] end
function FindSpellBookSlotByID(id)
    for slot, known in ipairs(spells) do if known == id then return slot, 'spell' end end
end
function PickupSpell(slot, book)
    assert(book == 'spell', 'wrong spellbook')
    if spells[slot] then cursor = { kind = 'spell', id = spells[slot], book = slot } end
end

-- Items: equipment first, then the bags, as C_Item.PickupItem searches.
function give(id, n, locked) for _ = 1, n or 1 do bags[#bags + 1] = { id = id, locked = locked } end end
function GetItemInfo(id) return 'Item ' .. id end
local function eachItem(f)
    for _, item in pairs(equipment) do if f(item) then return end end
    for _, item in ipairs(bags) do if f(item) then return end end
end
C_Item = {
    GetItemCount = function(id)
        local n = 0; eachItem(function(item) if item.id == id then n = n + 1 end end); return n
    end,
    PickupItem = function(id)
        if cursor then return end
        eachItem(function(item)
            if item.id ~= id then return end
            if not item.locked then cursor = { kind = 'item', id = id } end
            return true
        end)
    end,
}

-- Macros (index -> {name, body}) and sets (setID -> name).
function GetMacroInfo(index) local m = macros[index]; if m then return m.name, 'Icon', m.body end end
function PickupMacro(index) if macros[index] then cursor = { kind = 'macro', id = index } end end
C_EquipmentSet = {
    GetEquipmentSetID = function(name) for id, value in pairs(sets) do if value == name then return id end end end,
    PickupEquipmentSet = function(id) if sets[id] then cursor = { kind = 'equipmentset', id = sets[id] } end end,
}

-- Popups, as StaticPopup.lua runs them.
popup = CreateFrame('Frame', 'StaticPopup1'); popup:Hide()
popupBox = CreateFrame('EditBox', 'StaticPopup1EditBox', popup)
popupButton = CreateFrame('Button', 'StaticPopup1Button1', popup)
function StaticPopup_Show(which, a1, a2, data)
    local info = StaticPopupDialogs[which]
    if not info then return end
    popup.which, popup.data, popup.text = which, data, string.format(info.text, a1 or '', a2 or '')
    popupBox:SetText('')
    popup:Show()
    if info.OnShow then this = popup; info.OnShow(data); this = nil end
    return popup
end
function popupShown() return popup:IsShown() and popup.which end
function accept(text)
    if text then popupBox:SetText(text) end
    this = popupButton
    local keep = StaticPopupDialogs[popup.which].OnAccept(popup.data, popup.data2)
    this = nil
    if not keep then popup:Hide() end
end
function pressEnter(text)
    popupBox:SetText(text); this = popupBox
    StaticPopupDialogs[popup.which].EditBoxOnEnterPressed(popup.data)
    this = nil
end

-- FostercareTweaks' Extra Rows 2-7 (its ExtraActions.lua returns).
function tweaksOn(rows)
    local extra = { ProfileVersion = 1, rows = rows or { version = 1, rows = { [2] = { [1] = { kind = 'spell', id = 5 } } } }, log = {} }
    function extra:GetProfile() if self.failGet then return nil, self.failGet end; return clone(self.rows) end
    function extra:ValidateProfile(saved)
        self.log[#self.log + 1] = 'validate after ' .. changes() .. ' changes'
        if self.failValidate then return nil, self.failValidate end
        return clone(saved)
    end
    function extra:ApplyProfile(checked)
        self.log[#self.log + 1] = 'apply after ' .. changes() .. ' changes'
        if self.failApply then return false, self.failApply end
        self.applied = checked; return true
    end
    FostercareTweaks = { ExtraActions = extra }
end

function chatText() return table.concat(chat, '\n') end
function bagsChanged() fire('BAG_UPDATE', 0); fire('BAG_UPDATE_DELAYED'); step(0) end
-- Every frame registered for an event, or with an OnUpdate.
function busyFrames()
    local out = {}
    for _, w in ipairs(widgets) do
        for event in pairs(w.events) do out[#out + 1] = event end
        if w.scripts.OnUpdate then out[#out + 1] = 'OnUpdate' end
    end
    table.sort(out)
    return table.concat(out, ',')
end
'''

GLOBALS = ("FostercareBarsDB", "FostercareBars", "ABP_GetProfileNames", "ABP_LoadProfileByName",
           "SLASH_FOSTERCAREBARS1")


def load(saved="", setup="", world=True):
    """The addon loaded over `saved` (Lua that sets FostercareBarsDB); with
    `world`, the login events have fired, so the Settings page exists."""
    lua = wowkit.runtime()
    lua.execute(MOCK)
    lua.execute(setup)
    wowkit.load_addon(lua, ROOT, "FostercareBars", saved=saved or None)
    if world:
        lua.execute('fire("VARIABLES_LOADED") fire("PLAYER_ENTERING_WORLD")')
    return lua


def profiles(lua):
    """The saved profile names, in the addon's order."""
    return list(lua.eval("FostercareBars.GetProfileNames()").values())
