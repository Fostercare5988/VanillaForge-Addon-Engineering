"""ClassicAPI 1.17.11 pass, 2026-10-27.

- The conditions frame takes unit events only for the units it reads: health
  and auras for player and target, power for the player. ClassicAPI fires
  unit events once per token, nameplates and raid members included.
- Name sorts compare with strcmputf8i (1.17.11), which builds no lowered
  copies; no sort lowers both sides any more.
"""
import re
import unittest

import test_condition_delivery as tcd

ROOT = tcd.ADDON


class UnitEventScopeTests(unittest.TestCase):
    def test_unit_events_only_for_the_units_read(self):
        lua = tcd.runtime()
        expect = {"UNIT_AURA": ["player", "target"], "UNIT_HEALTH": ["player", "target"],
                  "UNIT_MANA": ["player"], "UNIT_ENERGY": ["player"], "UNIT_RAGE": ["player"]}
        for ev, units in expect.items():
            reg = lua.eval('eventFrame.events.%s' % ev)
            self.assertEqual(list(reg.values()), units, ev)


class SortTests(unittest.TestCase):
    def test_no_sort_lowers_both_sides(self):
        found = []
        for path in ROOT.rglob("*.lua"):
            text = path.read_text("utf-8-sig", errors="replace")
            for m in re.finditer(r'string\.lower\(\s*a\b', text):
                found.append("%s:%d" % (path.name, text.count("\n", 0, m.start()) + 1))
        self.assertEqual(found, [])

    def test_sorts_use_strcmputf8i(self):
        main = (ROOT / "FostercareAuras.lua").read_text("utf-8-sig")
        edit = (ROOT.parent / "FostercareAuras_Edit" / "FostercareEdit.lua").read_text("utf-8-sig")
        self.assertIn("strcmputf8i(", main)
        self.assertEqual(edit.count("strcmputf8i(a or \"\", b or \"\") < 0"), 4)


if __name__ == "__main__":
    unittest.main()
