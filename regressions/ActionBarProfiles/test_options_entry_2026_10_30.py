"""ActionBarProfiles is listed in ClassicAPI's AddOn Options (2026-10-30)."""
import unittest
from abp_env import load


class OptionsEntry(unittest.TestCase):
    def test_entry_is_listed_once(self):
        lua = load()
        self.assertEqual(lua.eval("#categories"), 1)
        self.assertEqual(lua.eval("categories[1].name"), "ActionBarProfiles")


if __name__ == "__main__":
    unittest.main()
