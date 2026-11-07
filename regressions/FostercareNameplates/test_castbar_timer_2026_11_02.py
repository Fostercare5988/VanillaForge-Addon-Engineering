"""Enemy cast bars fill themselves (ClassicAPI 1.19 SetTimerDuration), 2026-11-02.

The bar used to be written to and its spark moved on every frame of a cast.
Now a cast sets the time span once.

2026-11-03: the bar is event-driven. ClassicAPI's cast events for the
nameplateN token, and a plate getting its unit, are the only times it asks
C_Spell; the 0.1 s re-query while casting and the 1 s idle query are gone.
Another unit's pushback is never sent to the client (ClassicAPI docs,
UNIT_SPELLCAST_*: DELAYED fires for the player only), so nothing was there to
catch. A bar whose STOP never came hides at its end time, checked twice a
second while a bar is up. Native drawing stays an in-game check.
"""
import unittest
from fnp_env import load

PRELUDE = '''
    cast = nil
    C_Spell.UnitCastingInfo = function()
        calls.UnitCastingInfo = (calls.UnitCastingInfo or 0) + 1
        if cast and not cast.channel then
            return cast.name, "", "tex", cast.s, cast.e, false, 1, cast.locked
        end
    end
    C_Spell.UnitChannelInfo = function()
        if cast and cast.channel then return cast.name, "", "tex", cast.s, cast.e, false, cast.locked end
    end
    C_Timer.NewTicker = function(_, f) backstop = f; return { Cancel = function() backstop = nil end } end
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

    def test_nothing_asks_during_a_cast_or_while_idle(self):
        self.lua.execute("calls = {}; runFrames(plate, 120)")
        self.assertIsNone(self.lua.eval("calls.UnitCastingInfo"))
        self.start()
        self.lua.execute("calls = {}; runFrames(plate, 90)")
        self.assertIsNone(self.lua.eval("calls.UnitCastingInfo"))

    def test_the_bar_gets_its_time_span_in_seconds(self):
        self.start(seconds=2)
        self.assertTrue(self.lua.eval("plate.fnpCastbar:IsShown()"))
        self.assertEqual(self.lua.eval("plate.fnpCastbar.timerDirection"), 0)
        self.assertAlmostEqual(self.lua.eval("plate.fnpCastbar.timer.endTime - plate.fnpCastbar.timer.startTime"), 2, 3)

    def test_a_channel_empties_the_bar(self):
        self.start(channel=True)
        self.assertEqual(self.lua.eval("plate.fnpCastbar.timerDirection"), 1)

    def test_the_bar_hides_when_the_cast_stops(self):
        self.start(seconds=1)
        self.lua.execute("runFrames(plate, 30)")
        self.assertTrue(self.lua.eval("plate.fnpCastbar:IsShown()"))
        self.lua.execute('cast = nil; fire("UNIT_SPELLCAST_STOP", "nameplate1")')
        self.assertFalse(self.lua.eval("plate.fnpCastbar:IsShown()"))

    def test_the_bar_hides_at_the_end_time_without_an_event(self):
        self.start(seconds=0.5)
        self.lua.execute("runFrames(plate, 20); backstop()")
        self.assertTrue(self.lua.eval("plate.fnpCastbar:IsShown()"))
        self.lua.execute("runFrames(plate, 20); backstop()")
        self.assertFalse(self.lua.eval("plate.fnpCastbar:IsShown()"))
        self.assertIsNone(self.lua.eval("backstop"), "the backstop keeps running with no bar up")

    def test_a_unit_that_comes_into_view_mid_cast_shows_it(self):
        self.lua.execute('cast = { name = "Heal", s = now * 1000, e = (now + 3) * 1000 }; other = nativePlate("0xF2", "nameplate2")')
        self.assertTrue(self.lua.eval("other.fnpCastbar and other.fnpCastbar:IsShown()"))

    def test_cast_events_are_heard_for_nameplate_tokens_only(self):
        self.assertTrue(self.lua.eval("receives(FNPNameplateCastEvents, 'UNIT_SPELLCAST_START', 'nameplate1')"))
        self.assertFalse(self.lua.eval("receives(FNPNameplateCastEvents, 'UNIT_SPELLCAST_START', 'target')"))


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
