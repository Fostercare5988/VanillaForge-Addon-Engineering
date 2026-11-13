"""The GearRack regressions on the shared game model (wowkit).

Loads selected files of the addon at VANILLAFORGE_ADDON_ROOT with widget mocks.
Every frame the addon's XML names (template children included) exists as a mock
widget, so Lua that styles or drives XML frames runs as it would after load.
ClassicAPI's file varargs are supplied: each file gets ("GearRack", ns).

The mocks record colors, parents and frame levels. They do not prove how the
client draws a texture, which font a button uses or how a window looks.
"""
from pathlib import Path
import os
import wowkit

ROOT = Path(os.environ["VANILLAFORGE_ADDON_ROOT"])
SRC = ROOT / "src"

MOCK = r'''
messages = chat
function GetAddOnMetadata(addon, field) if field == "Version" then return "test" end end
CLASSIC_API_VERSION, SUPERWOW_VERSION = 11805, "2.2"
function GetNampowerVersion() return 4, 6, 2 end
function GetCastInfo() end
function GetSpellIdCooldown() end

-- Frame levels follow the parent; heights start at 20; colours are kept apart.
local make = newWidget
function newWidget(kind, name, parent)
    local w = make(kind, name, parent)
    w.height, w.level, w.calls = 20, parent and (parent.level + 1) or 1, {}
    return w
end
UIParent.level = 1
function Widget:SetParent(p) self.parent = p; self.level = p.level + 1 end
function Widget:SetFrameLevel(l) self.level = l end
function Widget:GetFrameLevel() return self.level end
function Widget:SetHitRectInsets(l, r, t, b) self.hitInsets = { l, r, t, b } end
function Widget:SetTextColor(r, g, b) self.textColor = { r, g, b } end
function Widget:SetHighlightTextColor(r, g, b) self.highlightColor = { r, g, b } end
function Widget:SetDisabledTextColor(r, g, b) self.disabledColor = { r, g, b } end
function Widget:CreateTexture(name, layer) local t = newWidget("Texture", name, self); t.layer = layer; return t end
function Widget:CreateFontString(name, layer) local f = newWidget("FontString", name, self); f.layer = layer; return f end
function Widget:SetInventoryItem(...) table.insert(self.calls, "SetInventoryItem") end
'''


# Children of the client templates GearRack inherits.
CLIENT_TEMPLATES = {
    "UICheckButtonTemplate": ["$parentText"],
    "ActionButtonTemplate": ["$parentIcon", "$parentCount", "$parentHotKey", "$parentName",
                             "$parentCooldown", "$parentBorder", "$parentNormalTexture", "$parentFlash"],
    "FauxScrollFrameTemplate": ["$parentScrollBar", "$parentScrollChildFrame"],
    "UIPanelScrollFrameTemplate": ["$parentScrollBar"],
}


class Env:
    def __init__(self, files):
        self.lua = wowkit.runtime()
        self.lua.execute(MOCK)
        make = self.lua.globals().newWidget
        for name, kind in wowkit.xml_frames(sorted(SRC.glob("*.xml")), CLIENT_TEMPLATES):
            if self.lua.globals()[name] is None:
                make(kind, name)
        self.ns = self.lua.table()
        loader = self.lua.eval('function(src, name, ns) local f = assert(loadstring(src, name)); return f("GearRack", ns) end')
        for f in files:
            loader((SRC / f).read_text(encoding="utf-8"), f, self.ns)

    def run(self, code):
        return self.lua.execute(code)

    def eval(self, code):
        return self.lua.eval(code)


def text(name):
    return (SRC / name).read_text(encoding="utf-8")


# Every Lua file in TOC order, for a whole-addon login.
ALL = ["Bootstrap.lua", "ForgeUI.lua", "Core.lua", "Constants.lua", "Events.lua", "Equipment.lua",
       "PoisonSwap.lua", "Trinkets.lua", "TrinketOptions.lua", "TrinketQueues.lua", "Skin.lua",
       "Navigation.lua", "Settings.lua", "BarLayout.lua", "SetMacros.lua", "Minimap.lua"]

