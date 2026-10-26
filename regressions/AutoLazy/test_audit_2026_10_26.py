"""Reproductions for the 2026-10-26 AutoLazy audit (.private/audit-AutoLazy-2026-10-26.md).

Quest and loot tests load AutoLazy.lua; tray tests load AutoLazy_MinimapTray.lua
with mock frames, a frame-stepped C_Timer and a debugprofilestop that advances
0.5 ms per call, so "work in one tick" can be counted. Frame time itself is an
in-game check (/lag).
"""
from pathlib import Path
import os
import unittest
from lupa.lua51 import LuaRuntime

ROOT = Path(os.environ["VANILLAFORGE_ADDON_ROOT"])
CORE = (ROOT / "AutoLazy.lua").read_text("utf-8-sig")
TRAY = (ROOT / "AutoLazy_MinimapTray.lua").read_text("utf-8-sig")

CORE_MOCKS = r'''
CLASSIC_API_VERSION = 11707
function table.wipe(t) for k in pairs(t) do t[k] = nil end return t end
getglobal = function(n) return _G[n] end
SlashCmdList = {}
DEFAULT_CHAT_FRAME = { AddMessage = function() end }
C_Timer = { After = function() end, NewTimer = function() return { Cancel = function() end } end }
function GetInstanceInfo() return "Kalimdor", "none" end
function GetRealZoneText() return "" end
function GetLootRollItemID() end
shift = false
function IsLeftShiftKeyDown() return shift end
function IsRightShiftKeyDown() return nil end
npc = "0xF130000001000001"
function UnitGUID(unit) if unit == "npc" then return npc end end
GossipFrame = { IsShown = function() return true end }
active, available, options, selected, looted = {}, {}, {}, {}, {}
C_GossipInfo = {
    GetActiveQuests = function() return active end,
    GetAvailableQuests = function() return available end,
    GetOptions = function() return options end,
    SelectActiveQuest = function(id) table.insert(selected, "quest" .. id) end,
    SelectAvailableQuest = function(id) table.insert(selected, "avail" .. id) end,
    SelectOption = function(id) table.insert(selected, "option" .. id) end,
}
C_Item = { GetItemCount = function() return 0 end }
function LootSlot(slot) table.insert(looted, slot) end
function StaticPopup_Hide() end
title = "Some Repeatable"
function GetTitleText() return title end
function GetNumQuestChoices() return 0 end
function GetQuestReward() end
function IsQuestCompletable() return 1 end
function CompleteQuest() end
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

TRAY_MOCKS = r'''
function table.wipe(t) for k in pairs(t) do t[k] = nil end return t end
getglobal = function(n) return _G[n] end
UISpecialFrames, tests = {}, 0
local now, clockMs, queue = 0, 0, {}
function debugprofilestop() clockMs = clockMs + 0.5; return clockMs end
C_Timer = { After = function(d, fn) table.insert(queue, { at = now + d, fn = fn }) end }
function tick()
    now = now + 0.02
    local due, rest = {}, {}
    for _, t in ipairs(queue) do table.insert(t.at <= now and due or rest, t) end
    queue = rest
    for _, t in ipairs(due) do t.fn() end
end
function settle() for i = 1, 2000 do tick(); if #queue == 0 then return end end end
local noop = function() end
local methods = {
    -- rawget: a nil field must not fall through to the method table.
    GetName = function(f) return rawget(f, "name") end,
    -- Every launcher test asks the object type once, before and after the fix.
    IsObjectType = function(f, k) if f.counted then tests = tests + 1 end return f.kind == k end,
    GetObjectType = function(f) return f.kind end,
    GetNumPoints = function() return 0 end,
    GetWidth = function(f) return f.w end, GetHeight = function(f) return f.h end,
    GetScript = function(f, k) return f.scripts[k] end,
    SetScript = function(f, k, fn) f.scripts[k] = fn end,
    GetParent = function(f) return rawget(f, "parent") end,
    IsShown = function(f) return f.shown end,
    GetAlpha = function() return 1 end, GetFrameStrata = function() return "MEDIUM" end,
    GetFrameLevel = function() return 1 end, IsMouseEnabled = function() return true end,
    GetEffectiveScale = function() return 1 end, IsMouseOver = function() return false end,
    CreateTexture = function() return setmetatable({}, { __index = function() return noop end }) end,
    GetChildren = function(f) return unpack(rawget(f, "children")) end,
}
local mt = { __index = function(_, k) return methods[k] or noop end }
function CreateFrame(kind, name, parent)
    local f = setmetatable({ [0] = newproxy(), kind = kind, name = name, parent = parent,
        w = 10, h = 10, shown = true, scripts = {}, children = {} }, mt)
    if name then _G[name] = f end
    if parent then table.insert(rawget(parent, "children"), f) end
    return f
