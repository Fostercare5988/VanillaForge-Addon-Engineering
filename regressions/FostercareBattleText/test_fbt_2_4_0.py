"""FostercareBattleText 2.4.0, 2026-11-13: filter groups; copy and rename profiles.

A player asked for groups of filters that fold, and for profiles that can be
copied and renamed. Groups only order the Filters tab: every enabled filter
still hides what it matches. Each test fails on 2.3.0 (a19bb9e). Lua model
only (_fbt_runtime.py).
"""
import unittest

import _fbt_runtime as m

OLD_PROFILE = '''
FostercareBattleTextDB = {UserDisabled = false, Profiles = {Default = {Suppressions = {
  MSBT_SUPPRESSION_SHAMAN_MANA_SPRING = {Enabled = true, SearchPattern = "Mana Spring"},
  MSBT_SUPPRESSION_SHAMAN_STONESKIN = {Enabled = false, SearchPattern = "Stoneskin"},
  MSBT_SUPPRESSION_ROGUE_VIGOR = {Enabled = true, SearchPattern = "Vigor"},
  MSBT_SUPPRESSION_CUSTOM1 = {Enabled = true, SearchPattern = "Renew"},
}}}}'''


def rows(lua):
    """What the Filters tab shows: ("group", title) or ("filter", text, indented)."""
    out = []
    for i in range(1, 11):
        row = f"FBT_FilterRow{i}"
        if not lua.eval(f"{row}:IsShown()"):
            continue
        if lua.eval(f"{row}Title:IsShown()"):
            out.append(("group", lua.eval(f"{row}Title:GetText()")))
        else:
            out.append(("filter", lua.eval(f"{row}Pattern:GetText()")))
    return out


def row_of(lua, text):
    for i in range(1, 11):
        row = f"FBT_FilterRow{i}"
        if not lua.eval(f"{row}:IsShown()"):
            continue
        # Only the part the row shows: a row that turned into a group keeps its old text.
        part = "Title" if lua.eval(f"{row}Title:IsShown()") else "Pattern"
        if text in (lua.eval(f"{row}{part}:GetText()") or ""):
            return row
    raise AssertionError(text + " not shown")


