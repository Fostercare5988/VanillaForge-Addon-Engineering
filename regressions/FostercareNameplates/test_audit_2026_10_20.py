"""Reproductions for the 2026-10-20 FostercareNameplates audit
(.private/audit-FostercareNameplates-2026-10-20.md).

Each test fails on FostercareNameplates 1.0.0 for the reason in its docstring.
Lua 5.1 with generic mocks; native plates and engine timing stay in-game checks.
"""
import unittest
from fnp_env import load


class AuditReproductions(unittest.TestCase):
    def test_p2_master_switch_off_is_honored(self):
        """P2-1: Lifecycle.lua reads the saved master switch at file scope, before
        the client restores SavedVariables, so a saved 0 still claims every plate."""
        lua = load("{ nameplatesEnabled = 0, overwrites = {}, settingsVersion = 1 }")
        self.assertFalse(lua.eval("FostercareNameplates.nameplatesEnabled"))
        self.assertFalse(lua.eval("FostercareNameplates.OwnsNameplates() and true or false"))
        self.assertIsNone(lua.eval('FNPLibNameplate.events.NAME_PLATE_UNIT_ADDED'))

    def test_p2_saved_module_choice_reaches_initialize(self):
        """P2-1: Core.lua keeps a local alias of the pre-restore table, so Initialize
        reads defaults, not the saved module choice, when deciding what to enable."""
        lua = load('{ ["Nameplate Castbar"] = 0, overwrites = {}, settingsVersion = 1 }')
        self.assertEqual(lua.eval('FostercareNameplates_Config["Nameplate Castbar"]'), 0)
        self.assertIsNone(lua.eval('rawget(_G, "FNPNameplateCastEvents")'))

    def test_p2_guid_lookup_uses_guid_api(self):
        """P2-2: GUIDs went to GetNamePlateForUnit, which ClassicAPI documents for unit
        tokens; GetNamePlateForGUID is the documented GUID lookup."""
        lua = load(prelude='''
            plate = CreateFrame("Button")
            C_NamePlate.GetNamePlateForUnit = function(u)
                if string.find(u, "^0x") then return nil end
                if u == "nameplate1" then return plate end
            end
            C_NamePlate.GetNamePlateForGUID = function(g) if g == "0xF1" then return plate end end
        ''')
        lua.execute('plate.fnpUnitGUID = "0xF1"')
        self.assertEqual(lua.eval("FostercareNameplates.GetNameplateUnit(plate)"), "0xF1")


if __name__ == "__main__":
    unittest.main()
