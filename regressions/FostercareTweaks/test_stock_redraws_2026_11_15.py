"""The game's own redraws, once and only where something changed (audit 2026-11-15).

* Action buttons (ActionButton.lua ActionButton_OnEvent): each button with an
  action ran ActionButton_Update for every UNIT_INVENTORY_CHANGED of the
  player, and UpdateUsable plus UpdateCooldown for every UPDATE_INVENTORY_ALERTS
  and ACTIONBAR_UPDATE_USABLE. Durability and equipping send several in one
  frame; /lag (2026-11-14, Blood Ring and Stranglethorn) caught frames of 66
  to 84 ms in these redraws, 655 to 960 hook calls each. Now the inventory
  events redraw each button once, on the next frame, and ClassicAPI's
  ACTION_USABLE_CHANGED recolours only the slots that changed.
* Buff and debuff buttons (BuffFrame.xml BuffButtonTemplate OnUpdate) redrew
  every frame they showed; SHOW_BUFF_DURATIONS is "1" on all three accounts.
  Now the stock redraw runs only while an aura flashes or holds the tooltip,
  and the label is written when it next changes (the enchants' rule, 1.21.0).
* Extra Rows 2-7 refreshed every icon, count, cooldown and click action on
  each modifier key, target, aura, usable and state change. Modifier keys do
  nothing now; the other four read only usable, active and range.

FrameXML stand-ins keep the stock fields (this.action, eventsRegistered,
buffIndex, untilCancelled). Fails on 00ded4d.
"""
import os
import unittest
from pathlib import Path

import ft_env
from test_audit_2026_10_26 import source

ROOT = Path(os.environ["VANILLAFORGE_ADDON_ROOT"])

# ActionButton.lua, as the stock buttons run it (client 2026.10.31).
BUTTONS = r'''
NUM_ACTIONBAR_BUTTONS, RANGE_INDICATOR = 12, "dot"
C_ActionBar = { EnableActionRangeCheck = function() end }
calls = { update = 0, usable = 0, cooldown = 0 }
usableOf = {}
OWN = { "ACTIONBAR_UPDATE_STATE", "ACTIONBAR_UPDATE_USABLE", "ACTIONBAR_UPDATE_COOLDOWN",
    "UPDATE_INVENTORY_ALERTS", "PLAYER_AURAS_CHANGED", "PLAYER_TARGET_CHANGED", "UNIT_INVENTORY_CHANGED" }
held = {}
function HasAction(slot) return held[slot] end
function ActionButton_OnUpdate() end
function ActionButton_UpdateHotkeys() end
function ActionButton_StartFlash() end
function ActionButton_SetTooltip() end
function ActionButton_UpdateUsable() calls.usable = calls.usable + 1; usableOf[this] = (usableOf[this] or 0) + 1 end
function ActionButton_UpdateCooldown() calls.cooldown = calls.cooldown + 1 end
function ActionButton_Update()
    calls.update = calls.update + 1
    if HasAction(this.action) then
        if not this.eventsRegistered then
            for _, e in ipairs(OWN) do this:RegisterEvent(e) end
            this.eventsRegistered = 1
        end
        this.rangeTimer = -1
        ActionButton_UpdateUsable(); ActionButton_UpdateCooldown()
    else
        if this.eventsRegistered then
            for _, e in ipairs(OWN) do this:UnregisterEvent(e) end
            this.eventsRegistered = nil
        end
        this.rangeTimer = nil
    end
end
function ActionButton_OnEvent(event)
    if event == "UNIT_INVENTORY_CHANGED" then
        if arg1 == "player" then ActionButton_Update() end
    elseif event == "ACTIONBAR_UPDATE_USABLE" or event == "UPDATE_INVENTORY_ALERTS" or event == "ACTIONBAR_UPDATE_COOLDOWN" then
        ActionButton_UpdateUsable(); ActionButton_UpdateCooldown()
    end
end
for _, prefix in ipairs({ "Action", "BonusAction", "MultiBarBottomLeft", "MultiBarBottomRight", "MultiBarRight", "MultiBarLeft" }) do
    for i = 1, 12 do
        local b = CreateFrame("CheckButton", prefix .. "Button" .. i, UIParent)
        b:SetID(i)
        b.action = i + (prefix == "Action" and 0 or 12)
        b:SetScript("OnEvent", function() ActionButton_OnEvent(event) end)
        CreateFrame("FontString", prefix .. "Button" .. i .. "HotKey", b):SetText("1")
    end
end
held[1], held[2], held[13] = true, true, true
for _, name in ipairs({ "ActionButton1", "ActionButton2", "BonusActionButton1" }) do
    this = _G[name]; ActionButton_Update()
end
this = nil
'''


def buttons_world():
    lua = ft_env.world(["mods/actionbar-range.lua"], BUTTONS)
    ft_env.start(lua)
    lua.execute("calls.update, calls.usable, calls.cooldown = 0, 0, 0; usableOf = {}")
    return lua


