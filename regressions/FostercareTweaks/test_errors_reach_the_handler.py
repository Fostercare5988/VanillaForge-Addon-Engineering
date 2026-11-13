"""Errors reach the error handler with their stack (KNOWN_PATTERNS KP-63), 2026-11-13.

ActionBars' WithButton ran FrameXML in pcall and raised the error again without
its stack, so !ErrorLog showed the line in ActionBars.lua, not the failing one.
Extra Rows' profile load caught a failed refresh and passed only its message
to ActionBarProfiles. Both now go through geterrorhandler(). Fails on 180b2bc.
"""
import re
import unittest

import ft_env
from test_audit_2026_10_26 import source


def between(text, start, end):
    i = text.index(start)
    return text[i:text.index(end, i)]


class ErrorsReachTheHandler(unittest.TestCase):
    def test_with_button_reports_and_restores_this(self):
        lua = ft_env.world()
        # Sliced at function definitions, not comments.
        lua.execute(between(source("ActionBars.lua"), "local function WithButton", "local function Snapshot")
                    + "\nWith = WithButton")
        lua.execute('before = {}; this = before; button = {}; '
                    'With(button, function() seen = this; error("stock code failed") end)')
        self.assertTrue(lua.eval("seen == button"))
        self.assertTrue(lua.eval("this == before"))
        self.assertEqual(len(lua.eval("errors")), 1)
        self.assertIn("stock code failed", lua.eval("errors[1]"))

    def test_no_catch_that_drops_the_stack(self):
        for name in ("ActionBars.lua", "ExtraActions.lua"):
            text = source(name)
            self.assertIsNone(re.search(r"(?<!x)pcall\(", text), name)
        self.assertIn("xpcall(refresh, Report)", source("ExtraActions.lua"))


if __name__ == "__main__":
    unittest.main()
