"""Mailroom on modern Lua forms, 2026-11-08.

Before 2026-11-08 Mailroom's GetContainerItemInfo replacement packed every
call's returns into a new table (the Lua 5.0 'arg' table); the replacement
is now gone.
"""
import unittest
from mailroom_env import load


class ModernForms(unittest.TestCase):
    def test_open_mailbox_container_info_is_the_clients(self):
        """Bag addons call GetContainerItemInfo per slot; with the mailbox open
        Mailroom's replacement made garbage. Since 2026-11-08 there is no
        replacement: queued items are locked by ClassicAPI (test_audit_2026_11_08)."""
        lua = load("nativeContainerInfo = GetContainerItemInfo")
        lua.execute("MailFrame:Show()")
        self.assertTrue(lua.eval("rawequal(GetContainerItemInfo, nativeContainerInfo)"))

    def test_debug_word_is_retired(self):
        """/mr debug was a developer switch; it now shows the command list like any unknown word."""
        lua = load()
        lua.execute('Mailroom.slash_command("debug")')
        self.assertIsNone(lua.eval("rawget(Mailroom, 'debug')"))
        self.assertIsNone(lua.eval("rawget(Mailroom, 'debug_enabled')"))


if __name__ == "__main__":
    unittest.main()
