"""ThreatMeter 1.0: what the window shows (spec 4.5, tests 7-10 and 13).

Rows in threat order, your own red, others by class; percent of the tank's threat
from the raw numbers (the answer's percent field is not read); "Pull aggro +N" at
110% in melee and 130% at range; the warning at 80% of the tank's threat, every 5 s
at most, never as the tank; a preview through the same path as an answer.
"""
import unittest

from tm_env import FIGHT, fight, load, names, rows


class Parse(unittest.TestCase):
    def test_the_tail_after_a_hash_is_ignored(self):
        lua = fight()
        lua.execute('answer("Tank:1:1000:100:1;Me:0:500:50:0#Ghost:0:9999:99:1")')
        self.assertEqual(names(lua), ["Tank", "Me"])

    def test_text_before_the_answer_and_odd_names(self):
        lua = fight()
        lua.execute('''fire("CHAT_MSG_ADDON", "TWT", "x=1 TWTv4=Tank:1:1000:100:1;Zoë-NZ:0:800:80:1;Me:0:10:1:0", "RAID", "Tank")''')
        self.assertEqual(names(lua), ["Tank", "Zoë-NZ", "Me"])

    def test_an_empty_answer_shows_no_rows_and_keeps_asking(self):
        lua = fight()
        lua.execute('answer(""); step(0.2)')
        self.assertEqual(names(lua), [])
        self.assertEqual(lua.eval("title()"), "Onyxia")
        self.assertEqual(lua.eval("#sent"), 2)

    def test_fourteen_players(self):
        lua = fight()
        body = ";".join("P%d:%d:%d:0:1" % (i, i == 1, 2000 - i * 100) for i in range(1, 15))
        lua.execute('answer("%s")' % body)
        self.assertEqual(names(lua), ["P%d" % i for i in range(1, 15)])

    def test_a_field_that_is_no_number_reads_as_zero(self):
        lua = fight()
        lua.execute('answer("Tank:1:1000:100:1;Me:0:lots:?:0")')
        self.assertEqual(rows(lua)[1]["threat"], "0")
        self.assertEqual(lua.eval("#handled"), 0)


