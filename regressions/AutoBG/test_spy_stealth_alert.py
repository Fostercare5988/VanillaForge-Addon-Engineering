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
        self.assertIn("Stealth Detected!", lua.eval('AutoBG_SpyAlertWindow.Title.text'))
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

    def test_distant_rogue_alerts_once_within_ten_yards(self):
        lua = runtime()
        lua.execute('stealthed["%s"] = "Stealth"; yards["%s"] = 25' % (ROGUE, ROGUE))
        show_plate(lua)
        self.assertQuiet(lua)
        lua.execute('yards["%s"] = 8' % ROGUE)
        advance(lua, 1)
        self.assertEqual(lua.eval('sounds[1]'), "RaidWarning")
        self.assertEqual(lua.eval('table.getn(sounds)'), 1)

    def test_blocked_line_of_sight_stays_quiet(self):
        lua = runtime()
        lua.execute('stealthed["%s"] = "Stealth"; los = false' % ROGUE)
        show_plate(lua)
        self.assertQuiet(lua)

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
