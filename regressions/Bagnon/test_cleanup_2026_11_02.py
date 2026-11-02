"""Bagnon cleanup of 2026-11-02: the paths the cleanup moved or removed.

1. Reopening or regenerating a window with the same slot count, columns and spacing
   leaves the buttons where they are (no ClearAllPoints/SetPoint per slot).
2. One OnTooltipSetItem script adds the other characters' counts (it replaced seven hooks).
3. The cooldown refresh skips empty slots.
4. Sort works when the backpack is left out of it (the 1.15.15 gate is gone).
5. Settings of the retired auto-open triggers are cleared on load.
6. Free space of a cached bank view and a stack of specialty bags still count per bag.
"""
import unittest
from bgn_env import ROOT, load

PLAIN = '''
    frame = widget("Bagnon"); frame.size = 12; frame.items = {}
    for i = 1, 12 do frame.items[i] = widget("Slot" .. i, i) end
    BagnonSets.Bagnon.cols = 4; BagnonSets.Bagnon.space = 2
    pointCalls = 0
    for _, w in ipairs(frame.items) do
        function w:SetPoint() pointCalls = pointCalls + 1 end
    end
'''


def run_file(lua, name):
    lua.execute((ROOT / name).read_text("utf-8-sig"), name)


class Layout(unittest.TestCase):
    def test_same_layout_is_not_laid_out_twice(self):
        lua = load("localization", "utility", "frame")
        lua.execute(PLAIN + "BagnonFrame_Layout(frame, 4, 2); first = pointCalls; BagnonFrame_Layout(frame, 4, 2)")
        self.assertEqual(lua.eval("first"), 12)
        self.assertEqual(lua.eval("pointCalls"), 12)

    def test_other_columns_lay_out_again(self):
        lua = load("localization", "utility", "frame")
        lua.execute(PLAIN + "BagnonFrame_Layout(frame, 4, 2); BagnonFrame_Layout(frame, 5, 2)")
        self.assertEqual(lua.eval("pointCalls"), 24)


class Tooltip(unittest.TestCase):
    def test_the_item_script_adds_other_characters(self):
        lua = load("localization", "utility")
        lua.execute('''
            hooks = {}
            local function tip(name)
                local t = widget(name)
                function t:HookScript(script, fn) hooks[name .. script] = fn end
                function t:GetItem() return "Name", "|cffffffff|Hitem:2589:0:0:0|h[Cloth]|h|r", 2589 end
                t.lines = {}
                function t:AddLine(text) table.insert(self.lines, text) end
                return t
            end
            GameTooltip = tip("GameTooltip"); ItemRefTooltip = tip("ItemRefTooltip")
            BagnonSets.showForeverTooltips = 1
            BagnonDB = { GetPlayers = function() return pairs({ Tester = {}, Alt = {} }) end,
                         GetPlayerItemTotals = function(id, player) if player == "Alt" then return 5, 2 end return 9, 9 end }
        ''')
        run_file(lua, "tooltips.lua")
        lua.execute('this = GameTooltip; hooks["GameTooltipOnTooltipSetItem"](); hooks["GameTooltipOnTooltipSetItem"]()')
        self.assertEqual(lua.eval("#GameTooltip.lines"), 1)
        self.assertEqual(lua.eval("GameTooltip.lines[1]"), "Alt has 5 (Bags) 2 (Bank)")
        lua.execute('hooks["GameTooltipOnTooltipCleared"](); hooks["GameTooltipOnTooltipSetItem"]()')
        self.assertEqual(lua.eval("#GameTooltip.lines"), 2)


class Events(unittest.TestCase):
    SETUP = '''
        scripts, timers = {}, {}
        function CreateFrame(kind, name)
            local w = widget(name)
            function w:SetScript(n, fn) scripts[n] = fn end
            return w
        end
        C_Timer.NewTimer = function(_, fn) local t = { Cancel = function() end, run = fn }; timers[#timers + 1] = t; return t end
        BankFrame = widget("BankFrame")
        Bagnon = widget("Bagnon"); Banknon = widget("Banknon")
        Bagnon.shown = true; Bagnon.player = "Tester"; Bagnon.size = 3
        Bagnon_SetAtBank(nil)
        Bagnon.items = {}
        for i = 1, 3 do
            local item = widget("Item" .. i, i); item.parent = widget(nil, 0); item.hasItem = (i ~= 2) and 1 or nil
            Bagnon.items[i] = item
        end
        updated = {}
        function BagnonItem_UpdateCooldown(_, item) updated[#updated + 1] = item.id end
        function BagnonFrame_UpdateBags() end
        BagnonSets.Bagnon.bags = { 0 }
    '''

    def test_cooldown_refresh_skips_empty_slots(self):
        lua = load("localization", "utility")
        lua.execute(self.SETUP)
        run_file(lua, "Events.lua")
        lua.execute('''
            scripts.OnEvent(widget(), "ADDON_LOADED", "Bagnon")
            scripts.OnEvent(widget(), "BAG_UPDATE_COOLDOWN")
            for _, t in ipairs(timers) do t.run() end
        ''')
        self.assertEqual(list(lua.eval("updated").values()), [1, 3])

    def test_retired_settings_are_cleared_on_load(self):
        lua = load("localization", "utility")
        lua.execute(self.SETUP + '''
            BagnonSets.showBankAtTrade = 1; BagnonSets.showBagsAtCraft = 1; BagnonSets.version = "1.0.0"
            BagnonSets.showBagsAtAH = 1
        ''')
        run_file(lua, "Events.lua")
        lua.execute('scripts.OnEvent(widget(), "ADDON_LOADED", "Bagnon")')
        self.assertIsNone(lua.eval("BagnonSets.showBankAtTrade"))
        self.assertIsNone(lua.eval("BagnonSets.showBagsAtCraft"))
        self.assertIsNone(lua.eval("BagnonSets.version"))
        self.assertEqual(lua.eval("BagnonSets.showBagsAtAH"), 1)


class Sort(unittest.TestCase):
    def test_sort_runs_with_the_backpack_left_out(self):
        lua = load("localization", "utility", "frame")
        lua.execute('''
            sorted = 0
            C_Container.GetBackpackAutosortDisabled = function() return true end
            C_Container.SortBags = function() sorted = sorted + 1 end
            function PlaySound() end
        ''')
        self.assertTrue(lua.eval("Bagnon_RequestSort(false)"))
        self.assertEqual(lua.eval("sorted"), 1)


if __name__ == "__main__":
    unittest.main()
