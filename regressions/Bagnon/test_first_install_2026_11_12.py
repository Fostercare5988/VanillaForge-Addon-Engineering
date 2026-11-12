"""Bagnon 2026-11-12: a first install starts with the player's own setup.

12 columns, spacing 3, fully opaque, not kept on screen; the inventory without
the keyring, its bag bar hidden and its background at 0.81. Each window starts
at its own place where that fits the screen. Saved settings are left alone.
"""
import unittest
from bgn_env import ROOT, load

SETUP = '''
    UIParent = widget("UIParent")
    function UIParent:GetScale() return uiScale end
    function UIParent:GetWidth() return uiWidth end
    function UIParent:GetHeight() return 768 / uiScale end
    uiScale, uiWidth = 0.8, 1706
    Bagnon = widget("Bagnon"); Banknon = widget("Banknon")
    function Bagnon:GetParent() return UIParent end
    function Banknon:GetParent() return UIParent end
    BagnonSets = { showFreeSlots = 1 }
'''


class FirstInstall(unittest.TestCase):
    def fresh(self, extra=""):
        lua = load("utility", "frame")
        lua.execute(SETUP + extra)
        lua.execute('''
            inv = BagnonFrame_Settings(Bagnon, {0, 1, 2, 3, 4})
            bank = BagnonFrame_Settings(Banknon, {-1, 5, 6, 7, 8, 9, 10})
        ''')
        return lua

    def test_layout_of_both_windows(self):
        lua = self.fresh()
        for name in ("inv", "bank"):
            self.assertEqual(lua.eval(f"{name}.cols"), 12)
            self.assertEqual(lua.eval(f"{name}.space"), 3)
            self.assertEqual(lua.eval(f"{name}.alpha"), 1)
            self.assertEqual(lua.eval(f"{name}.stayOnScreen"), 0)
            self.assertEqual(lua.eval(f"{name}.strata"), 3)

    def test_inventory_hides_its_bag_bar_and_is_a_little_see_through(self):
        lua = self.fresh()
        self.assertEqual(lua.eval("inv.bagsShown"), 0)
        self.assertAlmostEqual(lua.eval("inv.bg.a"), 0.81)
        self.assertEqual(lua.eval("bank.bagsShown"), 1)
        self.assertEqual(lua.eval("bank.bg.a"), 1)
        self.assertEqual(list(lua.eval("inv.bags").values()), [0, 1, 2, 3, 4])

    def test_the_inventory_starts_without_the_keyring(self):
        source = (ROOT / "Bagnon.lua").read_text("utf-8-sig")
        self.assertIn('BagnonFrame_Load(Bagnon, {0, 1, 2, 3, 4}', source)

    def test_each_window_starts_at_its_place(self):
        lua = self.fresh()
        self.assertEqual((lua.eval("inv.left"), lua.eval("inv.top"), lua.eval("inv.parentScale")), (1078, 495, 0.8))
        self.assertEqual((lua.eval("bank.left"), lua.eval("bank.top")), (192, 898))

    def test_a_narrow_screen_keeps_the_standard_place(self):
        lua = self.fresh("uiWidth = 1280")  # 4:3: the inventory would hang over the right edge
        self.assertIsNone(lua.eval("inv.left"))
        self.assertIsNone(lua.eval("inv.top"))
        self.assertEqual(lua.eval("bank.left"), 192)

    def test_saved_settings_are_left_alone(self):
        lua = self.fresh('''
            BagnonSets.Bagnon = { cols = 8, space = 2, alpha = 0.5, stayOnScreen = 1, bagsShown = 1,
                                  bags = {-2, 0}, bg = { r = 1, g = 0, b = 0, a = 0.5 } }
        ''')
        self.assertEqual(lua.eval("inv.cols"), 8)
        self.assertEqual(lua.eval("inv.stayOnScreen"), 1)
        self.assertEqual(lua.eval("inv.bagsShown"), 1)
        self.assertEqual(lua.eval("inv.bg.a"), 0.5)
        self.assertIsNone(lua.eval("inv.left"))
        self.assertEqual(list(lua.eval("inv.bags").values()), [-2, 0])


if __name__ == "__main__":
    unittest.main()
