"""Review fixes (2026-11-10, the player's go-ahead on the review's findings).

Each test fails on c7ef5cf, the code the review read.
"""
import unittest

from test_audit_2026_10_25 import source
from test_watched_auras_2026_11_02 import watched


class OnlyMineKeepsOthersInTheRow(unittest.TestCase):
    # A watched target debuff was kept out of the target row by name alone, so
    # with "Only mine" another player's debuff of that name showed nowhere.
    def test_the_row_drops_only_your_own(self):
        lua = watched()
        lua.execute('W.Add("Corruption", "target")')                       # Only mine by default
        self.assertTrue(lua.eval('FT.IsAuraHidden("Corruption", "target", nil, "player")'))
        self.assertFalse(lua.eval('FT.IsAuraHidden("Corruption", "target", nil, "party2")'))
        self.assertFalse(lua.eval('FT.IsAuraHidden("Corruption", "target", nil, nil)'))

    def test_anyones_icon_takes_every_cast_from_the_row(self):
        lua = watched()
        lua.execute('W.Add("Corruption", "target"); W.SetMine(1, false)')
        self.assertTrue(lua.eval('FT.IsAuraHidden("Corruption", "target", nil, "party2")'))
        lua.execute('W.SetMine(1, true)')                                  # the switch rebuilds the rule
        self.assertFalse(lua.eval('FT.IsAuraHidden("Corruption", "target", nil, "party2")'))

    def test_the_rows_pass_the_caster(self):
        text = source("mods/unitframes/auras.lua")
        self.assertIn("FT.IsAuraHidden(name, unit, nil, source)", text)
        self.assertIn("FT.IsAuraHidden(d.name, unit, nil, d.sourceUnit)", text)

    def test_no_aura_read_for_a_unit_with_nothing_watched(self):
        lua = watched('reads = 0')
        lua.execute('local get = C_UnitAuras.GetAuraSlots;'
                    ' C_UnitAuras.GetAuraSlots = function(...) reads = reads + 1; return get(...) end')
        lua.execute('W.Add("Envenom", "player"); reads = 0; fire(events, "PLAYER_TARGET_CHANGED")')
        self.assertEqual(lua.eval("reads"), 0)
        lua.execute('fire(events, "UNIT_AURA_DELTA", "player", {})')
        self.assertEqual(lua.eval("reads"), 1)


class CenterTheRightBarsRetired(unittest.TestCase):
    # Custom layouts place the right bar; only characters with custom layouts had it on.
    def test_no_trace_and_the_saved_switch_is_cleared(self):
        for path in ("mods/actionbar-float.lua", "Settings.lua", "Defaults.lua"):
            self.assertNotIn("Center Vertical Actionbar", source(path), path)
        self.assertIn('FostercareTweaks_Config["Center Vertical Actionbar"] = nil', source("Core.lua"))


if __name__ == "__main__":
    unittest.main()
