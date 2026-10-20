"""Shared Lua 5.1 environment for the ActionBarProfiles regressions.

Adapted from the 2026-10-11 modernization harness. Mocks follow the ClassicAPI
GetCursorInfo/GetActionInfo and SuperWoW GetActionText shapes; they do not prove
native action-bar placement, item counts or cursor behavior.
"""
from pathlib import Path
import os
from lupa.lua51 import LuaRuntime

ROOT = Path(os.environ["VANILLAFORGE_ADDON_ROOT"])
SOURCE = ROOT / "ActionBarProfiles.lua"

MOCK = r'''
messages, calls, bars, spells, macros, bags, equipment, sets = {}, {}, {}, {}, {}, {}, {}, {}
local function count(name) calls[name] = (calls[name] or 0) + 1 end
function inc(name) count(name) end
function clone(value)
    if type(value) ~= 'table' then return value end
    local result = {}; for k,v in pairs(value) do result[k] = clone(v) end; return result
end
function expect(value, message) if not value then error(message or 'expectation failed') end end
function link(id) return '|cff00ff00|Hitem:'..id..':0:0:0|h[Item '..id..']|h|r' end
SUPERWOW_VERSION = '2.2'; MAX_SKILLLINE_TABS = 4; NUM_BAG_SLOTS = 4; BOOKTYPE_SPELL = 'spell'
getn, tinsert, tremove, getglobal = table.getn, table.insert, table.remove, function(name) return _G[name] end
cos = function(value) return math.cos(math.rad(value)) end
sin = function(value) return math.sin(math.rad(value)) end
DEFAULT_CHAT_FRAME = { AddMessage = function(_, message) table.insert(messages, message) end }
SlashCmdList, StaticPopupDialogs = {}, {}; SAVE = 'Save'; CANCEL = 'Cancel'
cvars = { realmName = 'Realm', autoSelfCast = '1' }
function UnitName() return 'Player' end
function GetCVar(name) return cvars[name] end
function SetCVar(name, value)
    count('SetCVar'); if failSetting then failSetting = false; error('setting fault') end
    cvars[name] = tostring(value)
end
function UnitAffectingCombat() return combat end
function HasAction(slot) count('HasAction'); return bars[slot] ~= nil end
function SpellInfo(id)
    count('SpellInfo'); local spell = spellDB[id]; if spell then return spell.name, spell.rank or '' end
end
spellDB = {}
function GetActionText(slot)
    count('GetActionText'); local action = bars[slot]; if not action then return end
    if action.kind == 'MACRO' then
        if action.super then return action.name, 'MACRO', 0 end
        local macro = macros[action.id]; return macro and macro.name, 'MACRO', action.id
    elseif action.kind == 'EQUIPMENTSET' then return action.name
    elseif action.kind == 'UNKNOWN' then return end
    return nil, action.kind, action.id
end
function GetActionInfo(slot)
    count('GetActionInfo'); local action = bars[slot]; if not action then return end
    if action.kind == 'EQUIPMENTSET' then return 'equipmentset', action.name end
    if action.kind == 'UNKNOWN' then return end
    return string.lower(action.kind), action.id
end
function GetItemInfo(value)
    count('GetItemInfo'); local id = tonumber(value)
    if not id and type(value) == 'string' then id = tonumber(string.match(value, 'item:(%d+)')) end
    if id and not itemUncached then return 'Item '..id, link(id) end
end
function GetSpellTabInfo(tab)
    count('GetSpellTabInfo'); if tab == 1 then return 'General', nil, 0, table.getn(spells) end
end
function GetSpellName(slot) count('GetSpellName'); local s = spells[slot]; if s then return s.name, s.rank or '' end end
C_SpellBook = { GetSpellBookItemInfo = function(slot, bank)
    count('SpellBookItem'); expect(bank == 0, 'player book only'); local s = spells[slot]
    if s then return { spellID = s.id, name = s.name, subName = s.rank or '', isPassive = s.passive } end
end }
function GetMacroInfo(index)
    count('GetMacroInfo'); local m = macros[index]; if m then return m.name, 'Icon', m.body end
end
function GetMacroIndexByName(name)
    count('GetMacroIndexByName'); for i=1,36 do if macros[i] and macros[i].name == name then return i end end; return 0
end
function GetInventoryItemLink(_, slot) count('InventoryLink'); if equipment[slot] then return link(equipment[slot].id) end end
function IsInventoryItemLocked(slot) return equipment[slot] and equipment[slot].locked end
function GetContainerNumSlots(bag) count('BagSlots'); return bags[bag] and table.getn(bags[bag]) or 0 end
function GetContainerItemLink(bag, slot) count('BagLink'); if bags[bag] and bags[bag][slot] then return link(bags[bag][slot].id) end end
function GetContainerItemInfo(bag, slot)
    count('BagInfo'); local item = bags[bag] and bags[bag][slot]
    if item then return 'Icon', 1, item.locked end
end
function ClearCursor() count('ClearCursor'); cursor = nil end
function CursorHasItem() return cursor and cursor.kind == 'ITEM' end
function CursorHasSpell() return cursor and (cursor.kind == 'SPELL' or cursor.super) end
function CursorHasMacro() return cursor and cursor.kind == 'MACRO' end
function GetCursorMoney() return cursor and cursor.kind == 'MONEY' and cursor.amount or 0 end
function GetCursorInfo()
    count('GetCursorInfo'); if not cursor then return end
    if cursor.kind == 'SPELL' then return 'spell', cursor.slot, 'spell', cursor.id end
    if cursor.kind == 'EQUIPMENTSET' then return 'equipmentset', cursor.name end
    if cursor.kind == 'MONEY' then return 'money', cursor.amount end
    return string.lower(cursor.kind), cursor.id
end
function PickupSpell(slot, book)
    count('PickupSpell'); expect(book == 'spell', 'wrong spellbook')
    if spells[slot] then cursor = { kind = 'SPELL', id = spells[slot].id, slot = slot } end
end
function PickupMacro(id, name)
    count('PickupMacro'); if id == 0 then cursor = { kind = 'MACRO', super = true, name = name }
    elseif macros[id] then cursor = { kind = 'MACRO', id = id, name = macros[id].name } end
end
function PickupInventoryItem(slot)
    count('PickupItem'); local item = equipment[slot]
    if item and not item.locked then cursor = { kind = 'ITEM', id = item.id } end
end
function PickupContainerItem(bag, slot)
    count('PickupItem'); local item = bags[bag] and bags[bag][slot]
    if item and not item.locked then cursor = { kind = 'ITEM', id = item.id } end
end
function PickupAction(slot)
    count('PickupAction'); expect(slot <= 120, 'invalid action slot'); cursor = bars[slot]; bars[slot] = nil
end
function PlaceAction(slot)
    count('PlaceAction'); expect(slot <= 120, 'invalid action slot')
    if failPlacement then failPlacement = false; return end
    if throwPlacement then throwPlacement = false; error('placement fault') end
    local old = bars[slot]; bars[slot] = clone(cursor); cursor = old
end
C_EquipmentSet = {
    GetEquipmentSetID = function(name) for id,value in pairs(sets) do if value == name then return id end end end,
    PickupEquipmentSet = function(id) cursor = {kind = 'EQUIPMENTSET', name = sets[id]} end
}
menu, initialized = {}, {}
UIDROPDOWNMENU_MAXBUTTONS = 32
function UIDropDownMenu_AddButton(info, level)
    level = level or 1; menu[level] = menu[level] or {}; table.insert(menu[level], clone(info))
    expect(table.getn(menu[level]) <= 32, 'native dropdown overflow')
end
function UIDropDownMenu_Initialize(frame, handler, mode, level)
    level = level or 1; menu[level] = {}; frame.initialize = handler; table.insert(initialized, level); handler(level)
end
function UIDropDownMenu_Refresh(frame, value, level) count('RefreshMenu'); expect(level == 1) end
function HideDropDownMenu(level) count('HideMenu'); menu[level] = nil end
function ToggleDropDownMenu(level, value, frame) UIDROPDOWNMENU_MENU_VALUE = value; UIDropDownMenu_Initialize(frame, frame.initialize, nil, level) end
function StaticPopup_Show(which) popupShown = which end
function PlaySound() end
local frameMethods = {}
function frameMethods:GetName() return self.name end
function frameMethods:RegisterEvent(value) self.registered = value end
function frameMethods:RegisterForDrag(value) self.dragButton = value end
function frameMethods:UnregisterEvent(value) self.registered = nil end
function frameMethods:SetScript(script, handler) count('SetScript'); self.scripts[script] = handler end
function frameMethods:GetScript(script) return self.scripts[script] end
function frameMethods:ClearAllPoints() count('ClearAllPoints') end
function frameMethods:SetPoint(...) count('SetPoint'); self.point = {...} end
function frameMethods:GetEffectiveScale() return self.scale end
function frameMethods:GetLeft() return self.left end
function frameMethods:GetBottom() return self.bottom end
function frameMethods:GetTop() return self.top end
function frameMethods:GetParent() return self.parent end
function frameMethods:IsShown() return not self.hidden end
function frameMethods:Hide() self.hidden = true end
function frameMethods:Show() self.hidden = false end
function frameMethods:GetText() return self.text or '' end
function frameMethods:SetText(value) self.text = value end
function frameMethods:SetFocus() self.focused = true end
function frameMethods:SetHeight(value) self.height = value end
function newFrame(name)
    return setmetatable({name = name, scripts = {}}, {__index = function(_,key)
        if frameMethods[key] then return frameMethods[key] end
        if string.find(key, '^[A-Z]') then error('unsupported widget method: '..key) end
    end})
end
ActionBarProfiles_IconFrame = newFrame('ActionBarProfiles_IconFrame')
ABP_DropDownMenu = newFrame('ABP_DropDownMenu')
Minimap = newFrame('Minimap'); Minimap.scale = 0.8; Minimap.left = 100; Minimap.bottom = 100; Minimap.top = 240
UIParent = { GetScale = function() return 1 end }
GameTooltip = { Hide = function() end }
function GetCursorPosition() return cursorX, cursorY end
function startup()
    this = ActionBarProfiles_IconFrame; ABP_OnLoad(); event = 'VARIABLES_LOADED'; ABP_OnEvent(); this = nil
end
function profile(actions, name)
    ABP_Layout['Player of Realm'] = {{profileName = name or 'Test', actions = actions}}
end
function learn(id, name, rank)
    local spell = {id = id, name = name, rank = rank}; table.insert(spells, spell); spellDB[id] = spell
end
function resetCounts() calls = {} end
'''


def load(setup=""):
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(MOCK)
    lua.execute(setup)
    lua.execute(SOURCE.read_text(encoding="utf-8-sig"))
    lua.execute("startup()")
    return lua
