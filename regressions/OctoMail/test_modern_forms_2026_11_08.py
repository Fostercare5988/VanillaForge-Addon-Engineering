"""OctoMail on modern Lua forms, 2026-11-08.

The open-mailbox test fails on OctoMail before 2026-11-08: its
GetContainerItemInfo replacement packed every call's returns into a new
table (the Lua 5.0 'arg' table).
"""
import unittest
from octomail_env import load


class ModernForms(unittest.TestCase):
    def test_open_mailbox_container_info_allocates_nothing(self):
        """Bag addons call GetContainerItemInfo per slot; with the mailbox open that made garbage."""
        lua = load()
        delta = lua.eval('''(function()
            MailFrame:Show()
            bag["0:1"] = { texture = "t", count = 3 }; bag["0:2"] = { texture = "t" }
            OctoMail.sendmail_state = { attachments = { { 0, 2 } } }
            collectgarbage("collect"); collectgarbage("stop")
            local before = collectgarbage("count")
            for i = 1, 20000 do GetContainerItemInfo(0, 1) end
            local after = collectgarbage("count")
            collectgarbage("restart")
            return after - before
        end)()''')
        self.assertLess(delta, 64)
        self.assertEqual(lua.eval("(select(2, GetContainerItemInfo(0, 1)))"), 3)
        self.assertIsNone(lua.eval("(select(3, GetContainerItemInfo(0, 1)))"))
        # an item queued for a later part of a multi-part send shows as locked
        self.assertEqual(lua.eval("(select(3, GetContainerItemInfo(0, 2)))"), 1)

    def test_debug_word_is_retired(self):
        """/om debug was a developer switch; it now shows the command list like any unknown word."""
        lua = load()
        lua.execute('OctoMail.slash_command("debug")')
        self.assertIsNone(lua.eval("rawget(OctoMail, 'debug')"))
        self.assertIsNone(lua.eval("rawget(OctoMail, 'debug_enabled')"))


if __name__ == "__main__":
    unittest.main()
