"""The bars on action slots (FostercareTweaks spec B1, B4, B5, B7; its tests
4.7 "Bars"): each bar shows its slots, the main bar pages, and each event
redraws only what it names. Written 2026-11-17 for FostercareBars 1.1.0.
"""
import unittest
from fb_env import load


class SlotBars(unittest.TestCase):
    def test_each_bar_shows_its_slots(self):
        lua = load(setup="bars[61] = { kind = 'spell', id = 1 } bars[25] = { kind = 'spell', id = 2 }")
        for bar, first in (("main", 1), ("bottomleft", 61), ("bottomright", 49), ("right", 25),
                           ("left", 37), ("extra1", 13)):
            self.assertEqual(lua.eval(f"button('{bar}', 1).slot"), first, bar)
            self.assertEqual(lua.eval(f"button('{bar}', 12).slot"), first + 11, bar)
        self.assertEqual(lua.eval("button('bottomleft', 1).icon.texture"), "tex:spell:1")

    def test_main_follows_stealth_and_the_page(self):
        lua = load()
        lua.execute("bonusOffset = 1 fire('UPDATE_BONUS_ACTIONBAR')")
        self.assertEqual(lua.eval("button('main', 1).slot"), 73, "stealth: offset 1 is 73-84")
        lua.execute("CURRENT_ACTIONBAR_PAGE = 2 fire('ACTIONBAR_PAGE_CHANGED')")
        self.assertEqual(lua.eval("button('main', 1).slot"), 13, "another page wins over the bonus bar")
        lua.execute("CURRENT_ACTIONBAR_PAGE = 1 bonusOffset = 0 fire('UPDATE_BONUS_ACTIONBAR')")
        self.assertEqual(lua.eval("button('main', 12).slot"), 12)

    def test_one_slot_change_redraws_one_button(self):
        lua = load()
        before = [lua.eval(f"readsOf({s})") for s in (5, 6)]
        lua.execute("bars[5] = { kind = 'spell', id = 9 } fire('ACTIONBAR_SLOT_CHANGED', 5)")
        self.assertEqual(lua.eval("readsOf(5)"), before[0] + 1)
        self.assertEqual(lua.eval("readsOf(6)"), before[1], "slot 6 is not read again")
        self.assertEqual(lua.eval("button('main', 5).icon.texture"), "tex:spell:9")

    def test_range_is_checked_for_shown_slots_and_painted_from_the_event(self):
        lua = load(setup="bars[3] = { kind = 'spell', id = 1 } bars[4] = { kind = 'spell', id = 2 }")
        self.assertEqual(lua.eval("rangeChecks[3]"), 1)
        lua.execute("fire('ACTION_RANGE_CHECK_UPDATE', 3, false, true)")
        self.assertTrue(lua.eval("hotkeyRed(button('main', 3))"))
        self.assertFalse(lua.eval("hotkeyRed(button('main', 4))"), "only the slot named")
        lua.execute("fire('ACTION_RANGE_CHECK_UPDATE', 3, true, true)")
        self.assertFalse(lua.eval("hotkeyRed(button('main', 3))"))
        lua.execute("fire('ACTION_RANGE_CHECK_UPDATE', 3, false, false)")
        self.assertFalse(lua.eval("hotkeyRed(button('main', 3))"), "no check is not out of range")

    def test_a_hidden_bar_gives_its_range_checks_back(self):
        lua = load()
        self.assertEqual(lua.eval("rangeChecks[25]"), 1)
        lua.execute("settingsWindow.use('FostercareBars_right_shown', false)")
        self.assertEqual(lua.eval("rangeChecks[25]"), 0)
        self.assertFalse(lua.eval("button('right', 1).bar.holder:IsShown()"))

    def test_a_page_change_moves_the_range_check(self):
        lua = load()
        lua.execute("bonusOffset = 1 fire('UPDATE_BONUS_ACTIONBAR')")
        self.assertEqual(lua.eval("rangeChecks[1]"), 0)
        self.assertEqual(lua.eval("rangeChecks[73]"), 1)

    def test_usable_only_for_the_slots_named(self):
        lua = load(setup="bars[1] = { kind = 'spell', id = 1 } bars[2] = { kind = 'spell', id = 2 }")
        lua.execute("fire('ACTION_USABLE_CHANGED', { { slot = 1, usable = false, noMana = true } })")
        self.assertEqual(lua.eval("button('main', 1).icon.color[1]"), 0.5, "no mana is blue")
        self.assertEqual(lua.eval("button('main', 2).icon.color[1]"), 1)

    def test_cooldown_from_the_cooldown_event(self):
        lua = load(setup="bars[1] = { kind = 'spell', id = 1 }")
        lua.execute("cooldowns[1] = { 100, 30 } fire('ACTIONBAR_UPDATE_COOLDOWN')")
        self.assertEqual(lua.eval("button('main', 1).cooldown.cd"), "100+30")
        lua.execute("cooldowns[1] = nil fire('ACTIONBAR_UPDATE_COOLDOWN')")
        self.assertIsNone(lua.eval("button('main', 1).cooldown.cd"))

    def test_the_flash_timer_runs_only_while_a_slot_flashes(self):
        lua = load(setup="bars[7] = { kind = 'spell', id = 75 }")
        self.assertEqual(lua.eval("timerCount()"), 0)
        lua.execute("autoRepeat[7] = 1 fire('START_AUTOREPEAT_SPELL')")
        self.assertEqual(lua.eval("timerCount()"), 1)
        lua.execute("step(0.4)")
        self.assertTrue(lua.eval("button('main', 7).flash:IsShown()"))
        lua.execute("autoRepeat[7] = nil fire('STOP_AUTOREPEAT_SPELL')")
        self.assertEqual(lua.eval("timerCount()"), 0)
        self.assertFalse(lua.eval("button('main', 7).flash:IsShown()"))

    def test_auto_attack_flashes_in_combat(self):
        lua = load(setup="bars[1] = { kind = 'spell', id = 6603 } attackSlots[1] = 1")
        lua.execute("current[1] = 1 fire('PLAYER_ENTER_COMBAT')")
        self.assertEqual(lua.eval("timerCount()"), 1)
        self.assertTrue(lua.eval("button('main', 1):GetChecked()"))
        lua.execute("current[1] = nil fire('PLAYER_LEAVE_COMBAT')")
        self.assertEqual(lua.eval("timerCount()"), 0)

    def test_the_stock_keys_press_our_buttons(self):
        lua = load(setup="keys.ACTIONBUTTON3 = { '3' } keys.MULTIACTIONBAR3BUTTON1 = { 'F', 'G' } "
                         "bars[3] = { kind = 'spell', id = 1 }")
        self.assertEqual(lua.eval("overrides['3']"), "FostercareBars_main_3")
        self.assertEqual(lua.eval("overrides['G']"), "FostercareBars_right_1")
        lua.execute("pressKey('3')")
        self.assertEqual(lua.eval("used[1]"), 3)
        self.assertEqual(lua.eval("button('main', 3).hotkey.text"), "k3")

    def test_new_keys_are_taken_when_the_bindings_change(self):
        lua = load()
        lua.execute("keys.ACTIONBUTTON1 = { 'Q' } fire('UPDATE_BINDINGS')")
        self.assertEqual(lua.eval("overrides['Q']"), "FostercareBars_main_1")

    def test_an_extra_bar_key_from_key_bindings(self):
        lua = load(setup="bars[13] = { kind = 'spell', id = 1 } keys.FOSTERCAREBARS_EXTRA1_1 = { 'Z' }")
        self.assertEqual(lua.eval("BINDING_NAME_FOSTERCAREBARS_EXTRA1_1"), "Extra 1 Button 1")
        lua.execute("FostercareBars.Press('extra1', 1, 'down')")
        self.assertEqual(lua.eval("#used"), 0, "the key acts when it is released")
        lua.execute("FostercareBars.Press('extra1', 1, 'up')")
        self.assertEqual(lua.eval("used[1]"), 13)
        self.assertEqual(lua.eval("button('extra1', 1).hotkey.text"), "kZ")

    def test_drag_and_drop_with_the_action_bar_lock(self):
        lua = load(setup="bars[1] = { kind = 'spell', id = 1 }")
        lua.execute("LOCK_ACTIONBAR = '1' run(button('main', 1), 'OnDragStart')")
        self.assertEqual(lua.eval("bars[1].id"), 1, "locked: nothing moves")
        lua.execute("LOCK_ACTIONBAR = '0' run(button('main', 1), 'OnDragStart') run(button('main', 2), 'OnReceiveDrag')")
        self.assertIsNone(lua.eval("bars[1]"))
        self.assertEqual(lua.eval("bars[2].id"), 1)

    def test_empty_buttons_show_while_something_is_on_the_cursor(self):
        lua = load()
        self.assertFalse(lua.eval("button('bottomleft', 1):IsShown()"), "empty, and Show empty is off")
        self.assertTrue(lua.eval("button('main', 1):IsShown()"), "the main bar shows empty buttons")
        lua.execute("cursor = { kind = 'item', id = 5 } fire('CURSOR_CHANGED')")
        self.assertTrue(lua.eval("button('bottomleft', 1):IsShown()"))
        lua.execute("cursor = nil fire('CURSOR_CHANGED')")
        self.assertFalse(lua.eval("button('bottomleft', 1):IsShown()"))

    def test_reagent_counts_follow_the_bags_and_the_switch(self):
        lua = load(setup="bars[1] = { kind = 'spell', id = 1 } reagentSpells[1] = 4 "
                         "bars[2] = { kind = 'item', id = 50 } give(50, 3)")
        self.assertEqual(lua.eval("button('main', 1).count.text"), 4)
        self.assertEqual(lua.eval("button('main', 2).count.text"), 3)
        lua.execute("reagentSpells[1] = 2 fire('BAG_UPDATE_DELAYED')")
        self.assertEqual(lua.eval("button('main', 1).count.text"), 2)
        lua.execute("settingsWindow.use('FostercareBars_reagents', false)")
        self.assertEqual(lua.eval("button('main', 1).count.text"), "")

    def test_an_equipped_item_has_the_green_border(self):
        lua = load(setup="bars[1] = { kind = 'item', id = 50 }")
        self.assertFalse(lua.eval("button('main', 1).border:IsShown()"))
        lua.execute("equipment[50] = { id = 50 } fire('UNIT_INVENTORY_CHANGED', 'player')")
        self.assertTrue(lua.eval("button('main', 1).border:IsShown()"))

    def test_the_combat_events_build_no_garbage(self):
        lua = load("FostercareBarsDB = { extraBars = 4, free = { [5] = { [1] = { kind = 'spell', id = 1 } } } }",
                   "learn(1) for s = 1, 84 do bars[s] = { kind = 'spell', id = 1 } end hasTarget = true spellRanged[1] = true")
        grown = lua.eval('''(function()
            local changes = { { slot = 3, usable = true, noMana = false } }
            local function burst()
                fire('ACTIONBAR_UPDATE_COOLDOWN') fire('ACTION_USABLE_CHANGED', changes)
                fire('ACTION_RANGE_CHECK_UPDATE', 3, true, true) fire('ACTIONBAR_UPDATE_STATE')
                fire('SPELL_UPDATE_COOLDOWN') fire('UNIT_POWER_UPDATE', 'player') step(0.2)
            end
            burst() burst()
            collectgarbage() collectgarbage("stop")
            local before = collectgarbage("count")
            for _ = 1, 200 do burst() end
            local after = collectgarbage("count")
            collectgarbage("restart")
            return after - before
        end)()''')
        self.assertLess(grown, 4, "KB over 200 bursts")


if __name__ == "__main__":
    unittest.main()
