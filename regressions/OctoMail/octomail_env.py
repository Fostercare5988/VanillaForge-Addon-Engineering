"""The OctoMail regressions on the shared game model (wowkit).

Loads the Script files named in the selected OctoMail.xml, in order. Frames
start hidden here (MailFrame is shown on load, as opening a mailbox does), and
XML frames are made on first use. Native widget behaviour, real event payloads
and the server's mail handling remain in-game checks.
"""
from pathlib import Path
import os

import wowkit

ROOT = Path(os.environ["VANILLAFORGE_ADDON_ROOT"])
SCRIPTS = wowkit.xml_scripts(ROOT, "OctoMail.xml")

BASE = r'''
CLASSIC_API_VERSION, SUPERWOW_VERSION = 11711, "2.2"
messages, tickers = chat, timers
local function widget(name) local w = newWidget("Frame", name); w.shown = false; return w end

-- Edit boxes answer "" when empty; the sizes are what OctoMail's layout reads.
function Widget:GetText() return self.text or "" end
function Widget:GetHeight() return 14 end
function Widget:GetWidth() return 37 end
function Widget:GetStringWidth() return 40 end
function Widget:GetID() return self.id or 1 end
function Widget:GetFontString() self.fontString = self.fontString or widget(); return self.fontString end
function Widget:GetRegions() local r = {} for i = 1, 10 do r[i] = widget() end return unpack(r) end
function CreateFrame(_, name) return widget(name) end

local AUTO = { "^Mail", "^OctoMail%u", "^SendMail", "^Inbox", "^OpenMail", "^Stationery", "^MoneyReceived" }
setmetatable(_G, { __index = function(_, k)
    if type(k) ~= "string" or string.find(k, "_") then return nil end
    for _, p in ipairs(AUTO) do
        if string.find(k, p) then return widget(k) end
    end
end })

WorldFrame, GameTooltip, TradeFrame = widget("WorldFrame"), widget("GameTooltip"), widget("TradeFrame")
UIPanelWindows = { MailFrame = { area = "left", pushable = 0 } }
NORMAL_FONT_COLOR = { r = 1, g = 0.82, b = 0 }
GRAY_FONT_COLOR = { r = 0.5, g = 0.5, b = 0.5 }
TOOLTIP_DEFAULT_COLOR, TOOLTIP_DEFAULT_BACKGROUND_COLOR = NORMAL_FONT_COLOR, NORMAL_FONT_COLOR
MAIL_AUTOCOMPLETE_MAX_BUTTONS = 5
INBOXITEMS_TO_DISPLAY = 7
COD_AMOUNT, AMOUNT_TO_SEND = "C.O.D. Amount:", "Amount to Send:"
AUCTION_SOLD_MAIL_SUBJECT = "Auction successful: %s"
AUCTION_REMOVED_MAIL_SUBJECT = "Auction cancelled: %s"
AUCTION_EXPIRED_MAIL_SUBJECT = "Auction expired: %s"
AUCTION_WON_MAIL_SUBJECT = "Auction won: %s"
AUCTION_OUTBID_MAIL_SUBJECT = "Outbid on %s"
OPENMAIL, INBOX, EMPTY, NO_ATTACHMENTS, ERROR_CAPS = "Open All", "Inbox", "Empty", "No attachments", "Error"

now = 1760000000
function time(t) return now end
function GetCVar() return "OctoWoW" end
function GetRealmName() return "OctoWoW" end
function UnitFactionGroup() return "Horde" end
function UnitName() return "Me" end
function GetAddOnMetadata() return "1.5.0" end
function IsAddOnLoaded() return nil end
function GetMoney() return 10000000 end
function GetSendMailPrice() return 30 end
function MoneyInputFrame_GetCopper(f) return f.copper or 0 end
function MoneyInputFrame_ResetMoney(f) f.copper = 0 end
function MoneyFrame_Update() end
function PanelTemplates_SetNumTabs() end
function PanelTemplates_SetTab() end
function UIDropDownMenu_SetText() end
function UIDropDownMenu_Initialize() end
function UIDropDownMenu_SetWidth() end
function UIDropDownMenu_AddButton() end
function CloseDropDownMenus() end
function PlaySound() end
function IsShiftKeyDown() end
function IsControlKeyDown() end
function IsAltKeyDown() end
checks = 0
function CheckInbox() checks = checks + 1 end
MAX_COD_AMOUNT, COPPER_PER_GOLD = 10000, 10000
SEND_MONEY_CONFIRMATION, ACCEPT, CANCEL = "Send money to %s?", "Accept", "Cancel"
StaticPopupDialogs, popups = {}, {}
function StaticPopup_Show(which, text) table.insert(popups, which) end
function StaticPopup_Hide() end
function GetNumFriends() return 0 end
function GetNumGuildMembers() return 0 end

inbox = {}
function GetInboxNumItems() return table.getn(inbox) end
function GetInboxHeaderInfo(i)
    local m = inbox[i]
    if not m then return end
    return nil, nil, m.sender, m.subject or "", m.money or 0, m.cod or 0, 3, m.item, m.read, m.returned, nil, m.canReply, nil
end
function GetInboxItem() return nil end
function GetInboxText() end
function TakeInboxMoney() end
function TakeInboxItem() end
function DeleteInboxItem() end
function InboxFrame_Update() end
function InboxFrame_OnClick() end
function InboxFrameItem_OnEnter() end
function OpenMail_Reply() end
function OpenMailFrame_OnHide() end
function MailFrameTab_OnClick() end
function SendMailFrame_Update() end
function SendMailFrame_CanSend() end
function SendMailRadioButton_OnClick() end
function SendMailMailButton_OnClick() end

-- Bags, cursor and the send slot. An item on the cursor or in the send slot
-- is locked, as the client locks it; a locked item cannot be picked up.
attached, cursor = nil, nil
bag, locks = {}, {}
local function key(b, s) return b .. ":" .. s end
function GetContainerItemInfo(b, s) local it = bag[key(b, s)]; if it then return it.texture, it.count or 1, locks[key(b, s)] and 1 or nil, 1, nil end end
function PickupContainerItem(b, s) if locks[key(b, s)] then return end cursor = { b, s }; locks[key(b, s)] = true end
function ClearCursor() if cursor then locks[key(cursor[1], cursor[2])] = nil; cursor = nil end end
function CursorHasItem() return cursor and 1 or nil end
function SplitContainerItem() end
function UseContainerItem() end
function ClickSendMailItemButton() if cursor then attached, cursor = cursor, nil elseif attached then locks[key(attached[1], attached[2])] = nil; attached = nil end end
function GetSendMailItem() if attached then return "Linen Cloth", "tex", 1 end end
-- ClassicAPI's client-side lock (API.md, C_Item.LockItem / UnlockItem).
C_Item = {
    LockItem = function(loc) locks[key(loc.bagID, loc.slotIndex)] = true end,
    UnlockItem = function(loc) locks[key(loc.bagID, loc.slotIndex)] = nil end,
}
-- ClassicAPI's name completion (API.md, AutoComplete): the names in `known`
-- that start with the text, case ignored.
Enum = { AutoCompleteEntryFlag = { InGroup = 1, InGuild = 2, Friend = 4, Bnet = 8, InteractedWith = 16, Online = 32 } }
known = {}
C_AutoComplete = { GetAutoCompleteResults = function(text, n, cursorPosition, allowFullMatch, include, exclude)
    autocompleteInclude = include
    local r = {}
    for _, name in ipairs(known) do
        local up, typed = string.upper(name), string.upper(text)
        if string.find(up, typed, 1, true) == 1 and (allowFullMatch or up ~= typed) and (n <= 0 or #r < n) then
            r[#r + 1] = { name = name, priority = 0, bnetID = 0 }
        end
    end
    return r
end }
sent = {}
function SendMail(to, subject, body)
    table.insert(sent, { to = to, subject = subject, cod = codAmount, money = moneyAmount })
    if attached then locks[key(attached[1], attached[2])] = nil end
    attached, codAmount, moneyAmount = nil, nil, nil
end
function SetSendMailCOD(a) codAmount = a end
function SetSendMailMoney(a) moneyAmount = a end

function frame() run(OctoMailFrame, "OnUpdate") end
'''


def load(prelude=""):
    """Return a runtime with OctoMail loaded and ADDON_LOADED/PLAYER_LOGIN fired."""
    lua = wowkit.runtime()
    lua.execute(BASE)
    if prelude:
        lua.execute(prelude)
    wowkit.load_files(lua, ROOT, SCRIPTS, "OctoMail")
    if lua.eval('rawget(_G, "OctoMailFrame") ~= nil'):
        lua.execute('fire("ADDON_LOADED", "OctoMail"); fire("PLAYER_LOGIN"); MailFrame:Show()')
    return lua
