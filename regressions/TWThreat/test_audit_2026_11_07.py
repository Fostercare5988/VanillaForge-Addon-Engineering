"""TWThreat audit, 2026-11-07: a smooth display, and the bugs under it.

Smooth display (the player's request): the bars eased out in about 0.15 s and then
sat still until the next server answer, the numbers jumped, and a rank change put
another player into a bar that kept the old player's width. Bars now glide over
the measured time between answers, belong to one player each, and slide to a new
rank; the numbers roll with them.

Bugs: each bar set its own alpha on top of the window's (combat opacity counted
twice); the full-screen glow was shown, invisible, on every update; an answer
for the previous target showed under the new target's name; messages went to
RAID while in a party until the first target change; tank mode cleared the
glow and sound settings for good. Retired: Healer Master Target (its button was
hidden and nothing set it), relays, /twt skeram, debug, the who window, the
unused warning frame.
"""
import re
import unittest

from twt_env import load, SOURCE, XML

FIGHT = "Tank:1:1000:100:1;A:0:600:60:1;B:0:500:50:1;Me:0:300:30:1"
BAR = 298  # the bar track: window width 300 minus the border


def fight(config="{}", setup=""):
    lua = load(config, setup)
    lua.execute("startFight()")
    return lua


class SmoothBars(unittest.TestCase):
    def test_bar_glides_over_the_whole_interval(self):
        lua = fight()
        lua.execute('packet("Tank:1:1000:100:1;Me:0:200:20:1"); run(0.5); tick()')
        lua.execute('packet("Tank:1:1000:100:1;Me:0:800:80:1"); run(0.25)')
        start, end = BAR * 0.2, BAR * 0.8
        progress = (lua.eval('width("Me")') - start) / (end - start)
        self.assertGreater(progress, 0.3, "the bar should still be moving halfway to the next answer")
        self.assertLess(progress, 0.7)
        lua.execute("run(0.5)")
        self.assertAlmostEqual(lua.eval('width("Me")'), end, delta=0.6)

    def test_bar_keeps_its_player_on_rank_change(self):
        lua = fight()
        lua.execute('packet("%s"); run(1); tick()' % FIGHT)
        self.assertAlmostEqual(lua.eval('width("B")'), BAR * 0.5, delta=0.6)
        lua.execute('packet("Tank:1:1000:100:1;B:0:700:70:1;A:0:600:60:1;Me:0:300:30:1"); step(0.001)')
        self.assertAlmostEqual(lua.eval('width("B")'), BAR * 0.5, delta=2,
                               msg="B's bar continues from B's width, not from the bar above")

    def test_rank_change_slides_the_bar(self):
        lua = fight()
        lua.execute('packet("%s"); run(1); tick()' % FIGHT)
        y_before = lua.eval('bars()["B"].frame.point[5]')
        lua.execute('packet("Tank:1:1000:100:1;B:0:700:70:1;A:0:600:60:1;Me:0:300:30:1"); run(0.08)')
        y_mid = lua.eval('bars()["B"].frame.point[5]')
        lua.execute("run(1)")
        y_after = lua.eval('bars()["B"].frame.point[5]')
        self.assertGreater(y_after, y_before, "B moved up one rank")
        self.assertTrue(y_before < y_mid < y_after, "and slid there")

    def test_numbers_roll_at_a_steady_rate(self):
        lua = fight()
        lua.execute('packet("Tank:1:1000:100:1;Me:0:200:20:1"); run(0.5); tick()')
        lua.execute('packet("Tank:1:1000:100:1;Me:0:800:80:1"); run(0.25)')
        perc = lua.eval('rawget(_G, "TWThreat" .. bars()["Me"].index .. "Perc").text')
        value = int(perc.rstrip("%"))
        self.assertTrue(30 < value < 70, perc)

    def test_animation_sleeps_when_settled(self):
        lua = fight()
        lua.execute('packet("%s"); run(2)' % FIGHT)
        self.assertEqual(lua.eval('(function() local n = 0 for _, w in ipairs(widgets) do '
                                  'if w.shown and w.scripts.OnUpdate then n = n + 1 end end return n end)()'), 0)
        writes = lua.eval('bars()["Me"].bg.widthWrites')
        lua.execute("run(0.5)")
        self.assertEqual(lua.eval('bars()["Me"].bg.widthWrites'), writes, "a settled bar makes no writes")

    def test_first_answer_for_a_target_snaps(self):
        lua = fight()
        lua.execute('packet("%s"); step(0.001)' % FIGHT)
        self.assertAlmostEqual(lua.eval('width("A")'), BAR * 0.6, delta=0.6)

    def test_tps_from_real_time(self):
        lua = fight()
        for i in range(8):
            lua.execute('packet("Tank:1:5000:100:1;Me:0:%d:%d:1"); run(0.5); tick()' % (1000 + 100 * i, 20 + i))
        lua.execute("run(1)")
        tps = lua.eval('rawget(_G, "TWThreat" .. bars()["Me"].index .. "TPS").text')
        self.assertAlmostEqual(float(tps), 200, delta=20)


