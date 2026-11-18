"""The GearRack 2.0 regressions on the shared game model (wowkit).

The addon is loaded from its TOC with `## LoadSavedVariablesFirst`. Its game
API is modelled as ClassicAPI's docs/API.md describes it:

* Items are copies with GUIDs (`item(guid, id, name, ...)`), worn (`wear`) or
  in bags (`carry`). `GetInventoryItemsForSlot` keys them by the packed
  location code (### C_EquipmentSet.GetItemLocations) and fits them to the
  slot by inventory type (its table); `C_Item.*` takes a GUID string or a
  location table (### Item, "itemLocation argument shapes");
  `C_Item.EquipItemByName(guid, slot)` swaps at once unless the test refuses
  it, and fires PLAYER_EQUIPMENT_CHANGED for each slot that changed.
* Sets (`C_EquipmentSet`): a slot holds a GUID, "ignored" or "empty";
  Create and Save read the worn gear and the global ignore state, a name of
  32 bytes or a line break raises "Invalid string for setName";
  UseEquipmentSet moves what it can (in combat only 16-18) and reports
  EQUIPMENT_SWAP_FINISHED at the next frame; every change fires
  EQUIPMENT_SETS_CHANGED.
* The player (combat, death, class, power, mount, instance, rest, forms,
  auras, target) is a table a test sets, read by the stock calls.
* The character window: CharacterFrame, PaperDollFrame, the 19 Character*Slot
  buttons with their ids, PaperDollItemSlotButton_OnEnter (it takes the
  tooltip, PaperDollFrame.lua:731) and a real hooksecurefunc.
* Popups as StaticPopup.lua runs them (`data` is the fourth argument).

The mocks do not prove the server's swaps, the native cooldown's drawing,
the client's frame placement or when it sends events.
"""
from pathlib import Path
import os
import wowkit

ROOT = Path(os.environ["VANILLAFORGE_ADDON_ROOT"])

