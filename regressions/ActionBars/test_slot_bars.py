"""The bars on action slots (Tweaks spec B1, B4, B5, B7; its tests
4.7 "Bars"): each bar shows its slots, the main bar pages, and each event
redraws only what it names. Written 2026-11-17 for ActionBars 1.1.0.
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

    def test_the_games_own_binding_uses_the_same_slot(self):
        # At a first login (2026-11-17) the override on F was not in place: the
        # game's MULTIACTIONBAR1BUTTON10 pressed the hidden stock button, which read
        # slot 10 (Disenchant), not 70 (Stealth). Stock MultiActionButtonUp and
        # ActionButtonUp (FrameXML) use the button's `action`.
        lua = load(setup="keys.MULTIACTIONBAR1BUTTON10 = { 'F' } keys.MULTIACTIONBAR3BUTTON1 = { 'G' } "
                         "keys.ACTIONBUTTON3 = { '3' }")
        lua.execute("""used = {}
            pressKey('F') pressKey('G') pressKey('3')
            bonusOffset = 1 fire('UPDATE_BONUS_ACTIONBAR') pressKey('3')""")
        self.assertEqual(list(lua.eval("used").values()), [70, 25, 3, 75])

    def test_with_actionbuttonusekeydown_a_key_acts_once_on_the_press(self):
        # 2026-11-18, the player's Config.wtf has ActionButtonUseKeyDown 1:
        # ClassicAPI's handlers then used ActionButton_GetPagedID of the hidden
        # stock button, so F (Bottom Left 10) pressed slot 10 and Z slot 1.
        lua = load(setup="cvars.ActionButtonUseKeyDown = '1' keys.MULTIACTIONBAR1BUTTON10 = { 'F' } "
                         "keys.MULTIACTIONBAR2BUTTON1 = { 'Z' } keys.ACTIONBARS_EXTRA1_1 = { 'X' }")
        lua.execute("used = {} pressKey('F', 'down')")
        self.assertEqual(list(lua.eval("used").values()), [70], "on the press")
        lua.execute("MultiActionButtonUp('MultiBarBottomLeft', 10) pressKey('Z') pressKey('Z')")
        self.assertEqual(list(lua.eval("used").values()), [70, 49, 49], "once per press")
        lua.execute("ActionBars.Press('extra1', 1, 'down')")
        self.assertEqual(lua.eval("used[4]"), 13, "Key Bindings' keys follow the setting too")
        lua.execute("ActionBars.Press('extra1', 1, 'up')")
        self.assertEqual(lua.eval("#used"), 4)

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
        lua.execute("settingsWindow.use('ActionBars_right_shown', false)")
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
        lua.execute("pressKey('3', 'down')")
        self.assertEqual(lua.eval("button('main', 3):GetButtonState()"), "PUSHED", "ours shows the press")
        self.assertEqual(lua.eval("#used"), 0, "the key acts when it is released")
        lua.execute("ActionButtonUp(3) pressKey('G')")
        self.assertEqual(list(lua.eval("used").values()), [3, 25])
        self.assertEqual(lua.eval("button('main', 3):GetButtonState()"), "NORMAL")
        self.assertEqual(lua.eval("button('main', 3).hotkey.text"), "k3")
        self.assertEqual(lua.eval("button('right', 1).hotkey.text"), "kF")

    def test_shift_and_the_cursor_do_not_change_what_a_key_does(self):
        # Claude's Shift+6 has no binding, so the game runs 6's with Shift held
        # (### Keys with modifiers); a Shift-click picks the action up. Stock
        # ActionButtonUp uses the slot, never placing what is on the cursor.
        lua = load(setup="keys.ACTIONBUTTON7 = { '6' } bars[7] = { kind = 'spell', id = 1 } "
                         "bars[9] = { kind = 'spell', id = 2 }")
        lua.execute("shift = true pressKey('6') shift = nil")
        self.assertEqual(lua.eval("used[1]"), 7, "Shift+6 casts")
        self.assertEqual(lua.eval("bars[7].id"), 1, "and leaves the button where it is")
        self.assertIsNone(lua.eval("cursor"))
        lua.execute("cursor = { kind = 'spell', id = 2, book = 2 } pressKey('6')")
        self.assertEqual(lua.eval("usedCheckCursor"), 0, "the cursor is not dropped on the slot")
        self.assertEqual(lua.eval("next(overrides)"), None, "the game's own bindings")

    def test_new_keys_are_taken_when_the_bindings_change(self):
        lua = load()
        lua.execute("keys.ACTIONBUTTON1 = { 'Q' } fire('UPDATE_BINDINGS')")
        self.assertEqual(lua.eval("button('main', 1).hotkey.text"), "kQ")

    def test_an_extra_bar_key_from_key_bindings(self):
        lua = load(setup="bars[13] = { kind = 'spell', id = 1 } keys.ACTIONBARS_EXTRA1_1 = { 'Z' }")
        self.assertEqual(lua.eval("BINDING_NAME_ACTIONBARS_EXTRA1_1"), "Extra 1 Button 1")
        lua.execute("ActionBars.Press('extra1', 1, 'down')")
        self.assertEqual(lua.eval("#used"), 0, "the key acts when it is released")
        lua.execute("ActionBars.Press('extra1', 1, 'up')")
        self.assertEqual(lua.eval("used[1]"), 13)
        self.assertEqual(lua.eval("button('extra1', 1).hotkey.text"), "kZ")
        # A key bound in Lua sees Shift held (### Modifier keys during a binding).
        lua.execute("shift = true ActionBars.Press('extra1', 1, 'down') ActionBars.Press('extra1', 1, 'up') shift = nil")
        self.assertEqual(lua.eval("used[2]"), 13, "SHIFT-Z casts too")
        self.assertEqual(lua.eval("bars[13].id"), 1, "nothing picked up")
        self.assertEqual(lua.eval("usedCheckCursor"), 0)

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
        lua.execute("settingsWindow.use('ActionBars_reagents', false)")
        self.assertEqual(lua.eval("button('main', 1).count.text"), "")

    def test_an_equipped_item_has_the_green_border(self):
        lua = load(setup="bars[1] = { kind = 'item', id = 50 }")
        self.assertFalse(lua.eval("button('main', 1).border:IsShown()"))
        lua.execute("equipment[50] = { id = 50 } fire('PLAYER_EQUIPMENT_CHANGED', 16, true)")
        self.assertTrue(lua.eval("button('main', 1).border:IsShown()"))

    def test_an_inventory_change_redraws_counts_not_borders(self):
        # UNIT_INVENTORY_CHANGED also fires for each durability point and charge;
        # the stock button redraws then (ActionButton.lua:325): a thrown stack.
        lua = load(setup="bars[1] = { kind = 'item', id = 50 } give(50, 3)")
        lua.execute("equipment[50] = { id = 50 } fire('UNIT_INVENTORY_CHANGED', 'player')")
        self.assertFalse(lua.eval("button('main', 1).border:IsShown()"), "only PLAYER_EQUIPMENT_CHANGED")
        self.assertEqual(lua.eval("button('main', 1).count.text"), 4)

    def test_a_tooltip_refreshes_only_while_it_counts_a_cooldown(self):
        lua = load(setup="bars[1] = { kind = 'spell', id = 1 } bars[2] = { kind = 'spell', id = 2 }")
        lua.execute("run(button('main', 2), 'OnEnter')")
        self.assertEqual(lua.eval("GameTooltip.shows"), "SetAction 2")
        self.assertEqual(lua.eval("timerCount()"), 0, "no cooldown in the tooltip: no refresh")
        lua.execute("counting[1] = 1 run(button('main', 2), 'OnLeave') run(button('main', 1), 'OnEnter')")
        self.assertEqual(lua.eval("timerCount()"), 1)
        lua.execute("GameTooltip.shows = nil step(1)")
        self.assertEqual(lua.eval("GameTooltip.shows"), "SetAction 1", "filled again a second later")
        lua.execute("counting[1] = nil step(1)")
        self.assertEqual(lua.eval("timerCount()"), 0, "the cooldown is over")
        lua.execute("counting[1] = 1 run(button('main', 1), 'OnEnter') run(button('main', 1), 'OnLeave')")
        self.assertEqual(lua.eval("timerCount()"), 0, "the cursor left")
        self.assertIsNone(lua.eval("GameTooltip.owner"))

    def test_the_combat_events_build_no_garbage(self):
        lua = load("ActionBarsDB = { extraBars = 4, free = { [5] = { [1] = { kind = 'spell', id = 1 } } } }",
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
