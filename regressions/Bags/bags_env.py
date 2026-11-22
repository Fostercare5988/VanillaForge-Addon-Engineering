"""Bags 1.0 (written new, 2026-11-22) on the shared game model (wowkit).

The game is modelled as the docs have it (ClassicAPI docs/API.md, the client's
FrameXML in `.private/framexml`):

* Bags and the bank: `bags[bag] = { size, link, slots = { [slot] = item } }`,
  an item `{ id, count, icon, quality, locked, filtered, name }`. Bank IDs (-1,
  5-10) answer only while `atBank` (### C_Container.GetContainerNumFreeSlots).
  `C_Container.GetContainerItemInfo` fills the buffer it is given
  (### ... [, buf]) and is counted; `SetItemSearch` fires INVENTORY_SEARCH_UPDATE
  only when the text changes (### C_Container.SetItemSearch).
* Items by ID: `items[id] = { name, quality, icon }`; `C_Item.GetItemInfo` gives
  the 1st, 2nd, 3rd and 10th returns, nothing for an ID not in the cache.
* Cooldowns `cds["bag:slot"] = { start, duration, enable }`, temporary enchants
  `enchants["bag:slot"] = { ms, charges, id }`, new items `newItems["bag:slot"]`.
* The templates the addon inherits make the children the client makes:
  ItemButtonTemplate's IconTexture and Count, SmallMoneyFrameTemplate's coin
  buttons. An EditBox runs OnTextChanged when its text changes, as the client does.
  Cooldown frames record SetCooldown and Clear; animation groups record Play and Stop.
* Tooltips: SetHyperlink, SetBagItem and SetInventoryItem set the item, then
  OnTooltipSetItem runs; SetOwner and Hide clear (OnTooltipCleared).
* The stock functions the addon calls or replaces record their calls in `calls`.

Not modelled: drawing, layout, the server's answers to moves, and dropdown menus
beyond the generator the addon gives (`menuEntries(w)` runs it).
"""
from pathlib import Path
import os
import wowkit

ROOT = Path(os.environ["VANILLAFORGE_ADDON_ROOT"])

