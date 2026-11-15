"""Items that are not in the bags wait for them (spec K5; test 6)."""
import unittest
from fb_env import load

SAVED = '''FostercareBarsDB = { profiles = {
    PVP = { actions = { [1] = { kind = 'item', id = 300 }, [2] = { kind = 'item', id = 400 } } },
    PVE = { actions = { [3] = { kind = 'item', id = 500 } } },
} }'''


class Waiting(unittest.TestCase):
    def test_the_slot_is_emptied_then_filled_when_the_item_arrives(self):
        lua = load(SAVED, "bars[1] = { kind = 'spell', id = 9 }")
        self.assertEqual(lua.eval("busyFrames()"), "", "nothing listens before a slot waits")
        lua.execute("FostercareBars.LoadProfile('PVP')")
        self.assertIsNone(lua.eval("bars[1]"), "the other profile's button goes")
        self.assertIn("Placed when they reach your bags: Item 300, Item 400.", lua.eval("chatText()"))
        self.assertEqual(lua.eval("busyFrames()"), "BAG_UPDATE_DELAYED,PLAYER_REGEN_ENABLED")
        lua.execute("give(300) bagsChanged()")
        self.assertEqual(lua.eval("bars[1].kind .. bars[1].id"), "item300")
        self.assertIn("Placed Item 300.", lua.eval("chatText()"))
        self.assertNotEqual(lua.eval("busyFrames()"), "", "item 400 still waits")
        lua.execute("give(400) bagsChanged()")
        self.assertEqual(lua.eval("bars[2].id"), 400)
        self.assertEqual(lua.eval("busyFrames()"), "", "nothing listens once no slot waits")

    def test_a_new_load_ends_the_old_waits(self):
        lua = load(SAVED)
        lua.execute("FostercareBars.LoadProfile('PVP') FostercareBars.LoadProfile('PVE') give(300) bagsChanged()")
        self.assertIsNone(lua.eval("bars[1]"))
        lua.execute("give(500) bagsChanged()")
        self.assertEqual(lua.eval("bars[3].id"), 500)
        self.assertEqual(lua.eval("busyFrames()"), "")

    def test_a_slot_the_player_filled_is_left_alone(self):
        lua = load(SAVED)
        lua.execute("FostercareBars.LoadProfile('PVP') bars[1] = { kind = 'spell', id = 9 } give(300) bagsChanged()")
        self.assertEqual(lua.eval("bars[1].kind"), "spell")

    def test_in_combat_it_waits_for_the_fight_to_end(self):
        lua = load(SAVED)
        lua.execute("FostercareBars.LoadProfile('PVP') combat = true give(300) bagsChanged()")
        self.assertIsNone(lua.eval("bars[1]"))
        lua.execute("combat = nil fire('PLAYER_REGEN_ENABLED')")
        self.assertEqual(lua.eval("bars[1].id"), 300)

    def test_a_locked_item_that_arrives_is_tried_again(self):
        lua = load(SAVED)
        lua.execute("FostercareBars.LoadProfile('PVP') give(300, 1, true) bagsChanged()")
        self.assertIsNone(lua.eval("bars[1]"))
        lua.execute("bags[1].locked = nil bagsChanged()")
        self.assertEqual(lua.eval("bars[1].id"), 300)

    def test_an_item_already_in_its_slot_stays_though_none_is_left(self):
        lua = load(SAVED, "bars[1] = { kind = 'item', id = 300 }")
        lua.execute("FostercareBars.LoadProfile('PVP')")
        self.assertEqual(lua.eval("bars[1].id"), 300)
        self.assertIn("Item 400.", lua.eval("chatText()"))
        self.assertNotIn("Item 300", lua.eval("chatText()"))


if __name__ == "__main__":
    unittest.main()
