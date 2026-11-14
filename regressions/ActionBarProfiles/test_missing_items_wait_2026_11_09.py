"""A saved item that is not in the bags (conjured food, used-up potion) leaves
its slot empty and is placed once it reaches the bags. Reported 2026-11-09:
loading "Cana" back from "Niko" left Niko's buttons where the mage's
conjured items and potions belonged. Mocks only; native placement stays an
in-game check.
"""
import unittest
from abp_env import load

SETUP = '''
    bars[11] = {kind='SPELL', id=99}
    profile({[11]={kind='ITEM', id=5349, name='Conjured Muffin'},
             [12]={kind='ITEM', id=5350, name='Conjured Water'}})
    ok = ABP_LoadProfileByName('Test')
'''
# Whether any frame still listens for bag changes.
LISTENING = ("(function() for _, w in ipairs(widgets) do"
             " if w.events.BAG_UPDATE or w.events.BAG_UPDATE_DELAYED then return true end end"
             " return false end)()")


class MissingItemsWait(unittest.TestCase):
    def test_missing_item_clears_stale_slot_and_waits(self):
        lua = load()
        lua.execute(SETUP)
        self.assertTrue(lua.eval("ok"))
        self.assertIsNone(lua.eval("bars[11]"), "the other profile's button must go")
        text = lua.eval("chatText()")
        self.assertIn("placed automatically", text)
        self.assertIn("slot 11 (Conjured Muffin): not in your bags", text)
        self.assertTrue(lua.eval(LISTENING))

    def test_item_is_placed_when_it_reaches_the_bags(self):
        lua = load()
        lua.execute(SETUP)
        lua.execute("bags[0] = {{id=5349}}; bagsChanged()")
        self.assertEqual(lua.eval("bars[11] and bars[11].id"), 5349)
        self.assertIsNone(lua.eval("bars[12]"))
        self.assertTrue(lua.eval(LISTENING), "still waiting for the water")
        lua.execute("bags[0] = {{id=5349},{id=5350}}; bagsChanged()")
        self.assertEqual(lua.eval("bars[12] and bars[12].id"), 5350)
        self.assertFalse(lua.eval(LISTENING), "nothing left: listener off")

    def test_slot_the_player_filled_is_not_overwritten(self):
        lua = load()
        lua.execute(SETUP)
        lua.execute("bars[11] = {kind='SPELL', id=7}; bags[0] = {{id=5349}}; bagsChanged()")
        self.assertEqual(lua.eval("bars[11].id"), 7)

    def test_nothing_waits_when_nothing_is_missing(self):
        lua = load()
        lua.execute('''
            bags[0] = {{id=5349}}
            profile({[11]={kind='ITEM', id=5349, name='Conjured Muffin'}})
            ok = ABP_LoadProfileByName('Test')
        ''')
        self.assertTrue(lua.eval("ok"))
        self.assertFalse(lua.eval(LISTENING))

    def test_waits_end_when_the_next_load_starts(self):
        """Audit 2026-11-14: a load that stopped part way kept the earlier
        profile's waits, which then filled a slot the new profile leaves empty."""
        lua = load()
        lua.execute(SETUP)
        lua.execute('''
            learn(10, 'Wanted', 'Rank 1')
            ABP_Layout['Player of Realm'][2] = {profileName = 'Other',
                actions = {[1] = {kind='SPELL', id=10, name='Wanted'}}}
            failPlacement = true
            ABP_LoadProfileByName('Other')
            bags[0] = {{id=5349}}; bagsChanged()
        ''')
        self.assertIsNone(lua.eval("bars[11]"), "slot 11 is empty in the profile now loaded")


if __name__ == "__main__":
    unittest.main()