class FilterGroups(unittest.TestCase):
    def filters_tab(self, saved=OLD_PROFILE):
        lua = m.runtime(saved)
        lua.execute("FBT.Options.ShowTab(7)")
        return lua

    def test_the_built_in_shaman_filters_start_in_a_group(self):
        lua = self.filters_tab()
        self.assertEqual(rows(lua), [("filter", "Renew"), ("filter", "Vigor"), ("group", "Shaman totems  (2)"),
                                     ("filter", "Mana Spring"), ("filter", "Stoneskin")])

    def test_a_group_folds_and_unfolds(self):
        lua = self.filters_tab()
        lua.execute(f"{row_of(lua, 'Shaman totems')}Fold:Click()")
        self.assertEqual(rows(lua), [("filter", "Renew"), ("filter", "Vigor"), ("group", "Shaman totems  (2)")])
        self.assertEqual(lua.eval("FBT.CurrentProfile.FilterGroups[1].Collapsed"), True)
        lua.execute(f"{row_of(lua, 'Shaman totems')}Fold:Click()")
        self.assertEqual(len(rows(lua)), 5)

    def test_the_group_switch_turns_all_its_filters_on_and_off(self):
        lua = self.filters_tab()
        s = "FBT.CurrentProfile.Suppressions"
        group = row_of(lua, "Shaman totems")
        self.assertFalse(lua.eval(f"{group}All:GetChecked() and true or false"))  # one of two is off
        lua.execute(f"{group}All:Click()")
        self.assertTrue(lua.eval(f"{s}.MSBT_SUPPRESSION_SHAMAN_STONESKIN.Enabled and {s}.MSBT_SUPPRESSION_SHAMAN_MANA_SPRING.Enabled"))
        lua.execute(f"{group}All:Click()")
        self.assertFalse(lua.eval(f"{s}.MSBT_SUPPRESSION_SHAMAN_STONESKIN.Enabled or {s}.MSBT_SUPPRESSION_SHAMAN_MANA_SPRING.Enabled"))
        self.assertTrue(lua.eval(f"{s}.MSBT_SUPPRESSION_ROGUE_VIGOR.Enabled"))

    def test_add_rename_and_delete_a_group(self):
        lua = self.filters_tab()
        lua.execute("FBT_FilterAddGroup:Click()")
        group = row_of(lua, "New group")
        lua.execute(f'{group}Title:Click(); FBT_InlineEdit:SetText("Paladin"); FBT_InlineEdit:PressEnter()')
        group = row_of(lua, "Paladin")
        # A filter moves into it with its group picker, and goes with a rename.
        # Each click moves the row, so find it again before the next.
        lua.execute(f"{row_of(lua, 'Vigor')}GroupNext:Click()")
        lua.execute(f"{row_of(lua, 'Vigor')}GroupNext:Click()")
        self.assertEqual(lua.eval("FBT.CurrentProfile.Suppressions.MSBT_SUPPRESSION_ROGUE_VIGOR.Group"), "Paladin")
        lua.execute(f'{row_of(lua, "Paladin")}Title:Click(); FBT_InlineEdit:SetText("Rogue"); FBT_InlineEdit:PressEnter()')
        self.assertEqual(lua.eval("FBT.CurrentProfile.Suppressions.MSBT_SUPPRESSION_ROGUE_VIGOR.Group"), "Rogue")
        # Deleting the group keeps its filters, with no group.
        lua.execute(f"{row_of(lua, 'Rogue')}Delete:Click()")
        self.assertIsNone(lua.eval("FBT.CurrentProfile.Suppressions.MSBT_SUPPRESSION_ROGUE_VIGOR.Group"))
        self.assertEqual(lua.eval("FBT.CurrentProfile.Suppressions.MSBT_SUPPRESSION_ROGUE_VIGOR.SearchPattern"), "Vigor")
        self.assertEqual(lua.eval("#FBT.CurrentProfile.FilterGroups"), 1)

    def test_a_name_another_group_has_is_refused(self):
        lua = self.filters_tab()
        lua.execute("FBT_FilterAddGroup:Click()")
        lua.execute(f'{row_of(lua, "New group")}Title:Click(); FBT_InlineEdit:SetText("Shaman totems"); FBT_InlineEdit:PressEnter()')
        self.assertEqual(lua.eval("FBT.CurrentProfile.FilterGroups[2].Name"), "New group")

    def test_plus_adds_a_filter_to_its_group(self):
        lua = self.filters_tab()
        lua.execute(f"{row_of(lua, 'Shaman totems')}Fold:Click(); {row_of(lua, 'Shaman totems')}Add:Click()")
        self.assertEqual(lua.eval("FBT.CurrentProfile.Suppressions.MSBT_SUPPRESSION_CUSTOM2.Group"), "Shaman totems")
        self.assertIn(("group", "Shaman totems  (3)"), rows(lua))
        self.assertIn(("filter", "New filter"), rows(lua))

    def test_groups_do_not_change_what_is_hidden(self):
        lua = self.filters_tab()
        lua.execute('''
          FBT.CombatEventsHandler = RealCombatEventsHandler
          CL("SPELL_PERIODIC_ENERGIZE", "0xTOTEM", "Totem", "0xPLAYER", "Hero", 5677, "Mana Spring", 8, 10, 0)
          CL("SPELL_PERIODIC_ENERGIZE", "0xPLAYER", "Hero", "0xPLAYER", "Hero", 12051, "Evocation", 64, 10, 0)
          RunTimers()''')
        shown = [lua.eval(f"FBT.scrollAreas.Notification.Slots[{i}].IsActive and FBT.scrollAreas.Notification.Slots[{i}].FontObject.text") for i in range(1, 11)]
        self.assertEqual([t for t in shown if t], ["+10 Mana"])

    def test_groups_survive_the_load_sweep_and_a_deleted_one_stays_deleted(self):
        lua = m.runtime(OLD_PROFILE)
        lua.execute("FBT.CurrentProfile.FilterGroups = {}")
        lua.execute('FBT.UpdateProfiles()')
        self.assertEqual(lua.eval("#FBT.CurrentProfile.FilterGroups"), 0)
        lua.execute('table.insert(FBT.CurrentProfile.FilterGroups, {Name = "Mine", Collapsed = true}); FBT.UpdateProfiles()')
        self.assertEqual(lua.eval("FBT.CurrentProfile.FilterGroups[1].Name"), "Mine")

    def test_in_addon_options_the_group_picker_takes_a_second_line(self):
        lua = m.runtime(OLD_PROFILE)
        lua.execute("host = categories[8]; host.shown = false; host:Show()")  # the Filters page
        row = row_of(lua, "Vigor")
        self.assertEqual(lua.eval(f"{row}Group.pt[5]"), -28)
        self.assertEqual(lua.eval(f"{row}:GetHeight()"), 52)

    def test_a_new_profile_has_the_shaman_group(self):
        lua = m.runtime()
        self.assertEqual(lua.eval("FBT.CurrentProfile.FilterGroups[1].Name"), "Shaman totems")
        self.assertEqual(lua.eval("FBT.CurrentProfile.Suppressions.MSBT_SUPPRESSION_SHAMAN_STONESKIN.Group"), "Shaman totems")
        self.assertIsNone(lua.eval("FBT.CurrentProfile.Suppressions.MSBT_SUPPRESSION_ROGUE_VIGOR.Group"))


