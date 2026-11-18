"""The extra bars (Tweaks spec B3, 4.2 "Free button", 4.3 GAP; its
tests 4.7 "Extra bars"): slot pages the class never pages to first, then free
bars past slot 120 that take spells, items, macros and sets from the cursor.
Written 2026-11-17 for ActionBars 1.1.0.
"""
import unittest
from fb_env import load

FOUR = "ActionBarsDB = { extraBars = 4 }"


class ExtraBars(unittest.TestCase):
    def test_a_rogue_has_three_slot_bars_then_free_ones(self):
        lua = load(FOUR)
        for bar, first in (("extra2", 85), ("extra3", 97), ("extra4", 109)):
            self.assertEqual(lua.eval(f"button('{bar}', 1).slot"), first, bar)
        self.assertIsNone(lua.eval("button('extra5', 1).slot"))
        self.assertEqual(lua.eval("button('extra5', 1).bar.free"), 5)

    def test_a_warrior_has_one_slot_bar_a_mage_four(self):
        lua = load(FOUR, "playerClass = 'WARRIOR'")
        self.assertEqual(lua.eval("button('extra2', 1).slot"), 109)
        self.assertEqual(lua.eval("button('extra3', 1).bar.free"), 3)
        lua = load(FOUR, "playerClass = 'MAGE'")
        self.assertEqual(lua.eval("button('extra2', 1).slot"), 73)
        self.assertEqual(lua.eval("button('extra5', 1).slot"), 109)

    def test_only_as_many_bars_as_the_page_says(self):
        lua = load()
        self.assertTrue(lua.eval("button('extra2', 1).bar.holder:IsShown()"))
        self.assertIsNone(lua.eval("button('extra3', 1)"), "a bar past the number is not built")
        lua.execute("settingsWindow.use('ActionBars_extraBars', 3)")
        self.assertTrue(lua.eval("button('extra4', 1).bar.holder:IsShown()"))
        lua.execute("settingsWindow.use('ActionBars_extraBars', 1)")
        self.assertFalse(lua.eval("button('extra4', 1).bar.holder:IsShown()"))

    def test_a_free_button_takes_each_kind_from_the_cursor(self):
        lua = load(FOUR, '''learn(13920, 'Blind') ranks[13920] = 'Rank 1' give(21151)
            macros[2] = { name = 'Kick', body = '/cast Kick' } sets[7] = 'PvP' ''')
        lua.execute('''
            cursor = { kind = 'spell', id = 13920, book = 1 } run(button('extra5', 1), 'OnReceiveDrag')
            cursor = { kind = 'item', id = 21151 } run(button('extra5', 2), 'OnReceiveDrag')
            cursor = { kind = 'macro', id = 2 } run(button('extra5', 3), 'OnReceiveDrag')
            cursor = { kind = 'equipmentset', id = 'PvP' } run(button('extra5', 4), 'OnReceiveDrag')
        ''')
        row = "ActionBarsDB.free[5]"
        self.assertEqual(lua.eval(f"{row}[1].kind .. {row}[1].id"), "spell13920")
        self.assertEqual(lua.eval(f"{row}[2].kind .. {row}[2].id"), "item21151")
        self.assertEqual(lua.eval(f"{row}[3].name .. '|' .. {row}[3].body"), "Kick|/cast Kick")
        self.assertEqual(lua.eval(f"{row}[4].name"), "PvP")
        self.assertIsNone(lua.eval("cursor"))
        self.assertEqual(lua.eval("button('extra5', 1).icon.texture"), "spellTex:13920")
        for i in range(1, 5):
            lua.execute(f"run(button('extra5', {i}), 'OnClick', 'LeftButton')")
        self.assertEqual(lua.eval("casts[1]"), "Blind(Rank 1)", "the saved rank")
        self.assertEqual(lua.eval("usedItems[1]"), 21151)
        self.assertEqual(lua.eval("ranMacros[1]"), "/cast Kick")
        self.assertEqual(lua.eval("equippedSets[1]"), "PvP")

    def test_dropping_on_a_full_button_swaps(self):
        lua = load(FOUR, "learn(1) learn(2)")
        lua.execute('''cursor = { kind = 'spell', id = 1, book = 1 } run(button('extra5', 1), 'OnReceiveDrag')
            cursor = { kind = 'spell', id = 2, book = 2 } run(button('extra5', 1), 'OnReceiveDrag')''')
        self.assertEqual(lua.eval("ActionBarsDB.free[5][1].id"), 2)
        self.assertEqual(lua.eval("cursor.id"), 1, "the old spell is on the cursor")

    def test_drag_to_a_slot_and_shift_right_click_clears(self):
        lua = load(FOUR, "learn(1) learn(2)")
        lua.execute('''cursor = { kind = 'spell', id = 1, book = 1 } run(button('extra5', 1), 'OnReceiveDrag')
            run(button('extra5', 1), 'OnDragStart') run(button('main', 5), 'OnReceiveDrag')''')
        self.assertEqual(lua.eval("bars[5].id"), 1, "from a free button to a slot")
        self.assertIsNone(lua.eval("ActionBarsDB.free[5][1]"))
        lua.execute('''cursor = { kind = 'spell', id = 2, book = 2 } run(button('extra5', 2), 'OnReceiveDrag')
            shift = true run(button('extra5', 2), 'OnClick', 'RightButton') shift = nil''')
        self.assertIsNone(lua.eval("ActionBarsDB.free[5][2]"))
        self.assertEqual(lua.eval("#casts"), 0, "clearing casts nothing")

    def test_the_lock_keeps_free_buttons(self):
        lua = load(FOUR, "learn(1)")
        lua.execute("LOCK_ACTIONBAR = '1' cursor = { kind = 'spell', id = 1, book = 1 } "
                    "run(button('extra5', 1), 'OnReceiveDrag')")
        self.assertIsNone(lua.eval("(ActionBarsDB.free[5] or {})[1]"))

    def test_cooldown_and_usable_follow_their_events(self):
        saved = "ActionBarsDB = { extraBars = 4, free = { [5] = { [1] = { kind = 'spell', id = 1 } } } }"
        lua = load(saved, "learn(1)")
        lua.execute("spellCooldowns[1] = { 100, 8 } fire('SPELL_UPDATE_COOLDOWN')")
        self.assertEqual(lua.eval("button('extra5', 1).cooldown.cd"), "100+8")
        lua.execute("spellUsable[1] = false fire('UNIT_POWER_UPDATE', 'player')")
        self.assertEqual(lua.eval("button('extra5', 1).icon.color[1]"), 0.4)

    def test_range_checks_only_with_a_target_and_a_ranged_button(self):
        saved = "ActionBarsDB = { extraBars = 4, free = { [5] = { [1] = { kind = 'spell', id = 1 } } } }"
        lua = load(saved, "learn(1)")
        lua.execute("fire('PLAYER_TARGET_CHANGED')")
        self.assertEqual(lua.eval("timerCount()"), 0, "no target")
        lua.execute("hasTarget = true fire('PLAYER_TARGET_CHANGED')")
        self.assertEqual(lua.eval("timerCount()"), 0, "a spell without range needs no check")
        lua.execute("spellRanged[1] = true fire('SPELLS_CHANGED') spellRange[1] = false fire('PLAYER_TARGET_CHANGED')")
        self.assertEqual(lua.eval("timerCount()"), 1)
        self.assertTrue(lua.eval("hotkeyRed(button('extra5', 1))"))
        lua.execute("spellRange[1] = true step(0.2)")
        self.assertFalse(lua.eval("hotkeyRed(button('extra5', 1))"))
        lua.execute("hasTarget = nil fire('PLAYER_TARGET_CHANGED')")
        self.assertEqual(lua.eval("timerCount()"), 0)

    def test_a_melee_spell_follows_the_swing_range(self):
        saved = "ActionBarsDB = { extraBars = 4, free = { [5] = { [1] = { kind = 'spell', id = 1766 } } } }"
        lua = load(saved, "learn(1766, 'Kick') hasTarget = true")
        self.assertEqual(lua.eval("swingChecks"), 1)
        lua.execute("fire('PLAYER_SWING_RANGE_UPDATE', Enum.PlayerSwingType.MainHand, nil, 1)")
        self.assertTrue(lua.eval("hotkeyRed(button('extra5', 1))"))
        lua.execute("fire('PLAYER_SWING_RANGE_UPDATE', Enum.PlayerSwingType.MainHand, 1, 1)")
        self.assertFalse(lua.eval("hotkeyRed(button('extra5', 1))"))
        self.assertEqual(lua.eval("timerCount()"), 0, "no check of our own")
        lua.execute("shift = true run(button('extra5', 1), 'OnClick', 'RightButton') shift = nil")
        self.assertEqual(lua.eval("swingChecks"), 0, "off once no button needs it")

    def test_a_ranged_spell_on_a_slot_follows_that_slot(self):
        saved = "ActionBarsDB = { extraBars = 4, free = { [5] = { [1] = { kind = 'spell', id = 2 } } } }"
        lua = load(saved, "learn(2) spellRanged[2] = true bars[100] = { kind = 'spell', id = 2 } hasTarget = true")
        self.assertEqual(lua.eval("button('extra5', 1).rangeSlot"), 100)
        self.assertEqual(lua.eval("timerCount()"), 0)
        lua.execute("fire('ACTION_RANGE_CHECK_UPDATE', 100, false, true)")
        self.assertTrue(lua.eval("hotkeyRed(button('extra5', 1))"))
        lua.execute("bars[100] = nil fire('ACTIONBAR_SLOT_CHANGED', 100)")
        self.assertEqual(lua.eval("timerCount()"), 1, "off the slot: the GAP check")

    def test_a_spell_on_yourself_has_no_range(self):
        saved = "ActionBarsDB = { extraBars = 4, free = { [5] = { [1] = { kind = 'spell', id = 3 } } } }"
        lua = load(saved, "learn(3) selfBuffs[3] = true hasTarget = true")
        self.assertIsNone(lua.eval("button('extra5', 1).rangeBy"))
        self.assertIsNone(lua.eval("swingChecks"))

    def test_a_worn_item_has_the_green_border(self):
        saved = "ActionBarsDB = { extraBars = 4, free = { [5] = { [1] = { kind = 'item', id = 50 } } } }"
        lua = load(saved, "give(50)")
        self.assertFalse(lua.eval("button('extra5', 1).border:IsShown()"))
        lua.execute("equipment[50] = { id = 50 } fire('PLAYER_EQUIPMENT_CHANGED', 16, true)")
        self.assertTrue(lua.eval("button('extra5', 1).border:IsShown()"))

    def test_a_key_with_shift_uses_a_free_button(self):
        # A key bound in Lua sees Shift held (### Modifier keys during a binding):
        # a Shift-click would take the button off the bar.
        saved = "ActionBarsDB = { extraBars = 4, free = { [5] = { [1] = { kind = 'spell', id = 3 } } } }"
        lua = load(saved, "learn(3, 'Blind')")
        lua.execute("shift = true ActionBars.Press('extra5', 1, 'down') ActionBars.Press('extra5', 1, 'up') "
                    "ActionBars.Press('extra5', 2, 'up') shift = nil")
        self.assertEqual(lua.eval("casts[1]"), "Blind")
        self.assertEqual(lua.eval("ActionBarsDB.free[5][1].id"), 3, "still on the bar")
        self.assertIsNone(lua.eval("cursor"))

    def test_an_item_with_none_left_is_not_dragged_away(self):
        # Nothing can put it on the cursor, so dragging it off would delete it.
        saved = "ActionBarsDB = { extraBars = 4, free = { [5] = { [1] = { kind = 'item', id = 50 } } } }"
        lua = load(saved)
        lua.execute("run(button('extra5', 1), 'OnDragStart')")
        self.assertEqual(lua.eval("ActionBarsDB.free[5][1].id"), 50)
        lua.execute("give(50) run(button('extra5', 1), 'OnDragStart')")
        self.assertIsNone(lua.eval("ActionBarsDB.free[5][1]"), "with one in the bags it moves")
        self.assertEqual(lua.eval("cursor.id"), 50)

    def test_no_free_bar_no_free_events(self):
        lua = load()
        self.assertEqual(lua.eval("busyFrames()"), "")
        lua = load("ActionBarsDB = { extraBars = 3 }")
        self.assertNotIn("SPELL_UPDATE_COOLDOWN", lua.eval("allEvents()"), "a rogue's first three are slot bars")
        lua.execute("settingsWindow.use('ActionBars_extraBars', 4)")
        self.assertIn("SPELL_UPDATE_COOLDOWN", lua.eval("allEvents()"))

    def test_a_profile_saves_and_loads_the_free_bars(self):
        saved = '''ActionBarsDB = { extraBars = 4, free = { [5] = { [1] = { kind = 'spell', id = 1 } } } }'''
        lua = load(saved, "learn(1) learn(2)")
        lua.execute("StaticPopup_Show('ACTIONBARS_NEW') accept('A')")
        self.assertEqual(lua.eval("ActionBarsDB.profiles.A.free[5][1].id"), 1)
        lua.execute("cursor = { kind = 'spell', id = 2, book = 2 } run(button('extra5', 3), 'OnReceiveDrag') ClearCursor()")
        self.assertTrue(lua.eval("ActionBars.LoadProfile('A')"))
        self.assertIsNone(lua.eval("ActionBarsDB.free[5][3]"))
        self.assertIsNone(lua.eval("button('extra5', 3).action"))
        self.assertIn('Loaded "A": 1 button changed.', lua.eval("chatText()"))
        self.assertEqual(lua.eval("ActionBarsDB.profiles.A.free[5][3]"), None, "the profile keeps its copy")

    def test_a_profile_from_before_the_free_bars_leaves_them(self):
        saved = '''ActionBarsDB = { extraBars = 4, free = { [5] = { [1] = { kind = 'spell', id = 1 } } },
            profiles = { Old = { actions = {} } } }'''
        lua = load(saved, "learn(1)")
        lua.execute("ActionBars.LoadProfile('Old')")
        self.assertEqual(lua.eval("ActionBarsDB.free[5][1].id"), 1)


if __name__ == "__main__":
    unittest.main()
