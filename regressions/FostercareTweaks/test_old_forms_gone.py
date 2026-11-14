"""2006 forms the audit of 2026-11-13 took out (1.20.0); each fails on 4010322.

- FT.rgbhex decoded its arguments by type (a table with r/g/b, an array or
  numbers) to build a colour code; ClassicAPI's C_ClassColor.GetClassColor
  gives the class colour's markup (and follows Blue Shamans).
- Lua 5.0's global gsub and `_G.arg1 or 0` in script handlers.
- MODIFIER_STATE_CHANGED names LSHIFT and RSHIFT only: the "any SHIFT" branch
  never ran. The ShapeshiftBar_Update guard checked a FrameXML function that
  always exists; `UnitHealth(unit) or 0` a unit already checked to exist.
- The raid bars wrapped their own SetStatusBarColor to colour the background;
  raid.lua's SetBarColor, which remembers the colour, sets both.
"""
import re
import unittest

from test_audit_2026_10_26 import ROOT


def lua_files():
    return [p for p in ROOT.rglob("*.lua") if p.name not in ("ForgeUI.lua", "ForgeLayout.lua")]


class OldFormsGone(unittest.TestCase):
    def test_no_type_decoding_colour_helper(self):
        for path in lua_files():
            self.assertNotIn("rgbhex", path.read_text("utf-8-sig"), path.name)

    def test_no_lua50_globals_in_handlers(self):
        for path in lua_files():
            text = path.read_text("utf-8-sig")
            self.assertIsNone(re.search(r"(?<![.\w])gsub\(", text), path.name)
            self.assertNotIn("_G.arg1", text, path.name)

    def test_no_fallbacks_for_what_always_exists(self):
        self.assertNotIn('string.find(key, "SHIFT")', (ROOT / "mods/equip-compare.lua").read_text("utf-8-sig"))
        self.assertNotIn("elseif ShapeshiftBar_Update then", (ROOT / "mods/gameplay.lua").read_text("utf-8-sig"))
        for path in lua_files():
            self.assertIsNone(re.search(r"UnitHealth(Max)?\([^)]*\) or 0", path.read_text("utf-8-sig")), path.name)

    def test_native_hookscript_not_a_hand_made_one(self):
        # 2026-11-14: FT.HookScript rebuilt ClassicAPI's frame:HookScript, which
        # passes the same arguments to both handlers (API.md, frame:HookScript).
        for path in lua_files():
            self.assertNotIn("FT.HookScript", path.read_text("utf-8-sig"), path.name)

    def test_bars_keep_their_own_methods(self):
        core = (ROOT / "mods/unitframes/core.lua").read_text("utf-8-sig")
        self.assertNotIn("bar.SetStatusBarColor =", core)
        raid = (ROOT / "mods/unitframes/raid.lua").read_text("utf-8-sig")
        self.assertIn("bar.bg:SetVertexColor(r * 0.2, g * 0.2, b * 0.2, 1)", raid)


if __name__ == "__main__":
    unittest.main()
