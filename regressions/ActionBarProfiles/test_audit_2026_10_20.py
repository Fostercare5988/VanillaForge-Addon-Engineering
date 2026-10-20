"""Reproductions for the 2026-10-20 ActionBarProfiles audit
(.private/audit-ActionBarProfiles-2026-10-20.md).

Reported in game: "Cannot load slot 19 (Elixir of the Mongoose): unavailable,
locked, or ambiguous. Action bars were left unchanged." Mocks only; native
placement of a zero-count item stays an in-game check.
"""
import unittest
from abp_env import load


class AuditReproductions(unittest.TestCase):
    def test_p1_item_already_in_slot_does_not_block_load(self):
        """P1-1: an item with none left in the bags blocks the whole profile even
        when that slot already holds it, so nothing else is restored."""
        lua = load()
        lua.execute('''
            learn(10, 'Wanted', 'Rank 1')
            bars[19] = {kind='ITEM', id=13452}
            profile({[1]={kind='SPELL', id=10, name='Wanted', rank='Rank 1'},
                     [19]={kind='ITEM', id=13452, name='Elixir of the Mongoose'}})
            ok = ABP_LoadProfile(1, 'Test')
        ''')
        self.assertTrue(lua.eval("ok"), list(lua.eval("messages").values()))
        self.assertEqual(lua.eval("bars[1] and bars[1].id"), 10)
        self.assertEqual(lua.eval("bars[19] and bars[19].id"), 13452)
        self.assertEqual(lua.eval("calls.PickupAction or 0"), 0)

    def test_p2_unavailable_slots_are_skipped_and_named(self):
        """P2-1: one unknown spell or used-up item stopped every other slot from loading."""
        lua = load()
        lua.execute('''
            learn(10, 'Wanted', 'Rank 1'); learn(30, 'Current', 'Rank 1')
            bars[2] = {kind='SPELL', id=30}
            profile({[1]={kind='SPELL', id=10, name='Wanted', rank='Rank 1'},
                     [2]={kind='SPELL', id=20, name='Other Spec', rank=''},
                     [3]={kind='ITEM', id=13452, name='Elixir of the Mongoose'}})
            ok = ABP_LoadProfile(1, 'Test')
            text = table.concat(messages, '\\n')
        ''')
        self.assertTrue(lua.eval("ok"))
        self.assertEqual(lua.eval("bars[1] and bars[1].id"), 10)
        self.assertEqual(lua.eval("bars[2] and bars[2].id"), 30, "skipped slot must keep its action")
        self.assertIsNone(lua.eval("bars[3]"))
        text = lua.eval("text")
        self.assertIn("slot 2 (Other Spec): spell not known", text)
        self.assertIn("slot 3 (Elixir of the Mongoose): not in your bags", text)

    def test_p3_locked_item_reason(self):
        """P3-1: the message did not say which of four reasons applied."""
        lua = load()
        lua.execute('''
            bags[0] = {{id=13452, locked=true}}
            profile({[1]={kind='ITEM', id=13452, name='Elixir of the Mongoose'}})
            ABP_LoadProfile(1, 'Test'); text = table.concat(messages, '\\n')
        ''')
        self.assertIn("slot 1 (Elixir of the Mongoose): item is locked", lua.eval("text"))
        self.assertEqual(lua.eval("calls.PlaceAction or 0"), 0)


if __name__ == "__main__":
    unittest.main()
