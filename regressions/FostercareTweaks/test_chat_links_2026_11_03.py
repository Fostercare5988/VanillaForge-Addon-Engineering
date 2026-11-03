"""Chat lines with a link came out empty, 2026-11-03.

The player typed "test cus my chat bugging: https://octowow.st/forum/viewtopic.php?t=3274"
and only the time stamp showed. 1.16.0 had made the link splitter reuse one
table (table.wipe, then table.concat); ClassicAPI reads a table's stored length
for concat, which a wiped, refilled table can get wrong. The line is now built
by concatenation. The harness runs Lua 5.1 and cannot show the stored-length
fault, so the source is checked too. In game: type a link and an @ word in say.
"""
import os
import re
import unittest
from pathlib import Path

from test_hot_paths_2026_11_02 import ChatLinesWithoutLinks

ROOT = Path(os.environ["VANILLAFORGE_ADDON_ROOT"])
URL = "https://octowow.st/forum/viewtopic.php?t=3274"


class LinesWithLinksStayWhole(unittest.TestCase):
    def say(self, line):
        lua = ChatLinesWithoutLinks().chat()
        lua.execute('ChatFrame1:AddMessage("%s")' % line)
        return lua.eval("lines[1]")

    def test_the_players_line_keeps_its_words_and_the_link(self):
        out = self.say("test cus my chat bugging: " + URL)
        self.assertEqual(out, "test cus my chat bugging: |cffccccff|Hurl:%s|h[%s]|h|r" % (URL, URL))

    def test_a_link_between_a_player_link_and_text(self):
        out = self.say("|Hplayer:Bob|h[Bob]|h: see %s ok, mail x@y.com" % URL)
        self.assertTrue(out.startswith("|Hplayer:Bob|h[Bob]|h: see |cffccccff|Hurl:" + URL))
        self.assertTrue(out.endswith("|Hurl:x@y.com|h[x@y.com]|h|r"))

    def test_the_splitter_keeps_no_reused_table(self):
        source = (ROOT / "mods/chat-tweaks.lua").read_text("utf-8-sig")
        body = source[source.index("local function HandleLink"):source.index("local CopyLinkDialog")]
        self.assertNotIn("table.concat", body)
        self.assertNotIn("wipe", body)


if __name__ == "__main__":
    unittest.main()
