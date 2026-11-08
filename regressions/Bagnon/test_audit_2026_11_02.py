"""Bagnon audit repros (2026-11-02). Fail on the audited code.

1. Item.lua writes the font and the fallback icon paths with single backslashes.
   Lua 5.0 drops the backslash of an unknown escape, so the paths read
   "FontsFRIZQT__.TTF" and "InterfaceIconsINV_Misc_QuestionMark": the enchant
   countdown font and the fallback icon never load.
2. An item on a cooldown it has not started (enable == 0) is dimmed by
   BagnonItem_UpdateCooldown, and the very next call, SetItemButtonDesaturated, sets
   the icon colour back to white, so the dimming never shows.
3. A quiver, soul bag or herb bag in the bank is never tinted: Bagnon_BagFamily asked
   GetContainerNumFreeSlots, which answered (0, 0) for bank bags. Since ClassicAPI
   1.19.3 it answers the open bank's family, so a live bank bag asks it again.
"""
import re
import unittest
from bgn_env import ROOT, load

BS = chr(92)
# Escapes Lua 5.0 knows: a b f n r t v, backslash, quotes, brackets, digits, line break.
KNOWN = "abfnrtv" + BS + chr(34) + chr(39) + "[]0123456789" + chr(10) + chr(13)
ESCAPE = re.compile(re.escape(BS) + "(.)", re.S)
STRING = re.compile(chr(34) + "(?:[^" + chr(34) + re.escape(BS) + "]|" + re.escape(BS) + ".)*" + chr(34))


class StringEscapes(unittest.TestCase):
    def test_no_lua_file_has_an_unknown_escape_in_a_string(self):
        bad = []
        for path in ROOT.rglob("*.lua"):
            for number, line in enumerate(path.read_text("utf-8-sig").splitlines(), 1):
                for literal in STRING.findall(line.split("--")[0]):
                    if any(m.group(1) not in KNOWN for m in ESCAPE.finditer(literal)):
                        bad.append("%s:%d %s" % (path.relative_to(ROOT), number, literal))
        self.assertEqual(bad, [])


class CooldownDimming(unittest.TestCase):
    def test_item_waiting_for_its_cooldown_stays_dimmed(self):
        lua = load("utility", "frame", "item")
        lua.execute('''
            icon = { r = 1 }
            function SetItemButtonDesaturated(b, d) icon.r = 1 end
            function SetItemButtonTextureVertexColor(b, r) icon.r = r end
            function SetItemButtonTexture() end
            function SetItemButtonCount() end
            function CooldownFrame_SetTimer() end
            function GetContainerItemCooldown() return 10, 30, 0 end
            function GetContainerItemInfo() return "tex", 1, nil, 1, nil end
            Bagnon_SetAtBank(true)
            local parent = widget(nil, 0); parent.parent = widget("Bagnon"); parent.parent.player = "Tester"
            button = widget("Slot", 1); button.parent = parent
            button.border = widget(); button.qualityBorder = widget(); button.normalTexture = widget()
            button.cooldown = widget()
            BagnonSets.enchantBadges = 0
            BagnonItem_Update(button)
        ''')
        self.assertEqual(lua.eval("icon.r"), 0.4)


class BankBagFamily(unittest.TestCase):
    def test_an_open_bank_herb_bag_reads_its_family_from_classicapi(self):
        lua = load("utility")
        lua.execute("bagFamily[5] = 32; C_Item.GetItemFamily = function() error('read the item') end")
        self.assertEqual(lua.eval("Bagnon_BagFamily(5)"), 32)

    def test_a_bag_that_is_not_there_has_no_family(self):
        # ClassicAPI 1.19.3 answers only 0 for a missing bag; the colour needs a number.
        lua = load("utility")
        lua.execute("C_Container.GetContainerNumFreeSlots = function() return 0 end")
        self.assertEqual(lua.eval("Bagnon_BagFamily(5)"), 0)


if __name__ == "__main__":
    unittest.main()
