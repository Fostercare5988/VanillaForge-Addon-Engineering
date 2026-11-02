"""Timer bars drain by themselves (ClassicAPI 1.19 SetTimerDuration), 2026-11-02.

A row with an expiry gets its time span once and the bar follows it; the group's
per-frame update only rewrites the clock when the second changes. Preview and
queue rows hold a value. Drawing and the spark's look stay in-game checks.
"""
import unittest
from test_audit_2026_10_26 import av_timers, yell, frame_update, row
from test_timer_bars import runtime

STONEHEARTH = "The Stonehearth Graveyard is under attack! If left unchecked, the Horde will capture it!"


class TimerFill(unittest.TestCase):
    def test_a_counting_row_drains_from_a_time_span_in_seconds(self):
        lua = av_timers()
        yell(lua, STONEHEARTH)
        bar = lua.eval("AutoBG_AVNodeFrame.rows[1].bar")
        self.assertEqual(bar.timerDirection, 1)
        self.assertEqual(bar.timer.endTime - bar.timer.startTime, 300)
        self.assertEqual(bar.timer.endTime, 1300)

    def test_frames_write_no_fill(self):
        lua = av_timers()
        yell(lua, STONEHEARTH)
        lua.execute("AutoBG_AVNodeFrame.rows[1].bar.fillValue = nil")
        for i in range(120):
            frame_update(lua, "AutoBG_AVNodeFrame", 1000 + i / 60)
        self.assertIsNone(lua.eval("AutoBG_AVNodeFrame.rows[1].bar.fillValue"))

    def test_the_spark_appears_once_the_bar_is_part_way(self):
        lua = av_timers()
        yell(lua, STONEHEARTH)
        self.assertFalse(row(lua, "AutoBG_AVNodeFrame", 1, "sparkShown"))
        frame_update(lua, "AutoBG_AVNodeFrame", 1000 + 150)
        self.assertTrue(row(lua, "AutoBG_AVNodeFrame", 1, "sparkShown"))

    def test_preview_rows_hold_a_value(self):
        lua = runtime()
        bar = lua.eval("AutoBG_NodeFrame.rows[1].bar")
        self.assertIsNone(bar.timer)
        self.assertIsNotNone(bar.fillValue)


if __name__ == "__main__":
    unittest.main()