end
UIParent = CreateFrame("Frame", "UIParent")
MinimapCluster = CreateFrame("Frame", "MinimapCluster", UIParent)
Minimap = CreateFrame("Frame", "Minimap", MinimapCluster)
MinimapBackdrop = CreateFrame("Frame", "MinimapBackdrop", MinimapCluster)
GameTooltip = CreateFrame("Frame", "GameTooltip")
AutoLazy = { Style = { Surface = noop }, Print = noop, UpdateGUI = noop }
AutoLazyDB = { Tweaks = { CollapseAddons = true, KeepOnMinimap = {} } }
-- Ordinary named frames another addon made before AutoLazy loaded (not Buttons).
for i = 1, 200 do CreateFrame("Frame", "OtherAddonFrame" .. i).counted = true end
'''

TRAY_START = r'''
controller = AutoLazy_TrayController
function fire(ev, a1) controller.scripts.OnEvent(controller, ev, a1) end
'''


def core():
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(CORE_MOCKS)
    lua.execute(CORE)
    lua.execute("AutoLazy.UpdateActionButton = function() end; AutoLazy.ApplySystemIconToggles = function() end")
    lua.execute('fire("ADDON_LOADED", "AutoLazy")')
    return lua


def tray(before=""):
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(TRAY_MOCKS)
    lua.execute(before)
    lua.execute(TRAY)
    lua.execute(TRAY_START)
    return lua


def turn_in_by_hand(lua, quest_id):
    """No Shift: the player picks the quest from the list and takes the reward."""
    lua.execute('''
        shift = false
        fire("GOSSIP_SHOW")
        fire("QUEST_PROGRESS"); fire("QUEST_COMPLETE")
        fire("QUEST_TURNED_IN", %d, 0, 0)
        fire("QUEST_FINISHED")
    ''' % quest_id)


class QuestRepeat(unittest.TestCase):
    def test_p2_shift_repeats_the_quest_just_turned_in(self):
        """Request: Shift at the same NPC picks the quest just turned in among several complete ones."""
        lua = core()
        lua.execute('active = { { questID = 7, title = "A", isComplete = true }, { questID = 8, title = "B", isComplete = true } }')
        turn_in_by_hand(lua, 8)
        lua.execute('selected = {}; shift = true; fire("GOSSIP_SHOW")')
        self.assertEqual(lua.eval("selected[1]"), "quest8")

    def test_p2_shift_repeats_a_blue_available_repeatable(self):
        """Request: a repeatable offered as an available (blue) quest is picked again with Shift."""
        lua = core()
        lua.execute('available = { { questID = 9, title = "Blue" }, { questID = 10, title = "Other" } }')
        turn_in_by_hand(lua, 9)
        lua.execute('selected = {}; shift = true; fire("GOSSIP_SHOW")')
        self.assertEqual(lua.eval("selected[1]"), "avail9")

    def test_control_other_npc_does_not_repeat(self):
        """Control: the remembered quest belongs to its NPC; another NPC with two complete quests waits."""
        lua = core()
        lua.execute('active = { { questID = 7, title = "A", isComplete = true }, { questID = 8, title = "B", isComplete = true } }')
        turn_in_by_hand(lua, 8)
        lua.execute('selected = {}; npc = "0xF130000002000002"; shift = true; fire("GOSSIP_SHOW")')
        self.assertEqual(lua.eval("#selected"), 0)

    def test_control_out_of_items_stops_repeating(self):
        """Control: a repeat whose progress dialog cannot complete is forgotten, so closing it does not reopen it."""
        lua = core()
        lua.execute('available = { { questID = 9, title = "Blue" }, { questID = 10, title = "Other" } }')
        turn_in_by_hand(lua, 9)
        lua.execute('''
            function IsQuestCompletable() return nil end
            shift = true; fire("GOSSIP_SHOW"); fire("QUEST_PROGRESS")
            selected = {}; fire("GOSSIP_SHOW")
        ''')
        self.assertEqual(lua.eval("#selected"), 0)

    def test_greeting_panel_repeats_by_title(self):
        """Request, greeting panel: titles only; the title of the quest just turned in is picked again."""
        lua = core()
        lua.execute('''
            GossipFrame = { IsShown = function() return false end }
            QuestFrameGreetingPanel = { IsShown = function() return true end }
            titles = { "Blue", "Other" }
            function GetNumActiveQuests() return 0 end
            function GetActiveTitle() end
            function GetNumAvailableQuests() return 2 end
            function GetAvailableTitle(i) return titles[i] end
            function SelectAvailableQuest(i) table.insert(selected, "greet" .. i) end
            title = "Blue"
            shift = false; fire("QUEST_GREETING"); fire("QUEST_COMPLETE")
            fire("QUEST_TURNED_IN", 9, 0, 0); fire("QUEST_FINISHED")
            selected = {}; shift = true; fire("QUEST_GREETING")
        ''')
        self.assertEqual(lua.eval("selected[1]"), "greet1")


class LootBind(unittest.TestCase):
    def test_p2_auto_confirm_takes_bind_on_pickup_loot(self):
        """ConfirmLootSlot does not exist in 1.12; the stock LOOT_BIND popup accepts with LootSlot(slot)."""
        lua = core()
        lua.execute('fire("LOOT_BIND_CONFIRM", 2)')
        self.assertEqual(lua.eval("looted[1]"), 2)


class TrayDiscovery(unittest.TestCase):
    def test_p3_login_walks_test_each_frame_once(self):
        """Measured: the PLAYER_ENTERING_WORLD, +0.5 s and +2 s walks re-test every non-Button frame."""
        lua = tray()
        lua.execute('fire("PLAYER_ENTERING_WORLD"); settle()')
        self.assertLessEqual(lua.eval("tests"), 200)

    def test_p3_blizzard_load_on_demand_does_not_walk_globals(self):
        """Measured (:555, 113.9 ms): opening e.g. the trade skill window loads a Blizzard_ addon and walks _G again."""
        lua = tray()
        lua.execute('fire("PLAYER_ENTERING_WORLD"); settle(); tests = 0')
        lua.execute('fire("ADDON_LOADED", "Blizzard_TradeSkillUI"); settle()')
        self.assertEqual(lua.eval("tests"), 0)

    def test_p3_created_buttons_are_tested_in_batches(self):
        """Measured (:555): Scan tests every Lua-created Button in the one refresh tick."""
        lua = tray()
        lua.execute('''
            fire("PLAYER_ENTERING_WORLD"); settle()
            for i = 1, 300 do CreateFrame("Button", nil, UIParent).counted = true end
            tests = 0; tick()
        ''')
        self.assertLess(lua.eval("tests"), 50)

    def test_control_launchers_are_still_found(self):
        """Control: a named launcher from before login and one created later both join the tray."""
        lua = tray()
        lua.execute('''
            local art = { GetTexture = function() return "Interface\Icons\X" end }
            local border = { GetTexture = function() return "Interface\Minimap\MiniMap-TrackingBorder" end }
            local function Launcher(name)
                local b = CreateFrame("Button", name, Minimap)
                b.w, b.h = 32, 32
                b:SetScript("OnClick", function() end)
                b.GetNormalTexture = function() return art end
                return b
            end
            -- One the player can drag, one with the standard border.
            Launcher("EarlyAddonMinimapButton").IsMovable = function() return true end
            fire("PLAYER_ENTERING_WORLD"); settle()
            Launcher(nil).GetRegions = function() return border end
            settle()
        ''')
        self.assertEqual(lua.eval("#AutoLazy.Tray.GetEntries()"), 2)

    def test_p2_self_dragging_launchers_join_the_tray(self):
        """AtlasLoot and ActionBarProfiles: not movable, own art, dragged by an OnDragStart script."""
        lua = tray()
        lua.execute('''
            local art = { GetTexture = function() return "Interface\AddOns\AtlasLoot\Images\AtlasLootMinimap" end }
            local b = CreateFrame("Button", "AtlasLootMinimapButton", Minimap)
            b.w, b.h = 33, 33
            b:SetScript("OnClick", function() end)
            b:SetScript("OnDragStart", function() end)
            b.GetNormalTexture = function() return art end
            fire("PLAYER_ENTERING_WORLD"); settle()
        ''')
        self.assertEqual(lua.eval("#AutoLazy.Tray.GetEntries()"), 1)

    def test_p2_unnamed_launchers_from_earlier_addons_join_the_tray(self):
        """An unnamed launcher made before AutoLazy loads is no global and passed no CreateFrame hook."""
        lua = tray('''
            local b = CreateFrame("Button", nil, Minimap)
            b.w, b.h = 32, 32
            b:SetScript("OnClick", function() end)
            b:SetScript("OnDragStart", function() end)
            b.GetNormalTexture = function() return { GetTexture = function() return "Interface\Icons\X" end } end
        ''')
        lua.execute('fire("PLAYER_ENTERING_WORLD"); settle()')
        self.assertEqual(lua.eval("#AutoLazy.Tray.GetEntries()"), 1)

    def test_p2_map_pins_stay_on_the_minimap(self):
        """A quest or node pin is a clickable minimap button too, but neither movable nor bordered."""
        lua = tray()
        lua.execute('''
            local art = { GetTexture = function() return "Interface\Icons\Quest" end }
            for i = 1, 3 do
                local pin = CreateFrame("Button", "SomeMapPin" .. i, Minimap)
                pin.w, pin.h = 16, 16
                pin:SetScript("OnClick", function() end)
                pin.GetNormalTexture = function() return art end
            end
            fire("PLAYER_ENTERING_WORLD"); settle()
        ''')
        self.assertEqual(lua.eval("#AutoLazy.Tray.GetEntries()"), 0)


if __name__ == "__main__":
    unittest.main()
