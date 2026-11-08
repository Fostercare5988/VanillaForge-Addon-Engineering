"""OctoMail on modern Lua forms, 2026-11-08.

Before 2026-11-08 OctoMail's GetContainerItemInfo replacement packed every
call's returns into a new table (the Lua 5.0 'arg' table); the replacement
is now gone.
"""
import unittest
from octomail_env import load


class ModernForms(unittest.TestCase):
    def test_open_mailbox_container_info_is_the_clients(self):
        """Bag addons call GetContainerItemInfo per slot; with the mailbox open
        OctoMail's replacement made garbage. Since 2026-11-08 there is no
        replacement: queued items are locked by ClassicAPI (test_audit_2026_11_08)."""
        lua = load("nativeContainerInfo = GetContainerItemInfo")
        lua.execute("MailFrame:Show()")
        self.assertTrue(lua.eval("rawequal(GetContainerItemInfo, nativeContainerInfo)"))

    def test_debug_word_is_retired(self):
        """/om debug was a developer switch; it now shows the command list like any unknown word."""
        lua = load()
        lua.execute('OctoMail.slash_command("debug")')
        self.assertIsNone(lua.eval("rawget(OctoMail, 'debug')"))
        self.assertIsNone(lua.eval("rawget(OctoMail, 'debug_enabled')"))


if __name__ == "__main__":
    unittest.main()
