"""The page in ClassicAPI's Settings window and /fbars (spec "The page";
tests 13 and 14). Used through the kit's settingsWindow, as a player does.
"""
import unittest
from fb_env import load, profiles

SAVED = '''FostercareBarsDB = { profiles = {
    PVP = { actions = { [1] = { kind = 'spell', id = 10 } } },
    PVE = { actions = { [1] = { kind = 'spell', id = 20 } } },
} }'''

PAGE = "settingsWindow.find('FostercareBars')"


def row(name):
    return f"settingsWindow.row({PAGE}, '{name}')"


def choices(lua):
    return lua.eval(f'''(function()
        local out = {{}}
        for _, c in ipairs(settingsWindow.choices({row('Profile')})) do out[#out + 1] = c.value .. '=' .. c.label end
        return table.concat(out, '|')
    end)()''')


class Page(unittest.TestCase):
    def test_the_five_rows_in_play_order(self):
        lua = load(SAVED)
        names = lua.eval(f'''(function()
            local out = {{}}
            for _, r in ipairs({PAGE}.layout.rows) do out[#out + 1] = r:GetName() end
            return table.concat(out, '|')
        end)()''')
        self.assertEqual(names, "Profile|Load|Save over it|Delete|New profile")
        self.assertTrue(lua.eval(f"{PAGE}.addon"), "listed on the AddOns tab")

    def test_the_list_holds_the_profiles_and_the_first_is_chosen(self):
        lua = load(SAVED)
        self.assertEqual(choices(lua), "PVE=PVE|PVP=PVP")
        self.assertEqual(lua.eval("Settings.GetValue('FostercareBars_Profile')"), "PVE")

    def test_without_profiles_the_three_buttons_are_greyed(self):
        lua = load()
        self.assertEqual(choices(lua), "=No profiles yet")
        for name in ("Load", "Save over it", "Delete"):
            self.assertFalse(lua.eval(f"settingsWindow.enabled({row(name)})"), name)
        self.assertTrue(lua.eval(f"settingsWindow.enabled({row('New profile')})"))

    def test_choosing_a_profile_and_load_loads_it(self):
        lua = load(SAVED, "learn(10) learn(20)")
        lua.execute(f"settingsWindow.use('FostercareBars_Profile', 'PVP') settingsWindow.click({row('Load')})")
        self.assertEqual(lua.eval("bars[1].id"), 10)

    def test_save_over_it_saves_the_bars_now(self):
        lua = load(SAVED)
        lua.execute(f"bars[1] = {{ kind = 'spell', id = 99 }} settingsWindow.click({row('Save over it')})")
        self.assertEqual(lua.eval("FostercareBarsDB.profiles.PVE.actions[1].id"), 99)

    def test_delete_asks_then_removes(self):
        lua = load(SAVED)
        lua.execute(f"settingsWindow.click({row('Delete')})")
        self.assertEqual(lua.eval("popupShown()"), "FOSTERCAREBARS_DELETE")
        self.assertEqual(lua.eval("popup.text"), 'Delete the profile "PVE"?')
        self.assertEqual(profiles(lua), ["PVE", "PVP"], "nothing goes before Yes")
        lua.execute("accept()")
        self.assertEqual(profiles(lua), ["PVP"])
        self.assertEqual(lua.eval("Settings.GetValue('FostercareBars_Profile')"), "PVP")
        self.assertIn('Deleted "PVE".', lua.eval("chatText()"))
        lua.execute(f"settingsWindow.click({row('Delete')}) accept()")
        self.assertEqual(lua.eval("Settings.GetValue('FostercareBars_Profile')"), "")
        self.assertFalse(lua.eval(f"settingsWindow.enabled({row('Load')})"))

    def test_new_profile_saves_under_the_typed_name_and_chooses_it(self):
        lua = load()
        lua.execute(f"settingsWindow.click({row('New profile')})")
        self.assertEqual(lua.eval("popupShown()"), "FOSTERCAREBARS_NEW")
        lua.execute("accept('')")
        self.assertEqual(lua.eval("popupShown()"), "FOSTERCAREBARS_NEW", "an empty name is refused")
        lua.execute("accept('Arena')")
        self.assertFalse(lua.eval("popupShown()"))
        self.assertEqual(profiles(lua), ["Arena"])
        self.assertEqual(lua.eval("Settings.GetValue('FostercareBars_Profile')"), "Arena")
        self.assertTrue(lua.eval(f"settingsWindow.enabled({row('Load')})"))

    def test_the_buttons_are_heard_when_the_choice_changes(self):
        # The window re-greys a row when its parent's setting reports a change.
        lua = load()
        lua.execute('''heard = 0
            Settings.SetOnValueChangedCallback('FostercareBars_Profile', function() heard = heard + 1 end)
            StaticPopup_Show('FOSTERCAREBARS_NEW') accept('Arena')''')
        self.assertEqual(lua.eval("heard"), 1)

    def test_defaults_leaves_the_choice(self):
        lua = load(SAVED)
        lua.execute(f"settingsWindow.use('FostercareBars_Profile', 'PVP') settingsWindow.defaults({PAGE})")
        self.assertEqual(lua.eval("Settings.GetValue('FostercareBars_Profile')"), "PVP")
        self.assertEqual(profiles(lua), ["PVE", "PVP"])

    def test_the_choice_is_not_saved(self):
        lua = load(SAVED)
        lua.execute("settingsWindow.use('FostercareBars_Profile', 'PVP')")
        self.assertEqual(lua.eval("(function() local n = 0 for k in pairs(FostercareBarsDB) do n = n + 1 end return n end)()"), 1)

    def test_fbars_opens_the_page(self):
        lua = load()
        lua.execute("SlashCmdList.FOSTERCAREBARS('')")
        self.assertEqual(lua.eval("settingsWindow.opened:GetName()"), "FostercareBars")
        self.assertEqual(lua.eval("SLASH_FOSTERCAREBARS1"), "/fbars")


if __name__ == "__main__":
    unittest.main()
