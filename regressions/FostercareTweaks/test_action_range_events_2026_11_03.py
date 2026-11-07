"""Extra Row 1 follows ClassicAPI 1.19.1 range events, 2026-11-03.

Each of its twelve stock buttons ran ActionButton_OnUpdate every frame: a name
concatenation for the hotkey, a flash check and the 0.2 s range poll.
ACTION_RANGE_CHECK_UPDATE fires when a slot's range changes, so the stock update
is only needed while a button flashes or shows its tooltip.

In-game checks: out-of-range buttons turn their key red and back as the target
moves; the dot of a key-less button shows out of range; an attack button flashes
in combat; the tooltip refreshes while held; hiding the row stops the events.
"""
import os
import unittest
from pathlib import Path

from wowlua import LuaRuntime  # noqa: F401  (runtime() builds the interpreter)

from test_audit_2026_10_26 import runtime, source

ROOT = Path(os.environ["VANILLAFORGE_ADDON_ROOT"])


class ExtraRowRange(unittest.TestCase):
    def setUp(self):
        self.lua = runtime()
        self.lua.execute(r'''
            enabledCount = {}
            C_ActionBar = { EnableActionRangeCheck = function(slot, on)
                enabledCount[slot] = (enabledCount[slot] or 0) + (on and 1 or -1)
            end }
            RANGE_INDICATOR = "dot"
            actionsHeld = { [13] = true, [14] = true }
            function HasAction(slot) return actionsHeld[slot] end
            stockUpdates = 0
            ActionButton_GetPagedID = function() return 0 end
            ActionButton_OnLoad = NOOP
            ActionButton_OnUpdate = function() stockUpdates = stockUpdates + 1 end
            hotkeys = {}
            local create = CreateFrame
            CreateFrame = function(kind, name, parent, template)
                local f = create(kind, name, parent, template)
                if name and string.find(name, "^FCTweaksExtraButton") then
                    local hk = Widget({ text = "", color = "gray" })
                    function hk:GetText() return self.text end
                    function hk:SetVertexColor(r) self.color = r > 0.9 and "red" or "gray" end
                    hk.Show = function(s) s.shown = true end
                    hk.Hide = function(s) s.shown = false end
                    hk.IsShown = function(s) return s.shown end
                    _G[name .. "HotKey"] = hk
                    hotkeys[#hotkeys + 1] = hk
                end
                return f
            end
        ''')
        self.lua.execute("FT.IsEnabled = function() return false end")
        self.lua.execute(source("ActionBars.lua"))
        self.lua.execute(r'''
            AB = FT.ActionBars
            AB.controller = CreateFrame("Frame", "ctl", UIParent)
            bar = AB:CreateBar(AB.definitions[6])
            events = function() return rawget(AB.controller, "events") or {} end
        ''')

    def test_slots_enabled_once_and_listening_only_while_shown(self):
        self.lua.execute("AB:SetRangeCheck(bar, true); AB:SetRangeCheck(bar, true)")
        self.assertEqual(self.lua.eval("enabledCount[13]"), 1)
        self.assertEqual(self.lua.eval("enabledCount[24]"), 1)
        self.assertTrue(self.lua.eval("events().ACTION_RANGE_CHECK_UPDATE"))
        self.lua.execute("AB:SetRangeCheck(bar, false); AB:SetRangeCheck(bar, false)")
        self.assertEqual(self.lua.eval("enabledCount[13]"), 0)
        self.assertIsNone(self.lua.eval("events().ACTION_RANGE_CHECK_UPDATE"))

    def test_never_enabled_row_does_not_disable(self):
        self.lua.execute("AB:SetRangeCheck(bar, false)")
        self.assertIsNone(self.lua.eval("enabledCount[13]"))

    def test_stock_update_only_while_flashing_or_tooltip(self):
        run = "local b = bar.buttons[1]; this = b; arg1 = 0.02; b.scripts.OnUpdate()"
        self.lua.execute(run)
        self.assertEqual(self.lua.eval("stockUpdates"), 0)
        self.lua.execute("bar.buttons[1].flashing = 1")
        self.lua.execute(run)
        self.lua.execute("bar.buttons[1].flashing = nil; bar.buttons[1].updateTooltip = 0.2")
        self.lua.execute(run)
        self.assertEqual(self.lua.eval("stockUpdates"), 2)

    def test_range_event_colours_the_hotkey(self):
        self.lua.execute("AB.bars.extra = bar")
        hk = "hotkeys[1]"
        self.lua.execute("AB:ShowRange(13, false, true)")
        self.assertEqual(self.lua.eval(hk + ".color"), "red")
        self.lua.execute("AB:ShowRange(13, true, true)")
        self.assertEqual(self.lua.eval(hk + ".color"), "gray")
        self.lua.execute("AB:ShowRange(13, false, false)")  # no range check: not red
        self.assertEqual(self.lua.eval(hk + ".color"), "gray")

    def test_range_dot_hides_in_range_and_shows_otherwise(self):
        self.lua.execute("AB.bars.extra = bar; hotkeys[1].text = RANGE_INDICATOR")
        self.lua.execute("AB:ShowRange(13, true, true)")
        self.assertFalse(self.lua.eval("hotkeys[1].shown"))
        self.lua.execute("AB:ShowRange(13, false, true)")
        self.assertTrue(self.lua.eval("hotkeys[1].shown"))

    def test_empty_slot_is_left_alone(self):
        self.lua.execute("AB.bars.extra = bar; AB:ShowRange(20, false, true)")
        self.assertEqual(self.lua.eval("hotkeys[8].color"), "gray")

    def test_source_has_no_per_frame_range_work(self):
        text = source("ActionBars.lua")
        self.assertIn("ACTION_RANGE_CHECK_UPDATE", text)
        self.assertIn("this.flashing == 1 or this.updateTooltip", text)


if __name__ == "__main__":
    unittest.main()
