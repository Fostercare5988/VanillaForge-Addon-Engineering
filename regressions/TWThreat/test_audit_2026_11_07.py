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
        base = lua.eval("#sent")
        lua.execute("party = 0; tick()")
        self.assertEqual(lua.eval("#sent"), base)
        lua.execute("party = 4; targetCombat = false; tick()")
        self.assertEqual(lua.eval("#sent"), base)
        lua.execute("targetCombat = true; tick()")
        self.assertEqual(lua.eval("#sent"), base + 1)
        self.assertEqual(lua.eval("sent[#sent].prefix"), "TWT_UDTSv4")

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
