"""FostercareNameplates, notes from play up to 2026-10-25.

- "Nameplate hp blinking all the time": the health text flickered. A plate
  that got a unit was hidden and redrawn a frame later, and the font was set
  again on every health update.
- Logout into ERROR #124: see test_plate_layout_2026_10_22.
Real flicker stays an in-game check.
"""
import unittest
from fnp_env import load

ALL_HEALTH = '{ overwrites = { nameplate_health_target = 0 }, settingsVersion = 1 }'


class HealthTextFlicker(unittest.TestCase):
    def test_new_plate_drawn_at_once(self):
        lua = load(ALL_HEALTH)
        lua.execute('plate = nativePlate("0xF1", "nameplate1")')
        self.assertTrue(lua.eval('plate.fnpHealth and plate.fnpHealth.shown'))
        self.assertEqual(lua.eval('plate.fnpHealth.fnpText'), "50%")

    def test_plate_coming_back_never_hides_text(self):
        lua = load(ALL_HEALTH)
        lua.execute('''
            plate = nativePlate("0xF1", "nameplate1")
            hidden = 0
            local hide = plate.fnpHealth.Hide
            plate.fnpHealth.Hide = function(self) hidden = hidden + 1; hide(self) end
            fire("NAME_PLATE_UNIT_ADDED", "nameplate1")
            runFrames(plate, 3)
        ''')
        self.assertEqual(lua.eval('hidden'), 0)

    def test_font_set_once_across_health_updates(self):
        """GetFont may report a scaled height that never equals our size."""
        lua = load(ALL_HEALTH)
        lua.execute('''
            plate = nativePlate("0xF1", "nameplate1")
            local label = plate.fnpHealth
            label.GetFont = function() return STANDARD_TEXT_FONT, 8.9999, "OUTLINE" end
            sets = 0
            label.SetFont = function() sets = sets + 1 end
            for _ = 1, 5 do FostercareNameplates.Nameplates:Health(plate, "0xF1") end
        ''')
        self.assertEqual(lua.eval('sets'), 0)


if __name__ == "__main__":
    unittest.main()
