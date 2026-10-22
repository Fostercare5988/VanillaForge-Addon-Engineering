"""Reproduction for a FostercareNameplates 1.1.0 problem seen in play on 2026-10-21.

- Logout: Details.lua:87 "attempt to call method `SetWidth' (a nil value)" from
  Shutdown, after the client had freed the plate's raid mark.
Engine timing stays an in-game check.
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


if __name__ == "__main__":
    unittest.main()
