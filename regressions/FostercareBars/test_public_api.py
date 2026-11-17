"""What other addons call (spec K8; test 11): BrainwasherPro links talent
specs to profiles by name, through the table FostercareBars only (the two
old ABP_ names went on 2026-11-18, when BrainwasherPro moved to it).
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

    def test_the_old_names_are_gone(self):
        lua = load(SAVED)
        self.assertIsNone(lua.eval("ABP_GetProfileNames"))
        self.assertIsNone(lua.eval("ABP_LoadProfileByName"))

    def test_names_work_before_the_world_is_entered(self):
        lua = load(SAVED, world=False)
        self.assertEqual(profiles(lua), ["PVE", "pveBWL", "PVP", "pvp"])


if __name__ == "__main__":
    unittest.main()
