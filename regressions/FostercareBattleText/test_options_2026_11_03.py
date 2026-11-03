"""AddOn Options, 2026-11-03 (FostercareBattleText 2.1.0).

The settings window keeps its two columns; every page is also a category under
FostercareBattleText in Game Menu > AddOn Options, one column at full size
(ForgeLayout.lua, as FostercareTweaks 1.15). Pattern: FostercareTweaks
test_settings_2026_10_25.py, SettingsWindow. Looks stay in-game checks.
"""
import unittest

import _fbt_runtime as m

LABELS = ["General", "Areas", "Incoming", "Outgoing", "Notices", "Triggers", "Filters", "Profiles"]


def pos(lua, name):
    return lua.eval(f"{name}.pt[4]"), lua.eval(f"{name}.pt[5]")


def host(lua, index):
    lua.execute(f"host = categories[{index + 1}]; host.shown = false; host:Show()")


class AddOnOptions(unittest.TestCase):
    def test_every_page_is_a_category_under_the_addon(self):
        lua = m.runtime()
        self.assertEqual(lua.eval("categories[1].name"), "FostercareBattleText")
        self.assertEqual([lua.eval(f"categories[{i}].name") for i in range(2, 10)], LABELS)
        self.assertTrue(all(lua.eval(f"categories[{i}].parent") == "FostercareBattleText" for i in range(2, 10)))
        self.assertIsNone(lua.eval("categories[10]"))

    def test_a_category_borrows_its_page_and_gives_it_back(self):
        lua = m.runtime()
        lua.execute("FBT.Options.ShowTab(2)")
        self.assertEqual(pos(lua, "FBT_AreaShow")[0], 352)                       # beside the area chooser
        host(lua, 2)
        self.assertFalse(lua.eval("FBT_Options:IsShown()"))                      # one place at a time
        self.assertTrue(lua.eval("FBT_Page2.parent == host.holder"))
        self.assertTrue(lua.eval("FBT_Page2:IsShown()"))
        # One column: the switch goes under the chooser, the buttons one a line.
        self.assertEqual(pos(lua, "FBT_AreaShow")[0], 28)
        self.assertLess(pos(lua, "FBT_AreaReset")[1], pos(lua, "FBT_AreaFonts")[1])
        lua.execute("FBT_AreaUnlock:Click()")                                    # it works there
        self.assertTrue(lua.eval("FBT_MoverIncoming:IsShown()"))
        lua.execute("host:Hide()")
        self.assertFalse(lua.eval("FBT_MoverIncoming:IsShown()"))                # handles close with it
        self.assertTrue(lua.eval("FBT_Page2.parent == FBT_Options"))
        lua.execute("FBT.Options.ShowTab(2)")
        self.assertTrue(lua.eval("FBT_Page2:IsShown()"))                         # back in the window
        self.assertEqual(pos(lua, "FBT_AreaShow")[0], 352)                       # two columns again

    def test_in_addon_options_every_page_is_one_column(self):
        # Nothing starts right of the left margin and no two controls share a line.
        lua = m.runtime()
        for index in range(1, 9):
            host(lua, index)
            spots = lua.eval(f'''(function()
                local page, t = FBT_Page{index}, {{}}
                for _, w in ipairs(frames) do
                    if w.name and w.pt and w.pt[2] == page and w:IsShown() then t[#t + 1] = {{ w.name, w.pt[4], w.pt[5] }} end
                end
                return t end)()''')
            self.assertGreater(len(spots), 2, LABELS[index - 1])
            seen = {}
            for i in range(1, len(spots) + 1):
                name, x, y = spots[i][1], spots[i][2], spots[i][3]
                self.assertLess(x, 120, f"{LABELS[index - 1]}: {name} at x={x}")
                self.assertNotIn(round(y), seen, f"{LABELS[index - 1]}: {name} shares a line with {seen.get(round(y))}")
                seen[round(y)] = name
            lua.execute("host:Hide()")

    def test_rows_fit_the_category(self):
        # 360 wide: rows are 320, and every row control ends inside its row.
        lua = m.runtime()
        for index, prefix, controls in ((5, "FBT_NotificationRow1", ("Color", "Font", "Message", "Icon", "Sticky")),
                                        (6, "FBT_TriggerRow1", ("Message", "Color", "Sticky", "Font", "Edit", "Delete")),
                                        (7, "FBT_FilterRow1", ("Pattern", "Delete"))):
            host(lua, index)
            width = lua.eval(f"{prefix}.width")
            self.assertEqual(width, 320)
            for control in controls:
                x, w = lua.eval(f"{prefix}{control}.pt[4]"), lua.eval(f"{prefix}{control}.width")
                self.assertLessEqual(x + w, width, f"{prefix}{control}")
            lua.execute("host:Hide()")

    def test_a_list_works_in_addon_options(self):
        lua = m.runtime()
        host(lua, 7)
        lua.execute("FBT_FilterAdd:Click()")
        self.assertEqual(lua.eval("FBT.CurrentProfile.Suppressions.MSBT_SUPPRESSION_CUSTOM1.SearchPattern"), "New filter")
        self.assertTrue(lua.eval("FBT_FilterRow10:IsShown()"))                   # ten filters now
        self.assertEqual(pos(lua, "FBT_FilterPager")[0], 28)                     # the pager under the list

    def test_the_window_closes_addon_options(self):
        lua = m.runtime()
        lua.execute("InterfaceOptionsFrame.shown = true; FBT.Options.ShowTab(3)")
        self.assertFalse(lua.eval("InterfaceOptionsFrame:IsShown()"))
        lua.execute("FBT.Options.Toggle(); InterfaceOptionsFrame.shown = true; FBT.Options.Toggle()")
        self.assertFalse(lua.eval("InterfaceOptionsFrame:IsShown()"))
        self.assertTrue(lua.eval("FBT_Options:IsShown()"))

    def test_the_entry_opens_the_window(self):
        lua = m.runtime()
        lua.execute("FostercareBattleTextOptionsOpen.scripts.OnClick()")
        self.assertTrue(lua.eval("FBT_Options:IsShown()"))


