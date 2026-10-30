"""Shared Lua 5.1 environment for the Bagnon regressions (2026-10-30).

Loads the real Utility, Frame and Item files against widget mocks. The XML
frames (Bagnon, Banknon and their children) are replaced by permissive stubs, so
these tests prove Lua logic and call counts, not layout, drawing or input.
"""
import os
from pathlib import Path
from lupa.lua51 import LuaRuntime

ROOT = Path(os.environ["VANILLAFORGE_ADDON_ROOT"])

MOCK = r'''
calls = {}
function count(name, n) calls[name] = (calls[name] or 0) + (n or 1) end
Bagnon_EngineReady = 1
KEYRING_CONTAINER = -2
BACKPACK_TOOLTIP = "Backpack"
function format(...) return string.format(...) end
tinsert = table.insert
UISpecialFrames = {}

-- Permissive widget: every method exists, SetText/GetText/SetPoint are recorded.
widgets = {}
function widget(name, id)
    local w = { name = name, id = id or 0, points = 0 }
    function w:GetName() return self.name end
    function w:GetID() return self.id end
    function w:SetID(i) self.id = i end
    function w:SetText(t) self.text = t end
    function w:GetText() return self.text end
    function w:SetPoint() self.points = self.points + 1 end
    function w:IsShown() return self.shown and true or false end
    function w:IsVisible() return self.shown and true or false end
    function w:Show() self.shown = true end
    function w:Hide() self.shown = false end
    function w:GetParent() return self.parent end
    function w:SetParent(p) self.parent = p end
    function w:SetVertexColor(r, g, b) self.color = { r, g, b } end
    function w:SetBackdropBorderColor() end
    function w:GetAlpha() return 1 end
    setmetatable(w, { __index = function(_, key)
        if string.find(key, "^[A-Z]") then return function() end end
    end })
    if name then _G[name] = w end
    return w
end
function getglobal(n) return _G[n] end
function CreateFrame(_, name) return widget(name) end
function hooksecurefunc() end
C_Timer = { NewTimer = function() return { Cancel = function() end } end,
            NewTicker = function() return { Cancel = function() end } end }
UnitName = function() return "Tester" end
function GetRealmName() return "Realm" end
BagnonForeverData = { Realm = { Alt = {
    [0] = { s = "16,0,", [1] = "6948", [5] = "2589,20" },
    [2] = { s = "8,5,21340:0:0:0", [1] = "2589,20" } } } }
GetAddOnInfo = function() return "Bagnon", "", "", 1 end

-- Containers: ids 0..4, bag 2 is a soul bag, bag 3 a herb bag.
bagSlots = { [0] = 16, [1] = 16, [2] = 8, [3] = 6, [4] = 0 }
bagFree = { [0] = 3, [1] = 0, [2] = 5, [3] = 2 }
bagFamily = { [2] = 4, [3] = 32 }
bagLinks = { [1] = "|cff9d9d9d|Hitem:4496:0:0:0|h[Small Brown Pouch]|h|r",
             [2] = "|cff9d9d9d|Hitem:21340:0:0:0|h[Soul Pouch]|h|r",
             [3] = "|cff9d9d9d|Hitem:22249:0:0:0|h[Herb Bag]|h|r" }
function GetContainerNumSlots(b) return bagSlots[b] or 0 end
function ContainerIDToInventoryID(b) return 19 + b end
function GetInventoryItemLink(_, inv) return bagLinks[inv - 19] end
itemTypes = { [4496] = { "Container", "Bag" }, [21340] = { "Container", "Soul Bag" },
              [22249] = { "Container", "Herb Bag" } }
function GetItemInfo(id)
    count("GetItemInfo")
    id = tonumber(id) or tonumber(string.match(tostring(id), "item:(%d+)"))
    local t = itemTypes[id]
    if t then return "Name", "link", 1, 1, t[1], t[2] end
end
C_Item = { GetItemFamily = function(item)
    count("GetItemFamily")
    local id = tonumber(item) or tonumber(string.match(tostring(item), "item:(%d+)"))
    return ({ [21340] = 4, [22249] = 32, [4496] = 0 })[id] or 0
end }
C_Container = {
    GetContainerNumFreeSlots = function(b) count("GetContainerNumFreeSlots"); return bagFree[b] or 0, bagFamily[b] or 0 end,
    CalculateTotalNumberOfFreeBagSlots = function()
        local n = 0
        for b = 0, 4 do if (bagFamily[b] or 0) == 0 then n = n + (bagFree[b] or 0) end end
        return n
    end,
    GetContainerItemID = function() return nil end,
}
function GetItemQualityColor() return 1, 1, 1 end
function SetItemButtonDesaturated() end
SPELL = nil
'''

FILES = {"utility": "core/Utility.lua", "localization": "localization.lua", "database": "database/database.lua",
         "frame": "core/Frame.lua", "item": "core/Item.lua"}


def load(*names):
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(MOCK)
    lua.execute("BagnonSets = { showFreeSlots = 1, qualityBorders = 1, Bagnon = { bags = {-2, 0, 1, 2, 3, 4} } }")
    for name in names or ("localization", "utility", "frame", "item"):
        source = (ROOT / FILES[name]).read_text("utf-8-sig")
        lua.execute(source, name)
    return lua