class ProfileCopyRename(unittest.TestCase):
    def profiles_tab(self, saved=None):
        lua = m.runtime(saved)
        lua.execute("FBT.Options.ShowTab(8)")
        return lua

    def profile_row(self, lua, name):
        for i in range(1, 11):
            if lua.eval(f"FBT_ProfileRow{i}:IsShown() and FBT_ProfileRow{i}.name") == name:
                return f"FBT_ProfileRow{i}"
        raise AssertionError(name + " not listed")

    def test_copy_current_makes_a_named_copy(self):
        lua = self.profiles_tab()
        lua.execute('''
          FBT.CurrentProfile.UseStickyCrits = false
          FBT_ProfileName:SetText("Raid"); FBT_ProfileCopy:Click()''')
        p = "FostercareBattleTextDB.Profiles"
        self.assertEqual(lua.eval(f"{p}.Raid.UseStickyCrits"), False)
        # A copy, not the same tables: changing one leaves the other.
        lua.execute(f"{p}.Raid.DisplaySettings.Incoming.ScrollHeight = 111")
        self.assertNotEqual(lua.eval(f"{p}.Default.DisplaySettings.Incoming.ScrollHeight"), 111)
        self.assertEqual(lua.eval("FBT.CurrentProfileName()"), "Default")
        self.profile_row(lua, "Raid")

    def test_rename_a_profile_by_clicking_its_name(self):
        lua = self.profiles_tab()
        lua.execute('FBT_ProfileName:SetText("Raid"); FBT_ProfileCopy:Click()')
        lua.execute(f'{self.profile_row(lua, "Raid")}Use:Click()')
        lua.execute(f'{self.profile_row(lua, "Raid")}Rename:Click(); FBT_InlineEdit:SetText("Dungeons"); FBT_InlineEdit:PressEnter()')
        self.assertIsNone(lua.eval("FostercareBattleTextDB.Profiles.Raid"))
        self.assertEqual(lua.eval("FBT.CurrentProfileName()"), "Dungeons")
        self.assertEqual(lua.eval("FBT.CurrentProfile == FostercareBattleTextDB.Profiles.Dungeons"), True)
        self.profile_row(lua, "Dungeons")

    def test_default_and_taken_names_are_kept(self):
        lua = self.profiles_tab()
        lua.execute('FBT_ProfileName:SetText("Raid"); FBT_ProfileCopy:Click()')
        self.assertFalse(lua.eval(f'{self.profile_row(lua, "Default")}Rename:IsEnabled() and true or false'))
        lua.execute(f'{self.profile_row(lua, "Raid")}Rename:Click(); FBT_InlineEdit:SetText("Default"); FBT_InlineEdit:PressEnter()')
        self.assertEqual(lua.eval("type(FostercareBattleTextDB.Profiles.Raid)"), "table")

    def test_another_character_follows_a_rename(self):
        # Renamed on one character; another still has the old name saved.
        lua = m.runtime('''
          FostercareBattleTextDB = {UserDisabled = false, Profiles = {Default = {}, Dungeons = {UseStickyCrits = false}},
            Renamed = {Raid = "Dungeons"}}
          FostercareBattleTextCharDB = {CurrentProfile = "Raid"}''')
        self.assertEqual(lua.eval("FBT.CurrentProfileName()"), "Dungeons")
        self.assertEqual(lua.eval("FBT.CurrentProfile.UseStickyCrits"), False)


if __name__ == "__main__":
    unittest.main()
