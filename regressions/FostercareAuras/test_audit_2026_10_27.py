"""FostercareAuras audit 2026-10-27.

- Opening the editor no longer turns the positioning grid on; Show Grid does.
- Target auras are read in one ClassicAPI walk (GetAuraSlots + UnitAuraBySlot)
  instead of UnitBuff/UnitDebuff by index, which walked the list per index.
- The aura logic editor's OK and Cancel refresh the panel, icons and state:
  they called the editor's locals by global name, which were always nil.
- The update loop keeps its accumulators local, not as bare globals.
- The 246 unused MikPowerAuras textures (most of 25 MB) are gone.

The real _ScanTargetUnitAuras body runs under Lua 5.1 with a mocked slot API;
the grid and logic checks read the source (the editor is 12,000 lines of UI).
Grid look and real aura data stay in-game checks.
"""
from pathlib import Path
import os
import re
import unittest
from lupa.lua51 import LuaRuntime

ADDON = Path(os.environ["VANILLAFORGE_ADDON_ROOT"])
CONDITIONS = (ADDON / "Modules/FostercareConditions.lua").read_text("utf-8-sig")
EDIT = (ADDON / "Modules/FostercareEdit.lua").read_text("utf-8-sig")
LOGIC = (ADDON / "Modules/FostercareLogic.lua").read_text("utf-8-sig")

SCAN_MOCKS = r'''
auras = {
  HELPFUL = { { name = "Slice and Dice", icon = "Interface\\Icons\\Ability_Rogue_SliceDice", id = 5171 } },
  HARMFUL = { { name = "Rupture", icon = "Interface\\Icons\\Ability_Rogue_Rupture", id = 8640 },
              { name = "Expose Armor", icon = "Interface\\Icons\\Ability_Warrior_Riposte", id = 8649 } },
}
slotReads = 0
C_UnitAuras = {
  GetAuraSlots = function(unit, filter, _, _, out)
    local list = auras[filter]
    for i = 1, table.getn(list) do out[i] = filter .. i end
    return nil, table.getn(list)
  end,
  UnitAuraBySlot = function(unit, slot)
    slotReads = slotReads + 1
    local _, _, filter, i = string.find(slot, "^(%u+)(%d+)$")
    local a = auras[filter][tonumber(i)]
    return a.name, a.icon, 1, nil, 0, 0, nil, false, false, a.id
  end,
}
function UnitBuff() error("UnitBuff by index is not used any more") end
function UnitDebuff() error("UnitDebuff by index is not used any more") end
auraSnapshot = { target = { buffs = {}, debuffs = {}, buffIds = {}, debuffIds = {} } }
IconCache = {}
FostercareAurasDB = { cache = {}, spells = { Rupture_Debuff = {} } }
function _NP_SpellNameAndTexture(id) return nil end
function _GetTrackedByName() return { Rupture = { "Rupture_Debuff" } } end
iconFrame = { icon = { GetTexture = function() return nil end, SetTexture = function(self, t) self.tex = t end } }
function _GetIconFrame(key) return iconFrame end
'''


def scan_runtime():
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(SCAN_MOCKS)
    start = CONDITIONS.index("local _buffSlots, _debuffSlots")
    end = CONDITIONS.index("_G.FostercareConditions_ScanUnitAuras = _ScanTargetUnitAuras")
    lua.execute(CONDITIONS[start:end] + "\nScan = _ScanTargetUnitAuras\n")
    return lua


class TargetAuraScanTests(unittest.TestCase):
    def test_target_auras_come_from_one_slot_walk(self):
        lua = scan_runtime()
        lua.execute("Scan()")
        snap = lua.eval("auraSnapshot.target")
        self.assertTrue(snap.debuffs["Rupture"])
        self.assertTrue(snap.debuffs["Expose Armor"])
        self.assertTrue(snap.buffs["Slice and Dice"])
        self.assertTrue(snap.debuffIds[8640])
        self.assertEqual(lua.eval("slotReads"), 3)

    def test_tracked_debuff_updates_its_icon_and_spell_id(self):
        lua = scan_runtime()
        lua.execute("Scan()")
        self.assertEqual(lua.eval("iconFrame.icon.tex"), "Interface\\Icons\\Ability_Rogue_Rupture")
        self.assertEqual(lua.eval("FostercareAurasDB.spells.Rupture_Debuff.spellid"), "8640")


class EditorGridTests(unittest.TestCase):
    def test_opening_the_editor_does_not_show_the_grid(self):
        calls = [m.start() for m in re.finditer(r"(?<!function )FostercareEdit_ToggleGrid\(\)", EDIT)]
        button = EDIT.index('gridBtn:SetScript("OnClick"')
        # The only call left is the Show Grid button's own click.
        self.assertEqual(len(calls), 1)
        self.assertLess(button, calls[0])
        self.assertLess(calls[0] - button, 200)
        self.assertNotIn("Show Grid by default", EDIT)


class LogicRefreshTests(unittest.TestCase):
    def test_logic_editor_refreshes_through_public_functions(self):
        self.assertNotRegex(LOGIC, r"\b(SafeRefresh|SafeEvaluate|AuraCond_RefreshFromDB)\s*\(")
        self.assertIn("FostercareAuras_RefreshIcons()", LOGIC)
        self.assertIn("FostercareConditions_RequestEvaluate()", LOGIC)


class LeanTests(unittest.TestCase):
    def test_update_loop_accumulators_are_local(self):
        for name in ("_acc", "_textAccum", "_distAccum", "_timeEvalAccum", "_teFastAccum", "_teFastActive"):
            self.assertRegex(CONDITIONS, r"\nlocal %s = " % name, name)

    def test_unused_mikpowerauras_textures_are_gone(self):
        self.assertFalse((ADDON / "Textures" / "MPOWA").exists())


if __name__ == "__main__":
    unittest.main()
