"""The target cast bar fills itself (ClassicAPI 1.19 SetTimerDuration), 2026-11-02.

No OnUpdate runs during a cast: the time span goes on the bar once, the spark
rides the bar's texture, and a stop event (or a one-shot timer, if the event
is missed) ends it. DELAYED and CHANNEL_UPDATE never fire for other units, so
the bar no longer listens for them. Native drawing stays an in-game check.
"""
import unittest
from lupa.lua51 import LuaRuntime
from test_event_fanout import BASE, CASTBAR


class TargetCastbarTimer(unittest.TestCase):
    def setUp(self):
        self.lua = lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute(BASE + r'''
            registered = {}
            local create = CreateFrame
            function CreateFrame(kind, name)
                local f = create(kind, name)
                f.RegisterEvent = function(_, ev) registered[ev] = true end
                f.RegisterUnitEvent = function(_, ev) registered[ev] = true end
                f.UnregisterAllEvents = function() registered = {} end
                f.SetScript = function(self, k, fn) self.scripts = self.scripts or {}; self.scripts[k] = fn end
                f.SetTimerDuration = function(self, d, i, dir) self.timer, self.dir = d, dir; sets = (sets or 0) + 1 end
                f.SetValue = function() values = (values or 0) + 1 end
                return f
            end
            TargetFrame = CreateFrame("Frame", "TargetFrame")
            now, channel = 1, false
            function GetTime() return now end
            function UnitGUID() return "0xT" end
            function UnitExists() return true end
            function UnitIsDeadOrGhost() return false end
            function UnitIsUnit() return false end
            C_Spell = {
                UnitCastingInfo = function()
                    if cast and not channel then return "Fireball", "", "icon", cast[1], cast[2], nil, "c", nil end
                end,
                UnitChannelInfo = function()
                    if cast and channel then return "Drain", "", "icon", cast[1], cast[2], nil, nil end
                end,
            }
        ''')
        lua.execute(CASTBAR)
        lua.execute(r'''
            module = FostercareTweaks.mods["Enemy Castbars"]
            module:enable()
            handler = handlers[module.frame]
        ''')

    def test_a_cast_sets_the_time_span_once_and_runs_no_update(self):
        self.lua.execute('cast = { 1000, 3500 }; handler(nil, "UNIT_SPELLCAST_START", "target")')
        self.assertTrue(self.lua.eval("FCTweaksTargetCastbar:IsShown()"))
        self.assertEqual(self.lua.eval("FCTweaksTargetCastbar.dir"), 0)
        self.assertEqual(self.lua.eval("FCTweaksTargetCastbar.timer.endTime - FCTweaksTargetCastbar.timer.startTime"), 2.5)
        self.assertIsNone(self.lua.eval("FCTweaksTargetCastbar.scripts and FCTweaksTargetCastbar.scripts.OnUpdate"))
        self.assertIsNone(self.lua.eval("values"))

    def test_a_channel_empties_the_bar(self):
        self.lua.execute('channel = true; cast = { 1000, 3000 }; handler(nil, "UNIT_SPELLCAST_CHANNEL_START", "target")')
        self.assertEqual(self.lua.eval("FCTweaksTargetCastbar.dir"), 1)

    def test_the_stop_event_hides_the_bar(self):
        self.lua.execute('cast = { 1000, 3500 }; handler(nil, "UNIT_SPELLCAST_START", "target"); cast = nil; handler(nil, "UNIT_SPELLCAST_STOP", "target")')
        self.assertFalse(self.lua.eval("FCTweaksTargetCastbar:IsShown()"))

    def test_a_missed_stop_event_is_covered_by_a_timer_at_the_end_time(self):
        self.lua.execute('cast = { 1000, 3500 }; handler(nil, "UNIT_SPELLCAST_START", "target"); now = 3.6; for _, fn in ipairs(timers) do fn() end')
        self.assertFalse(self.lua.eval("FCTweaksTargetCastbar:IsShown()"))

    def test_the_end_timer_of_an_old_cast_does_not_hide_a_new_one(self):
        self.lua.execute('''cast = { 1000, 3500 }; handler(nil, "UNIT_SPELLCAST_START", "target")
            cast = { 1500, 9000 }; handler(nil, "UNIT_SPELLCAST_START", "target")
            now = 3.6; for _, fn in ipairs(timers) do fn() end''')
        self.assertTrue(self.lua.eval("FCTweaksTargetCastbar:IsShown()"))

    def test_events_other_units_never_send_are_not_registered(self):
        for ev in ("UNIT_SPELLCAST_DELAYED", "UNIT_SPELLCAST_CHANNEL_UPDATE", "UNIT_SPELLCAST_FAILED"):
            self.assertIsNone(self.lua.eval('registered["%s"]' % ev), ev)
        self.assertTrue(self.lua.eval('registered["UNIT_SPELLCAST_START"]'))


if __name__ == "__main__":
    unittest.main()


class TargetCastbarMover(unittest.TestCase):
    """Ctrl+Shift moves the target cast bar (2026-11-02)."""

    def build(self, saved):
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute(BASE + r'''
            local create = CreateFrame
            function CreateFrame(kind, name)
                local f = create(kind, name)
                f.SetPoint = function(self, ...) points = (points or 0) + 1 end
                return f
            end
            TargetFrame = CreateFrame("Frame", "TargetFrame")
            local noop = function() end; C_Spell = { UnitCastingInfo = noop, UnitChannelInfo = noop }
            function UnitExists() return true end
            function UnitIsDeadOrGhost() return false end
            function GetTime() return 1 end
            FostercareTweaks.RestoreFramePosition = function(frame, key, rel) restored = { key, rel }; return %s end
            FostercareTweaks.RegisterFrameMover = function(frame, key, label, rel, onStop) mover = { frame, key, rel, onStop } end
        ''' % saved)
        lua.execute(CASTBAR)
        lua.execute('FostercareTweaks.mods["Enemy Castbars"]:enable()')
        return lua

    def test_the_bar_registers_a_mover_that_follows_the_target_frame(self):
        lua = self.build("false")
        self.assertEqual(lua.eval("mover[2]"), "target_castbar")
        self.assertTrue(lua.eval("mover[3] == TargetFrame and restored[2] == TargetFrame"))
        self.assertIsNotNone(lua.eval("FCTweaksTargetCastbar.fctRestoreShown"))

    def test_a_saved_position_replaces_the_default_anchor(self):
        lua = self.build("true")
        self.assertIsNone(lua.eval("points"))
        lua = self.build("false")
        self.assertEqual(lua.eval("points"), 1)
        lua.execute("mover[4]()")
        lua.execute("points = 0; FostercareTweaks.LayoutTargetCastbar()")
        self.assertEqual(lua.eval("points"), 0)

    def test_the_bar_stays_up_while_held_and_hides_after(self):
        lua = self.build("false")
        lua.execute("local b = FCTweaksTargetCastbar; b:Show(); b.fctForcedShown = true; FostercareTweaks.RefreshTargetCastbar()")
        self.assertTrue(lua.eval("FCTweaksTargetCastbar:IsShown()"))
        lua.execute("local b = FCTweaksTargetCastbar; b.fctForcedShown = nil; b.fctRestoreShown(b)")
        self.assertFalse(lua.eval("FCTweaksTargetCastbar:IsShown()"))
