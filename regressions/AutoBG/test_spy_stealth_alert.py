"""Open-world stealth warning: a detected stealthed rogue raises the alert and sound.

The complete AutoBG_Spy.lua runs under Lua 5.1 with the Spy widget mocks. A
hostile rogue named Sneaky carries a Stealth aura and is reached through each
real detection path (nameplate, stealth cast, NamPower buff event). Unit
visibility, real distances, the alert's screen position and the audible sound
stay in-game checks.
"""
import unittest
from lupa.lua51 import LuaRuntime

import addon_loader
from test_spy_nearby import BASE, SPY, FLUSH, advance, fire

ROGUE = "0x0000000000000002"

STEALTH = r'''
AutoBG_Settings.Spy.StealthAlert = true
AutoBG_Settings.Spy.SoundAlert = true
AutoBG_Settings.Spy.StealthProximityOnly = true
names["%(rogue)s"] = "Sneaky"
sounds = {}
function PlaySound(name) table.insert(sounds, name) end
stealthed = {}
AutoBG_Targets.CheckUnitStealth = function(unit)
    local guid = UnitGUID(unit)
    if guid and stealthed[guid] then return true, stealthed[guid] end
    return false
end
yards, los = {}, true
function UnitDistanceSquared(unit)
    local guid = UnitGUID(unit)
    if not guid then return 0, false end
    local d = yards[guid] or 5
    return d * d, true
end
function UnitInLineOfSight() return los end
function UnitTokenFromName(name)
    for guid, n in pairs(names) do if n == name then return guid end end
end
function UnitClass(u)
    if UnitGUID(u) == "%(rogue)s" then return "Rogue", "ROGUE" end
    return "Warrior", "WARRIOR"
end
''' % {"rogue": ROGUE}


def runtime():
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(BASE)
    lua.execute(STEALTH)
    addon_loader.load(lua, SPY, "AutoBG_Spy.lua")
    lua.execute('AutoBG_SpyEventFrame.scripts.OnEvent(AutoBG_SpyEventFrame, "PLAYER_LOGIN")')
    return lua


def dispatch(lua, *args):
    """Fire an event without running timers, so the 4.5 s hide timer stays pending."""
    values = ", ".join(repr(a) if isinstance(a, str) else str(a) for a in args)
    lua.execute('AutoBG_SpyEventFrame.scripts.OnEvent(AutoBG_SpyEventFrame, %s)' % values)


def show_plate(lua):
    lua.execute('plates["nameplate1"] = { name = "Sneaky", guid = "%s" }' % ROGUE)
    fire(lua, "NAME_PLATE_UNIT_ADDED", "nameplate1")


class SpyStealthAlertTests(unittest.TestCase):
    def assertAlerted(self, lua):
        self.assertTrue(lua.eval('AutoBG_SpyAlertWindow ~= nil and AutoBG_SpyAlertWindow.shown'))
        self.assertEqual("|cff00ffffStealth|r", lua.eval('AutoBG_SpyAlertWindow.Title.text'))
        self.assertEqual(lua.eval('AutoBG_SpyAlertWindow.Name.text'), "Sneaky")
        self.assertEqual(lua.eval('sounds[1]'), "RaidWarning")

    def assertQuiet(self, lua):
        self.assertFalse(lua.eval('AutoBG_SpyAlertWindow ~= nil and AutoBG_SpyAlertWindow.shown'))
        self.assertEqual(lua.eval('table.getn(sounds)'), 0)

    def test_detected_stealthed_rogue_shows_alert_and_plays_sound(self):
        lua = runtime()
        lua.execute('stealthed["%s"] = "Stealth"' % ROGUE)
        show_plate(lua)
        self.assertAlerted(lua)

    def test_rogue_casting_stealth_nearby_alerts(self):
        lua = runtime()
        lua.execute('stealthed["%s"] = "Stealth"' % ROGUE)
        dispatch(lua, "UNIT_CASTEVENT", ROGUE, "", "CAST", 1787, 0)
        self.assertAlerted(lua)

    def test_nampower_stealth_buff_alerts(self):
        lua = runtime()
        lua.execute('stealthed["%s"] = "Stealth"' % ROGUE)
        dispatch(lua, "BUFF_ADDED_OTHER", ROGUE, 1, 1787, 1, 60, 0, 0)
        self.assertAlerted(lua)

    def test_detected_rogue_far_away_still_alerts(self):
        # Detection gear reveals stealthers farther out; seeing one is the warning.
        lua = runtime()
        lua.execute('stealthed["%s"] = "Stealth"; yards["%s"] = 25; los = false' % (ROGUE, ROGUE))
        show_plate(lua)
        self.assertAlerted(lua)

    def test_stealthed_rogue_you_cannot_see_stays_quiet(self):
        lua = runtime()
        lua.execute('stealthed["%s"] = "Stealth"; visible = false' % ROGUE)
        dispatch(lua, "UNIT_CASTEVENT", ROGUE, "", "CAST", 1787, 0)
        self.assertQuiet(lua)

    def test_clicking_the_alert_targets_and_focuses_the_enemy(self):
        lua = runtime()
        lua.execute('stealthed["%s"] = "Stealth"' % ROGUE)
        show_plate(lua)
        lua.execute('picks = {}; AutoBG_Targets.SelectEnemy = function(n, g, b) table.insert(picks, n .. "|" .. tostring(g) .. "|" .. b) end')
        lua.execute('local w = AutoBG_SpyAlertWindow; w.scripts.OnClick(w, "LeftButton"); w.scripts.OnClick(w, "RightButton")')
        self.assertEqual(lua.eval('picks[1]'), "Sneaky|%s|LeftButton" % ROGUE)
        self.assertEqual(lua.eval('picks[2]'), "Sneaky|%s|RightButton" % ROGUE)

    def test_unstealthed_rogue_raises_no_stealth_alert(self):
        lua = runtime()
        show_plate(lua)
        self.assertFalse(lua.eval('AutoBG_SpyAlertWindow ~= nil and AutoBG_SpyAlertWindow.shown'))
        self.assertNotIn("RaidWarning", list(lua.eval('sounds').values()))

    def test_sound_setting_off_still_shows_the_alert(self):
        lua = runtime()
        lua.execute('AutoBG_Settings.Spy.SoundAlert = false; stealthed["%s"] = "Stealth"' % ROGUE)
        show_plate(lua)
        self.assertTrue(lua.eval('AutoBG_SpyAlertWindow.shown'))
        self.assertEqual(lua.eval('table.getn(sounds)'), 0)

    def test_alert_hides_by_itself(self):
        lua = runtime()
        lua.execute('stealthed["%s"] = "Stealth"' % ROGUE)
        show_plate(lua)
        lua.execute(FLUSH)
        self.assertFalse(lua.eval('AutoBG_SpyAlertWindow.shown'))

    def test_preview_plays_the_stealth_sound(self):
        lua = runtime()
        lua.execute('AutoBG_Spy:EnableTestMode()')
        self.assertTrue(lua.eval('AutoBG_SpyAlertWindow.shown'))
        self.assertEqual(lua.eval('sounds[1]'), "RaidWarning")

    def test_preview_respects_the_sound_setting(self):
        lua = runtime()
        lua.execute('AutoBG_Settings.Spy.SoundAlert = false; AutoBG_Spy:EnableTestMode()')
        self.assertTrue(lua.eval('AutoBG_SpyAlertWindow.shown'))
        self.assertEqual(lua.eval('table.getn(sounds)'), 0)


if __name__ == "__main__":
    unittest.main()
