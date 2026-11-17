"""The Mail regressions on the shared game model (wowkit).

Mail 1.0.0 (2026-11-17), built from scratch. It is loaded from its TOC with
`## LoadSavedVariablesFirst`. The model here:

* A bag click as OctoWoW's ContainerFrame.lua:567 has it: on the Send tab a
  right-click puts the item in the client's one mail slot, Shift-right-click
  uses it; elsewhere a right-click uses it. `rightClickBag(bag, slot)`.
* The client's mail page, as FrameXML MailFrame.lua and MailFrame.xml have it
  (`.private/framexml`): the frames Mail touches, the edit boxes with their
  own scripts, and the client's MailFrame_OnEvent, InboxFrame_Update,
  SendMailFrame_Update, SendMailFrame_CanSend, SendMailFrame_Reset and
  SendMailRadioButton_OnClick, reduced to what Mail reads or changes. The
  client's frame is registered first, so it hears each event before Mail.
* The server: inbox requests (take money, take item, delete, check) wait
  until `answer()`, which applies the oldest and fires MAIL_INBOX_UPDATE;
  `SendMail` waits until `deliver()` (MAIL_SEND_SUCCESS) or `refuse(err)`
  (UI_ERROR_MESSAGE, then MAIL_FAILED). Taking an item into full bags gives
  ERR_INV_FULL.
* LockItem and UnlockItem fire ITEM_LOCK_CHANGED inside the call, as
  "### C_Item.LockItem(itemLocation)" documents and play showed (2026-11-17).
* Bags of items with GUIDs, as ClassicAPI documents C_Item (GetItemGUID,
  GetItemLocation, IsItemGUIDInInventory, GetItemID, GetItemIcon,
  GetStackCount, LockItem, UnlockItem, IsLocked, IsBound, GetItemData); a locked item cannot
  be picked up; GetCursorInfo gives "item", itemID. The client's one send
  slot refuses a soulbound item.
* `hooksecurefunc` runs the hook after the original ("## Hooks").

Not modelled: drawing and layout (the slot rows and the letter are seen in
play), the real order of server answers, and whether the client keeps a
picked-up item's GUID at its bag slot.
"""
from pathlib import Path
import os
import wowkit

ROOT = Path(os.environ["VANILLAFORGE_ADDON_ROOT"])

