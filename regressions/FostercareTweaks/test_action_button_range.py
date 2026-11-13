"""The stock action buttons follow ClassicAPI's range event (audit 2026-11-13, 1.20.0).

FrameXML gives every action button an OnUpdate (ActionButton_OnUpdate): each
frame, on all 72 stock buttons, a name concatenation for the hotkey, a flash
check and a range poll every 0.2 s, also while nothing changes. Only Extra
Row 1 used ACTION_RANGE_CHECK_UPDATE (2026-11-03). mods/actionbar-range.lua now
does it for every stock button and Extra Row 1: each button enables the range
check of its own slot (and gives it back when it shows another one), the event
paints the game's colours, and the stock OnUpdate runs only while a button
flashes or shows its tooltip.

Built on ft_env (wowkit). The FrameXML functions are stand-ins with the stock fields
(this.action, rangeTimer, flashing, updateTooltip; ActionButton.lua of client
2026.10.31). Fails on 701d8b1 (no actionbar-range.lua; the stock buttons kept
their OnUpdate).

In-game checks: a key turns red out of range and grey in range as the target
moves, on the main bar, a side bar and after a stance or page change; the dot of
an unbound key shows out of range; the attack button flashes in combat; a held
tooltip refreshes its cooldown.
"""
import os
import unittest
from pathlib import Path

import ft_env

ROOT = Path(os.environ["VANILLAFORGE_ADDON_ROOT"])

# FrameXML stand-ins with the stock fields (ActionButton.lua, client 2026.10.31).
WORLD = r'''
NUM_ACTIONBAR_BUTTONS, RANGE_INDICATOR = 12, "dot"
enabled = {}
C_ActionBar = { EnableActionRangeCheck = function(slot, on)
    enabled[slot] = (enabled[slot] or 0) + (on and 1 or -1)
end }
stockUpdates = 0
function ActionButton_OnUpdate() stockUpdates = stockUpdates + 1 end
function ActionButton_Update() if HasAction(this.action) then this.rangeTimer = -1 else this.rangeTimer = nil end end
function ActionButton_UpdateAction()
    local action = this:GetID() + (page - 1) * 12
    if action ~= this.action then this.action = action; ActionButton_Update() end
end
function ActionButton_UpdateHotkeys() end
function ActionButton_StartFlash() this.flashing = 1 end
function ActionButton_StopFlash() this.flashing = 0 end
function ActionButton_SetTooltip() this.updateTooltip = 0.2 end
held = {}
function HasAction(slot) return held[slot] end
page = 1
-- The stock buttons, as ActionBarFrame.xml and MultiActionBars.xml make them.
for _, prefix in ipairs({ "Action", "BonusAction", "MultiBarBottomLeft", "MultiBarBottomRight", "MultiBarRight", "MultiBarLeft" }) do
    for i = 1, 12 do
        local b = CreateFrame("CheckButton", prefix .. "Button" .. i, UIParent)
        b:SetID(i)
        b:SetScript("OnUpdate", function() ActionButton_OnUpdate(arg1) end)
        CreateFrame("FontString", prefix .. "Button" .. i .. "HotKey", b):SetText("1")
        b.action = i
    end
end
held[1], held[2] = true, true
this = ActionButton1; ActionButton_Update(); this = ActionButton2; ActionButton_Update()
'''


def world():
    lua = ft_env.world(["mods/actionbar-range.lua"], extra=WORLD)
    return ft_env.start(lua)        # Core starts the always-on module


def call(lua, fn, button):
    lua.execute("local old = this; this = %s; %s(); this = old" % (button, fn))


