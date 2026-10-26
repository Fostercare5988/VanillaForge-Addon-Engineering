"""Reproductions for the 2026-10-20 AutoLazy audit (.private/audit-AutoLazy-2026-10-20.md).

Loads the selected AutoLazy.lua under Lua 5.1 with minimal mocks and drives
START_LOOT_ROLL. The zone strings are the stock 1.12 names; OctoWoW's own
zone text for AQ40 and the Dark Portal area is an in-game check.
"""
from pathlib import Path
import os
import unittest
from lupa.lua51 import LuaRuntime

ROOT = Path(os.environ["VANILLAFORGE_ADDON_ROOT"])
SOURCE = (ROOT / "AutoLazy.lua").read_text("utf-8-sig")

BASE = r'''
CLASSIC_API_VERSION = 11707
function table.wipe(t) for k in pairs(t) do t[k] = nil end return t end
getglobal = function(n) return _G[n] end
SlashCmdList = {}
DEFAULT_CHAT_FRAME = { AddMessage = function() end }
C_Timer = { After = function() end, NewTimer = function() return { Cancel = function() end } end }
zone = { real = "", zone = "", sub = "", minimap = "", instance = "Kalimdor" }
function GetInstanceInfo() return zone.instance, "none" end
function GetRealZoneText() return zone.real end
function GetZoneText() return zone.zone end
function GetSubZoneText() return zone.sub end
function GetMinimapZoneText() return zone.minimap end
rollItem, rolls = nil, {}
function GetLootRollItemID() return rollItem end
function RollOnLoot(id, kind) table.insert(rolls, kind) end
shift = { stock = nil, left = nil }
function IsShiftKeyDown() return shift.stock end
function IsLeftShiftKeyDown() return shift.left end
function IsRightShiftKeyDown() return nil end
function UnitGUID(unit) if unit == "npc" then return "0xF130000001000001" end end
GossipFrame = { IsShown = function() return true end }
active, options, selected = {}, {}, {}
C_GossipInfo = {
    GetActiveQuests = function() return active end,
    GetAvailableQuests = function() return {} end,
    GetOptions = function() return options end,
    SelectActiveQuest = function(id) table.insert(selected, "quest" .. id) end,
    SelectOption = function(id) table.insert(selected, "option" .. id) end,
}
C_Item = { GetItemCount = function() return 0 end }
local frames = {}
function CreateFrame(_, name)
    local f = { scripts = {} }
    function f:RegisterEvent() end
    function f:SetScript(k, fn) self.scripts[k] = fn end
    if name then _G[name] = f end
    return f
end
function fire(ev, a1, a2)
    AutoLazy_EventFrame.scripts.OnEvent(AutoLazy_EventFrame, ev, a1, a2)
end
'''


def load():
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(BASE)
    lua.execute(SOURCE)
    lua.execute("AutoLazy.UpdateActionButton = function() end; AutoLazy.ApplySystemIconToggles = function() end")
    lua.execute('fire("ADDON_LOADED", "AutoLazy")')
    return lua


def roll_in(lua, real, sub, item):
    lua.execute('zone.real, zone.zone, zone.sub, zone.minimap = %r, %r, %r, %r' % (real, real, sub, sub))
    lua.execute('rolls = {}; rollItem = %d; fire("ZONE_CHANGED_NEW_AREA"); fire("START_LOOT_ROLL", 1)' % item)
    return lua.eval("#rolls")


class AuditReproductions(unittest.TestCase):
    def test_control_listed_item_rolls_in_its_dungeon(self):
        """Control: a Stone Scarab in Ruins of Ahn'Qiraj follows its default Need rule."""
        self.assertEqual(roll_in(load(), "Ruins of Ahn'Qiraj", "", 20858), 1)

    def test_control_instance_name_identifies_the_dungeon(self):
        """Control: the GetInstanceInfo (Map.dbc) name alone identifies the dungeon."""
        lua = load()
        lua.execute('zone.instance = "Zul\'Gurub"')
        self.assertEqual(roll_in(lua, "Unknown", "", 19707), 1)

    def test_p2_aq40_is_not_ruins_of_ahnqiraj(self):
        """P2-1: "Ahn'Qiraj" (AQ40) is a substring of "ruins of ahn'qiraj", so AQ20 rules roll in AQ40."""
        self.assertEqual(roll_in(load(), "Ahn'Qiraj", "", 20858), 0)

    def test_p2_dark_portal_subzone_is_not_black_morass(self):
        """P2-1: subzone "The Dark Portal" (Blasted Lands) is inside the alias "opening of the dark portal"."""
        self.assertEqual(roll_in(load(), "Blasted Lands", "The Dark Portal", 50203), 0)

    def test_p3_stuck_stock_shift_does_not_turn_in(self):
        """P3-1: stock IsShiftKeyDown can stay down after Alt-Tab; the reconciled L/R keys are up."""
        lua = load()
        lua.execute('''
            shift.stock, shift.left = 1, nil
            active = { { questID = 7, title = "A Quest", isComplete = true } }
            fire("GOSSIP_SHOW")
        ''')
        self.assertEqual(lua.eval("#selected"), 0)

    def test_control_held_shift_turns_in(self):
        """Control: a really held Shift still turns in the single completed quest."""
        lua = load()
        lua.execute('''
            shift.stock, shift.left = 1, 1
            active = { { questID = 7, title = "A Quest", isComplete = true } }
            fire("GOSSIP_SHOW")
        ''')
        self.assertEqual(lua.eval("selected[1]"), "quest7")

    def test_p3_gossip_opener_is_selected_once_per_npc(self):
        """P3-2: an opener that returns to the same menu was selected on every GOSSIP_SHOW while Shift was held."""
        lua = load()
        lua.execute('''
            shift.stock, shift.left = 1, 1
            options = { { gossipOptionID = 3, name = "I want to turn in some items." } }
            for i = 1, 3 do fire("GOSSIP_SHOW") end
        ''')
        self.assertEqual(lua.eval("#selected"), 1)


if __name__ == "__main__":
    unittest.main()