class ActionButtonsRedrawOnce(unittest.TestCase):
    def test_a_burst_of_inventory_events_redraws_each_button_once(self):
        lua = buttons_world()
        lua.execute('for _ = 1, 3 do fire("UNIT_INVENTORY_CHANGED", "player") end; fire("UPDATE_INVENTORY_ALERTS")')
        lua.execute("step(0)")
        self.assertEqual(lua.eval("calls.update"), 3)          # three buttons with an action, once each
        lua.execute("step(0.1)")
        self.assertEqual(lua.eval("calls.update"), 3)

    def test_alerts_alone_read_usable_and_cooldown_once(self):
        lua = buttons_world()
        lua.execute('fire("UPDATE_INVENTORY_ALERTS"); fire("UPDATE_INVENTORY_ALERTS"); step(0)')
        self.assertEqual((lua.eval("calls.update"), lua.eval("calls.cooldown")), (0, 3))

    def test_only_the_slots_whose_usable_state_changed_are_recoloured(self):
        lua = buttons_world()
        lua.execute('fire("ACTIONBAR_UPDATE_USABLE")')
        self.assertEqual(lua.eval("calls.usable"), 0)
        lua.execute('fire("ACTION_USABLE_CHANGED", { { slot = 13, usable = false, noMana = true } })')
        self.assertEqual(lua.eval("calls.usable"), 1)
        self.assertEqual(lua.eval("usableOf[BonusActionButton1]"), 1)

    def test_a_slot_that_gets_an_action_hands_over_its_events_again(self):
        lua = buttons_world()
        lua.execute("held[3] = true; this = ActionButton3; ActionButton_Update(); this = nil")
        self.assertFalse(lua.eval('receives(ActionButton3, "UNIT_INVENTORY_CHANGED", "player")'))
        self.assertTrue(lua.eval('receives(ActionButton3, "ACTIONBAR_UPDATE_COOLDOWN")'))
        lua.execute("held[3] = nil; this = ActionButton3; ActionButton_Update(); held[3] = true; ActionButton_Update(); this = nil")
        self.assertFalse(lua.eval('receives(ActionButton3, "ACTIONBAR_UPDATE_USABLE")'))


BUFFS = r'''
SHOW_BUFF_DURATIONS, BUFF_WARNING_TIME = "1", 31
ends = {}            -- buff index -> GetTime() it ends; true = until cancelled
function GetPlayerBuff(id, filter) if ends[id] then return id, ends[id] == true and 1 or 0 end return -1, 0 end
function GetPlayerBuffTimeLeft(index) local e = ends[index]; if e == true then return 0 end return e - now end
function GetPlayerBuffID() return 1 end
function GetSpellInfo() return "Aura" end
labels = 0
function BuffFrame_UpdateDuration(button, left) labels = labels + 1; button.fctLabel = left end
stockRuns = 0
-- BuffFrame.lua BuffButton_Update: the button's buff, shown, alpha 1.
function BuffButton_Update()
    local index, cancelled = GetPlayerBuff(this:GetID(), this.buffFilter)
    this.buffIndex, this.untilCancelled = index, cancelled
    if index < 0 then this:Hide() else this:SetAlpha(1); this:Show(); _G[this:GetName() .. "Duration"]:Show() end
end
function BuffButtons_UpdatePositions() end
function BuffFrame_Enchant_OnUpdate() end
GameTooltip = CreateFrame("GameTooltip", "GameTooltip")
function GameTooltip:IsOwned(f) return self.owner == f end
C_Item = C_Item or {}
C_Item.GetWeaponEnchantInfo = function() return nil, nil, nil, 0, nil, nil, nil, 0 end
function GetWeaponEnchantInfo() end
BuffFrame = CreateFrame("Frame", "BuffFrame")
TemporaryEnchantFrame = CreateFrame("Frame", "TemporaryEnchantFrame")
for i = 0, 2 do
    local b = CreateFrame("Button", "BuffButton" .. i)
    b:SetID(i)
    b.buffFilter = "HELPFUL"
    b.FostercareTweaks_border = false
    CreateFrame("FontString", "BuffButton" .. i .. "Duration")
    CreateFrame("Texture", "BuffButton" .. i .. "Icon")
    b:SetScript("OnUpdate", function() stockRuns = stockRuns + 1 end)
    b:SetScript("OnEnter", function() GameTooltip.owner = this end)
    b:SetScript("OnLeave", function() GameTooltip.owner = nil end)
end
for i = 1, 2 do
    local b = CreateFrame("Button", "TempEnchant" .. i)
    b.id = 18 - i
    b.FostercareTweaks_border = false
    CreateFrame("FontString", "TempEnchant" .. i .. "Duration")
    CreateFrame("Texture", "TempEnchant" .. i .. "Icon")
end
function GetInventoryItemQuality() return 2 end
function GetItemQualityColor() return 1, 1, 1 end
'''


