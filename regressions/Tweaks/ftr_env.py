"""Tweaks 1.0 (the rebuild, released 2026-11-18 with a fresh
history; the suite of the old 1.22 is gone with it) on the shared game model
(wowkit). tools/run_suite.py and tools/audit_addon.py point
VANILLAFORGE_ADDON_ROOT at the addon.

The game is modelled as ClassicAPI documents it (docs/API.md) and as the
client's FrameXML runs it: tooltips fire OnTooltipCleared, then
OnTooltipSetItem with the item's GUID as arg1 (### OnTooltipSet* scripts);
SetTooltipMoney and MoneyFrame_Update record the price (FrameXML
GameTooltip.lua); ContainerFrame_Update, BankFrameItemButton_OnUpdate and the
paperdoll and inspect slot updates call their hooks as FrameXML does; chat
frames keep lines with their extra values (### smf:GetMessageInfo). The
mocks do not prove drawing, anchoring or when the client sends events.
"""
from pathlib import Path
import os
import wowkit

ROOT = Path(os.environ["VANILLAFORGE_ADDON_ROOT"])

MOCK = r'''
CLASSIC_API_VERSION = 12100
CLOSE = 'Close'
SPELL_FAILED_ONLY_SHAPESHIFT = 'Must be in %s'
NUM_CHAT_WINDOWS, MAX_CONTAINER_ITEMS, BANK_CONTAINER = 7, 36, -1
calls = {}
local function record(name, value) calls[name] = calls[name] or {}; table.insert(calls[name], value) end
function count(name) return calls[name] and #calls[name] or 0 end
function last(name) local list = calls[name]; return list and list[#list] end

-- hooksecurefunc(name, fn) and hooksecurefunc(table, name, fn), as the client runs them.
function hooksecurefunc(a, b, c)
    local t, name, hook = _G, a, b
    if type(a) == 'table' then t, name, hook = a, b, c end
    local stock = t[name]
    t[name] = function(...) local r = stock(...); hook(...); return r end
end

-- Widgets: what the addon reads back.
function Widget:GetCenter() return self.cx or 500, self.cy or 400 end
function Widget:StartMoving() self.moving = true end
function Widget:StopMovingOrSizing() self.moving = nil; self.cx, self.cy = dropAt[1], dropAt[2] end
dropAt = { 700, 300 }
function Widget:SetMaskTexture(path) self.mask = path end
function Widget:SetBackdropBorderColor(r, g, b) self.border = { r, g, b } end
function Widget:EnableMouseWheel(on) self.wheel = on and true or false end
function Widget:SetDontSavePosition(on) self.dontSave = on end
function Widget:SetHighlightTexture() end
function Widget:SetFrameLevel() end
for _, side in ipairs({ 'Left', 'Right', 'Top', 'Bottom' }) do Widget['Get' .. side] = function() return 100 end end
function Widget:GetEffectiveScale() return self.scale or 1 end
function MouseIsOver(frame) return frame.hovered end
function IsShiftKeyDown() return shift and 1 or nil end
function IsControlKeyDown() return ctrl and 1 or nil end
function press(s, c) shift, ctrl = s, c; fire('MODIFIER_STATE_CHANGED', s and 'LSHIFT' or 'LCTRL', s and 1 or 0) end

-- Items: id -> { price, quality }; GUID -> stack.
items, stacks = {}, {}
function GetItemQualityColor(q) return q / 10, q / 10, q / 10, 'hex' end
C_Item = {
    GetItemSellPriceByID = function(id) return items[id] and items[id].price end,
    GetItemQualityByID = function(id) return items[id] and items[id].quality end,
    GetStackCount = function(guid) return stacks[guid] or 0 end,
}
function link(id) return '|cffffffff|Hitem:' .. id .. ':0:0:0|h[Item ' .. id .. ']|h|r' end

-- Tooltips (### OnTooltipSet* scripts): Cleared, then the item, then SetItem with the GUID.
local function tooltip(name)
    local tip = CreateFrame('GameTooltip', name)
    tip:Hide()
    function tip:GetItem() if self.item then return 'Item ' .. self.item, link(self.item), self.item end end
    function tip:SetOwner() end
    function tip:AddLine() end
    function tip:AddDoubleLine() end
    function tip:SetText(text) self.text = text end
    return tip
end
GameTooltip, ItemRefTooltip = tooltip('GameTooltip'), tooltip('ItemRefTooltip')
ShoppingTooltip1, ShoppingTooltip2 = tooltip('ShoppingTooltip1'), tooltip('ShoppingTooltip2')
function showItem(tip, id, guid)
    tip.money = nil
    run(tip, 'OnTooltipCleared')
    tip.item = id
    run(tip, 'OnTooltipSetItem', guid)
    tip:Show()
end
function GameTooltip:SetAuctionItem(kind, index) showItem(self, auctions[index].id) end
function GameTooltip:SetAuctionSellItem() showItem(self, auctions.sell.id) end
auctions = {}
function GetAuctionItemInfo(kind, index) return 'x', 'tex', auctions[index].count end
function GetAuctionSellItemInfo() return 'x', 'tex', auctions.sell.count end
function SetTooltipMoney(frame, money) frame.money = money; record('SetTooltipMoney', money) end
function MoneyFrame_Update(name, money) _G[string.gsub(name, 'MoneyFrame$', '')].money = money end
function GameTooltip_ShowCompareItem(tip) record('compare', tip:GetName()); ShoppingTooltip1:Show() end

-- Bags, bank, character and inspect slots, as FrameXML updates them.
bagItems, bankItems, worn, inspectWorn = {}, {}, {}, {}
ContainerFrame1 = CreateFrame('Frame', 'ContainerFrame1'); ContainerFrame1:SetID(0); ContainerFrame1.size = 4
for i = 1, MAX_CONTAINER_ITEMS do CreateFrame('Button', 'ContainerFrame1Item' .. i):SetID(i) end
C_Container = { GetContainerItemInfo = function(bag, slot, buf)
    record('GetContainerItemInfo', slot)
    local id = bagItems[slot]; if not id then return end
    buf.itemID, buf.quality = id, items[id] and items[id].qualityInBag or -1
    return buf
end }
function ContainerFrame_Update(frame) end
function GetContainerItemLink(bag, slot) local id = bag == BANK_CONTAINER and bankItems[slot]; return id and link(id) end
function BankFrameItemButton_OnUpdate() end
function PaperDollItemSlotButton_Update() end
function GetInventoryItemLink(unit, slot)
    local id = (unit == 'player' and worn or inspectWorn)[slot]; return id and link(id)
end
loaded = {}
C_AddOns = { IsAddOnLoaded = function(name) return loaded[name] end }
function loadInspect()
    loaded.Blizzard_InspectUI = true
    InspectFrame = CreateFrame('Frame', 'InspectFrame'); InspectFrame:Hide(); InspectFrame.unit = 'party2'
    function InspectPaperDollItemSlotButton_Update(button) end
    fire('ADDON_LOADED', 'Blizzard_InspectUI')
end
function slotButton(name, id) local b = CreateFrame('Button', name); b:SetID(id); return b end
function borderOf(button) local b = button.ftBorder; return b and b.border end

-- The merchant (### C_MerchantFrame).
MerchantFrame = CreateFrame('Frame', 'MerchantFrame'); MerchantFrame:Hide(); MerchantFrame.selectedTab = 1
MerchantRepairItemButton = CreateFrame('Button', 'MerchantRepairItemButton')
MerchantBuyBackItemItemButton = CreateFrame('Button', 'MerchantBuyBackItemItemButton')
function MerchantFrame_Update() end
junkCount = 0
C_MerchantFrame = {
    GetNumJunkItems = function() return MerchantFrame:IsShown() and junkCount or 0 end,
    SellAllJunkItems = function() record('SellAllJunkItems', true) end,
}

-- Chat: frames keep lines with their extra values (### smf:GetMessageInfo / BackFillMessage).
ChatFrameEditBox = CreateFrame('EditBox', 'ChatFrameEditBox'); ChatFrameEditBox:Hide()
function ChatFrameEditBox:SetAltArrowKeyMode(on) self.altArrows = on end
function ChatFrameEditBox:Insert(text) self.inserted = text end
for i = 1, NUM_CHAT_WINDOWS do
    local f = CreateFrame('ScrollingMessageFrame', 'ChatFrame' .. i)
    f.lines, f.messageTypeList = {}, { 'SAY', 'GUILD' }
    function f:AddMessage(text, r, g, b, ...) table.insert(self.lines, { text, r, g, b, ... }) end
    function f:BackFillMessage(text, r, g, b, ...) table.insert(self.lines, 1, { text, r, g, b, ... }) end
    function f:GetNumMessages() return #self.lines end
    function f:GetMessageInfo(i) local l = self.lines[i]; if l then return unpack(l) end end
end
ChatFrame2.messageTypeList = { 'COMBAT_SELF_HITS', 'COMBAT_SELF_MISSES', 'SPELL_SELF_DAMAGE', 'SPELL_DAMAGESHIELDS_ON_SELF',
    'COMBAT_PARTY_HITS', 'SPELL_PARTY_DAMAGE', 'COMBAT_HOSTILEPLAYER_HITS' }
function lineOf(frame, i) local l = frame.lines[i or #frame.lines]; return l and l[1] end
clockAt = { H = '13', M = '07', S = '42' }
function date(format)
    return (string.gsub(format, '%%(%a)', function(c) return clockAt[c] end))
end
function GetGameTime() return 12, 5 end

-- Class colours (### C_ClassColor.GetClassColor returns RAID_CLASS_COLORS' own table).
local function color(r, g, b, s)
    return { r = r, g = g, b = b, colorStr = s, WrapTextInColorCode = function(self, text)
        return '|c' .. self.colorStr .. text .. '|r' end }
end
RAID_CLASS_COLORS = { SHAMAN = color(0.96, 0.55, 0.73, 'fff58cba'), ROGUE = color(1, 0.96, 0.41, 'fffff569'),
    MAGE = color(0.41, 0.8, 0.94, 'ff69ccf0') }
C_ClassColor = { GetClassColor = function(class) return RAID_CLASS_COLORS[class] end }
known, guids = {}, {}
C_PlayerCache = { GetPlayerInfoByName = function(name) local c = known[name]; if c then return c, c end end }
function GetPlayerInfoByGUID(guid) local g = guids[guid]; if g then return g[2], g[2], 'r', 'r', 2, g[1] end end
function GetCurrentChatGUID() return chatGUID end
function SetItemRef(link, text, button) record('stockRef', link) end
StaticPopupDialogs = {}
StaticPopup1 = CreateFrame('Frame', 'StaticPopup1'); StaticPopup1:Hide()
StaticPopup1WideEditBox = CreateFrame('EditBox', 'StaticPopup1WideEditBox', StaticPopup1)
function StaticPopup1WideEditBox:HighlightText() self.highlighted = true end
function StaticPopup_Show(which, a1, a2, data)
    StaticPopup1.which, StaticPopup1.data = which, data
    this = StaticPopup1; StaticPopupDialogs[which].OnShow(data); this = nil
    StaticPopup1:Show()
end

-- The minimap (FrameXML Minimap.xml) and the world map.
for _, name in ipairs({ 'MinimapCluster', 'Minimap', 'MinimapZoneTextButton', 'MiniMapMailFrame',
    'MiniMapBattlefieldFrame', 'MiniMapTrackingFrame', 'GameTimeFrame', 'MinimapToggleButton',
    'MinimapZoomIn', 'MinimapZoomOut', 'WorldMapFrame', 'WorldMapButton', 'BattlefieldMinimap' }) do
    CreateFrame('Frame', name)
end
MinimapBorder, MinimapBorderTop = Minimap:CreateTexture('MinimapBorder'), MinimapCluster:CreateTexture('MinimapBorderTop')
MiniMapMailFrame:Hide(); MiniMapBattlefieldFrame:Hide(); MiniMapTrackingFrame:Hide(); WorldMapFrame:Hide(); BattlefieldMinimap:Hide()
function Minimap_ZoomIn() record('zoom', 1) end
function Minimap_ZoomOut() record('zoom', -1) end
function HasNewMail() return newMail end
function BattlefieldFrame_UpdateStatus() record('bgStatus', true) end
function GetTrackingTexture() return tracking end
WORLDMAP_WINDOWED = 1
function WorldMapFrame_Minimize() WORLDMAP_WINDOWED = 1 end
function WorldMapFrame_Maximize() WORLDMAP_WINDOWED = 0 end
mapPos, cursorAt = { 0.4567, 0.1234 }, { 150, 50 }
function GetPlayerMapPosition(unit) record('mapPos', unit); return mapPos[1], mapPos[2] end
function GetCursorPosition() return cursorAt[1], cursorAt[2] end
function WorldMapButton:GetWidth() return 100 end
function WorldMapButton:GetHeight() return 100 end
-- The kit keeps a widget's name in `.name`; the map's group buttons use `.name` for a
-- member's name (FrameXML WorldMapFrame.lua), so these keep theirs apart.
function mapButtons(prefix)
    for _, kind in ipairs({ 'Party', 'Raid' }) do
        for i = 1, kind == 'Party' and 4 or 40 do
            local b = CreateFrame('Button', prefix .. kind .. i)
            b:Hide(); b.frameName, b.name = b.name, nil
            function b:GetName() return self.frameName end
            CreateFrame('Texture', prefix .. kind .. i .. 'Icon')
        end
    end
end
mapButtons('WorldMap')
names, classes = { player = 'Me' }, { player = 'ROGUE' }
function UnitName(unit) return names[unit] end
function UnitClass(unit) local c = classes[unit]; return c, c end

-- Stances.
forms = {}
function GetNumShapeshiftForms() return #forms end
function GetShapeshiftFormInfo(i) local f = forms[i]; return 'tex', f.name, f.active, f.castable end
function CastShapeshiftForm(i) record('CastShapeshiftForm', i) end

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
'''

GLOBALS = ("TweaksDB", "SLASH_TWEAKS1", "MinimapClock", "SetItemRef")


def load(saved="", setup="", world=True, cls="ROGUE"):
    """The addon loaded over `saved` (Lua that sets TweaksDB); with
    `world`, the login events have fired, so the page and the chat exist."""
    lua = wowkit.runtime()
    lua.execute(MOCK)
    lua.execute("classes.player = %r" % cls)
    lua.execute(setup)
    wowkit.load_addon(lua, ROOT, "Tweaks", saved=saved or None)
    if world:
        lua.execute('fire("VARIABLES_LOADED") fire("PLAYER_ENTERING_WORLD")')
    return lua
