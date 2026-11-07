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
function ClearCursor() end
function CheckInbox() end
MAX_COD_AMOUNT, COPPER_PER_GOLD = 10000, 10000
SEND_MONEY_CONFIRMATION, ACCEPT, CANCEL = "Send money to %s?", "Accept", "Cancel"
StaticPopupDialogs, popups = {}, {}
-- ClassicAPI: coin icons in the real client; plain letters here.
function GetCoinTextureString(copper)
    local g, s, c = math.floor(copper / 10000), math.floor(copper % 10000 / 100), copper % 100
    local t = {}
    if g > 0 then t[#t + 1] = g .. "g" end
    if s > 0 then t[#t + 1] = s .. "s" end
    if c > 0 or #t == 0 then t[#t + 1] = c .. "c" end
    return table.concat(t, " ")
end
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

attached = nil
bag = {}
function GetContainerItemInfo(b, s) local it = bag[b .. ":" .. s]; if it then return it.texture, it.count or 1, nil, 1, nil end end
function PickupContainerItem(b, s) cursor = { b, s } end
function SplitContainerItem() end
function UseContainerItem() end
function ClickSendMailItemButton() if cursor then attached, cursor = cursor, nil elseif attached then attached = nil end end
function GetSendMailItem() if attached then return "Linen Cloth", "tex", 1 end end
sent = {}
function SendMail(to, subject, body) table.insert(sent, { to = to, subject = subject, cod = codAmount, money = moneyAmount }); attached, codAmount, moneyAmount = nil, nil, nil end
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
