"""TWThreat, hole finder leads closed on 2026-10-26 (rewritten on 2026-11-07
against the full-file harness, twt_env.py).

- twtprint was a global; it is local to TWThreat.lua.
- Tank-mode bars targeted by hand: the GUID went through SetID (a number, too
  small for a 64-bit GUID) and fell back to TargetByName/AssistByName on the
  player's name, which targeted the wrong unit. The bars are ClassicAPI unit
  buttons now: unit = the creature's GUID, type1 = target.
- The undeclared FostercareTweaks.GetActiveTargetFrame lookup is gone.
Clicking a bar in tank mode stays an in-game check.
"""
import unittest
from lupa.lua51 import LuaRuntime

from twt_env import load, SOURCE, XML

TANK = ("Me:1:1000:100:1;A:0:500:50:1#TMTv1="
        "Ghoul:0xF130000A0A001234:Bob:78;Stalker:0xF130000A0A001235:Alice:95")


class TankModeBars(unittest.TestCase):
    def fight(self):
        lua = load("{ tankMode = true }", 'playerClass = "WARRIOR"')
        lua.execute('startFight(); packet("%s"); run(1)' % TANK)
        return lua

    def test_creature_guid_becomes_the_unit(self):
        lua = self.fight()
        # Rows are ordered by threat percent: Stalker (95) first.
        self.assertEqual(lua.eval("TMEF1TargetButton.attrs.unit"), "0xF130000A0A001235")
        self.assertEqual(lua.eval("TMEF2TargetButton.attrs.unit"), "0xF130000A0A001234")
        self.assertEqual(lua.eval("TMEF1TargetButton.attrs.type1"), "target")
        self.assertTrue(lua.eval("TWTMainTankModeWindow.shown"))
        self.assertEqual(lua.eval("TMEF1Perc.text"), "95%")

    def test_tank_rows_glide(self):
        lua = self.fight()
        lua.execute('tick(); packet("Me:1:1000:100:1;A:0:500:50:1#TMTv1='
                    'Ghoul:0xF130000A0A001234:Bob:38;Stalker:0xF130000A0A001235:Alice:95"); run(0.25)')
        value = int(lua.eval("TMEF2Perc.text").rstrip("%"))
        self.assertTrue(38 < value < 78, value)

    def test_one_creature_hides_the_window(self):
        lua = load("{ tankMode = true }", 'playerClass = "WARRIOR"')
        lua.execute('startFight(); packet("Me:1:1000:100:1#TMTv1=Ghoul:0xF130000A0A001234:Bob:78"); run(1)')
        self.assertFalse(lua.eval("TWTMainTankModeWindow.shown"))

    def test_test_rows_have_no_unit(self):
        lua = load("{ tankMode = true }", 'playerClass = "WARRIOR"')
        lua.execute("TWTSettingsToggle_OnClick()")
        self.assertTrue(lua.eval("TMEF1.shown"))
        self.assertIsNone(lua.eval("TMEF1TargetButton.attrs.unit"))

    def test_no_hand_made_targeting(self):
        for gone in ("TWTTargetButton_OnClick", "SetID(guid)", "AssistByName", "TargetByName"):
            self.assertNotIn(gone, SOURCE + XML)


class Globals(unittest.TestCase):
    def test_print_helper_is_local(self):
        self.assertRegex(SOURCE, r"(?m)^local function twtprint\(")

    def test_no_fostercaretweaks_lookup(self):
        self.assertNotIn("FostercareTweaks", SOURCE)

    def test_compiles(self):
        lua = LuaRuntime(unpack_returned_tuples=True)
        result = lua.globals().loadstring(SOURCE)
        self.assertTrue(callable(result) or (result and result[0]), result)


if __name__ == "__main__":
    unittest.main()