class Targets(unittest.TestCase):
    def test_rares_show_threat(self):
        lua = fight(setup='target.classification = "rare"; target.name = "Rare Croc"')
        lua.execute('packet("Me:1:300:100:1;Parting:0:120:40:1"); step(0.01)')
        self.assertIsNotNone(lua.eval('bars()["Parting"]'))
        self.assertIn("Rare Croc", lua.eval("TWTMainTitle.text"))

    def test_rare_glow_image(self):
        lua = fight("{ glow = true }", 'target.classification = "rare"')
        lua.execute('packet("Me:0:300:30:1;Parting:1:900:100:1"); step(0.01)')
        self.assertTrue(lua.eval('TWThreatDisplayTargetGlow.texture').endswith("images\\rare"))

    def test_normal_mobs_do_not(self):
        lua = fight(setup='target.classification = "normal"; target.name = "Young Sawtooth Crocolisk"')
        self.assertEqual(lua.eval('(function() local n = 0 for _, m in ipairs(sent) do '
                                  'if m.prefix == "TWT_UDTSv4" then n = n + 1 end end return n end)()'), 0)
        self.assertNotIn("Crocolisk", lua.eval("TWTMainTitle.text"))

    def test_title_names_the_target_before_the_first_answer(self):
        lua = fight()
        self.assertEqual(lua.eval("TWTMainTitle.text"), "Boss")

    def test_close_players_do_not_swap_rows_on_every_answer(self):
        lua = fight()
        lua.execute('packet("Tank:1:1000:100:1;A:0:500:50:1;B:0:510:51:1;Me:0:300:30:1"); run(0.2)')
        idx = lua.eval('bars()["B"].frame.point[5]')
        for perc_a, perc_b in ((51, 50), (50, 51), (51, 50)):
            lua.execute('tick(); packet("Tank:1:1000:100:1;A:0:500:%d:1;B:0:510:%d:1;Me:0:300:30:1"); run(0.2)'
                        % (perc_a, perc_b))
            self.assertEqual(lua.eval('bars()["B"].frame.point[5]'), idx)
        lua.execute('tick(); packet("Tank:1:1000:100:1;A:0:500:55:1;B:0:510:50:1;Me:0:300:30:1"); run(1)')
        self.assertLess(lua.eval('bars()["B"].frame.point[5]'), idx, "a real lead still moves the row")

    def test_answer_parsing_keeps_tank_part_apart(self):
        lua = fight("{ tankMode = true }", 'playerClass = "WARRIOR"')
        lua.execute('packet("Me:1:300:100:1;A:0:120:40:0#TMTv1=Ghoul:0xF1:Bob:78;Imp:0xF2:Al:20"); step(0.01)')
        names = lua.eval('(function() local t = {} for n in pairs(bars()) do t[#t+1] = n end '
                         'table.sort(t) return table.concat(t, ",") end)()')
        self.assertEqual(names, "-Pull Aggro at-,A,Me")
        self.assertEqual(lua.eval("TMEF1Target.text"), "Ghoul")


