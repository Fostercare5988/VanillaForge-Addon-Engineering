"""FostercareNameplates settings in AddOn Options, 2026-11-03 (1.7.0).

Like FostercareTweaks 1.15: the /fnp window keeps two columns, and each of its
four pages is also a category under FostercareNameplates in Game Menu > AddOn
Options, one column at full size (ForgeLayout.lua, UI.Book). A page lives in one
place at a time. The live preview moves with the page: top of the right column
in the window, top of the page in AddOn Options. Fails on 1.6.0, which had one
entry with an "Open settings" button. How the pages draw and scroll stays an
in-game check.
"""
import unittest
import fnp_env

LABELS = ["General", "Text & auras", "Target", "Casts"]
OPEN = "FostercareNameplatesSettingsGUI:Show(); FostercareNameplatesSettingsGUI.scripts.OnShow()"

# The 1.6.0 window: page, x, y of every named control (switches 2 below their line,
# sliders at their bar). The layout keeps them within a few pixels.
OLD = {
    'FNPOpt_EnemyNameplateCooldowns': (1, 28, -286), 'FNPOpt_Master': (1, 28, -120),
    'FNPOpt_NameplateCastbar': (1, 28, -260), 'FNPOpt_NameplateClassColors': (1, 28, -234),
    'FNPOpt_NameplateDetails': (1, 28, -208), 'FNPOpt_NameplateScale': (1, 28, -182),
    'FNPOpt_nameplate_scale': (1, 264, -294), 'FNPOpt_nameplate_follow_ui': (1, 264, -324),
    'FNPOpt_nameplate_health_target': (2, 28, -154), 'FNPOpt_nameplate_level': (2, 28, -214),
    'FNPOpt_nameplate_combo': (2, 28, -240), 'FNPOpt_nameplate_targeting': (2, 28, -266),
    'FNPOpt_nameplate_marks': (2, 28, -326), 'FNPOpt_nameplate_raidmark_size': (2, 28, -372),
    'FNPOpt_nameplate_own_auras': (2, 264, -280), 'FNPOpt_nameplate_cc': (2, 264, -306),
    'FNPOpt_nameplate_enemy_buffs': (2, 264, -332), 'FNPOpt_nameplate_aura_count': (2, 264, -376),
    'FNPOpt_nameplate_aura_size': (2, 264, -418),
    'FNPOpt_nameplate_target_glow': (3, 28, -120), 'FNPOpt_nameplate_target_scale': (3, 28, -166),
    'FNPOpt_nameplate_other_alpha': (3, 28, -208), 'FNPOpt_nameplate_fade_critters': (3, 28, -266),
    'FNPOpt_nameplate_fade_totems': (3, 28, -292), 'FNPOpt_nameplate_fade_pets': (3, 28, -318),
    'FNPOpt_nameplate_fade_trivial': (3, 28, -344), 'FNPOpt_nameplate_fade_neutral': (3, 28, -370),
    'FNPOpt_nameplate_fade_alpha': (3, 28, -416),
    'FNPOpt_nameplate_cast_height': (4, 28, -134), 'FNPOpt_nameplate_cast_gap': (4, 28, -176),
    'FNPOpt_nameplate_cd_target': (4, 28, -266), 'FNPOpt_nameplate_cd_size': (4, 28, -312),
    'FNPOpt_nameplate_cd_count': (4, 28, -354), 'FNPOpt_nameplate_cd_minimum': (4, 264, -274),
    'FNPOpt_nameplate_cd_offset': (4, 264, -316),
}

SPOTS = '''(function(page)
    local t = {}
    for _, w in ipairs(frames) do
        local p = w.points and w.points[1]
        if w.name and string.find(w.name, "^FNPOpt_") and p and p[2] == page and w:IsShown() then
            t[#t + 1] = { w.name, p[4], p[5] }
        end
    end
    return t end)'''


def spots(lua, index):
    found = lua.eval(SPOTS)(lua.eval("FNPOptPage%d" % index))
    return [(found[i][1], found[i][2], found[i][3]) for i in range(1, len(found) + 1)]


