"""ForgeUI options window: one preview toggle, one reset, switches bound to settings.

The complete AutoBG_Options.lua runs with ForgeUI under Lua 5.1 and the options
widget mocks. Drawing, dragging and text fit stay in-game checks.
"""
import unittest
from lupa.lua51 import LuaRuntime

import addon_loader
from test_options_preview import BASE, OPTIONS

EXTRA = r'''
local Widget = getmetatable(UIParent).__index
function Widget:SetChecked(v) self.checked = v and true or nil end
function Widget:GetChecked() return self.checked end
function Widget:Enable() self.enabled = true end
function Widget:Disable() self.enabled = false end
function Widget:SetValue(v)
    self.value = v
    if self.scripts and self.scripts.OnValueChanged then self.scripts.OnValueChanged(self) end
end
function Widget:GetValue() return self.value or 0 end
function Widget:SetHeight(h) self.height = h end
calls = {}
AutoBG_Targets.DisableConfigMode = function(self) self.isConfig = false; table.insert(calls, "targets off") end
AutoBG_Targets.EnableConfigMode = function(self, size) self.isConfig = true; table.insert(calls, "targets " .. size) end
AutoBG_Spy.EnableTestMode = function(self) self.isTestMode = true; table.insert(calls, "spy on") end
AutoBG_Spy.DisableTestMode = function(self) self.isTestMode = false; table.insert(calls, "spy off") end
AutoBG_Settings.Spy = { Enabled = true, SoundAlert = true, StealthAlert = true, Timeout = 30, MaxRows = 5, Scale = 1 }
AutoBG_Settings.AutoAcceptDelay = 12
AutoBG_Settings.Targets.StealthAlert = true
'''


def runtime():
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(BASE)
    lua.execute(EXTRA)
    lua.execute('AutoBG_Targets.activeBG = true')  # no automatic enemy-frame preview
    addon_loader.load(lua, OPTIONS, "AutoBG_Options.lua")
    return lua


def click(lua, name):
    lua.execute('local w = _G["%s"]; w.scripts.OnClick(w)' % name)


def toggle(lua, name):
    """A native checkbutton flips its state before OnClick."""
    lua.execute('local w = _G["%s"]; w:SetChecked(not w.checked); w.scripts.OnClick(w)' % name)