class Bugs(unittest.TestCase):
    def test_bars_do_not_multiply_window_alpha(self):
        lua = fight("{ combatAlpha = 0.5 }")
        lua.execute('packet("%s"); run(1)' % FIGHT)
        self.assertEqual(lua.eval('bars()["Me"].frame.setAlpha'), 0)

    def test_full_screen_glow_hidden_between_warnings(self):
        lua = fight("{ fullScreenGlow = true }")
        lua.execute('packet("%s"); run(1)' % FIGHT)
        self.assertFalse(lua.eval("TWTFullScreenGlow.shown"))

    def test_full_screen_glow_warns_once_over_threshold(self):
        lua = fight("{ fullScreenGlow = true, aggroSound = true, aggroThreshold = 85 }")
        lua.execute('packet("Tank:1:1000:100:1;Me:0:900:90:1"); run(0.5); tick()')
        self.assertTrue(lua.eval("TWTFullScreenGlow.shown"))
        self.assertEqual(lua.eval("sounds"), 1)
        lua.execute('packet("Tank:1:1000:100:1;Me:0:910:91:1"); run(0.5)')
        self.assertEqual(lua.eval("sounds"), 1, "once per five seconds")

    def test_stale_answer_after_target_change_is_dropped(self):
        lua = fight()
        lua.execute('packet("%s"); run(1)' % FIGHT)
        lua.execute('target.name = "Add"; event("PLAYER_TARGET_CHANGED")')
        lua.execute('packet("Tank:1:1000:100:1;Me:0:770:77:1"); run(0.1)')
        self.assertIsNone(lua.eval('bars()["Me"]'), "the answer was for the old target")
        lua.execute('tick(); packet("Tank:1:1000:100:1;Me:0:400:40:1"); step(0.001)')
        self.assertAlmostEqual(lua.eval('width("Me")'), BAR * 0.4, delta=0.6)

    def test_answer_in_flight_at_target_change_is_dropped(self):
        lua = fight()
        lua.execute('packet("%s"); step(0.1); tick()' % FIGHT)          # a query for Boss is out
        lua.execute('target.name = "Add"; event("PLAYER_TARGET_CHANGED"); step(0.1); tick()')
        queries = lua.eval("#sent")
        lua.execute('step(0.1); tick()')
        self.assertEqual(lua.eval("#sent"), queries, "no query for Add until Boss's answer is in")
        lua.execute('packet("Tank:1:1000:100:1;Me:0:770:77:1"); step(0.01)')   # Boss's answer
        self.assertIsNone(lua.eval('bars()["Me"]'))
        lua.execute('step(0.1); tick(); packet("Tank:1:1000:100:1;Me:0:400:40:1"); step(0.01)')
        self.assertAlmostEqual(lua.eval('width("Me")'), BAR * 0.4, delta=0.6)

    def test_messages_go_to_the_group_the_player_is_in(self):
        lua = fight()
        channels = lua.eval('(function() local t = {} for _, m in ipairs(sent) do t[#t + 1] = m.channel end '
                            'return table.concat(t, ",") end)()')
        self.assertTrue(channels)
        self.assertEqual(set(channels.split(",")), {"PARTY"})

    def test_tank_mode_keeps_warning_settings(self):
        lua = load("{ fullScreenGlow = true, aggroSound = true }", 'playerClass = "WARRIOR"')
        lua.execute("TWTChangeSetting_OnClick(1, 'tankMode')")
        self.assertTrue(lua.eval("TWT_CONFIG.fullScreenGlow"))
        lua.execute("TWTChangeSetting_OnClick(nil, 'tankMode')")
        self.assertTrue(lua.eval("TWT_CONFIG.fullScreenGlow and TWT_CONFIG.aggroSound"))

    def test_tankmode_command_toggles_without_test_bars(self):
        lua = load("{}", 'playerClass = "WARRIOR"')
        lua.execute('SlashCmdList.TWT("tankmode")')
        self.assertTrue(lua.eval("TWT_CONFIG.tankMode"))
        self.assertIsNone(lua.eval("next(bars())"), "test bars belong to the open settings window")
        lua.execute('SlashCmdList.TWT("tankmode")')
        self.assertFalse(lua.eval("TWT_CONFIG.tankMode"))

    def test_tankmode_command_refuses_other_classes(self):
        lua = load()
        lua.execute('SlashCmdList.TWT("tankmode")')
        self.assertFalse(lua.eval("TWT_CONFIG.tankMode"))

    def test_tank_mode_mutes_warnings(self):
        lua = fight("{ tankMode = true, aggroSound = true, aggroThreshold = 85 }", 'playerClass = "WARRIOR"')
        lua.execute('packet("Tank:1:1000:100:1;Me:0:900:90:1"); run(0.5)')
        self.assertEqual(lua.eval("sounds"), 0)