def buffs_world(setup=""):
    lua = ft_env.world([], BUFFS)
    lua.execute('''
        function FT.RestoreFramePosition() end
        function FT.RegisterFrameMover() end
        function FT.IsAuraHidden() return false end''')
    lua.execute(setup)
    ft_env.wowkit.load_files(lua, ROOT, ["mods/standard-player-auras.lua"], "FostercareTweaks")
    return ft_env.start(lua)


def auras_changed(lua):
    lua.execute("for i = 0, 2 do this = _G['BuffButton' .. i]; BuffButton_Update() end; this = nil")


class BuffButtonsRedrawWhenTheyChange(unittest.TestCase):
    def test_a_long_buff_runs_no_script_and_relabels_each_minute(self):
        lua = buffs_world("ends[0] = now + 1770")     # 29.5 minutes: "30 m" for 30 s more
        self.assertIsNone(lua.eval("BuffButton0.scripts.OnUpdate"))
        before = lua.eval("labels")
        lua.execute("for _ = 1, 60 do step(0.016) end")
        self.assertEqual(lua.eval("stockRuns"), 0)
        self.assertEqual(lua.eval("labels"), before)
        lua.execute("step(29.5)")
        self.assertEqual(lua.eval("labels"), before + 1)
        lua.execute("step(59.5)")
        self.assertEqual(lua.eval("labels"), before + 1)
        lua.execute("step(0.6)")
        self.assertEqual(lua.eval("labels"), before + 2)

    def test_the_last_seconds_flash_with_the_stock_redraw(self):
        lua = buffs_world("ends[0] = now + 40")
        lua.execute("step(9.2)")                           # 30.8 s left
        self.assertIsNotNone(lua.eval("BuffButton0.scripts.OnUpdate"))
        lua.execute("step(0.016); step(0.016)")
        self.assertGreaterEqual(lua.eval("stockRuns"), 2)
        lua.execute("ends[0] = nil"); auras_changed(lua)  # gone
        self.assertIsNone(lua.eval("BuffButton0.scripts.OnUpdate"))

    def test_a_permanent_aura_hides_its_label_and_sleeps(self):
        lua = buffs_world("ends[1] = true")
        self.assertIsNone(lua.eval("BuffButton1.scripts.OnUpdate"))
        self.assertFalse(lua.eval("BuffButton1Duration.shown"))

    def test_a_held_tooltip_runs_the_stock_redraw_until_it_leaves(self):
        lua = buffs_world("ends[0] = now + 1770")
        lua.execute("run(BuffButton0, 'OnEnter'); step(0.016)")
        self.assertEqual(lua.eval("stockRuns"), 1)
        lua.execute("run(BuffButton0, 'OnLeave'); step(0.016); step(0.016)")
        self.assertEqual(lua.eval("stockRuns"), 1)

    def test_a_recast_moves_the_wake(self):
        lua = buffs_world("ends[0] = now + 1770")
        before = lua.eval("labels")
        lua.execute("ends[0] = now + 3600"); auras_changed(lua)
        self.assertEqual(lua.eval("labels"), before + 1)
        lua.execute("step(30)")                                   # the old wake: nothing due
        self.assertEqual(lua.eval("labels"), before + 1)


class ExtraRowsReadOnlyWhatChanged(unittest.TestCase):
    def setUp(self):
        from test_audit_2026_10_25 import between
        lua = self.lua = ft_env.wowkit.runtime(unpack_returned_tuples=True)
        lua.execute(r'''
            EA, refreshes, callbacks = {}, {}, {}
            function RefreshVisible(full) refreshes[#refreshes + 1] = full and "full" or "light" end
            function SyncTicker() end
            C_Timer = { After = function(_, fn) callbacks[#callbacks + 1] = fn end }
            FT = { Guarded = function(f) return f end }
        ''')
        lua.execute(between(source("ExtraActions.lua").replace("\r\n", "\n"),
                            "local FlushRefresh", "local function SyncOwner") + "\nQueue = QueueRefresh")

    def test_target_aura_usable_and_state_events_read_little(self):
        self.lua.execute("Queue(true); Queue(true); callbacks[1]()")
        self.assertEqual(self.lua.eval("refreshes[1]"), "light")

    def test_a_full_event_in_the_burst_makes_it_full(self):
        self.lua.execute("Queue(true); Queue(); Queue(true); callbacks[1]()")
        self.assertEqual(self.lua.eval("refreshes[1]"), "full")
        self.assertEqual(self.lua.eval("#callbacks"), 1)

    def test_modifier_keys_wake_nothing(self):
        text = source("ExtraActions.lua")
        events = text[text.index("local events = {"):text.index("}", text.index("local events = {"))]
        self.assertNotIn("MODIFIER_STATE_CHANGED", events)
        self.assertIn("ACTIONBAR_UPDATE_USABLE = true", text)


if __name__ == "__main__":
    unittest.main()
