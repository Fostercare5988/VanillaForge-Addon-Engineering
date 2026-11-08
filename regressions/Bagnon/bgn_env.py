"""The Bagnon regressions on the shared game model (wowkit), 2026-10-30.

Loads the real Utility, Frame and Item files against widget mocks. The XML
frames (Bagnon, Banknon and their children) are replaced by permissive stubs, so
these tests prove Lua logic and call counts, not layout, drawing or input.
"""
import os
from pathlib import Path
import wowkit

ROOT = Path(os.environ["VANILLAFORGE_ADDON_ROOT"])

MOCK = r'''
calls = {}
function count(name, n) calls[name] = (calls[name] or 0) + (n or 1) end
Bagnon_EngineReady = 1
KEYRING_CONTAINER = -2
BACKPACK_TOOLTIP = "Backpack"

-- XML stand-ins start hidden.
function widget(name, id)
    local w = newWidget("Frame", name)
    w.shown, w.id = false, id or 0
    return w
end
function Widget:SetVertexColor(r, g, b) self.color = { r, g, b } end
function CreateFrame(_, name) return widget(name) end
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

FILES = {"utility": "core/Utility.lua", "database": "database/database.lua",
         "frame": "core/Frame.lua", "item": "core/Item.lua"}


def load(*names):
    lua = wowkit.runtime()
    lua.execute(MOCK)
    lua.execute("BagnonSets = { showFreeSlots = 1, qualityBorders = 1, Bagnon = { bags = {-2, 0, 1, 2, 3, 4} } }")
    for name in names or ("utility", "frame", "item"):
        source = (ROOT / FILES[name]).read_text("utf-8-sig")
        lua.execute(source, name)
    return lua