class OptionsLayoutTests(unittest.TestCase):
    def test_removed_test_buttons_stay_gone(self):
        lua = runtime()
        for name in ("AutoBG_BtnSpyTestSoundStealth", "AutoBG_BtnSpyTestSoundDetect", "AutoBG_BtnSpyTest",
                     "AutoBG_BtnTestTimers", "AutoBG_BtnTgtPreview", "AutoBG_BtnSpyResetPos",
                     "AutoBG_BtnTgtResetPos", "AutoBG_BtnResetTimersPos", "AutoBG_BtnClose"):
            self.assertIsNone(lua.eval('_G["%s"]' % name), name)

    def test_one_preview_toggle_shows_and_hides_every_frame(self):
        lua = runtime()
        lua.execute('AutoBG_OpenOptions("spy")')
        click(lua, "AutoBG_BtnTestAll")
        self.assertEqual(list(lua.eval('calls').values()), ["targets 10", "spy on"])
        self.assertTrue(lua.eval('AutoBG_Settings.TestAllTimers'))
        self.assertTrue(lua.eval('AutoBG_BtnTestAll.selected'))
        self.assertEqual(lua.eval('AutoBG_BtnTestAll.text'), "Hide preview")
        click(lua, "AutoBG_BtnTestAll")
        self.assertFalse(lua.eval('AutoBG_Settings.TestAllTimers'))
        self.assertFalse(lua.eval('AutoBG_Spy.isTestMode'))
        self.assertFalse(lua.eval('AutoBG_BtnTestAll.selected'))
        self.assertEqual(lua.eval('AutoBG_BtnTestAll.text'), "Preview frames")

    def test_closing_the_window_ends_the_preview(self):
        lua = runtime()
        lua.execute('AutoBG_OpenOptions("spy")')
        click(lua, "AutoBG_BtnTestAll")
        lua.execute('AutoBG_OptionsPanel:Hide(); AutoBG_OptionsPanel.scripts.OnHide()')
        self.assertFalse(lua.eval('AutoBG_Spy.isTestMode'))
        self.assertFalse(lua.eval('AutoBG_Targets.isConfig'))
        self.assertFalse(lua.eval('AutoBG_Settings.TestAllTimers'))

    def test_switches_save_their_settings(self):
        lua = runtime()
        lua.execute('AutoBG_OpenOptions("general")')
        toggle(lua, "AutoBG_Opt_AutoAccept")
        self.assertTrue(lua.eval('AutoBG_Settings.AutoAccept'))
        lua.execute('AutoBG_OpenOptions("spy")')
        self.assertTrue(lua.eval('AutoBG_Spy_SoundAlert.checked'))
        toggle(lua, "AutoBG_Spy_SoundAlert")
        self.assertFalse(lua.eval('AutoBG_Settings.Spy.SoundAlert'))

    def test_refresh_shows_saved_values_without_writing_them(self):
        lua = runtime()
        lua.execute('AutoBG_OpenOptions("general")')
        self.assertEqual(lua.eval('AutoBG_Opt_AcceptDelay.value'), 12)
        self.assertEqual(lua.eval('AutoBG_Opt_AcceptDelay.valueText.text'), "12s")
        self.assertEqual(lua.eval('AutoBG_Settings.AutoAcceptDelay'), 12)
        lua.execute('AutoBG_Opt_AcceptDelay:SetValue(0)')
        self.assertEqual(lua.eval('AutoBG_Settings.AutoAcceptDelay'), 0)
        self.assertEqual(lua.eval('AutoBG_Opt_AcceptDelay.valueText.text'), "Instant")

    def test_size_presets_set_the_size_and_light_up(self):
        lua = runtime()
        lua.execute('AutoBG_OpenOptions("targets")')
        click(lua, "AutoBG_Tgt_Preset1")
        self.assertEqual(lua.eval('AutoBG_Settings.Targets.ButtonWidth[10]'), 170)
        self.assertEqual(lua.eval('AutoBG_Settings.Targets.ButtonHeight[10]'), 20)
        self.assertEqual(lua.eval('AutoBG_Settings.Targets.ButtonFontSize[10]'), 10)
        self.assertTrue(lua.eval('AutoBG_Tgt_Preset1.selected'))
        self.assertFalse(lua.eval('AutoBG_Tgt_Preset2.selected'))
        # A custom width no longer matches any preset.
        lua.execute('AutoBG_Tgt_Width:SetValue(185)')
        self.assertFalse(lua.eval('AutoBG_Tgt_Preset1.selected'))

    def test_size_sliders_are_always_shown(self):
        # A new player sees every size control without hunting for a toggle.
        lua = runtime()
        lua.execute('AutoBG_OpenOptions("targets")')
        for name in ("AutoBG_Tgt_FontSize", "AutoBG_Tgt_Scale", "AutoBG_Tgt_Width", "AutoBG_Tgt_Height", "AutoBG_Tgt_Opacity"):
            self.assertNotEqual(lua.eval('%s.shown' % name), False, name)
        self.assertIsNone(lua.eval('AutoBG_Tgt_CustomSize'))
        self.assertEqual(lua.eval('AutoBG_OptionsPanel.height'), 542)

    def test_opacity_is_saved_per_battleground_size(self):
        lua = runtime()
        lua.execute('AutoBG_OpenOptions("targets")')
        self.assertEqual(lua.eval('AutoBG_Tgt_Opacity.value'), 100)
        lua.execute('AutoBG_Tgt_Opacity:SetValue(60)')
        self.assertAlmostEqual(lua.eval('AutoBG_Settings.Targets.ButtonOpacity[10]'), 0.6)
        self.assertIsNone(lua.eval('AutoBG_Settings.Targets.ButtonOpacity[15]'))

    def test_bg_stealth_warnings_live_on_the_spy_tab(self):
        lua = runtime()
        self.assertIsNone(lua.eval('AutoBG_Tgt_StealthAlert'))
        lua.execute('AutoBG_OpenOptions("spy")')
        self.assertTrue(lua.eval('AutoBG_Spy_BGStealthAlert.checked'))
        toggle(lua, "AutoBG_Spy_BGStealthAlert")
        self.assertFalse(lua.eval('AutoBG_Settings.Targets.StealthAlert'))

    def test_row_feature_switches_save(self):
        lua = runtime()
        lua.execute('AutoBG_OpenOptions("targets")')
        for name, key in (("AutoBG_Tgt_CastBars", "ShowCastBars"), ("AutoBG_Tgt_FadeRange", "FadeOutOfRange"),
                          ("AutoBG_Tgt_RaidIcons", "ShowRaidIcons"), ("AutoBG_Tgt_TargetCount", "ShowTargetCount")):
            self.assertTrue(lua.eval('%s.checked' % name), name)
            toggle(lua, name)
            self.assertFalse(lua.eval('AutoBG_Settings.Targets.%s' % key), key)

    def test_cast_bar_side_switch_saves_and_dims_without_cast_bars(self):
        lua = runtime()
        lua.execute('AutoBG_OpenOptions("targets")')
        self.assertTrue(lua.eval('AutoBG_Tgt_CastLeft.checked'))  # old default: away from the trinket
        toggle(lua, "AutoBG_Tgt_CastLeft")
        self.assertEqual(lua.eval('AutoBG_Settings.Targets.CastPos'), "RIGHT")
        toggle(lua, "AutoBG_Tgt_CastBars")
        self.assertFalse(lua.eval('AutoBG_Tgt_CastLeft.enabled'))

    def test_nearby_only_dims_while_stealth_warnings_are_off(self):
        lua = runtime()
        lua.execute('AutoBG_OpenOptions("spy")')
        self.assertFalse(lua.eval('AutoBG_Spy_StealthProximityOnly.disabled'))
        toggle(lua, "AutoBG_Spy_StealthAlert")
        self.assertFalse(lua.eval('AutoBG_Settings.Spy.StealthAlert'))
        self.assertTrue(lua.eval('AutoBG_Spy_StealthProximityOnly.disabled'))


if __name__ == "__main__":
    unittest.main()
