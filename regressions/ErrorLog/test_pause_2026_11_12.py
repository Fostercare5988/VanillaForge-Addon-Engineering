"""!ErrorLog places an engine stutter inside the frame (1.7.0, 2026-11-12).

Stratholme again: 35 of 40 stutters (100-1650 ms) with under 2 ms of script
time, hooks and XML scripts included, while the player saw them as mobs were
about to die. The time is in the engine or a DLL, and the events line cannot say
where. Every slow frame now keeps its longest stretch with no timed script
running, and what ran just before and after it: a script, an event the engine
sent, or the profiler's tick.

Runs Profiler.lua under Lua 5.1 with the mocks of the blind-spot suite. What
the engine does in each part of a frame stays an in-game question.
"""
import unittest
from test_blind_spots_2026_11_03 import load

START = r"""
    stack = "Interface\\AddOns\\ThreatMeter\\Core.lua:10: in function"
    local f = CreateFrame("Frame")
    f:SetScript("OnEvent", function()
        clockv = clockv + 2
        counter.scripts.OnEvent(counter, "PLAYER_TARGET_CHANGED") -- sent from inside the script
        clockv = clockv + 1
    end)
    addonHandler = f.scripts.OnEvent
    stack = "Interface\\AddOns\\!ErrorLog\\Profiler.lua:1: in function"
    now = now + 10 -- past the quiet seconds after login
    tick()
"""


class Pause(unittest.TestCase):
    def test_pause_between_two_events(self):
        lua = load()
        lua.execute(START + r"""
            clockv = clockv + 4
            counter.scripts.OnEvent(counter, "UNIT_HEALTH")
            clockv = clockv + 180 -- the engine, between two events
            counter.scripts.OnEvent(counter, "UNIT_DIED")
            clockv = clockv + 6
            tick()
        """)
        h = lua.eval("db.hitches[1]")
        self.assertEqual(h.ms, 190)
        self.assertEqual((h.gap, h.gapFrom, h.gapTo), (180, "event UNIT_HEALTH", "event UNIT_DIED"))
        lua.execute("ErrorLog.OpenStutters()")
        self.assertIn("longest pause with no script running: 180 ms, after event UNIT_HEALTH, before event UNIT_DIED",
                      lua.eval("text"))

    def test_pause_after_a_script_up_to_the_tick(self):
        lua = load()
        lua.execute(START + r"""
            clockv = clockv + 5
            addonHandler()          -- 3 ms of script, an event sent inside it
            clockv = clockv + 150   -- the engine, after the last script
            tick()
        """)
        h = lua.eval("db.hitches[1]")
        self.assertEqual((h.gap, h.gapFrom, h.gapTo), (150, "ThreatMeter Core.lua:10 OnEvent", "frame tick"))

    def test_pause_before_a_game_script(self):
        lua = load()
        lua.execute(START + r"""
            clockv = clockv + 120
            TargetFrame.scripts.OnEvent() -- 5 ms, and a 150 ms hook inside it
            tick()
        """)
        h = lua.eval("db.hitches[1]")
        self.assertEqual((h.gap, h.gapFrom, h.gapTo), (120, "frame tick", "TargetFrame OnEvent"))

    def test_each_frame_starts_fresh(self):
        lua = load()
        lua.execute(START + r"""
            clockv = clockv + 90; tick() -- a normal frame with a 90 ms pause is not kept
            now = now + 2
            counter.scripts.OnEvent(counter, "UNIT_AURA")
            clockv = clockv + 30
            addonHandler()
            clockv = clockv + 80
            tick()
        """)
        self.assertEqual(lua.eval("#db.hitches"), 1)
        h = lua.eval("db.hitches[1]")
        self.assertEqual((h.gap, h.gapFrom, h.gapTo), (80, "ThreatMeter Core.lua:10 OnEvent", "frame tick"))


if __name__ == "__main__":
    unittest.main()
