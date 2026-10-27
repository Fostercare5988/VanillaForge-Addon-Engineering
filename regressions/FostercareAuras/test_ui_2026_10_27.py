"""Main window rebuild, 2026-10-27.

- One ForgeUI window: type track (Ability, Buff, Debuff, Item), add row, a
  one-line hint, the tracker list (click edits, X removes), Show all and the
  Item tooltips switch. No separate Settings window, no pfUI option, no
  four-line guide.
- Bars, Groups/categories, custom code, logic, pet tracking, Export and the
  Turtle buff data are gone from the TOC.
- RefreshIcons(true) is honoured: the throttle ignored its argument, so the
  refresh after a removal could be skipped (fails on 29c4fee).

Window look and clicks stay in-game checks.
"""
from pathlib import Path
import os
import unittest
from lupa.lua51 import LuaRuntime

ADDON = Path(os.environ["VANILLAFORGE_ADDON_ROOT"])
MAIN = (ADDON / "FostercareAuras.lua").read_text("utf-8-sig")
TOC = (ADDON / "FostercareAuras.toc").read_text("utf-8", "replace")


class RefreshThrottleTests(unittest.TestCase):
    def test_forced_refresh_runs_inside_the_throttle_window(self):
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute("now = 100; function GetTime() return now end")
        start = MAIN.index("local _lastRefresh = 0")
        end = MAIN.index("local function RebuildOrder()")
        lua.execute(MAIN[start:end] + "\nCan = _CanRunRefresh\n")
        self.assertTrue(lua.eval("Can()"))
        self.assertFalse(lua.eval("Can()"))
        self.assertTrue(lua.eval("Can(true)"))


class WindowTests(unittest.TestCase):
    def test_one_forgeui_window_with_the_four_types(self):
        self.assertIn('UI.Window("FostercareAurasFrame"', MAIN)
        self.assertIn('local TYPES = { "Ability", "Buff", "Debuff", "Item" }', MAIN)
        self.assertIn('"Weapon tooltips"', MAIN)  # renamed in the rogue pass
        self.assertLess(TOC.index("ForgeUI.lua"), TOC.index("FostercareAuras.lua"))

    def test_no_settings_window_pfui_or_long_guide(self):
        for gone in ("FostercareSettings", "pfUI.api", "FostercareAuras_HasPfUI", "Guide:", "FostercareAurasSettingsFrame", "Rename"):
            self.assertNotIn(gone, MAIN + TOC, gone)


class RetiredModuleTests(unittest.TestCase):
    def test_retired_modules_are_not_loaded(self):
        for name in ("FostercareBars", "FostercareGroup", "FostercareExport", "FostercareLogic",
                     "FostercarePetAuras", "FostercareBuffData", "FostercareSettings"):
            self.assertNotIn(name, TOC, name)
            self.assertFalse((ADDON / "Modules" / (name + ".lua")).exists(), name)


CONDITIONS = (ADDON / "Modules/FostercareConditions.lua").read_text("utf-8-sig")
EDIT = (ADDON.parent / "FostercareAuras_Edit" / "FostercareEdit.lua").read_text("utf-8-sig")
TARGET = (ADDON / "Modules/FostercareTargetAuras.lua").read_text("utf-8-sig")


class EditorOnDemandTests(unittest.TestCase):
    """Batch E: the editor is the load-on-demand addon FostercareAuras_Edit."""

    def test_editor_is_its_own_load_on_demand_addon(self):
        toc = (ADDON.parent / "FostercareAuras_Edit" / "FostercareAuras_Edit.toc").read_text("utf-8", "replace")
        self.assertIn("## LoadOnDemand: 1", toc)
        self.assertIn("## Dependencies: FostercareAuras", toc)
        self.assertNotIn("FostercareEdit.lua", TOC)

    def test_first_edit_loads_the_editor(self):
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute('''
            opened, loads = nil, 0
            function LoadAddOn(name)
                loads = loads + 1
                FostercareConditions_Show = function(key) opened = key end
                return 1
            end
            DEFAULT_CHAT_FRAME = { AddMessage = function() end }
        ''')
        start = MAIN.index("local function FA_OpenEditor(key)")
        end = MAIN.index("local function Row_OnClick()")
        lua.execute(MAIN[start:end] + "\nOpen = FA_OpenEditor\n")
        lua.execute('Open("Rupture_Debuff"); Open("Envenom_Buff")')
        self.assertEqual(lua.eval("loads"), 1)
        self.assertEqual(lua.eval("opened"), "Envenom_Buff")


class IdleHandlerTests(unittest.TestCase):
    """Batch D: frames that ran OnUpdate every frame doing nothing now sleep."""

    def test_edit_heartbeat_and_throttle_start_hidden_and_hide_when_idle(self):
        self.assertIn("_editTick:Hide()", CONDITIONS)
        self.assertIn("_FostercareEdit_Throttle:Hide()", EDIT)
        self.assertIn("_FostercareEdit_Throttle:Show()", EDIT)
        self.assertIn("FostercareEditTick:Show()", EDIT)

    def test_delayed_init_is_one_restartable_timer(self):
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute('''
            timers, inits = {}, 0
            C_Timer = { NewTimer = function(_, fn)
                local t = { fn = fn, Cancel = function(self) self.cancelled = true end }
                table.insert(timers, t); return t end }
            FostercareTrack = { _frame = {}, _OnPlayerLogin = function() inits = inits + 1 end }
        ''')
        start = TARGET.index("function FostercareTrack:_ScheduleDelayedInit()")
        end = TARGET.index("\nend\n", start) + 5
        lua.execute(TARGET[start:end])
        lua.execute("FostercareTrack:_ScheduleDelayedInit(); FostercareTrack:_ScheduleDelayedInit()")
        lua.execute("for _, t in ipairs(timers) do if not t.cancelled then t.fn() end end")
        lua.execute("timers[1].fn()")  # a cancelled callback that was already dispatched
        self.assertEqual(lua.eval("inits"), 1)
        self.assertTrue(lua.eval("timers[1].cancelled"))


if __name__ == "__main__":
    unittest.main()
