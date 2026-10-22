"""FostercareNameplates plate layout, from play on 2026-10-21 and 10-22.

- Logout: Details.lua:87 "attempt to call method `SetWidth' (a nil value)" from
  Shutdown, after the client had freed the plate's raid mark.
- At plate size 0.6 the native level text spilled off the plate. Moving or
  re-fonting it crashed the client, so the addon now hides it by alpha and
  draws its own level in the border's oval.
Engine timing and the crash itself stay in-game checks.
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


LEVEL = '''
    levels = { ["0xF1"] = 54 }
    function UnitLevel(u) return levels[u] end
    function GetDifficultyColor() return { r = 0.25, g = 0.75, b = 0.25 } end
'''


class OwnLevel(unittest.TestCase):
    def level(self, saved="{ overwrites = { nameplate_scale = 0.6 }, settingsVersion = 1 }"):
        lua = load(saved, prelude=LEVEL)
        plate_with_regions(lua)
        lua.execute('FostercareNameplates.Nameplates:Level(plate, "0xF1")')
        return lua

    def test_level_drawn_inside_bar(self):
        """Level shows in our label with the difficulty color; native level
        text and skull are only made transparent."""
        lua = self.level()
        self.assertEqual(lua.eval('plate.fnpLevel.fnpText'), 54)
        self.assertEqual(lua.eval('plate.fnpLevel.fnpG'), 0.75)
        self.assertEqual(lua.eval('plate.level:GetAlpha()'), 0)
        self.assertEqual(lua.eval('plate.levelicon:GetAlpha()'), 0)

    def test_level_centered_in_oval(self):
        """Inside the bar it crowded the health text and left the border's
        level oval empty; the oval's center is a tenth of the bar width past
        the bar's right end."""
        lua = self.level()
        point = lua.eval('{ plate.fnpLevel:GetPoint(1) }')
        self.assertEqual((point[1], point[3], point[4]), ("CENTER", "RIGHT", 11))
        self.assertTrue(lua.eval('select(2, plate.fnpLevel:GetPoint(1)) == plate.healthbar'))

    def test_native_level_never_moved_or_refonted(self):
        """1.1.1 re-anchored and re-fonted the engine's level text and the
        client crashed on login. Only alpha may change."""
        lua = self.level()
        self.assertEqual(lua.eval('plate.level.points[1][4]'), 40)
        self.assertEqual(lua.eval('plate.levelicon.points[1][4]'), 50)
        self.assertIsNone(lua.eval('plate.level.fontSize'))

    def test_skull_level(self):
        lua = self.level()
        lua.execute('levels["0xF1"] = -1; FostercareNameplates.Nameplates:Level(plate, "0xF1")')
        self.assertEqual(lua.eval('plate.fnpLevel.fnpText'), "??")

    def test_setting_off_restores_native(self):
        lua = self.level('{ overwrites = { nameplate_level = 0 }, settingsVersion = 1 }')
        self.assertIsNone(lua.eval('plate.fnpLevel'))
        self.assertEqual(lua.eval('plate.level:GetAlpha()'), 1)

    def test_logout_restores_native_level(self):
        lua = self.level()
        lua.execute('fire("PLAYER_LOGOUT")')
        self.assertEqual(lua.eval('plate.level:GetAlpha()'), 1)
        self.assertEqual(lua.eval('plate.levelicon:GetAlpha()'), 1)


if __name__ == "__main__":
    unittest.main()