MOCK = r'''
CLASSIC_API_VERSION = 12301
STANDARD_TEXT_FONT = "Fonts\\FRIZQT__.TTF"
BANK_BAG_PURCHASE, EQUIP_CONTAINER, BANKSLOTPURCHASE = "Purchasable bag slot", "Bag slot", "Purchase"
luaErrors = {}
function geterrorhandler() return function(m) luaErrors[#luaErrors + 1] = m end end
calls = {}
function count(name) return calls[name] or 0 end
function tally(name) calls[name] = (calls[name] or 0) + 1 end
function forget() calls = {} end
function PlaySound() end
function ResetCursor() end
function GetScreenWidth() return 1024 end

-- Widgets: what the addon writes and the tests read back.
local made = CreateFrame
function CreateFrame(kind, name, parent, template)
    local w = made(kind, name, parent)
    w.template = template
    if template == "ItemButtonTemplate" then
        made("Texture", name .. "IconTexture", w)
        _G[name .. "Count"] = w:CreateFontString(name .. "Count", "BORDER", "NumberFontNormal")
    elseif template == "SmallMoneyFrameTemplate" then
        for _, coin in ipairs({ "Gold", "Silver", "Copper" }) do made("Button", name .. coin .. "Button", w) end
    end
    return w
end
function Widget:SetDesaturated(on) self.desaturated = on end
function Widget:SetBackdropBorderColor(r, g, b) self.edgeColor = { r, g, b } end
function Widget:SetEnabled(on) self.enabled = on and true or false end
function Widget:LockHighlight() self.highlit = true end
function Widget:UnlockHighlight() self.highlit = nil end
function Widget:SetCooldown(start, duration) self.cdStart, self.cdDuration = start, duration; tally("SetCooldown") end
function Widget:Clear() self.cdStart, self.cdDuration = nil, nil end
function Widget:GetCountdownFontString() self.numbers = self.numbers or newWidget("FontString", nil, self); return self.numbers end
function Widget:EnableMouse(on) self.mouse = on and true or false end
function Widget:IsMouseEnabled() return self.mouse end
function Widget:SetupMenu(generator) self.generator = generator end
function Widget:ClearFocus() self.focus = nil end
local stockText = Widget.SetText
function Widget:SetText(text)
    local old = self.text
    stockText(self, text)
    if self.kind == "EditBox" and old ~= text then run(self, "OnTextChanged") end
end
function Widget:CreateAnimationGroup()
    local g = newWidget("AnimationGroup", nil, self)
    g.Play = function(s) s.playing = true end
    g.Stop = function(s) s.playing = nil end
    g.IsPlaying = function(s) return s.playing end
    g.CreateAnimation = function() return newWidget("Animation") end
    return g
end
-- The menu the dropdown would show: { kind, text, picked } per entry.
function menuEntries(w)
    local out, root = {}, {}
    function root:CreateRadio(text, isSelected, select, data)
        out[#out + 1] = { kind = "radio", text = text, picked = isSelected(data) and true or false, pick = function() select(data) end }
    end
    function root:CreateButton(text, click) out[#out + 1] = { kind = "button", text = text, pick = click } end
    w.menu.generator(w.menu, root)
    return out
end

-- The character.
realm, me, money = "Y'Shaarj", "Claude", 10000
function GetRealmName() return realm end
function UnitName(u) if u == "player" then return me end end
function GetMoney() return money end

-- Bags and the bank.
atBank, search, rightToLeft = false, "", false
bags = { [0] = { size = 16, slots = {} } }
items = {}
cds, enchants, newItems = {}, {}, {}
local function bankID(bag) return bag == -1 or (bag >= 5 and bag <= 10) end
local function bagOf(bag) if bankID(bag) and not atBank then return nil end return bags[bag] end
local function key(bag, slot) return bag .. ":" .. slot end
function itemAt(bag, slot) local b = bagOf(bag); return b and b.slots[slot] end
function linkOf(it) return "|cff1eff00|Hitem:" .. it.id .. ":" .. (it.enchant or 0) .. ":" .. (it.suffix or 0) .. ":0:0:0:0:0|h[" .. (it.name or "Item") .. "]|h|r" end
function GetKeyRingSize() return bags[-2] and bags[-2].size or 0 end
C_Container = {
    GetContainerNumSlots = function(bag) local b = bagOf(bag); return b and b.size or 0 end,
    GetContainerItemInfo = function(bag, slot, buf)
        tally("GetContainerItemInfo")
        local it = itemAt(bag, slot)
        if not it then return nil end
        assert(type(buf) == "table", "one buffer for every slot")
        local known = items[it.id]
        buf.iconFileID = known and known.icon
        buf.quality = known and known.quality
        buf.stackCount, buf.isLocked, buf.isFiltered = it.count or 1, it.locked or false, it.filtered or false
        buf.itemID, buf.hyperlink, buf.isReadable = it.id, linkOf(it), false
        return buf
    end,
    SetItemSearch = function(text)
        assert(type(text) == "string")
        if string.lower(text) ~= string.lower(search) then search = text; fire("INVENTORY_SEARCH_UPDATE") end
        search = text
    end,
    SortBags = function() tally("SortBags") end,
    SortBankBags = function() tally("SortBankBags") end,
    GetSortBagsRightToLeft = function() return rightToLeft end,
    SetSortBagsRightToLeft = function(on) rightToLeft = on end,
}
function GetContainerItemCooldown(bag, slot)
    local c = cds[key(bag, slot)]
    if c then return c[1], c[2], c[3] end
    return 0, 0, 1
end
function ContainerIDToInventoryID(bag) if bag <= 4 then return 19 + bag end return 63 + bag end
function BankButtonIDToInvSlotID(slot) return 39 + slot end
local function bagAtSlot(inv) for bag, b in pairs(bags) do if bag > 0 and ContainerIDToInventoryID(bag) == inv then return b end end end
function GetInventoryItemLink(_, inv) local b = bagAtSlot(inv); return b and b.link and linkOf({ id = b.link, name = "Bag" }) end
function GetInventoryItemTexture(_, inv) local b = bagAtSlot(inv); return b and b.link and "Interface\\Icons\\INV_Misc_Bag_08" end
function IsInventoryItemLocked() return nil end
function PutItemInBag(inv) calls.PutItemInBag = inv end
function PickupBagFromSlot(inv) calls.PickupBagFromSlot = inv end
bankSlots, bankFull = 2, nil
function GetNumBankSlots() return bankSlots, bankFull end
function GetBankSlotCost(n) return 1000 * (n + 1) end
function StaticPopup_Show(which) calls.popup = which end
function CloseBankFrame() tally("CloseBankFrame"); if atBank then atBank = false; fire("BANKFRAME_CLOSED") end end
BankFrame = CreateFrame("Frame", "BankFrame")
BankFrame:RegisterEvent("BANKFRAME_OPENED"); BankFrame:RegisterEvent("BANKFRAME_CLOSED")
BankFrame:Hide()
BankFrame:SetScript("OnEvent", function() if event == "BANKFRAME_OPENED" then BankFrame:Show() end end)

-- Items, enchants, new items.
C_Item = {
    GetItemInfo = function(link)
        local id = tonumber(string.match(link, "item:(%d+)"))
        local it = items[id]
        if not it then tally("cacheMiss"); return end
        return it.name, "|cff0070dd|Hitem:" .. id .. ":0:0:0:0:0:0:0|h[" .. it.name .. "]|h|r", it.quality,
            nil, nil, nil, nil, nil, nil, it.icon
    end,
    GetItemTempEnchantInfo = function(loc)
        tally("GetItemTempEnchantInfo")
        local e = enchants[key(loc.bagID, loc.slotIndex)]
        if e then return true, e.ms, e.charges or 0, e.id end
        return false, 0, 0, 0
    end,
    GetEnchantInfo = function(id) if id == 7 then return { enchantID = 7, name = "Instant Poison", spellID = 8679 } end return { enchantID = id, name = "Odd" } end,
}
C_Spell = { GetSpellTexture = function(id) if id == 8679 then return "Interface\\Icons\\Ability_Poisons" end end }
C_NewItems = {
    IsNewItem = function(bag, slot) return newItems[key(bag, slot)] and true or false end,
    RemoveNewItem = function(bag, slot) newItems[key(bag, slot)] = nil; tally("RemoveNewItem") end,
    ClearAll = function() newItems = {}; tally("ClearAll") end,
}

-- The stock bag functions (ContainerFrame.lua) and slot handlers.
for _, name in ipairs({ "ToggleBag", "OpenBag", "CloseBag", "ToggleKeyRing" }) do
    _G[name] = function(id) calls[name] = id end
end
function ContainerFrameItemButton_OnClick(button, ignore) calls.click = { this, button, ignore } end
function ContainerFrameItemButton_OnEnter(b) calls.enter = b; GameTooltip:SetOwner(b); GameTooltip:SetBagItem(b:GetParent():GetID(), b:GetID()) end
function DressUpItemLink(link) calls.dressUp = link end
ChatFrameEditBox = newWidget("EditBox")
function ChatFrameEditBox:Insert(text) calls.inserted = text end
StackSplitFrame = newWidget("Frame")
shift, ctrl = nil, nil
function IsShiftKeyDown() return shift end
function IsControlKeyDown() return ctrl end

-- Money (MoneyFrame.lua): the type is set on `this`.
MoneyTypeInfo = { PLAYER = { canPickup = 1 }, STATIC = {} }
function MoneyFrame_SetType(kind) this.moneyType, this.info = kind, MoneyTypeInfo[kind] end
function MoneyFrame_Update(name, copper) _G[name].shownMoney = copper end
function SetTooltipMoney(tip, copper) tip.money = copper end

-- Tooltips.
local function tooltip(name)
    local t = CreateFrame("GameTooltip", name)
    t:Hide()
    function t:SetOwner(f) run(self, "OnTooltipCleared"); self.owner, self.lines, self.link = f, {}, nil end
    function t:AddLine(text) self.lines[#self.lines + 1] = text end
    function t:AddDoubleLine(a, b, r1, g1, b1, r2, g2, b2) self.lines[#self.lines + 1] = a .. "=" .. b; self.colors = self.colors or {}; self.colors[a] = { r2, g2, b2 } end
    function t:SetText(text) self.lines = { text } end
    function t:Hide() self.shown = false; run(self, "OnTooltipCleared") end
    local function item(self, link) self.link = link; self.shown = true; run(self, "OnTooltipSetItem") end
    function t:SetHyperlink(link) item(self, link) end
    function t:SetBagItem(bag, slot) local it = itemAt(bag, slot); if it then item(self, linkOf(it)) end end
    function t:SetInventoryItem(_, inv) self.inventory = inv; return 1 end
    function t:GetItem()
        if not self.link then return end
        return "Item", self.link, tonumber(string.match(self.link, "item:(%d+)"))
    end
    return t
end
GameTooltip, ItemRefTooltip = tooltip("GameTooltip"), tooltip("ItemRefTooltip")

-- Helpers for the tests.
function put(bag, slot, it) bags[bag].slots[slot] = it end
function window(kind) return kind == "bank" and BagsBank or BagsInventory end
function button(kind, bag, slot) return window(kind).holders[bag].buttons[slot] end
function shownButtons(kind)
    local n = 0
    for _, bag in ipairs(window(kind).bags) do
        local h = window(kind).holders[bag]
        for slot = 1, #h.buttons do if h.buttons[slot].shown and slot <= h.size then n = n + 1 end end
    end
    return n
end
function openBank() atBank = true; fire("BANKFRAME_OPENED") end
function closeBank() atBank = false; fire("BANKFRAME_CLOSED") end
function listening(w)
    local out = {}
    for e in pairs(w.events) do out[#out + 1] = e end
    table.sort(out)
    return table.concat(out, ",")
end
function onUpdates() local n = 0; for _, w in ipairs(widgets) do if w.scripts.OnUpdate then n = n + 1 end end; return n end
function liveTimers() local n = 0; for _, t in ipairs(timers) do if not t.cancelled then n = n + 1 end end; return n end
function click(b, mouse) run(b, "OnClick", mouse or "LeftButton") end
function enter(b) run(b, "OnEnter") end
'''

