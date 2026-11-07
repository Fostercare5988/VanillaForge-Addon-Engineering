"""The EasyPoisons regressions on the shared game model (wowkit).

Loads the files the selected addon's TOC lists, in order, with mocks shaped
like the stock 1.12 merchant/bag/tradeskill API and the ClassicAPI calls
EasyPoisons uses (GetMerchantItemID, C_MerchantFrame.GetItemInfo, C_Item,
C_Container, C_Timer). The mocks do not prove the server's vendor behaviour,
how many items one purchase gives, or how the window looks.

Lua 5.0's `for k, v in t do` form is rewritten to `pairs(t)` so the original
1.3 source runs under Lua 5.1 and fails on behaviour, not on syntax.
"""
from pathlib import Path
import os
import wowkit

ROOT = Path(os.environ["VANILLAFORGE_ADDON_ROOT"])

MOCK = r'''
CLASSIC_API_VERSION = 11711
messages, purchases, fonts, calls = chat, {}, {}, {}
local function count(name) calls[name] = (calls[name] or 0) + 1 end
GameTooltip = { SetOwner = function() end, SetText = function() end, Show = function() end, Hide = function() end }
playerClass, money, playerName = "ROGUE", 1000000, "Claude"
function UnitName() return playerName end
function GetRealmName() return "Y'Shaarj" end
function UnitClass() return "Rogue", playerClass end
function GetMoney() return money end
function GetAddOnMetadata(_, key) if key == "Version" then return "test" end if key == "Author" then return "Horyoshi" end end

-- Widgets ----------------------------------------------------------------
local setText = Widget.SetText
function Widget:SetText(v) setText(self, v); if self.kind == "EditBox" then run(self, "OnTextChanged") end end
local createFontString = Widget.CreateFontString
function Widget:CreateFontString(name) local f = createFontString(self, name); table.insert(fonts, f); return f end
MerchantFrame = newWidget("Frame", "MerchantFrame")

function click(button) if button and button:IsEnabled() then run(button, "OnClick") end end
function allText()
    local out = {}
    for _, f in ipairs(fonts) do if f.text then table.insert(out, f.text) end end
    return table.concat(out, "\n")
end

-- Timers -----------------------------------------------------------------
now = 0
function advance(dt) now = now + (dt or 0); runTimers() end

-- Items and bags -----------------------------------------------------------
MAXSTACK = { [8924] = 20, [2931] = 20, [8925] = 20, [8923] = 20, [5173] = 20, [5140] = 20, [999] = 1 }
NAMES = { [8924] = "Dust of Deterioration", [2931] = "Maiden's Anguish", [8925] = "Crystal Vial",
          [8923] = "Essence of Agony", [5173] = "Deathweed", [5140] = "Flash Powder" }
bags = { [0] = { size = 16, family = 0, slots = {} } }
for b = 1, 4 do bags[b] = { size = 0, family = 0, slots = {} } end
local function link(id) return "|cffffffff|Hitem:" .. id .. ":0:0:0|h[" .. (NAMES[id] or "Item") .. "]|h|r" end
function GetContainerNumSlots(b) return bags[b] and bags[b].size or 0 end
function GetContainerItemLink(b, s) count("bagRead"); local i = bags[b] and bags[b].slots[s]; if i then return link(i.id) end end
function GetContainerItemInfo(b, s) local i = bags[b] and bags[b].slots[s]; if i then return "Icon", i.count end end
C_Container = {
    GetContainerItemID = function(b, s) count("bagRead"); local i = bags[b] and bags[b].slots[s]; return i and i.id end,
    CalculateTotalNumberOfFreeBagSlots = function()
        local free = 0
        for b = 0, 4 do
            local bag = bags[b]
            if bag.family == 0 then for s = 1, bag.size do if not bag.slots[s] then free = free + 1 end end end
        end
        return free
    end,
}
local function carried(id)
    local n = 0
    for b = 0, 4 do for s = 1, bags[b].size do local i = bags[b].slots[s]; if i and i.id == id then n = n + i.count end end end
    return n
end
C_Item = {
    GetItemCount = function(id) return carried(id) end,
    GetItemMaxStackSizeByID = function(id) return MAXSTACK[id] end,
    GetItemNameByID = function(id) return NAMES[id] end,
    GetItemIconByID = function() return "Interface\\Icons\\Test" end,
}
function addItem(id, n)
    local cap = MAXSTACK[id] or 1
    for b = 0, 4 do
        for s = 1, bags[b].size do
            local i = bags[b].slots[s]
            if n > 0 and i and i.id == id and i.count < cap then
                local add = math.min(n, cap - i.count); i.count = i.count + add; n = n - add
            end
        end
    end
    for b = 0, 4 do
        if bags[b].family == 0 then
            for s = 1, bags[b].size do
                if n > 0 and not bags[b].slots[s] then
                    local add = math.min(n, cap); bags[b].slots[s] = { id = id, count = add }; n = n - add
                end
            end
        end
    end
end

-- Merchant -------------------------------------------------------------------
-- Each entry: id, price (per purchase), count (items per purchase), stock (-1 unlimited).
merchant = { open = false, items = {} }
function sells(id, price, n, stock) table.insert(merchant.items, { id = id, price = price, count = n or 1, stock = stock or -1 }) end
function poisonVendor() for _, id in ipairs({ 8924, 2931, 8925, 8923, 5173 }) do sells(id, 25) end end
local function entry(i) return merchant.open and merchant.items[i] end
function GetMerchantNumItems() return merchant.open and #merchant.items or 0 end
function GetMerchantItemID(i) local e = entry(i); return e and e.id end
function GetMerchantItemLink(i) local e = entry(i); return e and link(e.id) end
function GetMerchantItemInfo(i) local e = entry(i); if e then return NAMES[e.id], "Icon", e.price, e.count, e.stock, 1 end end
function GetMerchantItemMaxStack(i) local e = entry(i); return e and MAXSTACK[e.id] or 1 end
C_MerchantFrame = { GetItemInfo = function(i)
    local e = entry(i); if e then return { itemID = e.id, price = e.price, stackCount = e.count, numAvailable = e.stock } end
end }
function BuyMerchantItem(i, n)
    n = n or 1
    local e = merchant.items[i]
    table.insert(purchases, { id = e.id, n = n, items = n * e.count })
end
function bought(id)
    local n = 0
    for _, p in ipairs(purchases) do if p.id == id then n = n + p.items end end
    return n
end
function largestPurchase(id)
    local n = 0
    for _, p in ipairs(purchases) do if p.id == id and p.items > n then n = p.items end end
    return n
end
delivered = 0
function deliver()
    for i = delivered + 1, #purchases do addItem(purchases[i].id, purchases[i].items) end
    delivered = #purchases
    fire("BAG_UPDATE", 0); advance(0)
end
-- Delivers purchases as they are made, like the server answering each one.
-- drop = { [n] = true } loses the nth purchase, as a burst did on OctoWoW.
drop = {}
function settle(seconds)
    for _ = 1, 200 do
        if delivered < #purchases then
            for i = delivered + 1, #purchases do
                if not drop[i] then addItem(purchases[i].id, purchases[i].items) end
            end
            delivered = #purchases
            fire("BAG_UPDATE", 0)
        end
        advance(0.1)
        seconds = (seconds or 10) - 0.1
        if seconds <= 0 then break end
    end
end
function openVendor() merchant.open = true; MerchantFrame.shown = true; fire("MERCHANT_SHOW"); advance(0) end
function closeVendor() merchant.open = false; MerchantFrame.shown = false; fire("MERCHANT_CLOSED"); advance(0) end

-- Tradeskill window -----------------------------------------------------------
tradeskills = {}   -- { { item = id, name = "Deadly Poison IV", reagents = { { id, count }, ... } } }
function GetNumTradeSkills() return #tradeskills end
function GetTradeSkillInfo(i) local t = tradeskills[i]; return t.name, t.kind or "optimal" end
function GetTradeSkillItemID(i) return tradeskills[i] and tradeskills[i].item end
function GetTradeSkillNumReagents(i) return #tradeskills[i].reagents end
function GetTradeSkillReagentItemID(i, r) return tradeskills[i].reagents[r][1] end
function GetTradeSkillReagentInfo(i, r) local x = tradeskills[i].reagents[r]; return NAMES[x[1]], "Icon", x[2], 0 end

-- Addon handles ------------------------------------------------------------
function window() return _G.EasyPoisonsFrame end
function buyButton() return _G.EasyPoisons_Buy or (EasyPoisonsFrame and EasyPoisonsFrame.buyButton) end
function setQty(row, n)
    local input = _G["EasyPoisons_Row" .. row .. "Count"] or (_G["EasyPoisonRow" .. row] and _G["EasyPoisonRow" .. row].input)
    input:SetText(tostring(n)); advance(0)
end
function buy() click(buyButton()); advance(0) end
-- 2.0.0 order; 1.4.2 and earlier used Dissolvent, Crippling, Instant, Corrosive, Deadly, Mind.
POISON = { Instant = 1, Dissolvent = 2, Crippling = 3, Mind = 4, Deadly = 5, Corrosive = 6, Wound = 7, Agitating = 8 }
-- A test recipe for Deadly Poison IV, whose real one is learned in game.
EasyPoisonsDB = { Recipes = { [8985] = { [5173] = 7, [8925] = 1 } } }
'''


def load(setup="", login=True):
    lua = wowkit.runtime()
    lua.execute(MOCK)
    lua.execute(setup)
    lua.execute("addonNS = {}; __addon_ns = addonNS")
    wowkit.load_files(lua, ROOT, wowkit.toc_files(ROOT), "EasyPoisons")
    if login:
        lua.execute('fire("ADDON_LOADED", "EasyPoisons"); fire("PLAYER_LOGIN"); advance(0)')
    return lua
