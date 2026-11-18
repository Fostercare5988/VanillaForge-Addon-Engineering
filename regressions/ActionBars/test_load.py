"""Loading a profile (spec K2, K3, K4, K6; tests 3, 4, 5, 7, 8 and 9)."""
import unittest
from fb_env import load

SAVED = '''ActionBarsDB = { profiles = { PVP = { actions = {
    [1] = { kind = 'spell', id = 10 },
    [2] = { kind = 'spell', id = 20 },
    [3] = { kind = 'item', id = 300 },
    [4] = { kind = 'macro', name = 'Kick', body = '/cast Kick' },
    [5] = { kind = 'equipmentset', name = 'PvP' },
} } } }'''

WORLD = '''
learn(10, 'Frostbolt') learn(20, 'Blink')
give(300, 2)
macros[1] = { name = 'Other', body = '/say hi' }
macros[2] = { name = 'Kick', body = '/cast Kick' }
sets[4] = 'PvP'
'''


def slot(lua, n):
    return lua.eval(f"bars[{n}] and (bars[{n}].kind .. ' ' .. tostring(bars[{n}].id)) or 'empty'")


class Load(unittest.TestCase):
    def test_every_kind_is_placed(self):
        lua = load(SAVED, WORLD)
        self.assertTrue(lua.eval("ActionBars.LoadProfile('PVP')"))
        self.assertEqual([slot(lua, n) for n in range(1, 6)],
                         ["spell 10", "spell 20", "item 300", "macro 2", "equipmentset PvP"])
        self.assertIsNone(lua.eval("cursor"), "the cursor is empty after a load")
        self.assertIn('Loaded "PVP": 5 buttons changed.', lua.eval("chatText()"))

    def test_only_slots_that_differ_change(self):
        lua = load(SAVED, WORLD + "bars[1] = { kind = 'spell', id = 10 } bars[4] = { kind = 'macro', id = 2 }")
        lua.execute("ActionBars.LoadProfile('PVP')")
        self.assertEqual(lua.eval("calls.PlaceAction"), 3)
        self.assertIn("3 buttons changed", lua.eval("chatText()"))
        lua.execute("chat = {} calls = {} ActionBars.LoadProfile('PVP')")
        self.assertEqual(lua.eval("changes()"), 0)
        self.assertIn("0 buttons changed", lua.eval("chatText()"))

    def test_a_slot_the_profile_has_empty_is_emptied(self):
        lua = load(SAVED, WORLD + "bars[9] = { kind = 'spell', id = 20 } bars[120] = { kind = 'item', id = 300 }")
        lua.execute("ActionBars.LoadProfile('PVP')")
        self.assertEqual(slot(lua, 9), "empty")
        self.assertEqual(slot(lua, 120), "empty")

    def test_an_unknown_spell_leaves_its_slot_and_is_named(self):
        lua = load(SAVED, WORLD.replace("learn(20, 'Blink')", "spellDB[20] = 'Blink'")
                   + "bars[2] = { kind = 'spell', id = 99 }")
        self.assertTrue(lua.eval("ActionBars.LoadProfile('PVP')"))
        self.assertEqual(slot(lua, 2), "spell 99")
        self.assertEqual(slot(lua, 1), "spell 10", "the rest loads")
        self.assertIn("Left as they were: Blink (spell not known).", lua.eval("chatText()"))

    def test_a_spell_already_in_its_slot_stays_though_the_book_lacks_it(self):
        lua = load(SAVED, WORLD.replace("learn(20, 'Blink')", "") + "bars[2] = { kind = 'spell', id = 20 }")
        lua.execute("ActionBars.LoadProfile('PVP')")
        self.assertEqual(slot(lua, 2), "spell 20")
        self.assertNotIn("Left as they were", lua.eval("chatText()"))

    def test_a_locked_item_is_skipped_and_the_rest_loads(self):
        lua = load(SAVED, WORLD.replace("give(300, 2)", "give(300, 1, true)") + "bars[3] = { kind = 'spell', id = 20 }")
        self.assertTrue(lua.eval("ActionBars.LoadProfile('PVP')"))
        self.assertEqual(slot(lua, 3), "spell 20")
        self.assertEqual(slot(lua, 5), "equipmentset PvP")
        self.assertIn("Item 300 (item is locked)", lua.eval("chatText()"))

    def test_macros_are_found_by_name_after_their_indexes_moved(self):
        lua = load(SAVED, WORLD + "macros[2] = nil macros[7] = { name = 'Kick', body = '/cast Kick' }")
        lua.execute("ActionBars.LoadProfile('PVP')")
        self.assertEqual(slot(lua, 4), "macro 7")

    def test_two_macros_with_one_name_are_told_apart_by_text(self):
        lua = load(SAVED, WORLD + "macros[1] = { name = 'Kick', body = '/cast Kick(Rank 1)' }")
        lua.execute("ActionBars.LoadProfile('PVP')")
        self.assertEqual(slot(lua, 4), "macro 2")

    def test_a_macro_whose_text_changed_is_found_when_its_name_is_alone(self):
        lua = load(SAVED, WORLD + "macros[2].body = '/cast Kick /say Kicked'")
        lua.execute("ActionBars.LoadProfile('PVP')")
        self.assertEqual(slot(lua, 4), "macro 2")

    def test_two_macros_with_one_name_and_other_text_are_not_guessed(self):
        lua = load(SAVED, WORLD + '''macros[1] = { name = 'Kick', body = '/a' } macros[2].body = '/b'
            bars[4] = { kind = 'spell', id = 10 }''')
        lua.execute("ActionBars.LoadProfile('PVP')")
        self.assertEqual(slot(lua, 4), "spell 10")
        self.assertIn("Kick (macro not found)", lua.eval("chatText()"))

    def test_a_missing_macro_or_set_is_named_and_its_slot_stays(self):
        lua = load(SAVED, WORLD + "macros[2] = nil sets[4] = nil bars[4] = { kind = 'spell', id = 10 }")
        lua.execute("ActionBars.LoadProfile('PVP')")
        self.assertEqual(slot(lua, 4), "spell 10")
        self.assertIn("Kick (macro not found), PvP (set not found)", lua.eval("chatText()"))

    def test_nothing_changes_in_combat_or_with_something_on_the_cursor(self):
        for setup, text in (("combat = true", "Leave combat to load a profile."),
                            ("cursor = { kind = 'item', id = 1 }", "Empty the cursor to load a profile.")):
            lua = load(SAVED, WORLD + setup)
            self.assertFalse(lua.eval("ActionBars.LoadProfile('PVP')"))
            self.assertEqual(lua.eval("changes()"), 0)
            self.assertIn(text, lua.eval("chatText()"))

    def test_an_unknown_profile_is_refused(self):
        lua = load(SAVED, WORLD)
        self.assertFalse(lua.eval("ActionBars.LoadProfile('pvp')"))
        self.assertIn('No profile "pvp".', lua.eval("chatText()"))


if __name__ == "__main__":
    unittest.main()