class OrderAndDraw(unittest.TestCase):
    def test_rows_in_threat_order_ties_by_name(self):
        lua = fight()
        lua.execute('answer("Me:0:300:0:0;Bob:0:500:0:1;Tank:1:900:0:1;Al:0:500:0:1")')
        self.assertEqual(names(lua), ["Tank", "Al", "Bob", "Me"])

    def test_your_row_is_red_others_by_class_a_stranger_grey(self):
        lua = fight()
        lua.execute('answer("Tank:1:1000:0:1;Stranger:0:800:0:1;Me:0:600:0:0")')
        tank, stranger, me = rows(lua)
        self.assertEqual((tank["r"], tank["g"], tank["b"]), (0.78, 0.61, 0.43))
        self.assertEqual((stranger["r"], stranger["g"], stranger["b"]), (0.5, 0.5, 0.5))
        self.assertEqual((me["r"], me["g"], me["b"]), (1, 0.15, 0.1))

    def test_the_same_owner_eases_a_new_owner_jumps(self):
        lua = fight()
        lua.execute('answer("%s"); step(0.2); answer("Tank:1:1000:0:1;Healer:0:750:0:0;Me:0:600:0:0")' % FIGHT)
        self.assertEqual(rows(lua)[1]["how"], 1, "Healer stays second: eased")
        lua.execute('step(0.2); answer("Tank:1:1000:0:1;Me:0:900:0:0;Healer:0:750:0:0")')
        second = rows(lua)[1]
        self.assertEqual((second["name"], second["how"]), ("Me", 0), "a new owner jumps")

    def test_texts_are_written_only_when_they_change(self):
        lua = fight()
        lua.execute('answer("%s"); step(0.2)' % FIGHT)
        before = [r["writes"] for r in rows(lua)]
        lua.execute('answer("%s")' % FIGHT)
        self.assertEqual([r["writes"] for r in rows(lua)], before)

    def test_percent_and_threat_texts(self):
        lua = fight()
        lua.execute('answer("Tank:1:12000:0:1;Me:0:10200:0:1")')
        tank, me = rows(lua)
        self.assertEqual((tank["pct"], tank["threat"]), ("100%", "12K"))
        self.assertEqual((me["pct"], me["threat"]), ("85%", "10K"))

    def test_threat_per_second_over_the_last_seconds(self):
        lua = fight("ThreatMeterDB = { width = 300 }")
        lua.execute('answer("Tank:1:1000:0:1;Me:0:0:0:0")')
        lua.execute('step(2); answer("Tank:1:1500:0:1;Me:0:400:0:0")')
        tank, me = rows(lua)
        self.assertEqual((tank["tps"], me["tps"]), (250, 200))

    def test_a_narrow_window_leaves_out_per_second_then_threat(self):
        widths = {}
        for width in (300, 220, 150):
            lua = fight("ThreatMeterDB = { width = %d }" % width)
            lua.execute('answer("%s")' % FIGHT)
            r = rows(lua)[0]
            widths[width] = (bool(r["tpsShown"]), bool(r["threatShown"]))
        self.assertEqual(widths, {300: (True, True), 220: (False, True), 150: (False, False)})

    def test_players_shown_cuts_the_list_but_you_are_always_on_it(self):
        lua = fight("ThreatMeterDB = { rows = 3 }")
        lua.execute('answer("Tank:1:1000:0:1;A:0:900:0:1;B:0:800:0:1;C:0:700:0:1;Me:0:100:0:0")')
        self.assertEqual(names(lua), ["Tank", "A", "Me"])
        self.assertEqual(rows(lua)[2]["r"], 1, "in red")

    def test_the_window_is_as_tall_as_what_it_shows(self):
        lua = fight("ThreatMeterDB = { rowHeight = 20 }")
        empty = lua.eval("ThreatMeter_Window:GetHeight()")
        lua.execute('answer("%s")' % FIGHT)
        three = lua.eval("ThreatMeter_Window:GetHeight()")
        self.assertEqual(three - empty, 3 * 20 + 20 + 10, "three rows, the pull line, the labels")

    def test_a_new_width_lays_the_rows_out_again(self):
        lua = fight()
        lua.execute('answer("%s"); settingsWindow.use("ThreatMeter_width", 300)' % FIGHT)
        self.assertEqual(lua.eval("ThreatMeter_Window:GetWidth()"), 300)
        self.assertEqual(names(lua), ["Tank", "Healer", "Me"], "the rows are drawn again at once")
        lua.execute('settingsWindow.use("ThreatMeter_rows", 3); settingsWindow.use("ThreatMeter_rows", 2)')
        self.assertEqual(names(lua), ["Tank", "Me"])


class PercentAndPull(unittest.TestCase):
    def test_percent_is_of_the_tanks_threat_whatever_the_answer_says(self):
        lua = fight()
        lua.execute('answer("Tank:1:1000:12:1;Me:0:500:99:0")')
        self.assertEqual(rows(lua)[1]["pct"], "50%")
        self.assertEqual(lua.eval("title()"), "Onyxia  50%")
        self.assertEqual(lua.eval("badgeText()"), "50%")

    def test_with_nobody_holding_aggro_percent_is_of_the_most(self):
        lua = fight()
        lua.execute('answer("A:0:800:0:1;Me:0:400:0:0")')
        self.assertEqual([r["pct"] for r in rows(lua)], ["100%", "50%"])
        self.assertIsNone(lua.eval("pullLine()"), "no pull line without a tank")

    def test_at_range_you_pull_at_130_percent(self):
        lua = fight()
        lua.execute('answer("Tank:1:1000:0:1;Me:0:600:0:0")')
        pull = dict(lua.eval("pullLine()").items())
        self.assertEqual(pull["name"], "Pull aggro +700")
        self.assertAlmostEqual(pull["value"], 600 * 100 / 1300)

    def test_in_melee_you_pull_at_110_percent(self):
        lua = fight()
        lua.execute('answer("Tank:1:10000:0:1;Me:0:6000:0:1")')
        self.assertEqual(lua.eval("pullLine().name"), "Pull aggro +5K")

    def test_as_the_tank_you_hold_aggro(self):
        lua = fight()
        lua.execute('answer("Me:1:1000:0:1;Healer:0:700:0:0")')
        self.assertEqual(lua.eval("pullLine().name"), "You hold aggro")
        self.assertEqual(lua.eval("badgeText()"), "100%")

    def test_no_pull_line_and_no_badge_when_you_are_not_in_the_answer(self):
        lua = fight()
        lua.execute('answer("Tank:1:1000:0:1;Healer:0:700:0:0")')
        self.assertIsNone(lua.eval("pullLine()"))
        self.assertFalse(lua.eval("ThreatMeter_Badge:IsShown()"))
        self.assertEqual(lua.eval("title()"), "Onyxia")


