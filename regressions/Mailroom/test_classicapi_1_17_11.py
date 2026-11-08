"""2026-10-27: Mailroom made a hidden tooltip frame at load that nothing
used. It is gone; no MailroomTooltipFrame is created.
"""
import unittest

import mailroom_env as env


class DeadTooltipTests(unittest.TestCase):
    def test_no_unused_tooltip_frame(self):
        lua = env.load()
        self.assertIsNone(lua.eval('rawget(_G, "MailroomTooltipFrame")'))
        source = (env.ROOT / "Mailroom.lua").read_text("utf-8-sig")
        self.assertNotIn("tooltip_frame", source)


if __name__ == "__main__":
    unittest.main()
