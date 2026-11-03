"""FostercareNameplates audit, 2026-11-03.

With plate details turned off, every settings change (a castbar slider, for
example) ran the details shutdown again on every plate: it cleared the plate,
restored the mark and level and wrote alpha 1 over the game's own alpha.
Fails on 1.5.0.
"""
import unittest
from fnp_env import load


class DisabledDetails(unittest.TestCase):
    def test_settings_changes_leave_plates_alone_while_details_is_off(self):
        lua = load('{ ["Nameplate Details"] = 0, overwrites = {} }')
        lua.execute('''
            plate = nativePlate("0xF1", "nameplate1")
            plate:SetAlpha(0.5)
            FostercareNameplates.Nameplates:ApplyConfiguration()
            FostercareNameplates.Nameplates:ApplyConfiguration(true)
        ''')
        self.assertEqual(lua.eval("plate:GetAlpha()"), 0.5)

    def test_turning_details_off_restores_plates_once(self):
        lua = load()
        lua.execute('''
            plate = nativePlate("0xF1", "nameplate1")
            plate:SetAlpha(0.3)
            FostercareNameplates_Config["Nameplate Details"] = 0
            FostercareNameplates.Nameplates:ApplyConfiguration()
        ''')
        self.assertEqual(lua.eval("plate:GetAlpha()"), 1)
        lua.execute('plate:SetAlpha(0.5); FostercareNameplates.Nameplates:ApplyConfiguration()')
        self.assertEqual(lua.eval("plate:GetAlpha()"), 0.5)


if __name__ == "__main__":
    unittest.main()
