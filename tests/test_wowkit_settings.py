"""The game model's Settings window and timer arguments (regressions/wowkit.py)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "regressions"))

try:
    import lupa  # noqa: F401
    import wowkit
    HAVE_LUPA = True
except ImportError:
    HAVE_LUPA = False


@unittest.skipUnless(HAVE_LUPA, "lupa is not installed")
class SettingsWindow(unittest.TestCase):
    """The Settings window as ClassicAPI's Lua for it behaves."""

    def setUp(self):
        self.lua = wowkit.runtime()
        self.lua.execute("""
            DemoDB, heard = { scale = 2 }, {}
            SettingsRegistrar:AddRegistrant(function()
                local layout
                category, layout = Settings.RegisterVerticalLayoutCategory("Demo")
                sound = Settings.RegisterAddOnSetting(category, "Demo_Sound", "sound", DemoDB,
                    Settings.VarType.Boolean, "Play a sound", true)
                scale = Settings.RegisterAddOnSetting(category, "Demo_Scale", "scale", DemoDB,
                    Settings.VarType.Number, "Scale", 1)
                soundRow = Settings.CreateCheckbox(category, sound, "Tooltip.")
                local options = Settings.CreateSliderOptions(0.5, 2, 0.5)
                options:SetLabelFormatter(MinimalSliderWithSteppersMixin.Label.Right)
                scaleRow = Settings.CreateSlider(category, scale, options, "How big.")
                scaleRow:SetParentInitializer(soundRow, function() return sound:GetValue() end)
                layout:AddInitializer(CreateSettingsListSectionHeaderInitializer("More"))
                layout:AddInitializer(CreateSettingsButtonInitializer("Reset position", "Reset",
                    function() heard[#heard + 1] = "clicked" end, "Tooltip.", true))
                sound:SetValueChangedCallback(function(setting, value)
                    heard[#heard + 1] = setting:GetVariable() .. "=" .. tostring(value)
                end)
                Settings.RegisterAddOnCategory(category)
            end)
        """)

    def load(self):
        self.lua.execute('fire("VARIABLES_LOADED") fire("PLAYER_ENTERING_WORLD")')

    def test_registrants_wait_for_saved_variables_and_the_world(self):
        self.lua.execute('''
            local f = CreateFrame("Frame")
            f:RegisterEvent("SETTINGS_LOADED")
            f:SetScript("OnEvent", function() loaded = (loaded or 0) + 1 end)
            fire("VARIABLES_LOADED")
        ''')
        self.assertIsNone(self.lua.eval("category"))
        self.lua.execute('fire("PLAYER_ENTERING_WORLD") fire("PLAYER_ENTERING_WORLD")')
        self.assertEqual(self.lua.eval("category:GetName()"), "Demo")
        self.assertEqual(self.lua.eval("loaded"), 1)
        # Later registrants run at once.
        self.lua.execute("SettingsRegistrar:AddRegistrant(function() late = true end)")
        self.assertTrue(self.lua.eval("late"))

    def test_an_addon_setting_lives_in_the_saved_table(self):
        self.load()
        # The default is written only where the saved table has nothing.
        self.assertEqual(self.lua.eval("DemoDB.sound"), True)
        self.assertEqual(self.lua.eval("DemoDB.scale"), 2)
        self.lua.execute('settingsWindow.use("Demo_Scale", 1.5)')
        self.assertEqual(self.lua.eval("DemoDB.scale"), 1.5)
        self.assertEqual(self.lua.eval("Settings.GetValue('Demo_Scale')"), 1.5)

    def test_every_write_is_heard_and_defaults_too(self):
        self.load()
        self.lua.execute('''
            settingsWindow.use("Demo_Sound", false)
            DemoDB.scale = 2
            settingsWindow.defaults(category)
        ''')
        self.assertEqual(list(self.lua.eval("heard").values()), ["Demo_Sound=false", "Demo_Sound=true"])
        self.assertEqual(self.lua.eval("DemoDB.scale"), 1)

    def test_wrong_types_and_double_registration_are_errors(self):
        self.load()
        for source, text in (
                ('settingsWindow.use("Demo_Sound", 1)', "requires 'boolean' type"),
                ('Settings.RegisterAddOnSetting(category, "Demo_Sound", "x", DemoDB, "boolean", "X", true)',
                 "previously registered"),
                ('Settings.RegisterAddOnSetting(category, "Demo_X", "x", DemoDB, "boolean", "X", 1)',
                 "doesn't match default value type"),
                ('Settings.SetValue("Demo_Missing", true)', "did not exist"),
                ('Settings.CreateCheckbox(category, scale)', "assertion failed")):
            with self.assertRaises(Exception) as raised:
                self.lua.execute(source)
            self.assertIn(text, str(raised.exception))

    def test_rows_dependence_and_buttons(self):
        self.load()
        names = self.lua.eval('''(function()
            local out = {}
            for _, row in ipairs(category.layout.rows) do out[#out + 1] = row:GetName() end
            return table.concat(out, "|")
        end)()''')
        self.assertEqual(names, "Play a sound|Scale|More|Reset position")
        self.assertTrue(self.lua.eval("settingsWindow.enabled(scaleRow)"))
        self.lua.execute('settingsWindow.use("Demo_Sound", false)')
        self.assertFalse(self.lua.eval("settingsWindow.enabled(scaleRow)"))
        self.lua.execute('settingsWindow.click(settingsWindow.row(category, "Reset position"))')
        self.assertEqual(self.lua.eval("heard[#heard]"), "clicked")
        self.assertEqual(self.lua.eval("settingsWindow.choices(scaleRow).steps"), 3)

    def test_opening_finds_only_a_registered_category(self):
        self.lua.execute('''
            opens = {}
            local f = CreateFrame("Frame")
            f:RegisterEvent("SETTINGS_PANEL_OPEN")
            f:SetScript("OnEvent", function(self, event, id) opens[#opens + 1] = id end)
        ''')
        self.load()
        self.lua.execute('''
            Settings.OpenToCategory(category:GetID())
            first = settingsWindow.opened
            local hidden = Settings.RegisterVerticalLayoutCategory("Never registered")
            Settings.OpenToCategory(hidden:GetID())
        ''')
        self.assertEqual(self.lua.eval("first:GetName()"), "Demo")
        self.assertIsNone(self.lua.eval("settingsWindow.opened"))
        self.assertEqual(self.lua.eval("#opens"), 2)
        self.assertTrue(self.lua.eval("settingsWindow.find('Demo') == category"))

    def test_an_older_panel_is_a_category_under_its_name(self):
        self.lua.execute('''
            local panel = CreateFrame("Frame")
            panel.name = "Old"
            panel.default = function() defaulted = true end
            InterfaceOptions_AddCategory(panel)
            Settings.OpenToCategory("Old")
            settingsWindow.defaults()
        ''')
        self.assertEqual(self.lua.eval("settingsWindow.opened.layout.frame.name"), "Old")
        self.assertEqual(self.lua.eval("categories[1].name"), "Old")
        self.assertTrue(self.lua.eval("defaulted"))


@unittest.skipUnless(HAVE_LUPA, "lupa is not installed")
class TimerArguments(unittest.TestCase):
    def test_timers_and_tickers_get_their_handle_and_after_gets_nothing(self):
        lua = wowkit.runtime()
        lua.execute('''
            got = {}
            timer = C_Timer.NewTimer(1, function(handle) got.timer = handle end)
            ticker = C_Timer.NewTicker(1, function(handle) got.ticker = handle; handle:Cancel() end)
            C_Timer.After(1, function(...) got.after = select("#", ...) == 0 or ... == nil end)
            step(1) step(1)
        ''')
        self.assertTrue(lua.eval("got.timer == timer and got.ticker == ticker and got.after"))
        self.assertTrue(lua.eval("ticker:IsCancelled()"))


if __name__ == "__main__":
    unittest.main()
