"""TWThreat, hole finder leads closed on 2026-10-26.

- twtprint and twtdebug were globals; they are local to TWThreat.lua.
- Tank-mode bars targeted by hand: the GUID went through SetID (a number, too
  small for a 64-bit GUID) and fell back to TargetByName/AssistByName on the
  player's name, which targeted the wrong unit. The bars are ClassicAPI unit
  buttons now: unit = the creature's GUID, type1 = target.
- The undeclared FostercareTweaks.GetActiveTargetFrame lookup is gone.
Clicking a bar in tank mode stays an in-game check.
"""
from pathlib import Path
import os
import re
import unittest
from lupa.lua51 import LuaRuntime

ROOT = Path(os.environ["VANILLAFORGE_ADDON_ROOT"])
LUA = (ROOT / "TWThreat.lua").read_text("latin-1")
XML = (ROOT / "TWThreat.xml").read_text("latin-1")


def row_snippet():
    start = LUA.index("local button = _G['TMEF' .. i .. 'TargetButton']")
    end = LUA.index("_G['TMEF' .. i]:SetPoint", start)
    return LUA[start:end]


class TankModeBars(unittest.TestCase):
    def bar(self, guid):
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute('''
            local __find = string.find
            attrs = {}
            button = { SetAttribute = function(_, k, v) attrs[k] = v end,
                       GetAttribute = function(_, k) return attrs[k] end }
            _G["TMEF1TargetButton"] = button
            function run(guid, i) %s end
        ''' % row_snippet().replace("__find", "string.find"))
        lua.globals().run(guid, 1)
        return lua.eval("attrs")

    def test_creature_guid_becomes_the_unit(self):
        attrs = self.bar("0xF130000A0A001234")
        self.assertEqual(attrs["unit"], "0xF130000A0A001234")
        self.assertEqual(attrs["type1"], "target")

    def test_test_rows_have_no_unit(self):
        self.assertIsNone(self.bar("3")["unit"])

    def test_no_hand_made_targeting(self):
        for gone in ("TWTTargetButton_OnClick", "SetID(guid)", "AssistByName", "TargetByName"):
            self.assertNotIn(gone, LUA + XML)


class Globals(unittest.TestCase):
    def test_print_helpers_are_local(self):
        self.assertRegex(LUA, r"(?m)^local function twtprint\(")
        self.assertRegex(LUA, r"(?m)^local function twtdebug\(")

    def test_no_fostercaretweaks_lookup(self):
        self.assertNotIn("FostercareTweaks", LUA)

    def test_compiles(self):
        lua = LuaRuntime(unpack_returned_tuples=True)
        result = lua.globals().loadstring(LUA)
        self.assertTrue(callable(result) or (result and result[0]), result)


if __name__ == "__main__":
    unittest.main()