class StockButtonsFollowTheRangeEvent(unittest.TestCase):
    def setUp(self):
        self.lua = world()

    def colour(self, button):
        return self.lua.eval("%sHotKey.color and %sHotKey.color[1]" % (button, button))

    def test_no_button_runs_a_script_while_nothing_changes(self):
        self.lua.execute("step(0.1); step(0.1); step(0.1)")
        self.assertEqual(self.lua.eval("stockUpdates"), 0)

    def test_each_button_enables_its_slot_once(self):
        self.assertEqual(self.lua.eval("enabled[1]"), 6)          # six bars show slots 1-12 here
        self.assertEqual(self.lua.eval("FCTweaksActionRange:IsEventRegistered('ACTION_RANGE_CHECK_UPDATE')"), 1)

    def test_the_event_paints_the_stock_colours(self):
        lua = self.lua
        lua.execute('fire("ACTION_RANGE_CHECK_UPDATE", 1, false, true)')
        self.assertEqual(self.colour("ActionButton1"), 1.0)          # red
        lua.execute('fire("ACTION_RANGE_CHECK_UPDATE", 1, true, true)')
        self.assertEqual(self.colour("ActionButton1"), 0.6)          # grey
        lua.execute('fire("ACTION_RANGE_CHECK_UPDATE", 1, false, false)')  # no range check: not red
        self.assertEqual(self.colour("ActionButton1"), 0.6)

    def test_an_empty_slot_keeps_the_game_colour(self):
        self.lua.execute('fire("ACTION_RANGE_CHECK_UPDATE", 3, false, true)')
        self.assertIsNone(self.colour("ActionButton3"))

    def test_the_dot_of_an_unbound_key_shows_out_of_range(self):
        lua = self.lua
        lua.execute('ActionButton2HotKey:SetText(RANGE_INDICATOR)')
        lua.execute('fire("ACTION_RANGE_CHECK_UPDATE", 2, true, true)')
        self.assertIsNone(lua.eval("ActionButton2HotKey:IsShown()"))
        lua.execute('fire("ACTION_RANGE_CHECK_UPDATE", 2, false, true)')
        self.assertEqual(lua.eval("ActionButton2HotKey:IsShown()"), 1)

    def test_a_page_change_moves_the_range_check_to_the_new_slot(self):
        lua = self.lua
        lua.execute("page = 2")
        call(lua, "ActionButton_UpdateAction", "ActionButton1")
        self.assertEqual(lua.eval("enabled[1]"), 5)
        self.assertEqual(lua.eval("enabled[13]"), 1)
        lua.execute("held[13] = true")
        call(lua, "ActionButton_Update", "ActionButton1")
        lua.execute('fire("ACTION_RANGE_CHECK_UPDATE", 13, false, true)')
        self.assertEqual(self.colour("ActionButton1"), 1.0)

    def test_the_stock_update_runs_only_while_flashing_or_showing_a_tooltip(self):
        lua = self.lua
        call(lua, "ActionButton_StartFlash", "ActionButton1")
        lua.execute("step(0.02); step(0.02)")
        self.assertEqual(lua.eval("stockUpdates"), 2)
        call(lua, "ActionButton_StopFlash", "ActionButton1")
        lua.execute("step(0.02); step(0.02); step(0.02)")
        self.assertEqual(lua.eval("stockUpdates"), 3)              # the last run stops itself
        call(lua, "ActionButton_SetTooltip", "ActionButton1")
        lua.execute("step(0.02)")
        self.assertEqual(lua.eval("stockUpdates"), 4)
        lua.execute("ActionButton1.updateTooltip = nil; step(0.02); step(0.02)")
        self.assertEqual(lua.eval("stockUpdates"), 5)
        self.assertIsNone(lua.eval("ActionButton1:GetScript('OnUpdate')"))

    def test_extra_row_one_is_tracked_like_the_stock_buttons(self):
        text = (ROOT / "ActionBars.lua").read_text("utf-8-sig")
        self.assertIn("FT.ActionButtonRange.Track(button)", text)
        for gone in ("SetRangeCheck", "ShowRange", '"OnUpdate"'):
            self.assertNotIn(gone, text)


if __name__ == "__main__":
    unittest.main()
