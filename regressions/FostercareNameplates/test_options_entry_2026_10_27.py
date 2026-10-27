"""FostercareNameplates is listed in ClassicAPI's AddOn Options, 2026-10-27.

ClassicAPI lists panels given to InterfaceOptions_AddCategory under AddOn
Options in the game menu (docs/API.md, InterfaceOptions). The entry's button
closes that window and the game menu and opens the settings window, like
/fnp. Fails on eaeaaf3, which had no entry. How the list draws stays an
in-game check.
"""
import unittest
import fnp_env


class OptionsEntry(unittest.TestCase):
    def test_listed_and_opens_the_settings(self):
        lua = fnp_env.load()
        lua.execute(r'''
            entry = nil
            for _, p in ipairs(categories) do if p.name == "FostercareNameplates" then entry = p end end
            hidden = {}
            InterfaceOptionsFrame = { IsShown = function() return true end, Hide = function() hidden.options = true end }
            GameMenuFrame = { IsShown = function() return true end }
            function HideUIPanel(f) if f == GameMenuFrame then hidden.menu = true end end
            FostercareNameplatesSettingsGUI:Hide()
        ''')
        self.assertTrue(lua.eval("entry ~= nil and entry.parent == nil"))
        lua.execute("FostercareNameplatesOptionsOpen.scripts.OnClick(FostercareNameplatesOptionsOpen)")
        self.assertTrue(lua.eval("FostercareNameplatesSettingsGUI:IsShown()"))
        self.assertTrue(lua.eval("hidden.options and hidden.menu"))


if __name__ == "__main__":
    unittest.main()