class AddOnOptions(unittest.TestCase):
    def setUp(self):
        self.lua = fnp_env.load()

    def host(self, index):
        self.lua.execute('''host = categories[%d]
            host.holder.SetWidth = function(self, w) self.width = w end
            host.scripts.OnShow(host)''' % (index + 1))

    def test_every_page_is_a_category_under_the_addon(self):
        lua = self.lua
        self.assertEqual(lua.eval("categories[1].name"), "FostercareNameplates")
        self.assertIsNone(lua.eval("categories[1].parent"))
        self.assertEqual([lua.eval("categories[%d].name" % i) for i in range(2, 6)], LABELS)
        self.assertTrue(all(lua.eval("categories[%d].parent" % i) == "FostercareNameplates" for i in range(2, 6)))

    def test_a_category_borrows_its_page_and_gives_it_back(self):
        lua = self.lua
        lua.execute(OPEN)
        self.host(2)                                                    # Text & auras
        self.assertFalse(lua.eval("FostercareNameplatesSettingsGUI:IsShown()"))
        self.assertTrue(lua.eval("FNPOptPage2.parent == host.holder and FNPOptPage2:IsShown()"))
        self.assertEqual(lua.eval("host.holder.width"), 360)
        # One column: the right column's auras move under the left column's marks.
        self.assertEqual(lua.eval("FNPOpt_nameplate_own_auras.points[1][4]"), 28)
        self.assertLess(lua.eval("FNPOpt_nameplate_own_auras.points[1][5]"),
                        lua.eval("FNPOpt_nameplate_raidmark_size.points[1][5]"))
        lua.execute("FNPOpt_nameplate_level:SetChecked(false); FNPOpt_nameplate_level.scripts.OnClick()")
        self.assertEqual(lua.eval("FostercareNameplates_Config.overwrites.nameplate_level"), 0)   # it works there
        lua.execute("host.scripts.OnHide(host)")
        self.assertTrue(lua.eval("FNPOptPage2.parent == FostercareNameplatesSettingsGUI"))
        self.assertFalse(lua.eval("FNPOptPage2:IsShown()"))
        lua.execute(OPEN)
        self.assertTrue(lua.eval("FNPOptPage2:IsShown()"))                # back in the window, same tab
        self.assertEqual(lua.eval("FNPOpt_nameplate_own_auras.points[1][4]"), 264)              # two columns again

    def test_in_addon_options_every_page_is_one_column(self):
        for index in range(1, 5):
            self.host(index)
            seen = {}
            for name, x, y in spots(self.lua, index):
                self.assertLess(x, 120, "page %d: %s at x=%s" % (index, name, x))
                self.assertNotIn(round(y), seen, "page %d: %s shares a line with %s" % (index, name, seen.get(round(y))))
                seen[round(y)] = name
            self.lua.execute("host.scripts.OnHide(host)")

    def test_the_preview_moves_with_the_page(self):
        lua = self.lua
        self.host(3)
        holder = "(function() for _, w in ipairs(frames) do if w.points and w.points[1] and w.points[1][2] == FNPOptPage3 and w.parent == FNPOptPage3 and not w.name then return w end end end)()"
        self.assertEqual(lua.eval(holder + ".points[1][4]"), 28)                 # first, at the margin
        self.assertEqual(lua.eval(holder + ".points[1][5]"), -98)
        self.assertLess(lua.eval("FNPOpt_nameplate_target_glow.points[1][5]"), -98 - 148)
        lua.execute("host.scripts.OnHide(host); " + OPEN + "; FNPOptTab3.scripts.OnClick()")
        self.assertEqual(lua.eval(holder + ".points[1][4]"), 264)                # top of the right column
        self.assertEqual(lua.eval("FNPOpt_nameplate_target_glow.points[1][5]"), -120)

    def test_the_preview_is_shown_again_after_each_move(self):
        """2026-11-03 in play: every AddOn Options page had an empty space at the
        top. The preview was made in the hidden window and moved without a Show;
        the pages themselves are shown after their move. Fails on cf53153."""
        lua = self.lua
        lua.execute('''
            shows = {}
            FNPOptPreview.Show = function(self) self.shown = true; shows[#shows + 1] = self.parent end
        ''')
        self.host(3)
        self.assertEqual(lua.eval("#shows"), 1)
        self.assertTrue(lua.eval("shows[1] == FNPOptPage3 and FNPOptPreview:IsShown()"))
        lua.execute("FostercareNameplates.Nameplates = FostercareNameplates.Nameplates; host.holder.scripts = host.holder.scripts")
        lua.execute("FNPOpt_nameplate_target_glow.scripts.OnClick()")       # a refresh on the same page
        self.assertEqual(lua.eval("#shows"), 1)
        lua.execute("host.scripts.OnHide(host)")
        self.host(4)
        self.assertTrue(lua.eval("#shows == 2 and shows[2] == FNPOptPage4"))

    def test_the_window_keeps_its_layout(self):
        lua = self.lua
        lua.execute(OPEN)
        for index in range(1, 5):
            lua.execute("FNPOptTab%d.scripts.OnClick()" % index)
            for name, x, y in spots(lua, index):
                if name not in OLD:
                    continue
                page, ox, oy = OLD[name]
                self.assertEqual((page, x), (index, ox), name)
                self.assertLessEqual(abs(y - oy), 4, "%s at %s, was %s" % (name, y, oy))

    def test_the_window_closes_addon_options(self):
        lua = self.lua
        lua.execute("InterfaceOptionsFrame.shown = true; FostercareNameplatesSettingsGUI:Hide(); SlashCmdList.FOSTERCARENAMEPLATES()")
        self.assertFalse(lua.eval("InterfaceOptionsFrame:IsShown()"))
        self.assertTrue(lua.eval("FostercareNameplatesSettingsGUI:IsShown()"))

    def test_the_entry_opens_the_window(self):
        lua = self.lua
        lua.execute("GameMenuFrame.shown = true; FostercareNameplatesSettingsGUI:Hide(); FostercareNameplatesOptionsOpen.scripts.OnClick(FostercareNameplatesOptionsOpen)")
        self.assertTrue(lua.eval("FostercareNameplatesSettingsGUI:IsShown()"))
        self.assertFalse(lua.eval("GameMenuFrame:IsShown()"))


if __name__ == "__main__":
    unittest.main()
