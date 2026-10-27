"""Unit buttons, 2026-10-27: enemy rows, their cast bars and the flag carrier
frames are ClassicAPI unit buttons once the enemy's GUID is known.

- type1 "target" (a spell or item on the cursor goes to the enemy), type2
  "focus", and the hover makes the enemy the mouseover; no hand-made
  TargetUnit, FocusUnit, TargetByName or SetMouseoverUnit is left.
- Ctrl and Shift clicks fall through to the addon (Ctrl-click announces an
  enemy opening a flag).
- A click on anything not bound (a row before its GUID is known, Spy rows, the
  warning cards, /abg efc) selects the enemy through one off-screen unit
  button, found by exact name; an unrelated unit is never used.

Which tooltip shows while hovering a bound frame stays an in-game check.
"""
from pathlib import Path
import os
import re
import unittest
from lupa.lua51 import LuaRuntime

import test_carrier_health as tch
from test_targets_guid_events import GROM, runtime

ROOT = Path(os.environ["VANILLAFORGE_ADDON_ROOT"])


def picked(lua):
    return list(lua.eval('picked').values())


class EnemyRowTests(unittest.TestCase):
    def bound(self):
        lua = runtime()
        lua.execute('AutoBG_Targets.UpdateRowStatus()')
        return lua

    def test_known_enemy_row_and_cast_bar_are_unit_buttons(self):
        lua = self.bound()
        for frame in ("AutoBG_TargetButton1", "AutoBG_TargetCast1"):
            self.assertEqual(lua.eval('%s:GetAttribute("unit")' % frame), GROM)
            self.assertEqual(lua.eval('%s:GetAttribute("type1")' % frame), "target")
            self.assertEqual(lua.eval('%s:GetAttribute("type2")' % frame), "focus")

    def test_clicks_target_and_focus_through_classicapi(self):
        lua = self.bound()
        lua.execute('AutoBG_TargetButton1:Click("LeftButton"); AutoBG_TargetButton1:Click("RightButton")')
        self.assertEqual(picked(lua), ["target " + GROM, "focus " + GROM])

    def test_ctrl_click_on_a_bound_opening_row_announces(self):
        lua = self.bound()
        lua.execute('announced = {}; AutoBG_FlagAlert = { Announce = function(_, n, node) table.insert(announced, n .. " " .. node) end }')
        lua.execute('function IsControlKeyDown() return true end; AutoBG_Targets.SetOpening("Grom", "Farm")')
        lua.execute('AutoBG_TargetButton1:Click("LeftButton")')
        self.assertEqual(list(lua.eval('announced').values()), ["Grom Farm"])
        self.assertEqual(picked(lua), [])

    def test_row_without_a_guid_selects_by_exact_name(self):
        lua = runtime(sighting=False)
        lua.execute('guidNames["%s"] = "Grom"' % GROM)
        lua.execute('local b = AutoBG_TargetButton1; b.scripts.OnClick(b, "LeftButton")')
        self.assertEqual(picked(lua), ["target " + GROM])
        self.assertIsNone(lua.eval('AutoBG_EnemySelector:GetAttribute("unit")'))

    def test_unrelated_unit_is_never_selected(self):
        lua = runtime(sighting=False)
        lua.execute('function UnitTokenFromName() return "0x0000000000000099" end')
        lua.execute('guidNames["0x0000000000000099"] = "Gromgar"')
        lua.execute('function UnitExists(u) return u == "0x0000000000000099" end')
        self.assertFalse(lua.eval('AutoBG_Targets.SelectEnemy("Grom", nil, "LeftButton")'))
        self.assertEqual(picked(lua), [])

    def test_preview_rows_are_not_bound(self):
        lua = runtime()
        lua.execute('AutoBG_Targets:EnableConfigMode(10); AutoBG_Targets.UpdateRowStatus()')
        self.assertIsNone(lua.eval('AutoBG_TargetButton1:GetAttribute("unit")'))


CARRIER_BUTTONS = r'''
selected = {}
AutoBG_Targets = {
    BindUnit = function(frame, guid) frame.bound = guid end,
    SelectEnemy = function(name, guid, button) table.insert(selected, name .. "|" .. tostring(guid) .. "|" .. button); return true end,
}
function AutoBG_Print() end
function GetMouseButtonClicked() return clickedButton end
'''


class CarrierFrameTests(unittest.TestCase):
    def runtime(self):
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute(tch.BASE + CARRIER_BUTTONS)
        lua.execute(tch.FC)
        lua.execute('local f = AutoBG_FCEventFrame; f.scripts.OnEvent(f, "CHAT_MSG_BG_SYSTEM_HORDE", "The Horde flag was picked up by Grom!")')
        lua.execute('AutoBG_FC_UpdateVisibility()')
        return lua

    def test_seen_carrier_frame_is_bound_to_the_guid(self):
        lua = self.runtime()
        self.assertEqual(lua.eval('AutoBG_AllianceFC.bound'), "0x00000000000000C3")

    def test_lost_carrier_unbinds(self):
        lua = self.runtime()
        lua.execute('function UnitTokenFromName() return nil end; function UnitExists() return false end')
        lua.execute('AutoBG_FC_UpdateVisibility()')
        self.assertIsNone(lua.eval('AutoBG_AllianceFC.bound'))

    def test_unbound_click_and_slash_commands_use_the_selector(self):
        lua = self.runtime()
        lua.execute('clickedButton = "RightButton"; this = AutoBG_AllianceFC; AutoBG_AllianceFC.scripts.OnClick()')
        lua.execute('function UnitFactionGroup() return "Horde" end; AutoBG_TargetCarrier("enemy")')
        self.assertEqual(list(lua.eval('selected').values()),
                         ["Grom|0x00000000000000C3|RightButton", "Grom|0x00000000000000C3|LeftButton"])


class NoHandMadeTargetingTests(unittest.TestCase):
    def test_no_hand_made_targeting_left(self):
        found = []
        for path in ROOT.glob("*.lua"):
            text = path.read_text("utf-8-sig")
            for m in re.finditer(r'\b(TargetByName|TargetUnit|FocusUnit|SetMouseoverUnit)\s*\(', text):
                found.append("%s %s" % (path.name, m.group(1)))
        self.assertEqual(found, [])


if __name__ == "__main__":
    unittest.main()
