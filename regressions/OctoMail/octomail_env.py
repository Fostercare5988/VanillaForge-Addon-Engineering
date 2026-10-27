"""Shared Lua 5.1 environment for the OctoMail regressions.

Loads the Script files named in the selected OctoMail.xml, in order, with
generic widget mocks. Lua 5.0 `for k, v in t do` loops are rewritten to
`pairs(t)` because lupa runs Lua 5.1. Native widget behavior, real event
payloads and the server's mail handling remain in-game checks.
"""
from pathlib import Path
import os
import re
from lupa.lua51 import LuaRuntime

ROOT = Path(os.environ["VANILLAFORGE_ADDON_ROOT"])
XML = (ROOT / "OctoMail.xml").read_text("utf-8-sig")
SCRIPTS = re.findall(r'<Script file="([^"]+)"', XML)

_LUA50_FOR = re.compile(r"\bin\s+(?!pairs\b|ipairs\b)([^\n]+?)\s+do\b")


def lua51(source):
    return _LUA50_FOR.sub(r"in pairs(\1) do", source)


BASE = r'''
CLASSIC_API_VERSION, SUPERWOW_VERSION = 11711, "2.2"
function table.setn() end
mod = math.mod or math.fmod
getn = table.getn
tinsert = table.insert
floor = math.floor
messages = {}
DEFAULT_CHAT_FRAME = { AddMessage = function(_, m) table.insert(messages, m) end }

local Widget = {}
local WidgetMeta = { __index = function(t, k)
    if Widget[k] then return Widget[k] end
    if string.find(k, "^%u") then return function() end end
end }
local function widget(name)
    local w = setmetatable({ name = name, scripts = {}, shown = false, enabled = true }, WidgetMeta)
    if name then rawset(_G, name, w) end
    return w
end
newWidget = widget
function Widget:GetName() return self.name end
function Widget:Show() self.shown = true end
function Widget:Hide() self.shown = false end
function Widget:IsVisible() return self.shown end
function Widget:IsShown() return self.shown end
function Widget:Enable() self.enabled = true end
function Widget:Disable() self.enabled = false end
function Widget:IsEnabled() return self.enabled and 1 or nil end
function Widget:SetText(t) self.text = t end
function Widget:GetText() return self.text or "" end
function Widget:SetChecked(v) self.checked = v end
function Widget:GetChecked() return self.checked end
function Widget:SetScript(k, f) self.scripts[k] = f end
function Widget:GetScript(k) return self.scripts[k] end
function Widget:GetHeight() return 14 end
function Widget:GetWidth() return 37 end
function Widget:GetStringWidth() return 40 end
function Widget:GetValue() return self.value or 0 end
function Widget:SetValue(v) self.value = v end
function Widget:GetMinMaxValues() return 0, 0 end
function Widget:GetID() return self.id or 1 end
function Widget:GetFontString() self.fs = self.fs or widget(); return self.fs end
function Widget:GetRegions() local r = {} for i = 1, 10 do r[i] = widget() end return unpack(r) end
function Widget:CreateTexture(name) return widget(name) end
function Widget:CreateFontString(name) return widget(name) end
function Widget:RegisterEvent(e) self.events = self.events or {}; self.events[e] = true end

local AUTO = { "^Mail", "^OctoMail%u", "^SendMail", "^Inbox", "^OpenMail", "^Stationery", "^MoneyReceived" }
setmetatable(_G, { __index = function(_, k)
    if type(k) ~= "string" or string.find(k, "_") then return nil end
    for _, p in ipairs(AUTO) do
        if string.find(k, p) then return widget(k) end
    end
end })

function CreateFrame(_, name) return widget(name) end
UIParent, WorldFrame, GameTooltip, TradeFrame = widget("UIParent"), widget("WorldFrame"), widget("GameTooltip"), widget("TradeFrame")
UISpecialFrames, SlashCmdList = {}, {}
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
date = os.date
function GetTime() return 100 end
function GetLocale() return "enUS" end
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
tickers = {}
C_Timer = { NewTicker = function(seconds, fn)
    local h = { seconds = seconds, fn = fn }
    function h:Cancel() self.cancelled = true end
    table.insert(tickers, h)
    return h
end }
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

function fire(e, a1)
    local f = OctoMailFrame
    if f.events and f.events[e] then
        event, arg1 = e, a1
        f.scripts.OnEvent()
    end
end
function frame() local f = OctoMailFrame.scripts.OnUpdate; if f then f() end end
'''


def load(prelude=""):
    """Return a runtime with OctoMail loaded and ADDON_LOADED/PLAYER_LOGIN fired."""
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(BASE)
    if prelude:
        lua.execute(prelude)
    for name in SCRIPTS:
        lua.execute(lua51((ROOT / name).read_text("utf-8-sig")))
    if lua.eval("rawget(_G, \"OctoMailFrame\") ~= nil and OctoMailFrame.events ~= nil"):
        lua.execute('fire("ADDON_LOADED", "OctoMail"); fire("PLAYER_LOGIN"); MailFrame:Show()')
    return lua
