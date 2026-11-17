"""The stock bars give way, the look switches and the Layout page
(FostercareTweaks spec B2, B6, B8, B9, 4.1; its tests 4.7 "Every addon" and
"Bars"). Written 2026-11-17 for FostercareBars 1.1.0.
"""
import unittest
from fb_env import load

LAYOUT = "settingsWindow.find('Layout')"


class Look(unittest.TestCase):
    def test_the_stock_bars_are_hidden_and_the_xp_bar_kept(self):
        lua = load()
        for name in ("ActionButton1", "MultiBarBottomLeftButton5", "BonusActionButton3", "MultiBarLeft",
                     "BonusActionBarFrame"):
            self.assertFalse(lua.eval(f"{name}:IsVisible()"), name)
        self.assertTrue(lua.eval("MainMenuExpBar:IsVisible()"))
        self.assertEqual(lua.eval("(MainMenuBar:GetPoint(1))"), "BOTTOM")
        self.assertTrue(lua.eval("select(2, MainMenuBar:GetPoint(1)) == button('main', 1).bar.holder"),
                        "the XP bar follows the main bar")

    def test_each_switch_is_on_by_default_and_applies_at_once(self):
        lua = load()
        self.assertEqual(lua.eval("MainMenuBarLeftEndCap:GetAlpha()"), 0)
        self.assertEqual(lua.eval("MainMenuBarTexture0:GetAlpha()"), 0)
        self.assertFalse(lua.eval("CharacterMicroButton:IsVisible()"))
        self.assertFalse(lua.eval("ShapeshiftBarFrame:IsVisible()"))
        self.assertTrue(lua.eval("button('main', 1).edge:IsShown()"))
        for variable in ("hideGryphons", "floating", "shortMain", "hideStanceBar"):
            lua.execute(f"settingsWindow.use('FostercareBars_{variable}', false)")
        self.assertEqual(lua.eval("MainMenuBarLeftEndCap:GetAlpha()"), 1)
        self.assertEqual(lua.eval("MainMenuBarTexture0:GetAlpha()"), 1)
        self.assertTrue(lua.eval("CharacterMicroButton:IsVisible()"))
        self.assertTrue(lua.eval("ShapeshiftBarFrame:IsVisible()"))
        self.assertFalse(lua.eval("button('main', 1).edge:IsShown()"))
        self.assertEqual(lua.eval("MainMenuExpBar:GetWidth()"), 1024)
        lua.execute("settingsWindow.defaults(settingsWindow.find('FostercareBars'))")
        self.assertEqual(lua.eval("MainMenuBarLeftEndCap:GetAlpha()"), 0, "Defaults puts it back")
        self.assertFalse(lua.eval("ShapeshiftBarFrame:IsVisible()"))

    def test_the_pet_and_stance_sweeps_get_countdown_numbers(self):
        lua = load()
        hook = lua.eval("hookedTimer")
        self.assertIsNotNone(hook)
        lua.execute("model = CreateFrame('Model') hookedTimer(model, 100, 10, 1)")
        self.assertEqual(lua.eval("model.fbNumbers.cd"), "100+10")
        lua.execute("hookedTimer(model, 0, 0, 0)")
        self.assertIsNone(lua.eval("model.fbNumbers.cd"))


class Layout(unittest.TestCase):
    def test_a_section_per_bar_with_its_five_rows(self):
        lua = load()
        names = lua.eval(f'''(function()
            local out = {{}}
            for i = 1, 6 do out[#out + 1] = {LAYOUT}.layout.rows[i]:GetName() end
            return table.concat(out, '|')
        end)()''')
        self.assertEqual(names, "Main|Shown|Size|Buttons per row|Spacing|Show empty")
        self.assertEqual(lua.eval(f"#{LAYOUT}.layout.rows"), 16 * 6)

    def test_an_extra_bar_rows_show_while_the_bar_exists(self):
        lua = load()
        self.assertTrue(lua.eval(f"settingsWindow.visible({LAYOUT}.layout.rows[6 * 6 + 1])"), "Extra 2")
        self.assertFalse(lua.eval(f"settingsWindow.visible({LAYOUT}.layout.rows[7 * 6 + 1])"), "Extra 3")

    def test_the_rows_change_the_bar(self):
        lua = load()
        lua.execute("settingsWindow.use('FostercareBars_bottomleft_scale', 1.2)")
        self.assertEqual(lua.eval("button('bottomleft', 1).bar.holder:GetScale()"), 1.2)
        lua.execute("settingsWindow.use('FostercareBars_bottomleft_columns', 6) "
                    "settingsWindow.use('FostercareBars_bottomleft_spacing', 4)")
        self.assertEqual(lua.eval("select(5, button('bottomleft', 7):GetPoint(1))"), -40, "the second row")
        self.assertEqual(lua.eval("button('bottomleft', 1).bar.holder:GetWidth()"), 6 * 40 - 4)
        lua.execute("settingsWindow.use('FostercareBars_bottomleft_showEmpty', true)")
        self.assertTrue(lua.eval("button('bottomleft', 1):IsShown()"))
        lua.execute(f"settingsWindow.defaults({LAYOUT})")
        self.assertEqual(lua.eval("FostercareBarsDB.bars.bottomleft.columns"), 12)
        self.assertEqual(lua.eval("FostercareBarsDB.bars.bottomleft.scale"), 0.9)

    def test_move_bars_saves_where_a_bar_is_dropped(self):
        lua = load()
        lua.execute("settingsWindow.click(settingsWindow.row(settingsWindow.find('FostercareBars'), 'Move bars'))")
        lua.execute("h = button('right', 1).bar.handle h:IsShown() local holder = button('right', 1).bar.holder "
                    "holder.left, holder.top, holder.scale = 1000, 600, 0.9 run(h, 'OnDragStop')")
        self.assertTrue(lua.eval("h:IsShown()"))
        self.assertAlmostEqual(lua.eval("FostercareBarsDB.bars.right.x"), 900)
        self.assertAlmostEqual(lua.eval("FostercareBarsDB.bars.right.y"), 540)
        self.assertEqual(lua.eval("(button('right', 1).bar.holder:GetPoint(1))"), "TOPLEFT")
        lua.execute("settingsWindow.click(settingsWindow.row(settingsWindow.find('FostercareBars'), 'Move bars'))")
        self.assertFalse(lua.eval("h:IsShown()"))
        self.assertIn("Bars locked.", lua.eval("chatText()"))


if __name__ == "__main__":
    unittest.main()
