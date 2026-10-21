"""The public API BrainwasherPro uses: profile names and loading by name
(added 2026-10-21). Mocks only; native placement stays an in-game check.
"""
import unittest
from abp_env import load


class PublicAPI(unittest.TestCase):
    def test_profile_names_are_listed(self):
        lua = load()
        lua.execute('''
            ABP_Layout['Player of Realm'] = {{profileName = 'PvE', actions = {}}, {profileName = 'PvP', actions = {}}}
            names = ABP_GetProfileNames()
        ''')
        self.assertEqual(lua.eval("names[1]"), "PvE")
        self.assertEqual(lua.eval("names[2]"), "PvP")
        lua.execute("names[1] = 'changed'")
        self.assertEqual(lua.eval("ABP_Layout['Player of Realm'][1].profileName"), "PvE", "callers get a copy")

    def test_profile_loads_by_name(self):
        lua = load()
        lua.execute('''
            learn(10, 'Wanted', 'Rank 1')
            profile({[1]={kind='SPELL', id=10, name='Wanted', rank='Rank 1'}}, 'PvP')
            ok = ABP_LoadProfileByName('PvP')
            missing = ABP_LoadProfileByName('Nope')
        ''')
        self.assertTrue(lua.eval("ok"))
        self.assertEqual(lua.eval("bars[1] and bars[1].id"), 10)
        self.assertFalse(lua.eval("missing"))


if __name__ == "__main__":
    unittest.main()
