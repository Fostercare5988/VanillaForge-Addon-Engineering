"""The loss-of-control swipe: a stun, silence or lockout that blocks a button's
spell shows a red swipe for the effect's time, over (or in place of) the
cooldown, and goes when the effect does. Written 2026-11-22 for ActionBars.

The kit should model: C_LossOfControl.GetActiveLossOfControlDataCount,
C_Spell.GetSpellLossOfControlCooldown (start, duration, nil for an unknown
spell) and the Cooldown widget's SetSwipeColor, SetDrawBling and
SetHideCountdownNumbers; here they are stubs in fb_env.py.
"""
import unittest
from fb_env import load

SETUP = "learn(1) learn(2) bars[1] = { kind = 'spell', id = 1 } bars[2] = { kind = 'spell', id = 2 }"
FREE = "ActionBarsDB = { extraBars = 4, free = { [5] = { [1] = { kind = 'spell', id = 1 }, [2] = { kind = 'item', id = 9 } } } }"
STUN = "lossEffects = 1 lossBlocks[1] = { 100, 4 } fire('LOSS_OF_CONTROL_UPDATE', 'player')"
END = "lossEffects = 0 lossBlocks[1] = nil fire('LOSS_OF_CONTROL_UPDATE', 'player')"


class LossOfControl(unittest.TestCase):
    def test_a_blocked_button_shows_the_swipe_and_clears(self):
        lua = load(setup=SETUP)
        self.assertIsNone(lua.eval("button('main', 1).loss.cd"))
        lua.execute(STUN)
        self.assertEqual(lua.eval("button('main', 1).loss.cd"), "100+4")
        self.assertEqual(lua.eval("button('main', 1).loss.swipe[1]"), 1, "red")
        lua.execute(END)
        self.assertIsNone(lua.eval("button('main', 1).loss.cd"))
        self.assertEqual(lua.eval("button('main', 1).cooldown.alpha"), 1)

    def test_an_unblocked_button_is_untouched(self):
        lua = load(setup=SETUP)
        lua.execute(STUN)
        self.assertIsNone(lua.eval("button('main', 2).loss.cd"))
        self.assertIsNone(lua.eval("button('main', 3).loss.cd"), "an empty button")
        lua.execute("loss2 = 0 button('main', 2).loss.Clear = function() loss2 = loss2 + 1 end "
                    "fire('LOSS_OF_CONTROL_UPDATE', 'player')")
        self.assertEqual(lua.eval("loss2"), 0, "no write for an unchanged button")

    def test_the_swipe_replaces_a_shorter_cooldown_only(self):
        lua = load(setup=SETUP)
        lua.execute("cooldowns[1] = { 100, 1.5 } fire('ACTIONBAR_UPDATE_COOLDOWN')")
        lua.execute(STUN)
        self.assertEqual(lua.eval("button('main', 1).cooldown.alpha"), 0, "the stun outlasts the cooldown")
        lua.execute(END)
        lua.execute("cooldowns[1] = { 100, 30 } fire('ACTIONBAR_UPDATE_COOLDOWN')")
        lua.execute(STUN)
        self.assertEqual(lua.eval("button('main', 1).cooldown.alpha"), 1, "the cooldown ends later")
        self.assertEqual(lua.eval("button('main', 1).loss.cd"), "100+4", "still shown over it")

    def test_a_button_drawn_during_the_effect_shows_it(self):
        lua = load(setup=SETUP)
        lua.execute(STUN)
        lua.execute("bars[3] = { kind = 'spell', id = 1 } fire('ACTIONBAR_SLOT_CHANGED', 3)")
        self.assertEqual(lua.eval("button('main', 3).loss.cd"), "100+4")
        lua.execute("bars[3] = nil fire('ACTIONBAR_SLOT_CHANGED', 3)")
        self.assertIsNone(lua.eval("button('main', 3).loss.cd"))

    def test_a_free_spell_button_too_and_an_item_not(self):
        lua = load(FREE, SETUP + " give(9)")
        lua.execute(STUN)
        self.assertEqual(lua.eval("button('extra5', 1).loss.cd"), "100+4")
        self.assertIsNone(lua.eval("button('extra5', 2).loss.cd"), "an item has no spell")
        lua.execute(END)
        self.assertIsNone(lua.eval("button('extra5', 1).loss.cd"))

    def test_the_events_only_and_no_timer(self):
        lua = load(setup=SETUP)
        lua.execute(STUN)
        self.assertEqual(lua.eval("timerCount()"), 0)
        self.assertEqual(lua.eval("busyFrames()"), "")