MOCK = r'''
CLASSIC_API_VERSION = 12101
ITEM_INVENTORY_LOCATION_PLAYER, ITEM_INVENTORY_LOCATION_BAGS, ITEM_INVENTORY_LOCATION_BANK = 1048576, 2097152, 4194304
YES, NO, UIERRORS_HOLD_TIME = "Yes", "No", 5
calls, used, equips, usedSets, errors, sounds, inserted = {}, {}, {}, {}, {}, {}, {}
function chatText() return table.concat(chat, "\n") end
function clearChat() for i = #chat, 1, -1 do chat[i] = nil end end

-- Items: copies by GUID; worn by slot, bags by bag and slot.
items, worn, bags, locked, refuse = {}, {}, { [0] = {}, {}, {}, {}, {} }, {}, {}
cooldowns = {} -- guid -> { start, duration }
bagSize = { [0] = 16, 16, 16, 16, 16 }
function item(guid, id, name, equipLoc, quality, extra)
    local it = { guid = guid, id = id, name = name, equipLoc = equipLoc, quality = quality or 2,
        icon = "icon:" .. name }
    for k, v in pairs(extra or {}) do it[k] = v end
    it.link = "|cff1eff00|Hitem:" .. id .. ":0:0:0|h[" .. name .. "]|h|r"
    items[guid] = it
    return it
end
function wear(slot, guid) worn[slot] = guid end
function carry(bag, slot, guid) bags[bag][slot] = guid end
local function where(guid)
    for s = 0, 19 do if worn[s] == guid then return "worn", s end end
    for b = 0, 4 do for s = 1, bagSize[b] do if bags[b][s] == guid then return b, s end end end
end
local function at(loc)
    if type(loc) == "string" then return where(loc) and loc end
    if loc.equipmentSlotIndex then return worn[loc.equipmentSlotIndex] end
    return bags[loc.bagID] and bags[loc.bagID][loc.slotIndex]
end
local function byLink(link) local id = tonumber(string.match(link, "item:(%d+)"))
    for _, it in pairs(items) do if it.id == id then return it end end
end
local FITS = {
    [1] = { INVTYPE_HEAD = 1 }, [2] = { INVTYPE_NECK = 1 }, [3] = { INVTYPE_SHOULDER = 1 },
    [4] = { INVTYPE_BODY = 1 }, [5] = { INVTYPE_CHEST = 1, INVTYPE_ROBE = 1 }, [6] = { INVTYPE_WAIST = 1 },
    [7] = { INVTYPE_LEGS = 1 }, [8] = { INVTYPE_FEET = 1 }, [9] = { INVTYPE_WRIST = 1 }, [10] = { INVTYPE_HAND = 1 },
    [11] = { INVTYPE_FINGER = 1 }, [12] = { INVTYPE_FINGER = 1 }, [13] = { INVTYPE_TRINKET = 1 },
    [14] = { INVTYPE_TRINKET = 1 }, [15] = { INVTYPE_CLOAK = 1 },
    [16] = { INVTYPE_WEAPON = 1, INVTYPE_2HWEAPON = 1, INVTYPE_WEAPONMAINHAND = 1 },
    [17] = { INVTYPE_WEAPON = 1, INVTYPE_SHIELD = 1, INVTYPE_WEAPONOFFHAND = 1, INVTYPE_HOLDABLE = 1 },
    [18] = { INVTYPE_RANGED = 1, INVTYPE_THROWN = 1, INVTYPE_RANGEDRIGHT = 1 }, [19] = { INVTYPE_TABARD = 1 },
}
function GetInventoryItemsForSlot(slot, t)
    calls.forSlot = (calls.forSlot or 0) + 1
    for s = 1, 19 do
        local it = worn[s] and items[worn[s]]
        if it and FITS[slot][it.equipLoc] then t[ITEM_INVENTORY_LOCATION_PLAYER + s] = it.link end
    end
    for b = 0, 4 do for s = 1, bagSize[b] do
        local it = bags[b][s] and items[bags[b][s]]
        if it and FITS[slot][it.equipLoc] then
            t[ITEM_INVENTORY_LOCATION_PLAYER + ITEM_INVENTORY_LOCATION_BAGS + b * 256 + s] = it.link
        end
    end end
    return t
end
local function changed(slot) fire("PLAYER_EQUIPMENT_CHANGED", slot, worn[slot] and 1 or nil) end
-- One server-side move: the item into the slot, what was there to where it came from.
function move(guid, slot)
    local b, s = where(guid)
    if not b or refuse[guid] then return end
    local old = worn[slot]
    if b == "worn" then worn[s] = old else bags[b][s] = old end
    worn[slot] = guid
    changed(slot)
    if b == "worn" then changed(s) end
end
C_Item = {
    GetItemGUID = function(loc) return at(loc) end,
    IsLocked = function(loc) local g = at(loc); return g and locked[g] or false end,
    IsItemGUIDInInventory = function(guid) return where(guid) ~= nil end,
    GetItemIcon = function(loc) local g = at(loc); return g and items[g].icon end,
    GetItemQuality = function(loc) local g = at(loc); return g and items[g].quality end,
    GetItemLink = function(loc) local g = at(loc); return g and items[g].link end,
    GetItemInfoInstant = function(link) local it = byLink(link); return it.id, "", "", it.equipLoc end,
    EquipItemByName = function(guid, slot)
        equips[#equips + 1] = tostring(guid) .. ">" .. tostring(slot)
        if not slot then -- the cursor path, by item ID: ammo goes to slot 0
            for b = 0, 4 do for s = 1, bagSize[b] do
                local it = bags[b][s] and items[bags[b][s]]
                if it and it.id == guid and it.equipLoc == "INVTYPE_AMMO" then
                    bags[b][s], worn[0] = worn[0], it.guid
                    return
                end
            end end
            return
        end
        if locked[guid] then return end
        move(guid, slot)
    end,
    GetItemCount = function(id)
        local n = 0
        for _, it in pairs(items) do if it.id == id and where(it.guid) then n = n + 1 end end
        return n
    end,
    GetItemSpell = function(id) for _, it in pairs(items) do if it.id == id then return it.spell end end end,
    GetItemIconByID = function(id) for _, it in pairs(items) do if it.id == id then return it.icon end end end,
    GetItemNameByID = function(id) for _, it in pairs(items) do if it.id == id then return it.name end end end,
}
-- A trinket's cooldown by item ID (### GetItemCooldown), from any copy that has one;
-- `use` marks an item with a use (enable 1), as the client's third return.
function GetItemCooldown(id)
    for guid, c in pairs(cooldowns) do if items[guid].id == id then return c[1], c[2], 1 end end
    return 0, 0, 0
end
casting = nil -- the end of a cast, in GetTime() seconds
C_Spell = { CastingInfo = function() if casting then return "Cast", "Cast", 1, 0, casting * 1000 end end,
    ChannelInfo = function() end,
    GetSpellTexture = function(id) return id == 11340 and "Interface\\Icons\\Ability_Poisons" or nil end }
-- Temporary enchants (### C_Item.GetItemTempEnchantInfo): guid -> { until = time, charges, enchant }.
poisons = {}
function C_Item.GetItemTempEnchantInfo(loc)
    local guid = C_Item.GetItemGUID(loc)
    local p = guid and poisons[guid]
    if not p then return false end
    return true, math.max(0, (p["until"] - now) * 1000), p.charges, p.enchant
end
function C_Item.GetEnchantInfo(id) return { enchantID = id, name = "Instant Poison VI", spellID = id == 625 and 11340 or nil } end
targeting = false
function SpellIsTargeting() return targeting end
Minimap = newWidget("Minimap", "Minimap", UIParent)
Minimap:SetPoint("TOPRIGHT", UIParent, "TOPRIGHT", -20, -20)
Minimap.left, Minimap.top = 800, 700
Minimap:SetSize(140, 140)
cursorX, cursorY = 0, 0
function GetCursorPosition() return cursorX, cursorY end
function Widget:SetDesaturated(on) self.desaturated = on and true or nil end
function Widget:SetHyperlink(link) self.shows = link end
function Widget:GetEffectiveScale() return 1 end
C_PlayerInfo = { CanUseItem = function(link) return not byLink(link).unusable end }
function CanDualWield() return dualWield end
function GetInventoryItemTexture(_, slot) return worn[slot] and items[worn[slot]].icon end
function GetInventoryItemQuality(_, slot) return worn[slot] and items[worn[slot]].quality end
function GetInventoryItemLink(_, slot) return worn[slot] and items[worn[slot]].link end
-- enable is 1 for an item with a use (`use` in its extras), cooling down or not.
function GetInventoryItemCooldown(_, slot)
    local c = worn[slot] and cooldowns[worn[slot]]
    if c then return c[1], c[2], 1 end
    return 0, 0, worn[slot] and items[worn[slot]].use and 1 or 0
end
function GetContainerItemCooldown(bag, slot)
    local c = bags[bag][slot] and cooldowns[bags[bag][slot]]
    if c then return c[1], c[2], 1 end
    return 0, 0, 0
end
function GetInventorySlotInfo(name) return 0, "slotTex:" .. name end
ITEM_QUALITY_COLORS = {}
for q = 0, 5 do ITEM_QUALITY_COLORS[q] = { r = q / 10, g = 0.5, b = 0.5 } end
function UseInventoryItem(slot) used[#used + 1] = slot end
function CursorHasItem() return cursor ~= nil end
function PickupInventoryItem(slot) cursor = worn[slot]; worn[slot] = nil; changed(slot) end
local function drop(bag)
    for s = 1, bagSize[bag] do if not bags[bag][s] then bags[bag][s] = cursor; cursor = nil; return end end
end
function PutItemInBackpack() drop(0) end
function ContainerIDToInventoryID(bag) return 19 + bag end
function PutItemInBag(inv) drop(inv - 19) end
bagFamily = {}
C_Container = { GetContainerNumFreeSlots = function(bag)
    local n = 0
    for s = 1, bagSize[bag] do if not bags[bag][s] then n = n + 1 end end
    return n, bagFamily[bag] or 0
end }

-- Sets, as ### EquipmentSet describes them.
sets, setOrder, ignoreForSave, swapping = {}, {}, {}, false
local nextID = 1
local function setsChanged() fire("EQUIPMENT_SETS_CHANGED") end
function makeSet(name, icon, slots)
    local id = nextID; nextID = nextID + 1
    sets[id] = { name = name, icon = icon, slots = slots }
    setOrder[#setOrder + 1] = id
    return id
end
local function snapshot(id, icon)
    local slots = {}
    for s = 1, 19 do slots[s] = ignoreForSave[s] and "ignored" or worn[s] or "empty" end
    sets[id].slots = slots
    if icon then sets[id].icon = icon end
end
local function inPlace(set, s)
    local v = set.slots[s]
    if v == "ignored" then return true end
    if v == "empty" then return worn[s] == nil end
    return worn[s] == v
end
C_EquipmentSet = {
    GetNumEquipmentSets = function() return #setOrder end,
    GetEquipmentSetIDs = function() local t = {}; for i, id in ipairs(setOrder) do t[i] = id end; return t end,
    GetEquipmentSetID = function(name) for _, id in ipairs(setOrder) do if sets[id].name == name then return id end end end,
    GetEquipmentSetInfo = function(id)
        local set = sets[id]
        if not set then return end
        local equipped, missing = true, 0
        for s = 1, 19 do
            if not inPlace(set, s) then equipped = false end
            local v = set.slots[s]
            if v ~= "ignored" and v ~= "empty" and not where(v) then missing = missing + 1 end
        end
        return set.name, set.icon, id, equipped, 0, 0, 0, missing, 0
    end,
    GetIgnoredSlots = function(id)
        local t = {}
        for s = 1, 19 do if sets[id].slots[s] == "ignored" then t[#t + 1] = s end end
        return t
    end,
    GetItemLocations = function(id)
        local t = {}
        for s = 1, 19 do
            local v = sets[id].slots[s]
            if v == "ignored" then t[s] = 1 elseif v == "empty" then t[s] = 0 else
                local b, bs = where(v)
                if not b then t[s] = -1
                elseif b == "worn" then t[s] = ITEM_INVENTORY_LOCATION_PLAYER + bs
                else t[s] = ITEM_INVENTORY_LOCATION_PLAYER + ITEM_INVENTORY_LOCATION_BAGS + b * 256 + bs end
            end
        end
        return t
    end,
    CreateEquipmentSet = function(name, icon)
        if #name >= 32 or string.find(name, "\n") then error("Invalid string for setName") end
        if name == "" or C_EquipmentSet.GetEquipmentSetID(name) then return end
        local id = makeSet(name, icon or "INV_Misc_QuestionMark", {})
        snapshot(id)
        setsChanged()
        return id
    end,
    SaveEquipmentSet = function(id, icon) snapshot(id, icon); setsChanged() end,
    DeleteEquipmentSet = function(id)
        sets[id] = nil
        for i, v in ipairs(setOrder) do if v == id then table.remove(setOrder, i); break end end
        setsChanged()
    end,
    IgnoreSlotForSave = function(s) ignoreForSave[s] = true; setsChanged() end,
    UnignoreSlotForSave = function(s) ignoreForSave[s] = nil; setsChanged() end,
    ClearIgnoredSlotsForSave = function() ignoreForSave = {}; setsChanged() end,
    CanUseEquipmentSets = function() return not swapping end,
    UseEquipmentSet = function(id)
        usedSets[#usedSets + 1] = sets[id] and sets[id].name or tostring(id)
        if swapping or not sets[id] then return false end
        swapping = true
        fire("EQUIPMENT_SWAP_PENDING", id)
        for s = 1, 19 do
            local v = sets[id].slots[s]
            if v ~= "ignored" and v ~= "empty" and worn[s] ~= v and (not combat or s >= 16 and s <= 18) then move(v, s) end
        end
        C_Timer.After(0, function() swapping = false; fire("EQUIPMENT_SWAP_FINISHED", 1, id) end)
        return true
    end,
    PickupEquipmentSet = function(id) if sets[id] then cursorSet = sets[id].name end end,
}

-- The player and the target.
player = { class = "ROGUE", power = 3, mana = 0, maxMana = 0, instance = "none", forms = {}, form = 0, auras = {} }
target = {}
function UnitAffectingCombat() return combat and 1 or nil end
function UnitIsDeadOrGhost() return dead and 1 or nil end
function UnitClass() return player.class, player.class end
function UnitPowerType() return player.power end
function UnitMana() return player.mana end
function UnitManaMax() return player.maxMana end
function IsMounted() return player.mounted == true end
function GetInstanceInfo() return "Somewhere", player.instance end
function IsResting() return player.resting and 1 or nil end
function GetNumShapeshiftForms() return #player.forms end
function GetShapeshiftFormInfo(i) return "formIcon", player.forms[i], player.form == i and 1 or nil, 1 end
function GetShapeshiftForm() return player.form end
auraReads = 0
C_UnitAuras = { GetAuraDataBySpellName = function(unit, name)
    auraReads = auraReads + 1
    if player.auras[name] then return { name = name } end
end }
function UnitCanAttack() return target.enemy and 1 or nil end
function UnitIsDead() return target.dead and 1 or nil end
function UnitCreatureType() return target.kind end

-- Keys and modifiers; the left and right reads (### MODIFIER_STATE_CHANGED).
mods, keys = {}, {}
function IsLeftShiftKeyDown() return mods.lshift end
function IsRightShiftKeyDown() return mods.rshift end
function IsLeftControlKeyDown() return mods.lctrl end
function IsRightControlKeyDown() return mods.rctrl end
function IsLeftAltKeyDown() return mods.lalt end
function IsRightAltKeyDown() return mods.ralt end
function IsShiftKeyDown() return mods.lshift or mods.rshift end
function IsAltKeyDown() return mods.lalt or mods.ralt end
function press(...)
    mods = {}
    for i = 1, select("#", ...) do mods[select(i, ...)] = 1 end
    fire("MODIFIER_STATE_CHANGED")
end
function GetBindingKey(action) return keys[action] end
function GetBindingText(key) return "k" .. key end
function GetBindingName(action) return "name:" .. action end
local bindingIndex = { GEARRACK_USE_TOP_TRINKET_ITEM = 41, GEARRACK_USE_BOTTOM_TRINKET_ITEM = 42 }
C_KeyBindings = { GetBindingIndex = function(action) return bindingIndex[action] end }
function CreateKeybindingEntryInitializer(index, search)
    return Settings.CreateElementInitializer("KeybindingFrame", { name = "Key " .. tostring(index), bindingIndex = index })
end

-- The look: the formatter, the Cooldown frame's calls, a pointer over a frame.
Enum = { NumericRuleFormatRounding = { Up = 1 } }
C_StringUtil = { CreateNumericRuleFormatter = function() return { SetBreakpoints = function() end } end }
function Widget:SetCooldown(start, duration) self.cd = start .. "+" .. duration end
function Widget:Clear() self.cd = nil end
function Widget:SetNormalTexture(path) self.normalPath = path end
function Widget:SetBackdropBorderColor(r, g, b) self.border = { r, g, b } end
function Widget:IsMouseOver() return self.mouse == true end
function Widget:GetFrameLevel() return self.level or 1 end
function Widget:SetFrameLevel(level) self.level = level end
function Widget:SetMinMaxValues(lo, hi) self.min, self.max = lo, hi end
function Widget:SetValue(v) self.value = v; run(self, "OnValueChanged") end
local kitCreate = CreateFrame
local PARTS = { Icon = "Texture", Flash = "Texture", HotKey = "FontString", Count = "FontString",
    Name = "FontString", Border = "Texture", NormalTexture = "Texture", Cooldown = "Model" }
function CreateFrame(kind, name, parent, template)
    local f = kitCreate(kind, name, parent)
    f.template = template
    if template == "ActionButtonTemplate" then
        for part, partKind in pairs(PARTS) do newWidget(partKind, name .. part, f) end
    end
    return f
end
function GetMacroIcons(t) t[#t + 1] = "SPELL_A"; t[#t + 1] = "SPELL_B" end
function GetMacroItemIcons(t) for i = 1, 70 do t[#t + 1] = "INV_" .. i end end
function PlaySound(name) sounds[#sounds + 1] = name end
UIErrorsFrame = { AddMessage = function(_, text) errors[#errors + 1] = text end }
ChatFrameEditBox = newWidget("EditBox", "ChatFrameEditBox", UIParent)
ChatFrameEditBox:Hide()
function ChatFrameEditBox:Insert(text) inserted[#inserted + 1] = text end

-- The tooltip: SetInventoryItem returns hasItem, hasCooldown (PaperDollFrame.lua:733).
GameTooltip = newWidget("GameTooltip", "GameTooltip", UIParent)
tipFills = 0
function GameTooltip:SetOwner(owner, anchor) self.owner, self.anchor = owner, anchor; self.lines = {} end
function GameTooltip:IsOwned(f) return self.owner == f and 1 or nil end
function GameTooltip:Hide() self.owner = nil end
function GameTooltip:SetText(text) self.lines = { text } end
function GameTooltip:AddLine(text) self.lines[#self.lines + 1] = text end
function GameTooltip:SetInventoryItem(_, slot)
    tipFills = tipFills + 1
    self.shows = "slot " .. slot
    local _, duration = GetInventoryItemCooldown("player", slot)
    return worn[slot] ~= nil, duration > 0
end
function GameTooltip:SetItemByGUID(guid) self.shows = "guid " .. guid end
function GameTooltip:SetEquipmentSet(name) self.shows = "set " .. name end

-- The character window (PaperDollFrame.xml; ids by slot number).
CharacterFrame = newWidget("Frame", "CharacterFrame", UIParent)
CharacterFrame:Hide()
PaperDollFrame = newWidget("Frame", "PaperDollFrame", CharacterFrame)
CharacterModelFrame = newWidget("PlayerModel", "CharacterModelFrame", PaperDollFrame)
SLOT_FRAMES = { "Head", "Neck", "Shoulder", "Shirt", "Chest", "Waist", "Legs", "Feet", "Wrist", "Hands",
    "Finger0", "Finger1", "Trinket0", "Trinket1", "Back", "MainHand", "SecondaryHand", "Ranged", "Tabard" }
for id, name in ipairs(SLOT_FRAMES) do
    local b = newWidget("Button", "Character" .. name .. "Slot", PaperDollFrame)
    b:SetID(id)
    b:SetScript("OnEnter", function() PaperDollItemSlotButton_OnEnter() end)
    b:SetScript("OnLeave", function() GameTooltip:Hide() end)
    b:SetScript("OnClick", function() stockClicks[#stockClicks + 1] = this:GetID() .. ":" .. tostring(arg1) end)
end
stockClicks = {}
function PaperDollItemSlotButton_OnEnter() GameTooltip:SetOwner(this, "ANCHOR_RIGHT") end
function ToggleCharacter() CharacterFrame:Show() end
function hooksecurefunc(name, f)
    local old = _G[name]
    _G[name] = function(...) local a, b, c = old(...); f(...); return a, b, c end
end

-- Popups, as StaticPopup.lua runs them.
StaticPopupDialogs = {}
popup = newWidget("Frame", "StaticPopup1", UIParent)
popup:Hide()
function StaticPopup_Show(which, a1, a2, data)
    local info = StaticPopupDialogs[which]
    popup.which, popup.data, popup.text = which, data, string.format(info.text, a1 or "", a2 or "")
    popup:Show()
    return popup
end
function accept() StaticPopupDialogs[popup.which].OnAccept(popup.data); popup:Hide() end

-- The pointer on and off a frame; a leave is checked a tenth of a second later.
function hover(f) f.mouse = true; run(f, "OnEnter") end
function leave(f) f.mouse = false; run(f, "OnLeave"); step(0.11) end
function login() fire("VARIABLES_LOADED"); fire("PLAYER_ENTERING_WORLD"); step(0) end
function timerCount()
    local n = 0
    for _, t in ipairs(timers) do if not t.cancelled then n = n + 1 end end
    return n
end
function tickers()
    local n = 0
    for _, t in ipairs(timers) do if not t.cancelled and t.left == nil then n = n + 1 end end
    return n
end
-- What frames listen to and every OnUpdate, sorted.
function allEvents()
    local out = {}
    for _, w in ipairs(widgets) do
        for e in pairs(w.events) do out[#out + 1] = e end
        if w.scripts.OnUpdate then out[#out + 1] = "OnUpdate:" .. tostring(w.name) end
    end
    table.sort(out)
    return table.concat(out, ",")
end
function menu() return GearRackMenu end
function menuItems()
    local out = {}
    for _, w in ipairs(widgets) do
        if w.parent == GearRackMenu and w.entry and w.shown then
            local e = w.entry
            out[#out + 1] = e.set and ("set:" .. e.name) or e.off and "off" or e.guid
        end
    end
    return table.concat(out, ",")
end
function menuButton(n)
    local i = 0
    for _, w in ipairs(widgets) do
        if w.parent == GearRackMenu and w.entry and w.shown then
            i = i + 1
            if i == n then return w end
        end
    end
end
function click(f, button) run(f, "OnClick", button or "LeftButton") end
-- Click the open menu's button for `guid` ("off" for the empty one).
function pick(guid, button)
    local i = 1
    while menuButton(i) do
        local e = menuButton(i).entry
        if e.guid == guid or (guid == "off" and e.off) then click(menuButton(i), button); return end
        i = i + 1
    end
    error("no menu button for " .. tostring(guid))
end
'''

