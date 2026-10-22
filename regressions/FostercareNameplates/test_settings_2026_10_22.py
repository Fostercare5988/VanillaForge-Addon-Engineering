"""FostercareNameplates settings window on the ForgeUI kit (1.3.0).

Layout, colors and the preview are in-game checks; these guard that no option
was lost in the move and that the controls save the same keys as before.
"""
import unittest
from fnp_env import load

OPEN = 'FostercareNameplatesSettingsGUI.scripts.OnShow()'


class SettingsWindow(unittest.TestCase):
    def test_every_option_has_a_control(self):
        """Each module default (override key) is reachable from the window."""
        lua = load()
        missing = lua.eval('''(function()
            local missing = {}
            for _, title in ipairs(FostercareNameplates.moduleOrder) do
                for key in pairs(FostercareNameplates.mods[title].config or {}) do
                    if not rawget(_G, "FNPOpt_" .. key) and not rawget(_G, "FNPOpt_" .. key .. "1") then
                        table.insert(missing, key)
                    end
                end
            end
            return table.concat(missing, " ")
        end)()''')
        self.assertEqual(missing, "")

    def test_opens_on_every_tab(self):
        lua = load()
        lua.execute(OPEN)
        for i in range(1, 5):
            lua.execute('FNPOptTab%d.scripts.OnClick()' % i)
        self.assertTrue(lua.eval('FNPOptPage4.shown'))

    def test_switch_saves_its_key(self):
        lua = load()
        lua.execute(OPEN + '; FNPOpt_nameplate_level:SetChecked(false); FNPOpt_nameplate_level.scripts.OnClick()')
        self.assertEqual(lua.eval('FostercareNameplates_Config.overwrites.nameplate_level'), 0)

    def test_choice_saves_its_value(self):
        lua = load()
        lua.execute(OPEN + '; FNPOpt_nameplate_raidmark_position2.scripts.OnClick()')
        self.assertEqual(lua.eval('FostercareNameplates_Config.overwrites.nameplate_raidmark_position'), "above")

    def test_reset_restores_options_and_keeps_features(self):
        lua = load('{ ["Nameplate Castbar"] = 0, overwrites = { nameplate_scale = 0.6 }, settingsVersion = 1 }')
        lua.execute(OPEN + '; FNPOpt_Reset.scripts.OnClick()')
        self.assertEqual(lua.eval('FostercareNameplates_Config.overwrites.nameplate_scale'), 1)
        self.assertEqual(lua.eval('FostercareNameplates_Config["Nameplate Castbar"]'), 0)


if __name__ == "__main__":
    unittest.main()