# Claude's bags in the shape the old record held them: a backpack and a 20-slot satchel.
WORLD = r'''
items[8928] = { name = "Instant Poison VI", quality = 1, icon = "Interface\\Icons\\Ability_Poisons" }
items[18142] = { name = "Severed Night Elf Head", quality = 1, icon = "Interface\\Icons\\INV_Misc_Head" }
items[10753] = { name = "Amulet of Grol", quality = 2, icon = "Interface\\Icons\\INV_Jewelry_Amulet_02" }
items[19019] = { name = "Thunderfury", quality = 5, icon = "Interface\\Icons\\INV_Sword_39" }
items[13209] = { name = "Seal of the Dawn", quality = 3, icon = "Interface\\Icons\\INV_Trinket" }
items[51043] = { name = "Void-Linked Satchel", quality = 3, icon = "Interface\\Icons\\INV_Misc_Bag_08" }
items[15138] = { name = "Onyxia Scale Cloak", quality = 4, icon = "Interface\\Icons\\INV_Misc_Cape_05" }
bags[1] = { size = 20, link = 51043, slots = {} }
put(0, 1, { id = 8928, count = 10, name = "Instant Poison VI" })
put(0, 16, { id = 10753, name = "Amulet of Grol" })
put(1, 16, { id = 18142, name = "Severed Night Elf Head" })
put(1, 2, { id = 19019, name = "Thunderfury" })
bags[-1] = { size = 24, slots = {} }
bags[5] = { size = 16, link = 51043, slots = {} }
put(-1, 24, { id = 15138, enchant = 2619, name = "Onyxia Scale Cloak" })
put(5, 3, { id = 13209, count = 2, name = "Seal of the Dawn" })
'''


def load(saved=None, setup="", world=True, layout=None):
    """The addon loaded over `saved` (Lua that sets BagsDB and BagsStore) on
    Claude's bags; with `world`, the login events have fired and the first frame
    has run, as at a first login. `layout` is the client's layout-cache
    ({ name: (x, y) })."""
    lua = wowkit.runtime()
    lua.execute(MOCK)
    lua.execute(WORLD)
    for name, (x, y) in (layout or {}).items():
        lua.execute(f"layoutCache['{name}'] = {{ {x}, {y} }}")
    lua.execute(setup)
    wowkit.load_addon(lua, ROOT, "Bags", saved=saved)
    if world:
        lua.execute('fire("VARIABLES_LOADED") fire("PLAYER_LOGIN") fire("PLAYER_ENTERING_WORLD") step()')
    return lua


def frame(lua):
    """Run the next frame: due timers (the coalesced redraw), then OnUpdate."""
    lua.execute("step(0.01)")