# A rogue with daggers, rings and trinkets in bags; a mage would set player.
GEAR = r'''
item("0xA", 1001, "The Ripper", "INVTYPE_WEAPON", 3); wear(16, "0xA")
item("0xB", 1002, "Distracting Dagger", "INVTYPE_WEAPON", 3); wear(17, "0xB")
item("0xC", 1003, "Skyrazors", "INVTYPE_THROWN", 2); wear(18, "0xC")
item("0xD", 1004, "Satyr Claw", "INVTYPE_WEAPON", 4); carry(0, 1, "0xD")
item("0xE", 1005, "Anasterian's Legacy", "INVTYPE_WEAPON", 4); carry(0, 2, "0xE")
item("0xF1", 1006, "Twin Blade", "INVTYPE_WEAPON", 2); carry(1, 1, "0xF1")
item("0xF2", 1006, "Twin Blade", "INVTYPE_WEAPON", 2); carry(1, 2, "0xF2")
item("0x10", 1007, "Big Axe", "INVTYPE_2HWEAPON", 2, { unusable = true }); carry(1, 3, "0x10")
item("0x11", 1008, "Insignia", "INVTYPE_TRINKET", 3); wear(13, "0x11")
item("0x12", 1009, "Arena Grand Master", "INVTYPE_TRINKET", 4); wear(14, "0x12")
item("0x13", 1010, "Hand of Justice", "INVTYPE_TRINKET", 4); carry(0, 3, "0x13")
item("0x14", 1011, "Band of Accuria", "INVTYPE_FINGER", 4); wear(11, "0x14")
item("0x15", 1012, "Seal of Jin", "INVTYPE_FINGER", 3); carry(0, 4, "0x15")
item("0x16", 1013, "Headband", "INVTYPE_HEAD", 3); wear(1, "0x16")
item("0x17", 1014, "Implants", "INVTYPE_HEAD", 3); carry(0, 5, "0x17")
item("0x18", 1015, "Cloak", "INVTYPE_CLOAK", 2); wear(15, "0x18")
dualWield = true
'''