class Retired(unittest.TestCase):
    def test_retired_settings_are_cleared(self):
        lua = load("{ skeram = true, debug = true }")
        self.assertIsNone(lua.eval("TWT_CONFIG.skeram"))
        self.assertIsNone(lua.eval("TWT_CONFIG.debug"))
        self.assertIsNone(lua.eval("SlashCmdList.TWTDEBUG"))

    def test_dead_features_are_gone(self):
        for gone in ("healerMasterTarget", "HealerMasterTarget", "relayTo", "TWTWarning",
                     "TWTWithAddonList", "queryWho", '"pps"', "name=\"pps\"", "twtdebug", "/twt skeram"):
            self.assertNotIn(gone, SOURCE + XML, gone)

    def test_lock_reads_the_setting(self):
        self.assertNotIn("GetTexture()", XML)

    def test_no_generic_global_handlers(self):
        lua = load()
        for name in ("FrameHeightSlider_OnValueChanged", "WindowScaleSlider_OnValueChanged",
                     "CombatOpacitySlider_OnValueChanged", "OOCombatSlider_OnValueChanged",
                     "AggroThresholdSlider_OnValueChanged", "QueryWho_OnClick"):
            self.assertIsNone(lua.eval("rawget(_G, %r)" % name), name)
        self.assertNotRegex(XML, r"\b(FrameHeight|WindowScale|CombatOpacity|OOCombat|AggroThreshold)Slider_OnValueChanged")

    def test_no_table_for_loop(self):
        self.assertIsNone(re.search(r"for [\w, ]+ in TWT\.\w+ do", SOURCE))


class Query(unittest.TestCase):
    """Moved from the addon's tests/ folder: one cancellable query ticker."""

    def live(self, lua):
        return lua.eval('(function() local n = 0 for _, t in ipairs(timers) do '
                        'if not t.cancelled and t.interval < 5 then n = n + 1 end end return n end)()')

    def test_one_ticker_per_fight_and_none_after(self):
        lua = fight()
        self.assertEqual(self.live(lua), 1)
        lua.execute('combat = false; event("PLAYER_REGEN_ENABLED")')
        self.assertEqual(self.live(lua), 0)
        queries = lua.eval("#sent")
        lua.execute("timers[#timers].callback()")
        self.assertEqual(lua.eval("#sent"), queries, "a cancelled ticker does not query")

    def test_query_needs_group_combat_and_target(self):
        lua = fight()
        lua.execute('packet("Tank:1:1000:100:1;Me:0:300:30:1")')
        base = lua.eval("#sent")
        lua.execute("party = 0; tick()")
        self.assertEqual(lua.eval("#sent"), base)
        lua.execute("party = 4; targetCombat = false; tick()")
        self.assertEqual(lua.eval("#sent"), base)
        lua.execute("targetCombat = true; tick()")
        self.assertEqual(lua.eval("#sent"), base + 1)
        self.assertEqual(lua.eval("sent[#sent].prefix"), "TWT_UDTSv4")

    def queries(self, lua):
        return lua.eval('(function() local n = 0 for _, m in ipairs(sent) do '
                        'if m.prefix == "TWT_UDTSv4" then n = n + 1 end end return n end)()')

    def test_one_query_in_flight_next_on_answer(self):
        lua = fight()
        self.assertEqual(self.queries(lua), 1)
        lua.execute("step(0.1); tick(); step(0.1); tick()")
        self.assertEqual(self.queries(lua), 1, "no new query while the answer is out")
        lua.execute('packet("Tank:1:1000:100:1;Me:0:300:30:1"); step(0.1); tick()')
        self.assertEqual(self.queries(lua), 2, "the next query goes out right after the answer")

    def test_lost_answer_is_asked_again(self):
        lua = fight()
        lua.execute("step(1.05); tick()")
        self.assertEqual(self.queries(lua), 2)

    def test_ticker_runs_at_ten_a_second(self):
        lua = fight()
        self.assertAlmostEqual(lua.eval("timers[#timers].interval"), 0.1)

    def test_no_answer_says_so(self):
        lua = fight()
        for _ in range(35):
            lua.execute("step(0.1); tick()")
        self.assertIn("no threat data", lua.eval("TWTMainTitle.text"))
        lua.execute('packet("Tank:1:1000:100:1;Me:0:300:30:1"); step(0.01)')
        self.assertEqual(lua.eval("TWTMainTitle.text"), "Boss (30%)")

    def test_startup_guard(self):
        from lupa.lua51 import LuaRuntime
        prefix = SOURCE[:SOURCE.index("\nlocal TWT = ")]
        for version, timer, expected in (("2.2", True, 0), ("2.1", True, 1), ("2.2", False, 1)):
            lua = LuaRuntime(unpack_returned_tuples=True)
            lua.execute("CLASSIC_API_VERSION = 12004; warnings = 0 "
                        "DEFAULT_CHAT_FRAME = { AddMessage = function() warnings = warnings + 1 end }")
            lua.globals().SUPERWOW_VERSION = version
            if timer:
                lua.execute("C_Timer = { NewTicker = function() end }")
            lua.execute("(function() %s\nend)()" % prefix)
            self.assertEqual(lua.globals().warnings, expected)


if __name__ == "__main__":
    unittest.main()
