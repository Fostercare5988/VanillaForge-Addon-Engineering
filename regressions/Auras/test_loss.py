"""The loss-of-control alert: icon, text and time of the strongest effect, gone
when the last ends; a root (displayType 0) shows nothing; the option off
registers no event. A first login: no frame until the first effect.

The kit should model (stubbed here in LOSS): C_LossOfControl (count and data,
a new table per read, in ClassicAPI's order), C_Spell.GetSchoolString and the
LOSS_OF_CONTROL_DISPLAY_* global strings."""
import unittest
from auras_env import load

LOSS = """
loc = {}
C_LossOfControl = {
    GetActiveLossOfControlDataCount = function() return #loc end,
    GetActiveLossOfControlData = function(i)
        local d = loc[i]
        if not d then return nil end
        local t = {}
        for k, v in pairs(d) do t[k] = v end
        return t
    end,
}
C_Spell.GetSchoolString = function(mask) return ({ [4] = 'Fire', [16] = 'Frost' })[mask] end
LOSS_OF_CONTROL_DISPLAY_INTERRUPT_SCHOOL = '%s Locked'
function effect(kind, text, priority, displayType, tex, duration, school)
    return { locType = kind, displayText = text, iconTexture = tex, priority = priority, displayType = displayType,
             startTime = now, duration = duration, lockoutSchool = school or 0 }
end
function changed() fire('LOSS_OF_CONTROL_UPDATE', 'player') end
"""
STUN = "loc[1] = effect('STUN', 'Stunned', 5, 2, 'stun', 4)"


def build(saved="", setup=""):
    return load(saved=saved, setup=LOSS + setup, frames=False)


class Alert(unittest.TestCase):
    def test_a_first_login_makes_no_frame_and_listens_for_one_event(self):
        lua = build()
        self.assertIsNone(lua.eval("AurasLossOfControl"))
        self.assertTrue(lua.eval("AurasDB.lossOfControl"))

    def test_a_stun_shows_icon_text_and_time(self):
        lua = build(setup=STUN)
        lua.execute("changed()")
        self.assertTrue(lua.eval("AurasLossOfControl:IsShown()"))
        self.assertEqual(lua.eval("AurasLossOfControl.icon.texture"), "stun")
        self.assertEqual(lua.eval("AurasLossOfControl.label.text"), "Stunned")
        self.assertEqual(lua.eval("AurasLossOfControl.cd.cooldown[2]"), 4)
        self.assertEqual(lua.eval("AurasLossOfControl.cd.cooldown[1]"), lua.eval("now"))

    def test_the_higher_priority_shows_and_the_last_ending_hides(self):
        lua = build(setup=STUN)
        lua.execute("loc[1] = effect('SILENCE', 'Silenced', 3, 1, 'sil', 5); loc[2] = effect('STUN', 'Stunned', 5, 2, 'stun', 4); changed()")
        self.assertEqual(lua.eval("AurasLossOfControl.label.text"), "Stunned")
        lua.execute("table.remove(loc, 2); changed()")
        self.assertTrue(lua.eval("AurasLossOfControl:IsShown()"))
        self.assertEqual(lua.eval("AurasLossOfControl.label.text"), "Silenced")
        lua.execute("loc = {}; changed()")
        self.assertFalse(lua.eval("AurasLossOfControl:IsShown()"))

    def test_the_same_priority_shows_the_later_end(self):
        lua = build(setup="loc[1] = effect('FEAR', 'Feared', 5, 2, 'f', 3); loc[2] = effect('STUN', 'Stunned', 5, 2, 's', 6)")
        lua.execute("changed()")
        self.assertEqual(lua.eval("AurasLossOfControl.label.text"), "Stunned")

    def test_a_root_shows_nothing(self):
        lua = build(setup="loc[1] = effect('ROOT', 'Rooted', 1, 0, 'root', 5)")
        lua.execute("changed()")
        self.assertIsNone(lua.eval("AurasLossOfControl"))
        lua.execute("loc[2] = effect('DISARM', 'Disarmed', 3, 1, 'dis', 5); changed()")
        self.assertEqual(lua.eval("AurasLossOfControl.label.text"), "Disarmed")

    def test_a_school_lockout_names_the_school_and_has_an_icon(self):
        lua = build(setup="loc[1] = effect('SCHOOL_INTERRUPT', 'Interrupted', 2, 1, '', 4, 4)")
        lua.execute("changed()")
        self.assertEqual(lua.eval("AurasLossOfControl.label.text"), "Fire Locked")
        self.assertNotEqual(lua.eval("AurasLossOfControl.icon.texture"), "")

    def test_an_effect_with_no_timer_shows_without_a_sweep(self):
        lua = build(setup="loc[1] = effect('STUN', 'Stunned', 5, 2, 'stun', nil); loc[1].startTime = nil")
        lua.execute("changed()")
        self.assertTrue(lua.eval("AurasLossOfControl:IsShown()"))
        self.assertIsNone(lua.eval("AurasLossOfControl.cd.cooldown"))

    def test_a_repeated_update_does_not_restart_the_sweep(self):
        lua = build(setup=STUN)
        lua.execute("changed(); sweeps = count('SetCooldown'); changed()")
        self.assertEqual(lua.eval("count('SetCooldown')"), lua.eval("sweeps"))

    def test_an_effect_already_on_at_login_shows(self):
        lua = build(setup=STUN)
        lua.execute("fire('PLAYER_ENTERING_WORLD'); changed()")
        self.assertTrue(lua.eval("AurasLossOfControl:IsShown()"))

    def test_the_option_off_shows_nothing_and_registers_no_event(self):
        lua = build(saved="AurasDB = { lossOfControl = false }", setup=STUN)
        lua.execute("changed()")
        self.assertIsNone(lua.eval("AurasLossOfControl"))
        found = lua.eval("""(function() for _, w in ipairs(widgets) do
            if w.events.LOSS_OF_CONTROL_UPDATE then return true end end return false end)()""")
        self.assertFalse(found)

    def test_the_checkbox_turns_it_off_and_on(self):
        lua = build(setup=STUN)
        lua.execute("changed()")
        lua.execute("settingsWindow.use('Auras_lossOfControl', false)")
        self.assertFalse(lua.eval("AurasLossOfControl:IsShown()"))
        found = "(function() for _, w in ipairs(widgets) do if w.events.LOSS_OF_CONTROL_UPDATE then return true end end return false end)()"
        self.assertFalse(lua.eval(found))
        lua.execute("settingsWindow.use('Auras_lossOfControl', true)")
        self.assertTrue(lua.eval(found))
        self.assertTrue(lua.eval("AurasLossOfControl:IsShown()"), "an effect still on shows again")

    def test_ctrl_shift_builds_it_to_be_placed_and_a_placed_frame_stays(self):
        lua = build(setup="layoutCache['AurasLossOfControl'] = { 300, -200 }")
        lua.execute("press(true, true)")
        self.assertTrue(lua.eval("AurasLossOfControl:IsShown()"))
        self.assertEqual(lua.eval("AurasLossOfControl.label.text"), "Loss of control")
        lua.execute("press(false, false)")
        self.assertFalse(lua.eval("AurasLossOfControl:IsShown()"))


if __name__ == "__main__":
    unittest.main()
