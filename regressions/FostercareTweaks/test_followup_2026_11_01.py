"""FostercareTweaks follow-up to the 2026-11-01 audit (the player's decisions).

- Energy and mana ticks: the line waited for a first observed gain, so at full
  energy or mana (after login, a reload, a shapeshift or a respawn) it never
  showed until the player spent some. It now runs at once on a two-second
  cycle; the first gain sets the phase, and the edge flashes only then.
- WorldMap Window retired for the client's own windowed map; a character that
  used it keeps a window (WORLDMAP_WINDOWED).
- Settings: one Ctrl+Shift hint on General and Unit Frames (action bars move
  with Move bars), Minimap size under Minimap, clearer labels and tooltips,
  "Reset all positions" names everything it resets.

Each test fails on e846905 unless marked as a control. Widget mocks count
calls; they prove our writes, not the engine's drawing.
"""
import unittest

from test_audit_2026_10_26 import runtime, source
from test_audit_2026_11_01 import core


class TickRunsBeforeTheFirstGain(unittest.TestCase):
    def start(self, power_type=3, value=100):
        lua = self.lua = runtime()
        lua.execute(r'''
            now, mana, powerType = 100, %d, %d
            function GetTime() return now end
            function UnitMana() return mana end
            function UnitPowerType() return powerType end
            C_Timer.After = function(_, fn) fn() end
            PlayerFrameManaBar.IsVisible = function() return true end
            PlayerFrameManaBar.GetEffectiveScale = function() return 1 end
            textures = {}
            function PlayerFrameManaBar:CreateTexture()
                local t = Widget()
                t.alpha = 0
                t.SetAlpha = function(self, a) self.alpha = a end
                textures[#textures + 1] = t
                return t
            end
        ''' % (value, power_type))
        lua.execute(source("mods/unitframe-energytick.lua"))
        lua.execute('FT.mods["Show Energy Ticks"]:enable()')
        return lua

    def render(self, at):
        self.lua.execute('now = %s; FCTweaksEnergyTick.scripts.OnUpdate()' % at)
        return self.lua.eval('textures[1].alpha')          # the edge pulse

    def test_full_energy_runs_at_login(self):
        lua = self.start()
        self.assertTrue(lua.eval('FCTweaksEnergyTick.scripts.OnUpdate ~= nil'))

    def test_full_mana_runs_at_login(self):
        lua = self.start(power_type=0)
        self.assertTrue(lua.eval('FCTweaksEnergyTick.scripts.OnUpdate ~= nil'))

    def test_no_flash_until_a_gain_sets_the_phase(self):
        lua = self.start(value=80)
        self.assertEqual(self.render(100.1), 0)             # guessed cycle: no beat
        lua.execute('now = 101; mana = 100; fire(FCTweaksEnergyTick, "UNIT_POWER_UPDATE", "player")')
        self.assertGreater(self.render(101.1), 0)           # the gain set the phase

    def test_the_first_gain_sets_the_phase_off_the_guess(self):
        # Control: a gain half way through the guessed cycle is still the
        # first real tick, not an off-phase gain to reject.
        lua = self.start(value=80)
        lua.execute('now = 101; mana = 100; fire(FCTweaksEnergyTick, "UNIT_POWER_UPDATE", "player")')
        self.assertEqual(lua.eval('FCTweaksEnergyTick.start'), 101)


class WorldMapWindowRetired(unittest.TestCase):
    def initialize(self, saved, windowed):
        lua = core()
        lua.execute('''
            minimized = 0
            WORLDMAP_WINDOWED = %d
            function WorldMapFrame_Minimize() minimized = minimized + 1 end
            FostercareTweaks_Config["WorldMap Window"] = %s
            FostercareTweaks:Initialize()
        ''' % (windowed, saved))
        return lua

    def test_a_character_that_used_it_keeps_a_window(self):
        lua = self.initialize("1", 0)
        self.assertEqual(lua.eval("WORLDMAP_WINDOWED"), 1)
        self.assertEqual(lua.eval("minimized"), 1)
        self.assertIsNone(lua.eval('FostercareTweaks_Config["WorldMap Window"]'))

    def test_others_keep_the_full_screen_map(self):
        lua = self.initialize("0", 0)
        self.assertEqual(lua.eval("WORLDMAP_WINDOWED"), 0)
        self.assertEqual(lua.eval("minimized"), 0)
        self.assertIsNone(lua.eval('FostercareTweaks_Config["WorldMap Window"]'))

    def test_the_client_owns_the_map_window(self):
        code = source("mods/worldmap-window.lua")
        for gone in ("WorldMap Window", "ToggleWorldMap", "UIPanelWindows", "SetScale(0.85)"):
            self.assertNotIn(gone, code)
        self.assertIn('title = "WorldMap Coordinates"', code)  # control: the rest stays
        self.assertIn('title = "WorldMap Class Colors"', code)
        self.assertNotIn("WorldMap Window", source("Settings.lua"))


class SettingsWording(unittest.TestCase):
    MOVE = "Hold Ctrl+Shift to move frames, aura areas, the raid frames and minimap pieces. Action bars: Move bars."

    def test_one_move_hint_on_general_and_unit_frames(self):
        code = source("Settings.lua")
        self.assertIn('local MOVE_HINT = "%s"' % self.MOVE, code)
        self.assertIn("Hint(general, MOVE_HINT", code)
        self.assertIn("Hint(unit, MOVE_HINT", code)
        self.assertNotIn("raid frames and action bars", code)

    def test_minimap_size_sits_under_minimap(self):
        code = source("Settings.lua")
        self.assertRegex(code, r'Slider\(general, "minimap_scale"[^\n]*, LEFT, ')
        self.assertLess(code.index('UI.Heading(general, "Minimap"'), code.index('"minimap_scale"'))

    def test_labels_and_tooltips(self):
        code = source("Settings.lua")
        self.assertIn('"Dismount to attack, fly, talk"', code)
        self.assertNotIn("Spells do this in ClassicAPI", code)
        self.assertNotIn('"Target buffs", nil', code)
        self.assertNotIn('"Target debuffs", nil', code)
        self.assertIn('"Reset all positions"', code)
        self.assertIn("the minimap pieces back in place", code)
        clock = source("mods/minimap-tweaks.lua")
        self.assertIn('"Local time"', clock)
        self.assertIn('"Server time"', clock)


if __name__ == "__main__":
    unittest.main()
