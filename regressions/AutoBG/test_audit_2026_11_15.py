"""Audit 2026-11-15: repros for what the audit found.

Each test fails on the commit before its fix (tools/run_suite.py --old).
"""
import unittest
from wowlua import LuaRuntime

import test_queue_types as queue_env


def core():
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(queue_env.BASE)
    lua.execute(queue_env.CORE)
    lua.execute('AutoBGFrame.scripts.OnEvent(AutoBGFrame, "ADDON_LOADED", "AutoBG")')
    return lua


class QueueByNameTests(unittest.TestCase):
    """/abg q took only the short names: "/abg q arathi" queued the last
    battleground played (or opened the menu), not Arathi Basin."""

    def queued(self, command):
        lua = core()
        # pcall: the old code fell through to the battleground menu here.
        lua.execute('pcall(SlashCmdList.AUTOBG, %r)' % command)
        return list(lua.eval('queued').values())

    def test_full_and_partial_names_queue_that_battleground(self):
        self.assertEqual(self.queued("q arathi"), ["Arathi"])
        self.assertEqual(self.queued("q warsong"), ["Warsong"])
        self.assertEqual(self.queued("q alterac"), ["Alterac"])
        self.assertEqual(self.queued("q thorn"), ["ThornGorge"])

    def test_short_names_still_work(self):
        self.assertEqual(self.queued("q ab"), ["Arathi"])
        self.assertEqual(self.queued("q wsg"), ["Warsong"])
        self.assertEqual(self.queued("q av"), ["Alterac"])


if __name__ == '__main__':
    unittest.main()
