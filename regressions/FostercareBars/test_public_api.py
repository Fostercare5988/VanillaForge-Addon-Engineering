"""What other addons call (spec K8; test 11): BrainwasherPro links talent
specs to profiles by name. The two ABP_ names serve the old BrainwasherPro
until it is rebuilt.
"""
import unittest
from fb_env import load, profiles

SAVED = '''FostercareBarsDB = { profiles = {
    pvp = { actions = {} }, PVP = { actions = {} }, pveBWL = { actions = {} },
    PVE = { actions = { [1] = { kind = 'spell', id = 10 } } },
} }'''


class PublicAPI(unittest.TestCase):
    def test_names_come_in_order_case_ignored_but_kept(self):
        lua = load(SAVED)
        self.assertEqual(profiles(lua), ["PVE", "pveBWL", "PVP", "pvp"])
        lua.execute("names = FostercareBars.GetProfileNames() names[1] = 'changed'")
        self.assertEqual(profiles(lua)[0], "PVE", "callers get a copy")

    def test_load_by_name_says_whether_it_loaded(self):
        lua = load(SAVED, "learn(10)")
        self.assertTrue(lua.eval("FostercareBars.LoadProfile('PVE')"))
        self.assertEqual(lua.eval("bars[1].id"), 10)
        self.assertFalse(lua.eval("FostercareBars.LoadProfile('Nope')"))
        self.assertFalse(lua.eval("FostercareBars.LoadProfile(nil)"))

    def test_the_old_names_do_the_same(self):
        lua = load(SAVED, "learn(10)")
        self.assertEqual(list(lua.eval("ABP_GetProfileNames()").values()), profiles(lua))
        self.assertTrue(lua.eval("ABP_LoadProfileByName('PVE')"))
        self.assertFalse(lua.eval("ABP_LoadProfileByName('Nope')"))

    def test_names_work_before_the_world_is_entered(self):
        lua = load(SAVED, world=False)
        self.assertEqual(profiles(lua), ["PVE", "pveBWL", "PVP", "pvp"])


if __name__ == "__main__":
    unittest.main()
