"""FostercareNameplates plate alpha under ClassicAPI 1.17.8 (2026-10-26).

1.17.8 makes GetAlpha on a default plate return the drawn byte (n/255), and the
nameplateSelectedAlpha / nameplateNotSelectedAlpha CVars replace a plate write
of byte 255 / 127. Render compared GetAlpha with the wanted value, so a faded
plate (0.3), a marked plate (0.9) or a changed CVar wrote SetAlpha every frame.
Fails on 1.4.1. The engine's own rounding stays an in-game check.
"""
import unittest
from fnp_env import load

# The plate mock stores alpha as 1.17.8 does: as a byte, with CVar substitution.
PLATE = '''
    cvars = { selected = 1, notSelected = 0.5 }
    plate = nativePlate("0xF1", "nameplate1")
    writes = 0
    function plate:SetAlpha(v)
        writes = writes + 1
        local byte = math.floor(v * 255 + 0.5)
        if byte == 255 then byte = math.floor(cvars.selected * 255 + 0.5)
        elseif byte == 127 then byte = math.floor(cvars.notSelected * 255 + 0.5) end
        self.alpha = byte / 255
    end
    function fade(key) FostercareNameplates.SetOverride(key, 1); FostercareNameplates.Nameplates:ApplyConfiguration() end
'''


class PlateAlpha(unittest.TestCase):
    def writes_over(self, lua, frames=30):
        lua.execute("runFrames(plate, 2); writes = 0; runFrames(plate, %d)" % frames)
        return lua.eval("writes")

    def test_faded_plate_is_written_once(self):
        """The default fade, 0.3, is no whole byte."""
        lua = load(prelude='units["0xF1"] = { type = 8 }')
        lua.execute(PLATE + 'fade("nameplate_fade_critters")')
        self.assertEqual(self.writes_over(lua), 0)
        self.assertAlmostEqual(lua.eval("plate:GetAlpha()"), 0.3, delta=1 / 255)

    def test_player_cvar_does_not_cause_rewrites(self):
        """With nameplateSelectedAlpha at 0.9, our write of 1 draws at 0.9."""
        lua = load(prelude='units["0xF1"] = { type = 7 }')
        lua.execute(PLATE + 'cvars.selected = 0.9; plate:SetAlpha(1)')  # the engine's write
        self.assertEqual(self.writes_over(lua), 0)
        self.assertAlmostEqual(lua.eval("plate:GetAlpha()"), 0.9, delta=1 / 255)

    def test_engine_fade_is_overridden(self):
        """A write by the engine still gets our alpha back the next frame."""
        lua = load(prelude='units["0xF1"] = { type = 8 }')
        lua.execute(PLATE + 'fade("nameplate_fade_critters"); runFrames(plate, 2)')
        lua.execute("plate.alpha = 0.5; runFrames(plate, 1)")
        self.assertAlmostEqual(lua.eval("plate:GetAlpha()"), 0.3, delta=1 / 255)


if __name__ == "__main__":
    unittest.main()
