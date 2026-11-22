"""Restock 1.0 (written new, 2026-11-22) on the shared game model (wowkit).

The game is modelled as ClassicAPI documents it (docs/API.md): C_MerchantFrame.GetItemInfo
(price per purchase, stackCount per purchase, numAvailable, -1 unlimited),
C_Container.GetContainerItemInfo with the `buf` argument (stackCount, itemID),
CalculateTotalNumberOfFreeBagSlots (general bags only), C_Item.GetItemCount (bags and
worn, no bank), GetTradeSkillItemID and GetTradeSkillReagentItemID, BAG_UPDATE_DELAYED.
The stock merchant and trade skill calls are the client's. The mocks do not prove what the
server gives for a purchase or when it answers: a purchase is delivered by the test
(`deliver()`), or lost (`lose()`).

The kit has no UnitClass, money, merchant, bag or trade skill model: they are stubbed
here. The recipes and item IDs are test data (Claude's saved Poisons window), not proof.
"""
from pathlib import Path
import os
import wowkit

ROOT = Path(os.environ["VANILLAFORGE_ADDON_ROOT"])

MOCK = r'''
CLASSIC_API_VERSION = 12302
playerClass, money = "ROGUE", 1000000
function UnitClass() return "Rogue", playerClass end
function GetMoney() return money end

-- Items and bags ---------------------------------------------------------------
MAXSTACK = { [8924] = 20, [2931] = 20, [8925] = 20, [8923] = 20, [5173] = 20, [2930] = 20, [3372] = 20, [5140] = 20 }
NAMES = { [8924] = "Dust A", [2931] = "Anguish", [8925] = "Vial", [8923] = "Essence", [5173] = "Deathweed",
          [2930] = "Pain", [3372] = "Leaded Vial", [5140] = "Flash Powder" }
bags = { [0] = { size = 16, family = 0, slots = {} } }
for b = 1, 4 do bags[b] = { size = 0, family = 0, slots = {} } end
function GetContainerNumSlots(b) return bags[b] and bags[b].size or 0 end
C_Container = {
    GetContainerItemInfo = function(b, s, buf)
        local i = bags[b] and bags[b].slots[s]
        if not i then return nil end
        buf = buf or {}
        buf.itemID, buf.stackCount = i.id, i.count
        return buf
    end,
    CalculateTotalNumberOfFreeBagSlots = function()
        local free = 0
        for b = 0, 4 do
            if bags[b].family == 0 then for s = 1, bags[b].size do if not bags[b].slots[s] then free = free + 1 end end end
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
    GetItemCount = carried,
    GetItemMaxStackSizeByID = function(id) return MAXSTACK[id] end,
    GetItemNameByID = function(id) return NAMES[id] end,
}
-- Stacks of an item, partial first, as the game fills them.
function addItem(id, n)
    local cap = MAXSTACK[id] or 1
    for b = 0, 4 do for s = 1, bags[b].size do
        local i = bags[b].slots[s]
        if n > 0 and i and i.id == id and i.count < cap then
            local add = math.min(n, cap - i.count); i.count = i.count + add; n = n - add
        end
    end end
    for b = 0, 4 do if bags[b].family == 0 then for s = 1, bags[b].size do
        if n > 0 and not bags[b].slots[s] then
            local add = math.min(n, cap); bags[b].slots[s] = { id = id, count = add }; n = n - add
        end
    end end end
end
-- A stack in a given slot (to make partial stacks).
function put(b, s, id, n) bags[b].slots[s] = { id = id, count = n } end
function fillBags(except)
    for b = 0, 4 do for s = 1, bags[b].size do
        if not (b == 0 and except and s <= except) then bags[b].slots[s] = bags[b].slots[s] or { id = 6948, count = 1 } end
    end end
end

-- The vendor ---------------------------------------------------------------------
purchases, delivered = {}, 0
merchant = { open = false, items = {} }
-- price per purchase, items per purchase, stock (-1 unlimited)
function sells(id, price, n, stock) merchant.items[#merchant.items + 1] = { id = id, price = price or 25, per = n or 1, stock = stock or -1 } end
function poisonVendor() for _, id in ipairs({ 8924, 2931, 8925, 8923, 5173, 2930, 3372 }) do sells(id) end end
function openVendor() merchant.open = true; fire("MERCHANT_SHOW") end
function closeVendor() merchant.open = false; fire("MERCHANT_CLOSED") end
local function entry(i) return merchant.open and merchant.items[i] end
function GetMerchantNumItems() return merchant.open and #merchant.items or 0 end
function GetMerchantItemMaxStack(i) local e = entry(i); return e and MAXSTACK[e.id] or 1 end
C_MerchantFrame = { GetItemInfo = function(i)
    local e = entry(i)
    if e then return { itemID = e.id, price = e.price, stackCount = e.per, numAvailable = e.stock } end
end }
function BuyMerchantItem(i, n)
    local e = merchant.items[i]
    purchases[#purchases + 1] = { id = e.id, n = n, items = n * e.per, cost = n * e.price, slot = i }
end
function bought(id) local n = 0; for _, p in ipairs(purchases) do if p.id == id then n = n + p.items end end return n end
function largest() local n = 0; for _, p in ipairs(purchases) do if p.items > n then n = p.items end end return n end
-- The server answers: every purchase sent since the last answer arrives, then one bag event.
function deliver()
    for i = delivered + 1, #purchases do
        local p = purchases[i]
        addItem(p.id, p.items); money = money - p.cost
        local e = merchant.items[p.slot]; if e.stock >= 0 then e.stock = e.stock - p.n end
    end
    delivered = #purchases
    fire("BAG_UPDATE", 0); fire("BAG_UPDATE_DELAYED"); step(0)
end
-- The server loses what was sent: it never arrives.
function lose() delivered = #purchases end
-- Delivers, answer by answer, until nothing more is sent (at most 60 answers).
function finish()
    for _ = 1, 60 do
        local sent = #purchases
        deliver()
        if #purchases == sent then return end
    end
end

-- Chat.
function said() return chat[#chat] end
function allSaid() return table.concat(chat, "\n") end

-- The Poisons window: rows { name, kind, item, { {id, count}, ... } }.
skills = {}
function GetNumTradeSkills() return #skills end
function GetTradeSkillInfo(i) local s = skills[i]; if s then return s[1], s[2] end end
function GetTradeSkillItemID(i) return skills[i] and skills[i][3] end
function GetTradeSkillNumReagents(i) return skills[i] and skills[i][4] and #skills[i][4] or 0 end
function GetTradeSkillReagentItemID(i, r) local x = skills[i][4][r]; return x and x[1] end
function GetTradeSkillReagentInfo(i, r) local x = skills[i][4][r]; if x then return "Reagent", "Icon", x[2], 0 end end
function recipe(name, item, ...) skills[#skills + 1] = { name, "optimal", item, { ... } } end
function openWindow() fire("TRADE_SKILL_SHOW") end

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
'''

# Claude's saved Poisons window, as the import writes it (three poisons are enough for the plan tests).
CLAUDE = '''RestockDB = { poisons = {
 ["Instant Poison"] = { item = 8928, rank = 6, reagents = { [8924] = 4, [8925] = 1 } },
 ["Crippling Poison"] = { item = 3776, rank = 2, reagents = { [8923] = 3, [8925] = 1 } },
 ["Deadly Poison"] = { item = 8985, rank = 4, reagents = { [5173] = 5, [8925] = 1 } } } }'''


def load(saved="", setup="", world=True):
    """The addon loaded over `saved` (Lua that sets RestockDB); with `world`, the login
    events have fired, so the page exists and the events are registered."""
    lua = wowkit.runtime()
    lua.execute(MOCK)
    lua.execute(setup)
    wowkit.load_addon(lua, ROOT, "Restock", saved=saved or None)
    if world:
        lua.execute('fire("VARIABLES_LOADED") fire("PLAYER_LOGIN") fire("PLAYER_ENTERING_WORLD") step()')
    return lua
