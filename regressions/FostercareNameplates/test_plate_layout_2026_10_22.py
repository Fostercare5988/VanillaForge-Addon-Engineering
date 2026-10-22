"""Reproductions for two FostercareNameplates 1.1.0 problems seen in play on 2026-10-21.

- Logout: Details.lua:87 "attempt to call method `SetWidth' (a nil value)" from
  Shutdown, after the client had freed the plate's raid mark.
- At plate size 0.6 the level text sat outside the plate: sizes scaled, native
  anchor offsets did not.
Real anchor values and engine timing stay in-game checks.
"""
import unittest
from fnp_env import load


def plate_with_regions(lua):
    """A bound plate whose seven native regions each have an offset anchor."""
    lua.execute('''
        local regions = {}
        for i = 2, 7 do
            regions[i] = CreateFrame("Texture")
            regions[i]:SetPoint("CENTER", "plate", "CENTER", 10 * i, -2 * i)
        end
        plate = nativePlate("0xF1", "nameplate1", regions)
    ''')


class PlateLayout(unittest.TestCase):
    def test_logout_skips_freed_plate_parts(self):
        """The client freed the raid mark (a table without methods) before
        PLAYER_LOGOUT; restoring it raised from Details.lua LayoutMark."""
        lua = load('{ overwrites = { nameplate_scale = 0.6 }, settingsVersion = 1 }')
        plate_with_regions(lua)
        lua.execute('''
            plate.raidicon.shown = true
            runFrames(plate, 2)
            setmetatable(plate.raidicon, nil)
            fire("PLAYER_LOGOUT")
        ''')
        self.assertTrue(lua.eval('FNPLibNameplate.stopping'))

    def test_level_text_follows_plate_size(self):
        """At plate size 0.6 the level text kept its full-size offset and its
        stock font, so it sat outside the shrunken border."""
        lua = load('{ overwrites = { nameplate_scale = 0.6 }, settingsVersion = 1 }')
        plate_with_regions(lua)
        level = 'plate.level'
        self.assertAlmostEqual(lua.eval(level + '.points[1][4]'), 40 * 0.6)
        self.assertAlmostEqual(lua.eval(level + '.points[1][5]'), -8 * 0.6)
        self.assertEqual(lua.eval(level + '.fontSize'), 7)
        self.assertAlmostEqual(lua.eval('plate.levelicon.points[1][4]'), 50 * 0.6)

    def test_logout_restores_native_layout(self):
        """Engine plates outlive a reload; the next UI must find stock offsets,
        font and opacity, not ours."""
        lua = load('{ overwrites = { nameplate_scale = 0.6 }, settingsVersion = 1 }')
        plate_with_regions(lua)
        lua.execute('plate:SetAlpha(0.5); fire("PLAYER_LOGOUT")')
        self.assertEqual(lua.eval('plate.level.points[1][4]'), 40)
        self.assertEqual(lua.eval('plate.level.fontSize'), 12)
        self.assertEqual(lua.eval('plate:GetAlpha()'), 1)


if __name__ == "__main__":
    unittest.main()