MOCK = r'''
CLASSIC_API_VERSION = 12100
-- The error handler: every error a guarded callback raises lands here (API.md, xpcall).
luaErrors = {}
function geterrorhandler() return function(m) luaErrors[#luaErrors + 1] = m end end
hooked = {}
function hooksecurefunc(name, hook)
    hooked[name] = true
    local original = _G[name]
    _G[name] = function(...) local a, b, c = original(...); hook(...); return a, b, c end
end
function Widget:SetNormalTexture(t) self.normal = t end
function Widget:HighlightText(a, b) self.highlight = { a or 0, b or -1 } end
function Widget:SetFocus() self.focus = true end
function Widget:LockHighlight() self.locked = true end
function Widget:UnlockHighlight() self.locked = nil end
function Widget:IsOwned(f) return self.owner == f and 1 or nil end
function Widget:SetOwner(f) self.owner = f; self.lines = {} end
function Widget:AddLine(text) self.lines[#self.lines + 1] = text end
function Widget:GetRegions() return unpack(self.regions or {}) end
local function frame(kind, name, parent) local w = CreateFrame(kind, name, parent); return w end

-- Strings and numbers from the client (GlobalStrings.lua, MailFrame.lua).
INBOXITEMS_TO_DISPLAY, MAX_COD_AMOUNT, COPPER_PER_GOLD = 7, 10000, 10000
INBOX, EMPTY, ATTACHMENT_TEXT = "Inbox", "Empty", "Drag an item here to mail it"
AMOUNT_TO_SEND, COD_AMOUNT = "Amount to Send:", "C.O.D. Amount:"
SEND_MONEY_CONFIRMATION, ACCEPT, CANCEL = "Send money to %s?", "Accept", "Cancel"
AUCTION_SOLD_MAIL_SUBJECT = "Auction successful: %s"
AUCTION_REMOVED_MAIL_SUBJECT = "Auction cancelled: %s"
AUCTION_EXPIRED_MAIL_SUBJECT = "Auction expired: %s"
AUCTION_WON_MAIL_SUBJECT = "Auction won: %s"
AUCTION_OUTBID_MAIL_SUBJECT = "Outbid on %s"
ERR_INV_FULL, ERR_ITEM_MAX_COUNT = "Inventory is full.", "You can't carry any more of those items."
ERR_MAIL_TO_SELF, ERR_PLAYER_WRONG_FACTION = "You can't send mail to yourself.", "Target is unfriendly."
ERR_MAIL_TARGET_NOT_FOUND, ERR_MAIL_REACHED_CAP = "Cannot find mail recipient.", "That player's mailbox is full."
NORMAL_FONT_COLOR = { r = 1, g = 0.82, b = 0 }
UIPanelWindows = { MailFrame = { area = "left", pushable = 0 }, FriendsFrame = { area = "left", pushable = 1 } }
StaticPopupDialogs, popups = {}, {}
function StaticPopup_Show(which, a1) popups[#popups + 1] = which; shownPopup = which end
function acceptPopup() local p = shownPopup; shownPopup = nil; StaticPopupDialogs[p].OnAccept() end
function MoneyFrame_Update(name, copper) postage = copper end
function PlaySound() end
function HideUIPanel(f) f:Hide() end
function UnitName() return "Claude" end
function GetRealmName() return "Y'Shaarj" end
function UnitFactionGroup() return "Horde" end
clock = 1800000000
function time() return clock end
money = 1000000
function GetMoney() return money end
function GetSendMailPrice() return 30 end
shift = nil
function IsShiftKeyDown() return shift end
function IsControlKeyDown() end
function IsAltKeyDown() end
function IsModifierKeyDown() return shift end

-- The mail frames.
MailFrame = frame("Frame", "MailFrame"); MailFrame:Hide()
InboxFrame = frame("Frame", "InboxFrame", MailFrame); InboxFrame.pageNum = 1
OpenMailFrame = frame("Frame", "OpenMailFrame", MailFrame)
InboxTitleText = frame("FontString", "InboxTitleText", InboxFrame)
for i = 1, 7 do
    local row = frame("Frame", "MailItem" .. i, InboxFrame)
    local b = frame("CheckButton", "MailItem" .. i .. "Button", row)
    b:SetScript("OnClick", function() InboxFrame_OnClick(this.index) end)
    b:SetScript("OnEnter", function() InboxFrameItem_OnEnter() end)
    frame("Texture", "MailItem" .. i .. "ButtonIcon", b)
    frame("Frame", "MailItem" .. i .. "ExpireTime", row)
end
SendMailFrame = frame("Frame", "SendMailFrame", MailFrame); SendMailFrame:Hide()
local function edit(name)
    local e = frame("EditBox", name, SendMailFrame); e.text = ""
    return e
end
SendMailNameEditBox, SendMailSubjectEditBox = edit("SendMailNameEditBox"), edit("SendMailSubjectEditBox")
SendMailBodyEditBox = edit("SendMailBodyEditBox")
SendMailNameEditBox:SetScript("OnTabPressed", function() SendMailSubjectEditBox:SetFocus() end)
SendMailNameEditBox:SetScript("OnEnterPressed", function() SendMailSubjectEditBox:SetFocus() end)
SendMailNameEditBox:SetScript("OnEscapePressed", function() SendMailNameEditBox.focus = nil end)
SendMailNameEditBox:SetScript("OnChar", function() clientGuess = true end)
SendMailNameEditBox:SetScript("OnTextChanged", function() SendMailFrame_CanSend() end)
SendMailSubjectEditBox:SetScript("OnTextChanged", function() SendMailFrame_CanSend() end)
-- SetText fires OnTextChanged, as the client does.
local SetText = Widget.SetText
function Widget:SetText(text)
    local changed = self.kind == "EditBox" and self.text ~= text
    SetText(self, text)
    if changed then run(self, "OnTextChanged") end
end
function typeInto(box, text) box:SetText(text); run(box, "OnChar") end
SendMailScrollFrame = frame("ScrollFrame", "SendMailScrollFrame", SendMailFrame)
StationeryBackgroundLeft = frame("Texture", "StationeryBackgroundLeft", SendMailScrollFrame)
StationeryBackgroundRight = frame("Texture", "StationeryBackgroundRight", SendMailScrollFrame)
SendMailScrollFrame.regions = { StationeryBackgroundLeft, StationeryBackgroundRight,
    frame("Texture", nil, SendMailScrollFrame), frame("Texture", nil, SendMailScrollFrame) }
SendMailScrollChildFrame = frame("Frame", "SendMailScrollChildFrame", SendMailScrollFrame)
SendMailScrollChildFrame:SetScript("OnMouseUp", function() if CursorHasItem() then ClickSendMailItemButton() end end)
SendMailHorizontalBarLeft = frame("Texture", "SendMailHorizontalBarLeft", SendMailFrame)
SendMailPackageButton = frame("Button", "SendMailPackageButton", SendMailFrame)
SendMailPackageButtonCount = frame("FontString", "SendMailPackageButtonCount", SendMailPackageButton)
SendMailMoneyText = frame("FontString", "SendMailMoneyText", SendMailPackageButton)
SendMailPackageButton.regions = { frame("Texture", nil, SendMailPackageButton), SendMailMoneyText, SendMailPackageButtonCount }
SendMailMoney = frame("Frame", "SendMailMoney", SendMailPackageButton); SendMailMoney.copper = 0
function MoneyInputFrame_GetCopper(f) return f.copper end
function MoneyInputFrame_ResetMoney(f) f.copper = 0 end
SendMailSendMoneyButton = frame("CheckButton", "SendMailSendMoneyButton", SendMailPackageButton)
SendMailCODButton = frame("CheckButton", "SendMailCODButton", SendMailPackageButton)
SendMailCODButtonText = frame("FontString", "SendMailCODButtonText", SendMailCODButton)
SendMailMailButton = frame("Button", "SendMailMailButton", SendMailFrame)
SendMailMailButton:SetScript("OnClick", function() clientSend = true end)

function MailFrameTab_OnClick(tab)
    if tab == 1 then InboxFrame:Show(); SendMailFrame:Hide() else InboxFrame:Hide(); SendMailFrame:Show(); SendMailFrame_Update() end
end
function InboxFrame_OnClick(index) opened = index end
function InboxFrameItem_OnEnter()
    GameTooltip:SetOwner(this)
    if this.hasItem then GameTooltip:AddLine("item of mail " .. this.index) end
end
function InboxFrame_Update()
    for i = 1, 7 do
        local b, index = _G["MailItem" .. i .. "Button"], (InboxFrame.pageNum - 1) * 7 + i
        local m = inbox[index]
        b.index, b.hasItem = index, m and m.item and 1
        b.money = m and (m.money or 0) > 0 and m.money or nil
        b.cod = m and (m.cod or 0) > 0 and m.cod or nil
    end
end
function SendMailRadioButton_OnClick(index)
    SendMailSendMoneyButton:SetChecked(index == 1); SendMailCODButton:SetChecked(index == 2)
    SendMailMoneyText:SetText(index == 1 and AMOUNT_TO_SEND or COD_AMOUNT)
end
function SendMailFrame_Update()
    if attached then SendMailCODButton:Enable() else SendMailRadioButton_OnClick(1); SendMailCODButton:Disable() end
    MoneyFrame_Update("SendMailCostMoneyFrame", GetSendMailPrice())
    SendMailFrame_CanSend()
end
function SendMailFrame_CanSend()
    if SendMailNameEditBox:GetText() ~= "" and SendMailSubjectEditBox:GetText() ~= "" then
        SendMailMailButton:Enable() else SendMailMailButton:Disable() end
end
function SendMailFrame_Reset()
    SendMailNameEditBox:SetText(""); SendMailSubjectEditBox:SetText(""); SendMailBodyEditBox:SetText("")
    SendMailFrame_Update(); MoneyInputFrame_ResetMoney(SendMailMoney); SendMailRadioButton_OnClick(1)
end
GameTooltip = frame("GameTooltip", "GameTooltip")
-- The client's own handler, registered before any addon's.
MailFrame:SetScript("OnEvent", function()
    if event == "MAIL_SHOW" then MailFrame:Show(); MailFrameTab_OnClick(1); CheckInbox()
    elseif event == "MAIL_INBOX_UPDATE" then InboxFrame_Update()
    elseif event == "MAIL_SEND_SUCCESS" then SendMailFrame_Reset()
    elseif event == "MAIL_FAILED" then SendMailMailButton:Enable()
    elseif event == "MAIL_CLOSED" then MailFrame:Hide() end
end)
for _, e in ipairs({ "MAIL_SHOW", "MAIL_INBOX_UPDATE", "MAIL_SEND_SUCCESS", "MAIL_FAILED", "MAIL_CLOSED" }) do MailFrame:RegisterEvent(e) end

-- The server's inbox: { sender, subject, money, cod, item = { name, count }, gm, returned }.
inbox, requests, log = {}, {}, {}
-- The server's lists are not addon Lua: no Lua 5.0 stored size.
function drop(list, i) local v = list[i]; for j = i, #list do list[j] = list[j + 1] end; return v end
function GetInboxNumItems() return math.min(#inbox, 50) end
function GetInboxHeaderInfo(i)
    local m = i <= GetInboxNumItems() and inbox[i]
    if not m then return end
    return nil, "stationery", m.sender, m.subject or "", m.money or 0, m.cod or 0, 3, m.item and 1, m.read,
        m.returned, nil, 1, m.gm
end
function GetInboxItem(i)
    local m = i <= GetInboxNumItems() and inbox[i]
    if m and m.item then return m.item[1], "icon", m.item[2] or 1 end
end
function GetInboxText(i) inbox[i].read = 1 end
local function ask(kind, i) log[#log + 1] = kind .. " " .. i; requests[#requests + 1] = { kind, inbox[i] } end
function TakeInboxMoney(i) ask("money", i) end
function TakeInboxItem(i) ask("item", i) end
function DeleteInboxItem(i) ask("delete", i) end
checks = 0
function CheckInbox() checks = checks + 1; requests[#requests + 1] = { "check" } end
bagsFull = false
-- The server answers the oldest request, then the client fires MAIL_INBOX_UPDATE.
function answer()
    local r = drop(requests, 1)
    if not r then return end
    local kind, m = r[1], r[2]
    local index
    for i, mail in ipairs(inbox) do if mail == m then index = i end end
    if kind == "money" and index then money = money + m.money; m.money = 0
    elseif kind == "item" and index then
        if bagsFull then return fire("UI_ERROR_MESSAGE", ERR_INV_FULL) end
        if m.max then return fire("UI_ERROR_MESSAGE", ERR_ITEM_MAX_COUNT) end
        taken[#taken + 1] = m.item[1]; m.item = nil
    elseif kind == "delete" and index then drop(inbox, index) end
    fire("MAIL_INBOX_UPDATE")
end
taken = {}
function answerAll() for _ = 1, 200 do if #requests == 0 then return end; answer() end end
function mail(m) inbox[#inbox + 1] = m; return m end

-- Bags: bags[bag][slot] = { id, guid, name, count, soulbound }.
bags, locks, nextGUID = { [0] = {}, {}, {}, {}, {} }, {}, 1
function give(bag, slot, name, count, soulbound)
    local guid = string.format("0x%016X", nextGUID); nextGUID = nextGUID + 1
    bags[bag][slot] = { id = 1000 + nextGUID, guid = guid, name = name, count = count or 1, soulbound = soulbound }
    return guid
end
local function at(loc) return loc and bags[loc.bagID] and bags[loc.bagID][loc.slotIndex] end
function move(fromBag, fromSlot, toBag, toSlot) bags[toBag][toSlot], bags[fromBag][fromSlot] = bags[fromBag][fromSlot], nil end
function sell(bag, slot) bags[bag][slot] = nil end
function itemAt(guid) for b, slots in pairs(bags) do for s, it in pairs(slots) do if it.guid == guid then return it, b, s end end end end
C_Item = {
    GetItemGUID = function(loc) local it = at(loc); return it and it.guid end,
    GetItemLocation = function(guid) local _, b, s = itemAt(guid); if b then return { bagID = b, slotIndex = s } end end,
    IsItemGUIDInInventory = function(guid) return itemAt(guid) ~= nil end,
    GetItemID = function(loc) local it = at(loc); return it and it.id end,
    GetItemIcon = function(loc) local it = at(loc); return it and "icon:" .. it.name end,
    GetStackCount = function(loc) local it = at(loc); return it and it.count or 0 end,
    LockItem = function(loc) local it = at(loc); if it then locks[it.guid] = true; fire("ITEM_LOCK_CHANGED") end end,
    IsBound = function(loc) local it = at(loc); return it and it.soulbound and true or false end,
    GetItemData = function(loc) local it = at(loc); if it then return { isConjured = it.conjured, bindType = it.quest and 4 or 0 } end end,
    GetItemLink = function(loc) local it = at(loc); return it and "[" .. it.name .. "]" end,
    UnlockItem = function(loc) local it = at(loc); if it then locks[it.guid] = nil; fire("ITEM_LOCK_CHANGED") end end,
    IsLocked = function(loc) local it = at(loc); return it and locks[it.guid] or false end,
}
function locked(guid) return locks[guid] == true end
function GetContainerItemInfo(b, s) local it = bags[b][s]; if it then return "icon", it.count, locks[it.guid] end end
function PickupContainerItem(b, s)
    local it = bags[b][s]
    if cursor or not it or locks[it.guid] then return end
    cursor = it.guid; locks[it.guid] = true
end
function ClearCursor() if cursor then locks[cursor] = nil; cursor = nil end end
function CursorHasItem() return cursor and 1 or nil end
function GetCursorInfo() local it = cursor and itemAt(cursor); if it then return "item", it.id, "link" end end
used = {}
function UseContainerItem(b, s) used[#used + 1] = b .. ":" .. s end
function ContainerFrameItemButton_OnClick(button)
    local b, s = this:GetParent():GetID(), this:GetID()
    if button ~= "RightButton" then return PickupContainerItem(b, s) end
    if MailFrame:IsShown() and SendMailFrame:IsShown() and not IsShiftKeyDown() then
        PickupContainerItem(b, s); ClickSendMailItemButton(); ClearCursor()
    else
        UseContainerItem(b, s)
    end
end
local bagFrames, bagButtons = {}, {}
function rightClickBag(b, s)
    bagFrames[b] = bagFrames[b] or CreateFrame("Frame"); bagFrames[b]:SetID(b)
    local key = b .. ":" .. s
    bagButtons[key] = bagButtons[key] or CreateFrame("Button", nil, bagFrames[b]); bagButtons[key]:SetID(s)
    local was = this; this = bagButtons[key]
    ContainerFrameItemButton_OnClick("RightButton")
    this = was
end
clicks = 0
function ClickSendMailItemButton()
    clicks = clicks + 1
    if cursor then
        local it = itemAt(cursor)
        if it.soulbound then return end -- the client refuses; it stays on the cursor
        attached, cursor = cursor, nil
    elseif attached then cursor, attached = attached, nil end
    fire("MAIL_SEND_INFO_UPDATE")
end
function GetSendMailItem() local it = attached and itemAt(attached); if it then return it.name, "icon", it.count end end
function GetSendMailItemLink() local it = attached and itemAt(attached); if it then return "link", it.id end end
sent = {}
function SetSendMailMoney(c) sendMoney = c end
function SetSendMailCOD(c) sendCOD = c end
function SendMail(to, subject, body)
    sent[#sent + 1] = { to = to, subject = subject, body = body, item = GetSendMailItem(), money = sendMoney, cod = sendCOD }
    sendMoney, sendCOD = nil, nil
end
function deliver()
    local letter = sent[#sent]
    if attached then local _, b, s = itemAt(attached); bags[b][s] = nil; locks[attached] = nil; attached = nil end
    fire("MAIL_SEND_SUCCESS")
    step(0) -- the next frame
end
function refuse(err) fire("UI_ERROR_MESSAGE", err); fire("MAIL_FAILED") end
function deliverAll() for _ = 1, 30 do local n = #sent; deliver(); if #sent == n then return end end end

-- ClassicAPI's name completion ("## AutoComplete"): known names starting with the text.
Enum = { AutoCompleteEntryFlag = { InGroup = 1, InGuild = 2, Friend = 4, InteractedWith = 16, Online = 32,
    AccountCharacter = 128 } }
known = {}
C_AutoComplete = { GetAutoCompleteResults = function(text, n)
    local r = {}
    for _, name in ipairs(known) do
        if string.find(string.upper(name), string.upper(text), 1, true) == 1 and #r < n then r[#r + 1] = { name = name } end
    end
    return r
end }

function chatText() return table.concat(chat, "\n") end
function click(w, button) run(w, "OnClick", button or "LeftButton") end
function rightClickRow(i) InboxFrame_Update(); run(_G["MailItem" .. i .. "Button"], "OnClick", "RightButton") end
function leftClickRow(i) InboxFrame_Update(); run(_G["MailItem" .. i .. "Button"], "OnClick", "LeftButton") end
function busy()
    local out = {}
    for _, w in ipairs(widgets) do
        if w ~= MailFrame then for e in pairs(w.events) do out[#out + 1] = e end end
        if w.scripts.OnUpdate then out[#out + 1] = "OnUpdate" end
    end
    table.sort(out)
    return table.concat(out, ",")
end
'''


def load(saved="", setup="", login=True, show=True):
    """Mail loaded over `saved` (Lua that sets MailDB); with `login` the
    player has logged in; with `show` a mailbox is open."""
    lua = wowkit.runtime()
    lua.execute(MOCK)
    lua.execute(setup)
    wowkit.load_addon(lua, ROOT, "Mail", saved=saved or None)
    if login:
        lua.execute('fire("PLAYER_LOGIN")')
    if show:
        lua.execute('fire("MAIL_SHOW"); answerAll()')
    return lua


def slots(lua):
    """The send slots' icons, in order, "" for an empty one."""
    return lua.eval('''(function()
        local out = {}
        for _, w in ipairs(widgets) do
            if w.kind == "Button" and w.parent == SendMailFrame and w.id and w.id > 0 then
                out[w.id] = w.icon and w.icon.shown and w.icon.texture or ""
            end
        end
        return table.concat(out, ",")
    end)()''')
