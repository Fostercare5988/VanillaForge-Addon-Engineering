"""Shared Lua 5.1 environment for the EasyPoisons regressions.

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
import re
from lupa.lua51 import LuaRuntime

ROOT = Path(os.environ["VANILLAFORGE_ADDON_ROOT"])

MOCK = r'''
math.mod = math.mod or math.fmod
table.getn = table.getn or function(t) return #t end
function table.wipe(t) for k in pairs(t) do t[k] = nil end return t end
getglobal = function(n) return _G[n] end
CLASSIC_API_VERSION = 11600
messages, purchases, widgets, fonts, calls = {}, {}, {}, {}, {}
local function count(name) calls[name] = (calls[name] or 0) + 1 end
DEFAULT_CHAT_FRAME = { AddMessage = function(_, m) table.insert(messages, m) end }
SlashCmdList, UISpecialFrames = {}, {}
GameTooltip = { SetOwner = function() end, SetText = function() end, Show = function() end, Hide = function() end }
playerClass, money, playerName = "ROGUE", 1000000, "Claude"
function UnitName() return playerName end
function GetRealmName() return "Y'Shaarj" end
function UnitClass() return "Rogue", playerClass end
function GetMoney() return money end
function GetAddOnMetadata(_, key) if key == "Version" then return "test" end if key == "Author" then return "Horyoshi" end end

-- Widgets ----------------------------------------------------------------
local Widget = {}
local mt = { __index = function(_, k)
    local m = Widget[k]; if m then return m end
    if type(k) == "string" and string.find(k, "^[A-Z]") then return function() end end
end }
function newWidget(kind, name)
    local w = setmetatable({ kind = kind, name = name, scripts = {}, events = {}, shown = true }, mt)
    if name then _G[name] = w end
    table.insert(widgets, w)
    return w
end
function run(w, script)
    local f = w.scripts[script]
    if f then local old = this; this = w; f(w); this = old end
end
function Widget:SetScript(k, f) self.scripts[k] = f end
function Widget:GetScript(k) return self.scripts[k] end
function Widget:RegisterEvent(e) self.events[e] = true end
function Widget:UnregisterEvent(e) self.events[e] = nil end
function Widget:Show() if not self.shown then self.shown = true; run(self, "OnShow") end end
function Widget:Hide() if self.shown then self.shown = false; run(self, "OnHide") end end
function Widget:IsShown() return self.shown end
function Widget:IsVisible() return self.shown end
function Widget:GetName() return self.name end
function Widget:Enable() self.disabled = false end
function Widget:Disable() self.disabled = true end
function Widget:IsEnabled() return not self.disabled end
function Widget:SetChecked(v) self.checked = v and true or nil end
function Widget:GetChecked() return self.checked end
function Widget:GetText() return self.text end
function Widget:SetText(v)
    self.text = v
    if self.font then self.font:SetText(v) end
    if self.kind == "EditBox" then run(self, "OnTextChanged") end
end
function Widget:SetFontString(f) self.font = f end
function Widget:GetFontString() return self.font end
function Widget:CreateFontString() local f = newWidget("FontString"); table.insert(fonts, f); return f end
function Widget:CreateTexture() return newWidget("Texture") end
function CreateFrame(kind, name) return newWidget(kind, name) end
UIParent = newWidget("Frame", "UIParent")
MerchantFrame = newWidget("Frame", "MerchantFrame")

function fire(ev, a1)
    for _, w in ipairs(widgets) do
        if w.events[ev] and w.scripts.OnEvent then
            event, arg1 = ev, a1
            run(w, "OnEvent")
        end
    end
end
function click(button) if button and not button.disabled then run(button, "OnClick") end end
function allText()
    local out = {}
    for _, f in ipairs(fonts) do if f.text then table.insert(out, f.text) end end
    return table.concat(out, "\n")
end

-- Timers -----------------------------------------------------------------
now, timers = 0, {}
C_Timer = { After = function(s, f) table.insert(timers, { at = now + s, fn = f }) end }
function advance(dt)
    now = now + (dt or 0)
    local ran = true
    while ran do
        ran = false
        for i, t in ipairs(timers) do
            if t.at <= now then table.remove(timers, i); t.fn(); ran = true; break end
        end
    end
end

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

LUA50_FOR = re.compile(r"(for\s+[\w\s,]+\s+in\s+)([A-Za-z_][\w.]*)(\s+do)")


def _sources():
    toc = (ROOT / "EasyPoisons.toc").read_text("utf-8-sig")
    for line in toc.splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            yield line, (ROOT / line).read_text("utf-8-sig")


def load(setup="", login=True):
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(MOCK)
    lua.execute(setup)
    lua.execute("addonNS = {}")
    chunk = lua.eval("function(src, name) return assert(loadstring(src, name)) end")
    for name, src in _sources():
        src = LUA50_FOR.sub(lambda m: m.group(1) + "pairs(" + m.group(2) + ")" + m.group(3), src)
        chunk(src, "@" + name)("EasyPoisons", lua.eval("addonNS"))
    if login:
        lua.execute('fire("ADDON_LOADED", "EasyPoisons"); fire("PLAYER_LOGIN"); advance(0)')
    return lua
