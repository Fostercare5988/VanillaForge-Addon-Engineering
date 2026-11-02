"""Enemy cast bars fill themselves (ClassicAPI 1.19 SetTimerDuration), 2026-11-02.

The bar used to be written to and its spark moved on every frame of a cast.
Now a cast sets the time span once; a query only touches the bar when the cast
changed. Native drawing and pushback timing stay in-game checks.
"""
import unittest
from fnp_env import load

PRELUDE = '''
    cast = nil
    C_Spell.UnitCastingInfo = function()
        if cast and not cast.channel then
            return cast.name, "", "tex", cast.s, cast.e, false, 1, cast.locked
        end
    end
    C_Spell.UnitChannelInfo = function()
        if cast and cast.channel then return cast.name, "", "tex", cast.s, cast.e, false, cast.locked end
    end
'''


class CastbarTimer(unittest.TestCase):
    def setUp(self):
        self.lua = load(None, PRELUDE)
        self.lua.execute('plate = nativePlate("0xF1", "nameplate1"); runFrames(plate, 1)')

    def start(self, name="Frostbolt", seconds=2, channel=False, locked=False):
        self.lua.execute('''cast = { name = "%s", s = now * 1000, e = (now + %s) * 1000, channel = %s, locked = %s }

            fire("UNIT_SPELLCAST_START", "nameplate1")''' % (name, seconds, str(channel).lower(), str(locked).lower()))

    def test_a_cast_never_writes_the_bar_per_frame(self):
        self.start()
        self.lua.execute("runFrames(plate, 1); calls = {}; runFrames(plate, 90)")
        self.assertIsNone(self.lua.eval("calls.SetValue"))
        self.assertIsNone(self.lua.eval("calls.SetTimerDuration"))

    def test_the_bar_gets_its_time_span_in_seconds(self):
        self.start(seconds=2)
        self.lua.execute("runFrames(plate, 1)")
        self.assertTrue(self.lua.eval("plate.fnpCastbar:IsShown()"))
        self.assertEqual(self.lua.eval("plate.fnpCastbar.timerDirection"), 0)
        self.assertAlmostEqual(self.lua.eval("plate.fnpCastbar.timer.endTime - plate.fnpCastbar.timer.startTime"), 2, 3)

    def test_a_channel_empties_the_bar(self):
        self.start(channel=True)
        self.lua.execute("runFrames(plate, 1)")
        self.assertEqual(self.lua.eval("plate.fnpCastbar.timerDirection"), 1)

    def test_pushback_moves_the_end_without_resetting_the_bar(self):
        self.start(seconds=2)
        self.lua.execute("runFrames(plate, 1); calls = {}; cast.e = cast.e + 500; runFrames(plate, 10)")
        self.assertIsNone(self.lua.eval("calls.SetTimerDuration"))
        self.assertAlmostEqual(self.lua.eval("plate.fnpCastbar.timer.endTime - plate.fnpCastbar.timer.startTime"), 2.5, 3)

    def test_the_bar_hides_when_the_cast_ends(self):
        self.start(seconds=1)
        self.lua.execute("runFrames(plate, 30)")
        self.assertTrue(self.lua.eval("plate.fnpCastbar:IsShown()"))
        self.lua.execute("cast = nil; runFrames(plate, 40)")
        self.assertFalse(self.lua.eval("plate.fnpCastbar:IsShown()"))

    def test_the_bar_hides_at_the_end_time_without_an_event(self):
        self.start(seconds=0.5)
        self.lua.execute("runFrames(plate, 20)")
        self.assertTrue(self.lua.eval("plate.fnpCastbar:IsShown()"))
        self.lua.execute("runFrames(plate, 20)")
        self.assertFalse(self.lua.eval("plate.fnpCastbar:IsShown()"))


class Rebinding(unittest.TestCase):
    def test_a_unit_that_moves_plates_is_removed_then_added(self):
        lua = load()
        lua.execute('''
            old = nativePlate("0xF1", "nameplate1")
            local removed = {}
            table.insert(FNPLibNameplate.OnRemoved, function(p) table.insert(removed, p) end)
            fire("NAME_PLATE_UNIT_REMOVED", "nameplate1")
            assert(old.fnpUnitGUID == nil and removed[1] == old)
            new = nativePlate("0xF1", "nameplate2")
            assert(new.fnpUnitGUID == "0xF1" and old.fnpUnitGUID == nil)
        ''')


if __name__ == "__main__":
    unittest.main()