class Warning(unittest.TestCase):
    def test_past_80_percent_one_pulse_one_sound_one_flash(self):
        lua = fight()
        lua.execute('answer("Tank:1:1000:0:1;Me:0:790:0:0")')
        self.assertEqual(lua.eval("sounds"), 0)
        lua.execute('step(0.2); answer("Tank:1:1000:0:1;Me:0:800:0:0")')
        self.assertEqual((lua.eval("pulses()"), lua.eval("sounds"), lua.eval("flashes")), (1, 1, 1))
        self.assertTrue(lua.eval('string.find(lastSound, "ThreatMeter\\\\sounds\\\\warn.ogg", 1, true) ~= nil'))

    def test_again_only_after_five_seconds(self):
        lua = fight()
        hot = 'answer("Tank:1:1000:0:1;Me:0:900:0:0")'
        lua.execute(hot)
        for _ in range(20):
            lua.execute("step(0.2); " + hot)
        self.assertEqual(lua.eval("sounds"), 1, "4 s later: still one")
        for _ in range(6):
            lua.execute("step(0.2); " + hot)
        self.assertEqual(lua.eval("sounds"), 2)

    def test_never_as_the_tank(self):
        lua = fight()
        lua.execute('answer("Me:1:1000:0:1;Healer:0:990:0:0")')
        self.assertEqual(lua.eval("sounds"), 0)


class Preview(unittest.TestCase):
    def test_fills_the_window_and_shows_the_warning_out_of_combat(self):
        lua = load()
        lua.execute('settingsWindow.click(settingsWindow.row(page(), "Preview"))')
        self.assertEqual(len(rows(lua)), 9)
        self.assertEqual(lua.eval("title()"), "Preview  85%")
        self.assertIn("Me", names(lua))
        self.assertEqual(lua.eval("pullLine().name"), "Pull aggro +3K")
        self.assertEqual((lua.eval("pulses()"), lua.eval("sounds")), (1, 1))
        self.assertTrue(lua.eval("ThreatMeter_Badge:IsShown()"), "the badge shows, to be dragged")
        self.assertEqual(lua.eval("#sent"), 0, "nothing is asked")

    def test_the_button_again_ends_it(self):
        lua = load()
        lua.execute('local r = settingsWindow.row(page(), "Preview"); settingsWindow.click(r); settingsWindow.click(r)')
        self.assertEqual(names(lua), [])
        self.assertEqual(lua.eval("title()"), "ThreatMeter")

    def test_a_fight_ends_it_and_the_meter_asks(self):
        lua = load()
        lua.execute('settingsWindow.click(settingsWindow.row(page(), "Preview")); fight()')
        self.assertEqual(names(lua), [])
        self.assertEqual(lua.eval("#sent"), 1)
        lua.execute('answer("%s")' % FIGHT)
        self.assertEqual(names(lua), ["Tank", "Healer", "Me"])
        self.assertEqual(rows(lua)[1]["g"], 1, "the Healer's class read from the group, not the sample")

    def test_its_warning_does_not_silence_the_first_real_one(self):
        lua = load()
        lua.execute('settingsWindow.click(settingsWindow.row(page(), "Preview")); step(1); fight()')
        lua.execute('answer("Tank:1:1000:0:1;Me:0:900:0:0")')
        self.assertEqual(lua.eval("sounds"), 2, "the preview's, then the fight's")

    def test_not_in_combat(self):
        lua = fight(setup='target.kind = "normal"')
        lua.execute('settingsWindow.click(settingsWindow.row(page(), "Preview"))')
        self.assertEqual(names(lua), [])

    def test_a_target_change_leaves_it_alone(self):
        lua = load()
        lua.execute('settingsWindow.click(settingsWindow.row(page(), "Preview")); retarget("Hogger", "rare")')
        self.assertEqual(len(rows(lua)), 9)


if __name__ == "__main__":
    unittest.main()