# The client a logged-in Rogue with empty bags sees. Errors that reach the error
# handler are kept in `errors`. After the files load, any other capitalised global
# is inert: it can be called or indexed and answers nil (missing[name] records it).
CLIENT = r'''
errors, missing = {}, {}
function geterrorhandler() return function(e) errors[#errors + 1] = tostring(e) end end
function UnitName() return "Claude" end
function GetRealmName() return "Y'Shaarj" end
function UnitClass() return "Rogue", "ROGUE" end
function GetInventorySlotInfo() return 1, "Interface\\PaperDoll\\Empty" end
function GetInventoryItemCooldown() return 0, 0, 0 end
function GetContainerItemCooldown() return 0, 0, 0 end
function GetContainerNumSlots() return 0 end
function GetBindingText(k) return k end
function GetBindingAction() return "" end
function SetBinding() return 1 end
function GetCurrentBindingSet() return 1 end
function GetNumMacroIcons() return 0 end
function GetShapeshiftForm() return 0 end
function GetNumShapeshiftForms() return 0 end
function GetNetStats() return 0, 0, 50 end
function FauxScrollFrame_GetOffset() return 0 end
function SecondsToTimeAbbrev(s) return s .. "s" end
function cos(d) return math.cos(math.rad(d)) end
function sin(d) return math.sin(math.rad(d)) end
C_PlayerInfo = { CanUseItem = function() return true end }
SHOW_COMBAT_TEXT = "0"
function Widget:GetNormalTexture() self.nt = self.nt or newWidget("Texture") return self.nt end
function Widget:GetPushedTexture() self.pt = self.pt or newWidget("Texture") return self.pt end
function Widget:GetCountdownFontString() self.cf = self.cf or newWidget("FontString") return self.cf end
for _, n in ipairs({ "Minimap", "PaperDollFrame", "CharacterAmmoSlotCount", "GameTooltip", "UIErrorsFrame",
        "MerchantFrame", "ChatFrameEditBox", "GossipFrameNpcNameText" }) do
    _G[n] = newWidget("Frame", n)
end
for _, n in ipairs({ "Ammo", "Head", "Neck", "Shoulder", "Shirt", "Chest", "Waist", "Legs", "Feet", "Wrist",
        "Hands", "Finger0", "Finger1", "Trinket0", "Trinket1", "Back", "MainHand", "SecondaryHand", "Ranged", "Tabard" }) do
    _G["Character" .. n .. "Slot"] = newWidget("Button", "Character" .. n .. "Slot")
end
local function inertTable() return setmetatable({}, { __index = function() return function() end end }) end
C_Item, C_Container, C_Spell = inertTable(), inertTable(), inertTable()
-- The fill form: slot ids into the table, then the token and their count.
C_UnitAuras = { GetAuraSlots = function() return nil, 0 end }
'''

# Installed after the files load, so `X = X or {}` still makes the addon's own tables.
INERT = r'''
local inert = setmetatable({}, { __call = function() end, __index = function() return function() end end })
setmetatable(_G, { __index = function(_, k)
    if type(k) == "string" and string.find(k, "^%u") then missing[k] = true return inert end
end })
'''


def logged_in(client=""):
    """The whole addon after PLAYER_LOGIN; `client` (Lua) adds to or replaces CLIENT first."""
    env = Env([])
    env.run(CLIENT + client)
    loader = env.lua.eval('function(src, name, ns) local f = assert(loadstring(src, name)); return f("GearRack", ns) end')
    for f in ALL:
        loader(text(f), f, env.ns)
    env.run(INERT)
    # The OnEvent scripts of GearRack's three event frames (Equipment.xml, Sets.xml).
    env.run('''
        GearRackUIFrame:SetScript("OnEvent", function() GearRackUI_OnEvent(event) end)
        GearRackEngineFrame:SetScript("OnEvent", function() GearRackEngine.OnEvent() end)
        GearRackUI_RegisterFrame:SetScript("OnEvent", function() GearRackUI_RegisterFrame_OnEvent(event) end)
        this = GearRackUIFrame; GearRackUI_OnLoad(); fire("PLAYER_LOGIN")''')
    return env
