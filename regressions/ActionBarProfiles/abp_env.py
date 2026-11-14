"""The ActionBarProfiles regressions on the shared game model (wowkit).

The addon is loaded from its TOC. Its game API is modelled here as ClassicAPI
documents it (API.md): GetActionInfo, GetCursorInfo, FindSpellBookSlotByID,
C_Item.GetItemCount and C_Item.PickupItem (equipment first, then bags; a
locked item stays put), the macro calls and C_EquipmentSet. The mocks do not
prove native placement, cursor behaviour or when the client sends events.

Setup that runs before the addon loads (saved variables) goes in `load(setup)`;
`profile(actions, name)` replaces this character's profiles at any time.
"""
from pathlib import Path
import os
import wowkit

ROOT = Path(os.environ["VANILLAFORGE_ADDON_ROOT"])

MOCK = r'''
CLASSIC_API_VERSION = 11711
messages = chat
calls, bars, spells, macros, bags, equipment, sets = {}, {}, {}, {}, {}, {}, {}
local function count(name) calls[name] = (calls[name] or 0) + 1 end
function clone(value)
    if type(value) ~= 'table' then return value end
    local result = {}; for k,v in pairs(value) do result[k] = clone(v) end; return result
end
function expect(value, message) if not value then error(message or 'expectation failed') end end
BOOKTYPE_SPELL = 'spell'
-- The game's trigonometry aliases take degrees.
cos = function(value) return math.cos(math.rad(value)) end
sin = function(value) return math.sin(math.rad(value)) end
StaticPopupDialogs = {}; SAVE = 'Save'; CANCEL = 'Cancel'; YES = 'Yes'; NO = 'No'
cvars = { realmName = 'Realm', autoSelfCast = '1' }
function UnitName() return 'Player' end
function GetCVar(name) return cvars[name] end
function SetCVar(name, value) count('SetCVar'); cvars[name] = tostring(value) end
function UnitAffectingCombat() return combat end

-- Action slots ------------------------------------------------------------
function HasAction(slot) count('HasAction'); return bars[slot] ~= nil end
function GetActionInfo(slot)
    count('GetActionInfo'); local action = bars[slot]; if not action then return end
    if action.kind == 'EQUIPMENTSET' then return 'equipmentset', action.name end
    if action.kind == 'UNKNOWN' then return end
    return string.lower(action.kind), action.id
end
function PickupAction(slot)
    count('PickupAction'); expect(slot <= 120, 'invalid action slot'); cursor = bars[slot]; bars[slot] = nil
end
function PlaceAction(slot)
    count('PlaceAction'); expect(slot <= 120, 'invalid action slot')
    if failPlacement then failPlacement = false; return end
    local old = bars[slot]; bars[slot] = clone(cursor); cursor = old
end

-- Spells ------------------------------------------------------------------
spellDB = {}
function learn(id, name, rank)
    local spell = {id = id, name = name, rank = rank}; table.insert(spells, spell); spellDB[id] = spell
end
function GetSpellInfo(id)
    count('GetSpellInfo'); local spell = spellDB[id]; if spell then return spell.name, spell.rank or '' end
end
function FindSpellBookSlotByID(id)
    count('FindSpellBookSlotByID')
    for slot, spell in ipairs(spells) do if spell.id == id then return slot, 'spell' end end
end
function PickupSpell(slot, book)
    count('PickupSpell'); expect(book == 'spell', 'wrong spellbook')
    if spells[slot] then cursor = { kind = 'SPELL', id = spells[slot].id, slot = slot } end
end

-- Items -------------------------------------------------------------------
function GetItemInfo(id) count('GetItemInfo'); return 'Item '..id end
-- Equipment first, then bags 0..4, as C_Item.PickupItem searches.
local function eachItem(f)
    for slot = 1, 19 do if equipment[slot] and f(equipment[slot]) then return end end
    for bag = 0, 4 do
        for _, item in ipairs(bags[bag] or {}) do if f(item) then return end end
    end
end
C_Item = {
    GetItemCount = function(id)
        count('GetItemCount'); local n = 0
        eachItem(function(item) if item.id == id then n = n + 1 end end)
        return n
    end,
    PickupItem = function(id)
        count('PickupItem'); if cursor then return end
        eachItem(function(item)
            if item.id ~= id then return end
            if not item.locked then cursor = { kind = 'ITEM', id = id } end
            return true
        end)
    end,
}

-- Macros and sets -----------------------------------------------------------
function GetMacroInfo(index)
    count('GetMacroInfo'); local m = macros[index]; if m then return m.name, 'Icon', m.body end
end
function PickupMacro(id)
    count('PickupMacro'); if macros[id] then cursor = { kind = 'MACRO', id = id, name = macros[id].name } end
end
C_EquipmentSet = {
    GetEquipmentSetID = function(name) for id,value in pairs(sets) do if value == name then return id end end end,
    PickupEquipmentSet = function(id) if sets[id] then cursor = {kind = 'EQUIPMENTSET', name = sets[id]} end end
}

-- Cursor ------------------------------------------------------------------
function ClearCursor() count('ClearCursor'); cursor = nil end
function GetCursorInfo()
    count('GetCursorInfo'); if not cursor then return end
    if cursor.kind == 'SPELL' then return 'spell', cursor.slot, 'spell', cursor.id end
    if cursor.kind == 'EQUIPMENTSET' then return 'equipmentset', cursor.name end
    if cursor.kind == 'MONEY' then return 'money', cursor.amount end
    return string.lower(cursor.kind), cursor.id
end

-- Menus and popups ----------------------------------------------------------
menu = {}
function UIDropDownMenu_AddButton(info, level)
    level = level or 1; menu[level] = menu[level] or {}; table.insert(menu[level], clone(info))
    expect(table.getn(menu[level]) <= 32, 'native dropdown overflow')
end
function UIDropDownMenu_Initialize(frame, handler, mode, level)
    level = level or 1; menu[level] = {}; frame.initialize = handler; handler(level)
end
function UIDropDownMenu_Refresh() count('RefreshMenu') end
function HideDropDownMenu(level) count('HideMenu'); menu[level] = nil end
function ToggleDropDownMenu(level, value, frame)
    UIDROPDOWNMENU_MENU_VALUE = value; UIDropDownMenu_Initialize(frame, frame.initialize, nil, level)
end
-- The menu entry whose text is `text`, clicked as the native button does.
function choose(level, text)
    for _, info in ipairs(menu[level] or {}) do
        if info.text == text then info.func(info.arg1, info.arg2); return true end
    end
end
popups = {}
function StaticPopup_Show(which, a1)
    local dialog = { which = which, a1 = a1 }; popups[which] = dialog; return dialog
end
function accept(which)
    local dialog = popups[which]; popups[which] = nil
    return StaticPopupDialogs[which].OnAccept(dialog.data)
end
GameTooltip = newWidget('GameTooltip', 'GameTooltip')
Minimap = newWidget('Frame', 'Minimap')
function Minimap:GetEffectiveScale() return 0.8 end
function Minimap:GetLeft() return 100 end
function Minimap:GetBottom() return 100 end
function Minimap:GetTop() return 240 end
function GetCursorPosition() return cursorX, cursorY end

function profile(actions, name)
    ABP_Layout['Player of Realm'] = {{profileName = name or 'Test', actions = actions}}
end
-- Bags changed: the events the client sends, then the next frame.
function bagsChanged() fire('BAG_UPDATE', 0); fire('BAG_UPDATE_DELAYED'); step(0) end
function chatText() return table.concat(messages, '\n') end
'''

def load(setup=""):
    lua = wowkit.runtime()
    lua.execute(MOCK)
    lua.execute(setup)
    wowkit.load_files(lua, ROOT, wowkit.toc_files(ROOT), "ActionBarProfiles")
    lua.execute("fire('VARIABLES_LOADED')")
    return lua
