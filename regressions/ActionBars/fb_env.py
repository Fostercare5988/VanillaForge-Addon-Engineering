"""The ActionBars regressions on the shared game model (wowkit).

The addon is loaded from its TOC with `## LoadSavedVariablesFirst`, so saved
data given to `load(saved=...)` exists when its files run. Its game API is
modelled as ClassicAPI documents it (docs/API.md): GetActionInfo (a set by
its name), GetCursorInfo (a spell as "spell", book slot, "spell", spellID),
FindSpellBookSlotByID, C_Item.GetItemCount and C_Item.PickupItem (equipment
first, then bags; a locked item stays put), the macro calls and
C_EquipmentSet. Popups follow the client's StaticPopup.lua: the first button
hides the popup unless OnAccept returns true, and `data` is the fourth
argument of StaticPopup_Show. Tweaks' ExtraActions is a stand-in
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

-- Macros (index -> {name, body}) and sets (setID -> name). GetMacroInfo also takes a name.
function GetMacroIndexByName(name)
    for index = 1, 36 do if macros[index] and macros[index].name == name then return index end end
    return 0
end
function GetMacroInfo(index)
    if type(index) == 'string' then index = GetMacroIndexByName(index) end
    local m = macros[index]; if m then return m.name, 'Icon' .. index, m.body end
end
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

function chatText() return table.concat(chat, '\n') end
function bagsChanged() fire('BAG_UPDATE', 0); fire('BAG_UPDATE_DELAYED'); step(0) end
-- The frames that listen from login on (the bars' slot events, test_at_rest pins
-- them); busyFrames() names what any other frame listens to, and every OnUpdate.
restFrames = {}
function markRest() for _, w in ipairs(widgets) do if next(w.events) then restFrames[w] = true end end end
local function listening(all)
    local out = {}
    for _, w in ipairs(widgets) do
        if all or not restFrames[w] then for event in pairs(w.events) do out[#out + 1] = event end end
        if w.scripts.OnUpdate then out[#out + 1] = 'OnUpdate' end
    end
    table.sort(out)
    return table.concat(out, ',')
end
function busyFrames() return listening(false) end
function allEvents() return listening(true) end
'''

BARS = r'''
-- The action slots as the buttons read them (stock ActionButton.lua's calls;
-- ClassicAPI's ### C_ActionBar.EnableActionRangeCheck, ### GetCursorInfo()).
-- A slot's texture is 'tex:<kind>:<id>'; usable, cooldown and state are tables a test sets.
usable, cooldowns, current, autoRepeat, attackSlots = {}, {}, {}, {}, {}
rangeChecks, used, overrides, keys = {}, {}, {}, {}
CURRENT_ACTIONBAR_PAGE, bonusOffset, playerClass, LOCK_ACTIONBAR = 1, 0, 'ROGUE', '0'
RANGE_INDICATOR = '*dot*'
function UnitClass() return playerClass, playerClass end
function hooksecurefunc(name, f)
    if name == 'CooldownFrame_SetTimer' then hookedTimer = f; return end
    local old = _G[name]
    _G[name] = function(a, b, c) local r = old(a, b, c); f(a, b, c); return r end
end
function IsShiftKeyDown() return shift end
function GetBonusBarOffset() return bonusOffset end
local reads = {}
function readsOf(slot) return reads[slot] or 0 end
function HasAction(slot) return bars[slot] and 1 or nil end
function GetActionTexture(slot)
    reads[slot] = (reads[slot] or 0) + 1
    local a = bars[slot]; if a then return 'tex:' .. a.kind .. ':' .. tostring(a.id) end
end
function GetActionText(slot) local a = bars[slot]; if a and a.kind == 'macro' then return macros[a.id].name end end
function IsUsableAction(slot) local u = usable[slot]; if u == nil then return 1 end; if u == 'mana' then return nil, 1 end; return u end
function GetActionCooldown(slot) local c = cooldowns[slot]; if c then return c[1], c[2], 1 end; return 0, 0, 0 end
function IsConsumableAction(slot) local a = bars[slot]; return a and a.kind == 'item' and 1 or nil end
function GetActionCount(slot) return C_Item.GetItemCount(bars[slot].id) end
function IsItemAction(slot) local a = bars[slot]; return a and a.kind == 'item' and 1 or nil end
function IsEquippedAction(slot) local a = bars[slot]; return a and a.kind == 'item' and equipment[a.id] and 1 or nil end
function IsCurrentAction(slot) return current[slot] end
function IsAutoRepeatAction(slot) return autoRepeat[slot] end
function IsAttackAction(slot) return attackSlots[slot] end
function UseAction(slot, checkCursor, onSelf) used[#used + 1] = slot; usedCheckCursor = checkCursor end
reagentSpells = {}
C_ActionBar = {
    EnableActionRangeCheck = function(slot, on) rangeChecks[slot] = (rangeChecks[slot] or 0) + (on and 1 or -1) end,
    GetSpell = function(slot) local a = bars[slot]; return a and a.kind == 'spell' and a.id or 0 end,
}
function IsConsumableSpell(id) return reagentSpells[id] ~= nil end
function IsConsumableItem(id) return 1 end

-- Keys and the tooltip. The game's own bindings run the stock functions as
-- ClassicAPI replaces them (its Util/ActionButton.lua: ActionButtonUseKeyDown,
-- the slot from ActionButton_GetPagedID, FrameXML ActionButton.lua:441).
cvars = { ActionButtonUseKeyDown = '0' }
function GetCVar(name) return cvars[name] end
BOTTOMLEFT_ACTIONBAR_PAGE, BOTTOMRIGHT_ACTIONBAR_PAGE, LEFT_ACTIONBAR_PAGE, RIGHT_ACTIONBAR_PAGE = 6, 5, 4, 3
function ActionButton_GetPagedID(button)
    if button.isBonus and CURRENT_ACTIONBAR_PAGE == 1 then return button:GetID() + (5 + bonusOffset) * 12 end
    local parent = button:GetParent() and button:GetParent():GetName()
    if parent == 'MultiBarBottomLeft' then return button:GetID() + (BOTTOMLEFT_ACTIONBAR_PAGE - 1) * 12
    elseif parent == 'MultiBarBottomRight' then return button:GetID() + (BOTTOMRIGHT_ACTIONBAR_PAGE - 1) * 12
    elseif parent == 'MultiBarLeft' then return button:GetID() + (LEFT_ACTIONBAR_PAGE - 1) * 12
    elseif parent == 'MultiBarRight' then return button:GetID() + (RIGHT_ACTIONBAR_PAGE - 1) * 12 end
    return button:GetID() + (CURRENT_ACTIONBAR_PAGE - 1) * 12
end
function GetBindingKey(command) local k = keys[command]; if k then return k[1], k[2] end end
function GetBindingText(key) return 'k' .. key end
function SetOverrideBindingClick(owner, priority, key, name) overrides[key] = name end
function ClearOverrideBindings() overrides = {} end
function Widget:Click(button) run(self, 'OnClick', button or 'LeftButton') end
function Widget:GetButtonState() return self.buttonState or 'NORMAL' end
function Widget:SetButtonState(state) self.buttonState = state end
local function stockButton(id)
    return _G[(BonusActionBarFrame:IsShown() and 'BonusAction' or 'Action') .. 'Button' .. id]
end
local function keyDown() return cvars.ActionButtonUseKeyDown == '1' end
local function down(button)
    if button:GetButtonState() == 'NORMAL' then button:SetButtonState('PUSHED') end
    if keyDown() then UseAction(ActionButton_GetPagedID(button), 0) end
end
local function up(button, onSelf)
    if button:GetButtonState() == 'PUSHED' then
        button:SetButtonState('NORMAL')
        if not keyDown() then UseAction(ActionButton_GetPagedID(button), 0, onSelf) end
    end
end
function ActionButtonDown(id) down(stockButton(id)) end
function ActionButtonUp(id, onSelf) up(stockButton(id), onSelf) end
function MultiActionButtonDown(bar, id) down(_G[bar .. 'Button' .. id]) end
function MultiActionButtonUp(bar, id, onSelf) up(_G[bar .. 'Button' .. id], onSelf) end
local MULTI = { 'MultiBarBottomLeft', 'MultiBarBottomRight', 'MultiBarRight', 'MultiBarLeft' }
-- A key press: its binding's down half, then (unless only `half` is 'down') the up
-- half. An override wins over the saved binding (### Override bindings); a CLICK
-- one clicks its button on release (### Direct-action bindings, "AnyUp").
function pressKey(key, half)
    if overrides[key] then
        if half ~= 'down' then _G[overrides[key]]:Click('LeftButton') end
        return
    end
    for command, k in pairs(keys) do
        if k[1] == key or k[2] == key then
            local id = tonumber(string.match(command, '^ACTIONBUTTON(%d+)$'))
            local m, mid = string.match(command, '^MULTIACTIONBAR(%d)BUTTON(%d+)$')
            if id then
                ActionButtonDown(id); if half ~= 'down' then ActionButtonUp(id) end
            elseif m then
                MultiActionButtonDown(MULTI[tonumber(m)], tonumber(mid))
                if half ~= 'down' then MultiActionButtonUp(MULTI[tonumber(m)], tonumber(mid)) end
            end
        end
    end
end
GameTooltip = CreateFrame('GameTooltip', 'GameTooltip')
function GameTooltip:SetOwner(owner) self.owner = owner end
function GameTooltip:IsOwned(f) return self.owner == f and 1 or nil end
function GameTooltip:Hide() self.owner = nil end
for _, m in ipairs({ 'SetAction', 'SetSpellByID', 'SetHyperlink', 'SetEquipmentSet' }) do
    local method = m
    GameTooltip[method] = function(self, value) self.shows = method .. ' ' .. tostring(value); return counting[value] end
end

-- The look: ClassicAPI's formatter, the Cooldown frame's calls recorded.
Enum = { NumericRuleFormatRounding = { Up = 1 }, PlayerSwingType = { MainHand = 0, OffHand = 1, Ranged = 2 } }
-- The swing range (### C_SwingTimer.EnableRangeCheck), self buffs, worn items, spells on slots.
selfBuffs, counting = {}, {}
C_SwingTimer = {
    EnableRangeCheck = function(swingType, on) swingChecks = (swingChecks or 0) + (on and 1 or -1) end,
    IsTargetWithinSwingRange = function() return swingInRange end,
}
-- Moving a frame makes it the client's to save (layout-cache.txt).
-- Positions, dragging and the client's saved places: the kit's (wowkit.py, "Positions").
C_StringUtil = { CreateNumericRuleFormatter = function() return { SetBreakpoints = function() end } end }
function Widget:SetCooldown(start, duration) self.cd = start .. '+' .. duration end
function Widget:Clear() self.cd = nil end
function Widget:SetSwipeColor(r, g, b, a) self.swipe = { r, g, b, a } end
function Widget:SetDrawBling(on) self.bling = on end
function Widget:SetHideCountdownNumbers(on) self.hideNumbers = on end
function Widget:SetNormalTexture(path) self.normalPath = path end
function Widget:GetEffectiveScale() return self.scale or 1 end
local kitCreate = CreateFrame
local PARTS = { Icon = 'Texture', Flash = 'Texture', HotKey = 'FontString', Count = 'FontString',
    Name = 'FontString', Border = 'Texture', NormalTexture = 'Texture', Cooldown = 'Model' }
function CreateFrame(kind, name, parent, template)
    local f = kitCreate(kind, name, parent)
    if template == 'ActionButtonTemplate' then
        for part, partKind in pairs(PARTS) do newWidget(partKind, name .. part, f) end
        _G[name .. 'Flash']:Hide()
    end
    return f
end

-- The stock bars and MainMenuBar's pieces (FrameXML ActionBarFrame.xml, MainMenuBar.xml).
MainMenuBar = newWidget('Frame', 'MainMenuBar', UIParent)
MainMenuBarArtFrame = newWidget('Frame', 'MainMenuBarArtFrame', MainMenuBar)
for _, name in ipairs({ 'BonusActionBarFrame', 'MultiBarBottomLeft', 'MultiBarBottomRight', 'MultiBarLeft',
    'MultiBarRight', 'MainMenuExpBar', 'MainMenuBarMaxLevelBar', 'ReputationWatchBar', 'ReputationWatchStatusBar',
    'ShapeshiftBarFrame' }) do
    newWidget('Frame', name, MainMenuBar)
end
BonusActionBarFrame:Hide()
-- Each stock button in its own bar frame, with its ID (ActionBarFrame.xml, MultiActionBars.xml).
for _, prefix in ipairs({ 'Action', 'BonusAction', 'MultiBarBottomLeft', 'MultiBarBottomRight', 'MultiBarLeft', 'MultiBarRight' }) do
    for i = 1, 12 do
        local b = newWidget('CheckButton', prefix .. 'Button' .. i, _G[prefix] or _G[prefix .. 'BarFrame'] or MainMenuBarArtFrame)
        b:SetID(i)
        b.isBonus = prefix == 'BonusAction' or nil
        b:RegisterEvent('ACTIONBAR_SLOT_CHANGED')
    end
end
for i = 0, 3 do
    for _, name in ipairs({ 'MainMenuBarTexture', 'MainMenuXPBarTexture', 'ReputationWatchBarTexture',
        'ReputationXPBarTexture', 'MainMenuMaxLevelBar' }) do newWidget('Texture', name .. i, MainMenuBar) end
end
for _, name in ipairs({ 'MainMenuBarLeftEndCap', 'MainMenuBarRightEndCap', 'MainMenuBarPageNumber' }) do
    newWidget('Texture', name, MainMenuBarArtFrame)
end
for _, name in ipairs({ 'CharacterMicroButton', 'SpellbookMicroButton', 'TalentMicroButton',
    'QuestLogMicroButton', 'SocialsMicroButton', 'WorldMapMicroButton', 'MainMenuMicroButton',
    'HelpMicroButton', 'MainMenuBarBackpackButton', 'CharacterBag0Slot', 'CharacterBag1Slot',
    'CharacterBag2Slot', 'CharacterBag3Slot', 'KeyRingButton', 'MainMenuBarPerformanceBarFrame',
    'ActionBarUpButton', 'ActionBarDownButton' }) do newWidget('Button', name, MainMenuBarArtFrame) end

-- What a free button calls (### C_Spell, ### C_Item, ### RunMacroText, ### C_EquipmentSet).
casts, ranMacros, usedItems, equippedSets, spellUsable, spellRange, spellRanged = {}, {}, {}, {}, {}, {}, {}
spellCooldowns, itemCooldowns, ranks = {}, {}, {}
function GetSpellInfo(id) if spellDB[id] then return spellDB[id], ranks[id] or '' end end
local READY = { 0, 0 }
function GetSpellCooldown(slot, book) local c = spellCooldowns[spells[slot]] or READY; return c[1], c[2], 1 end
function CastSpellByName(name) casts[#casts + 1] = name end
function RunMacroText(text) ranMacros[#ranMacros + 1] = text end
function GetMacroSpell(index) local m = macros[index]; if m and m.spell then return spellDB[m.spell], '', m.spell end end
function IsUsableSpell(id) if spellUsable[id] == false then return nil, nil end; return 1 end
function IsUsableItem(id) return C_Item.GetItemCount(id) > 0 and 1 or nil end
function UnitExists(unit) return unit == 'target' and hasTarget and 1 or nil end
rangeAsked = 0
C_Spell = {
    GetSpellTexture = function(id) return 'spellTex:' .. id end,
    GetSpellCooldown = function(id) local c = spellCooldowns[id] or { 0, 0 }
        return { startTime = c[1], duration = c[2], isEnabled = true } end,
    GetSpellCastCount = function(id) return reagentSpells[id] or 0 end,
    SpellHasRange = function(id) return spellRanged[id] == true end,
    IsSpellInRange = function(id, unit) rangeAsked = rangeAsked + 1; return spellRange[id] end,
}
-- Loss of control (### C_LossOfControl, ### C_Spell.GetSpellLossOfControlCooldown): a test sets
-- lossEffects (a count) and lossBlocks[spellID] = { start, duration }; unknown spells give nil.
lossEffects, lossBlocks = 0, {}
C_LossOfControl = { GetActiveLossOfControlDataCount = function() return lossEffects end }
C_Spell.GetSpellLossOfControlCooldown = function(id)
    if not spellDB[id] then return end
    local c = lossBlocks[id] or { 0, 0 }; return c[1], c[2]
end
C_Item.GetItemIconByID = function(id) return 'itemTex:' .. id end
C_Item.UseItemByName = function(id) usedItems[#usedItems + 1] = id end
C_Item.ItemHasRange = function() return false end
C_Item.IsEquippedItem = function(id) return equipment[id] ~= nil end
C_Spell.IsSelfBuff = function(id) return selfBuffs[id] == true end
C_ActionBar.FindSpellActionButtons = function(id)
    local out
    for slot = 1, 120 do
        local a = bars[slot]
        if a and a.kind == 'spell' and a.id == id then out = out or {}; out[#out + 1] = slot end
    end
    return out
end
C_Container = { GetItemCooldown = function(id) local c = itemCooldowns[id] or { 0, 0 }; return c[1], c[2], 1 end }
C_EquipmentSet.GetEquipmentSetInfo = function(id) return sets[id], 'setTex:' .. id end
C_EquipmentSet.UseEquipmentSet = function(id) equippedSets[#equippedSets + 1] = sets[id]; return true end

-- A button by bar and index, as the addon names it.
function button(bar, i) return _G['ActionBars_' .. bar .. '_' .. i] end
function hotkeyRed(b) local c = b.hotkey.color; return c ~= nil and c[1] == 1 and c[2] == 0.1 end
function timerCount() local n = 0 for _, t in ipairs(timers) do if not t.cancelled then n = n + 1 end end return n end
'''

GLOBALS = ("ActionBarsDB", "ActionBars",
           "SLASH_ACTIONBARS1")


def load(saved="", setup="", world=True):
    """The addon loaded over `saved` (Lua that sets ActionBarsDB); with
    `world`, the login events have fired, so the Settings page exists."""
    lua = wowkit.runtime()
    lua.execute(MOCK)
    lua.execute(BARS)
    lua.execute(setup)
    wowkit.load_addon(lua, ROOT, "ActionBars", saved=saved or None)
    if world:
        lua.execute('fire("VARIABLES_LOADED") fire("PLAYER_ENTERING_WORLD") markRest()')
    return lua


def profiles(lua):
    """The saved profile names, in the addon's order."""
    return list(lua.eval("ActionBars.GetProfileNames()").values())
