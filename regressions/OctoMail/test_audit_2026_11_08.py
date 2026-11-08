"""Reproductions for the 2026-11-08 OctoMail audit (.private/audit-OctoMail-2026-11-08.md).

Each test fails on OctoMail 1.6.0 (9c96af5) for the reason in its docstring.
Mocks model the game; the server's mail handling and drawing stay in-game
checks.
"""
import unittest
from octomail_env import load


class Bugs(unittest.TestCase):
    def test_options_button_says_what_it_does(self):
        """P2: the AddOn Options button read "Mail log", but it turned logging on
        or off without saying so, and closed the menus."""
        lua = load()
        lua.execute('run(OctoMailOptionsEntry, "OnShow")')
        self.assertEqual(lua.eval("OctoMailOptionsEntryOpen.text"), "Turn mail log on")
        lua.execute('run(OctoMailOptionsEntryOpen, "OnClick")')
        self.assertTrue(lua.eval("OctoMail_Log.Settings.Enabled"))
        self.assertEqual(lua.eval("OctoMailOptionsEntryOpen.text"), "Turn mail log off")

    def test_one_delete_per_mail(self):
        """P3: Open All takes from a mail again on each inbox update, and each
        take queued another delete for the same mail."""
        lua = load()
        lua.execute('''
            inbox = { { sender = "Bob", subject = "Ore", item = 1, read = 1 } }
            OctoMail.inbox_open(1); OctoMail.inbox_open(1); OctoMail.inbox_open(1)
        ''')
        self.assertEqual(lua.eval("#OctoMail.delete_queue"), 1)

    def test_commands_ignore_case(self):
        """P3: "/om LOG" showed the command list instead of turning the log on."""
        lua = load()
        lua.execute('OctoMail.slash_command("LOG")')
        self.assertTrue(lua.eval("OctoMail_Log.Settings.Enabled"))


if __name__ == "__main__":
    unittest.main()