class WindowUnchanged(unittest.TestCase):
    """The window's places as before the move to ForgeLayout (2.0.0)."""

    def test_general(self):
        lua = m.runtime()
        lua.execute("FBT.Options.ShowTab(1)")
        self.assertEqual(pos(lua, "FBT_Enabled"), (28, -120))
        self.assertEqual(pos(lua, "FBT_ShowGameDamage"), (28, -264))
        self.assertEqual(pos(lua, "FBT_LowHealthSound")[0], 264)
        self.assertEqual(pos(lua, "FBT_MasterFonts"), (300, -306))
        self.assertEqual(pos(lua, "FBT_GameDamageFont"), (300, -336))
        self.assertAlmostEqual(lua.eval("FBT_Options.height"), 410, delta=8)

    def test_areas(self):
        lua = m.runtime()
        lua.execute("FBT.Options.ShowTab(2)")
        self.assertEqual(pos(lua, "FBT_AreaShow"), (352, -106))
        self.assertEqual(pos(lua, "FBT_AreaUnlock"), (352, -264))
        self.assertEqual(pos(lua, "FBT_AreaReset"), (28, -324))
        self.assertEqual(pos(lua, "FBT_AreaFonts"), (352, -324))

    def test_lists(self):
        lua = m.runtime()
        lua.execute("FBT.Options.ShowTab(5)")
        self.assertEqual(pos(lua, "FBT_NotificationRow1"), (28, -118))
        self.assertEqual(pos(lua, "FBT_NotificationRow2"), (28, -146))
        self.assertEqual(pos(lua, "FBT_NotificationRow1Font"), (494, -2))
        self.assertEqual(pos(lua, "FBT_NotificationRow1Icon"), (386, -2))
        self.assertEqual(lua.eval("FBT_NotificationRowPager.pt[1]"), "BOTTOMLEFT")
        self.assertEqual(pos(lua, "FBT_NotificationRowPager"), (220, 18))
        self.assertAlmostEqual(lua.eval("FBT_Options.height"), 460, delta=8)
        lua.execute("FBT.Options.ShowTab(6)")
        self.assertEqual(pos(lua, "FBT_TriggerRow1Delete"), (512, -2))
        self.assertEqual(pos(lua, "FBT_TriggerAdd"), (28, 18))

    def test_profiles(self):
        lua = m.runtime()
        lua.execute("FBT.Options.ShowTab(8)")
        self.assertEqual(pos(lua, "FBT_ProfileRow1"), (28, -118))
        self.assertEqual(pos(lua, "FBT_ProfileName"), (352, -118))
        self.assertEqual(pos(lua, "FBT_ProfileReset"), (352, -210))
        self.assertEqual(pos(lua, "FBT_ProfileRow1Delete"), (236, -2))


if __name__ == "__main__":
    unittest.main()
