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
    ok = ABP_LoadProfile(1, 'Test')
'''
FIRE = '''
    local f = ABP_WaitFrame_for_test()
    this = f; event = 'BAG_UPDATE'; f.scripts.OnEvent(); this = nil
    this = f; if f.scripts.OnUpdate then f.scripts.OnUpdate() end; this = nil
'''


class MissingItemsWait(unittest.TestCase):
    def make(self):
        lua = load()
        lua.execute('''
            frames = {}
            local base = CreateFrame
            CreateFrame = function(...)
                local f = newFrame('wait'); f.events = {}
                function f:RegisterEvent(e) self.events[e] = true end
                function f:UnregisterEvent(e) self.events[e] = nil end
                frames[table.getn(frames) + 1] = f
                return f
            end
            function ABP_WaitFrame_for_test() return frames[1] end
        ''')
        return lua

    def test_missing_item_clears_stale_slot_and_waits(self):
        lua = self.make()
        lua.execute(SETUP + "text = table.concat(messages, ' / ')")
        self.assertTrue(lua.eval("ok"))
        self.assertIsNone(lua.eval("bars[11]"), "the other profile's button must go")
        self.assertIn("placed automatically", lua.eval("text"))
        self.assertIn("slot 11 (Conjured Muffin): not in your bags", lua.eval("text"))
        self.assertTrue(lua.eval("frames[1].events.BAG_UPDATE"))

    def test_item_is_placed_when_it_reaches_the_bags(self):
        lua = self.make()
        lua.execute(SETUP)
        lua.execute("bags[0] = {{id=5349}}")
        lua.execute(FIRE)
        self.assertEqual(lua.eval("bars[11] and bars[11].id"), 5349)
        self.assertIsNone(lua.eval("bars[12]"))
        self.assertTrue(lua.eval("frames[1].events.BAG_UPDATE"), "still waiting for the water")
        lua.execute("bags[0] = {{id=5349},{id=5350}}")
        lua.execute(FIRE)
        self.assertEqual(lua.eval("bars[12] and bars[12].id"), 5350)
        self.assertIsNone(lua.eval("frames[1].events.BAG_UPDATE"), "nothing left: listener off")

    def test_slot_the_player_filled_is_not_overwritten(self):
        lua = self.make()
        lua.execute(SETUP)
        lua.execute("bars[11] = {kind='SPELL', id=7}; bags[0] = {{id=5349}}")
        lua.execute(FIRE)
        self.assertEqual(lua.eval("bars[11].id"), 7)

    def test_nothing_waits_when_nothing_is_missing(self):
        lua = self.make()
        lua.execute('''
            bags[0] = {{id=5349}}
            profile({[11]={kind='ITEM', id=5349, name='Conjured Muffin'}})
            ok = ABP_LoadProfile(1, 'Test')
        ''')
        self.assertTrue(lua.eval("ok"))
        self.assertEqual(lua.eval("table.getn(frames)"), 0)


if __name__ == "__main__":
    unittest.main()
