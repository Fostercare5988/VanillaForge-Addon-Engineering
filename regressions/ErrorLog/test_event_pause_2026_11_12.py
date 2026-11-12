"""!ErrorLog names the event after a pause and saves its own numbers (1.7.1, 2026-11-12).

The first run with the longest pause (1.7.0) put every Stratholme stutter
between two FostercareTweaks hooks that ran outside any timed script: the
game's own handlers around them were not being timed, so the XML pass at login
had wrapped little or nothing in the real client. Each slow frame now also
keeps its longest pause between two events (hooks do not split it), and the
profiler saves at logout what the report shows: per addon time and new memory
per second, and what the XML pass did (frames walked, of a known widget type,
scripts wrapped, its error if it failed).
"""
import unittest
from test_blind_spots_2026_11_03 import load

START = r"""
    now = now + 10 -- past the quiet seconds after login
    tick()
"""


class EventPause(unittest.TestCase):
    def test_a_hook_does_not_split_the_pause_between_events(self):
        lua = load()
        lua.execute(START + r"""
            counter.scripts.OnEvent(counter, "UNIT_HEALTH")
            clockv = clockv + 100
            TargetFrame.scripts.OnEvent() -- 155 ms of script between the events
            clockv = clockv + 100
            counter.scripts.OnEvent(counter, "PARTY_MEMBERS_CHANGED")
            tick()
        """)
        h = lua.eval("db.hitches[1]")
        self.assertEqual((h.gap, h.gapFrom, h.gapTo), (100, "event UNIT_HEALTH", "TargetFrame OnEvent"))
        self.assertEqual((h.evGap, h.evFrom, h.evTo), (355, "event UNIT_HEALTH", "event PARTY_MEMBERS_CHANGED"))
        lua.execute("ErrorLog.OpenStutters()")
        self.assertIn("longest pause between events: 355 ms, after event UNIT_HEALTH, before event PARTY_MEMBERS_CHANGED",
                      lua.eval("text"))

    def test_a_frame_without_events_runs_tick_to_tick(self):
        lua = load()
        lua.execute(START + "clockv = clockv + 120; tick()")
        h = lua.eval("db.hitches[1]")
        self.assertEqual((h.evGap, h.evFrom, h.evTo), (120, "frame tick", "frame tick"))

    def test_logout_saves_the_numbers_and_the_xml_pass(self):
        lua = load()
        lua.execute(START + r"""
            TargetFrame.scripts.OnEvent()
            tick()
            now = now + 90
            event = "PLAYER_LOGOUT"; driver.scripts.OnEvent()
        """)
        self.assertEqual(lua.eval("db.seconds"), 100)
        self.assertAlmostEqual(lua.eval("db.cpu.FostercareTweaks"), 1.5)
        self.assertAlmostEqual(lua.eval("db.cpu['Game UI and XML']"), 0.05)
        self.assertEqual(lua.eval("db.xml.scripts"), 1) # the target frame's OnEvent
        self.assertEqual(lua.eval("db.xml.error"), None)
        lua.execute("function ErrorLog.ShowReport(report) _, subtitle = report() end ErrorLog.OpenStutters()")
        self.assertIn("hooks and 1 XML scripts.", lua.eval("subtitle"))

    def test_a_failed_xml_pass_is_kept_not_lost(self):
        lua = load()
        lua.execute(r"""
            function EnumerateFrames() error("no such function here") end
            event = "PLAYER_LOGIN"; driver.scripts.OnEvent()
            event = "PLAYER_LOGOUT"; driver.scripts.OnEvent()
        """)
        self.assertIn("no such function here", lua.eval("db.xml.error"))


if __name__ == "__main__":
    unittest.main()