GLOBALS = ("GearRackDB", "GearRack", "SLASH_GEARRACK1", "BINDING_HEADER_GEARRACK",
           "BINDING_NAME_GEARRACK_USE_TOP_TRINKET_ITEM", "BINDING_NAME_GEARRACK_USE_BOTTOM_TRINKET_ITEM",
           "GearRackGearBar", "GearRackTrinketBar", "GearRackMenu", "GearRackSetsWindow", "GearRackSetName",
           "GearRackTrinkets", "GearRackMinimapGear", "GearRackMinimapTrinkets",
           "GearRackSets", "GearRackTrinket13", "GearRackTrinket14")


def load(saved="", setup="", gear=True, world=True, layout=None):
    """GearRack loaded over `saved` (Lua that sets GearRackDB). `layout`
    fills the kit's layoutCache (a first login with places the client saved);
    with `world`, the login events have fired, so the pages exist."""
    lua = wowkit.runtime()
    lua.execute(MOCK)
    if gear:
        lua.execute(GEAR)
    lua.execute(setup)
    for name, (x, y) in (layout or {}).items():
        lua.execute(f'layoutCache["{name}"] = {{ {x}, {y} }}')
    wowkit.load_addon(lua, ROOT, "GearRack", saved=saved or None)
    if world:
        lua.execute("login()")
    return lua


def values(lua, expr):
    """A Lua array as a Python list."""
    t = lua.eval(expr)
    return [t[i] for i in range(1, len(t) + 1)] if t else []
