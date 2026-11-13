"""addon_edit.py keeps each file's line endings and writes backslashes through @@."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import addon_edit  # noqa: E402

BS = chr(92)


class AddonEdit(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.root = Path(self.dir.name)

    def tearDown(self):
        self.dir.cleanup()

    def test_crlf_and_lf_files_keep_their_endings(self):
        crlf, lf = self.root / "a.lua", self.root / "b.lua"
        crlf.write_bytes(b"local a = 1\r\nlocal b = 2\r\n")
        lf.write_bytes(b"local a = 1\nlocal b = 2\n")
        for path in (crlf, lf):
            addon_edit.sub(str(path), "local b = 2", "local b = 3")
        self.assertEqual(crlf.read_bytes(), b"local a = 1\r\nlocal b = 3\r\n")
        self.assertEqual(lf.read_bytes(), b"local a = 1\nlocal b = 3\n")

    def test_the_placeholder_writes_two_backslashes(self):
        path = self.root / "c.lua"
        path.write_bytes(b'local p = ""\n')
        addon_edit.sub(str(path), '""', '"Fonts@@FRIZQT__.TTF"')
        self.assertEqual(path.read_text(), 'local p = "Fonts' + BS * 2 + 'FRIZQT__.TTF"\n')

    def test_the_toc_placeholder_writes_one_backslash(self):
        # 2026-11-13: a TOC line takes one backslash; @@ wrote two and the match failed.
        path = self.root / "Toy.toc"
        path.write_bytes(b"mods" + BS.encode() + b"a.lua\r\n")
        addon_edit.sub(str(path), "mods@/a.lua\n", "mods@/a.lua\nmods@/b.lua\n")
        self.assertEqual(path.read_bytes(), b"mods\\a.lua\r\nmods\\b.lua\r\n")

    def test_a_patch_that_does_not_match_fails(self):
        path = self.root / "d.lua"
        path.write_bytes(b"x\n")
        with self.assertRaises(AssertionError):
            addon_edit.sub(str(path), "missing", "y")

    def test_cut_replaces_from_start_to_end(self):
        path = self.root / "e.lua"
        path.write_bytes(b"a\r\nBEGIN\r\nold\r\nEND\r\nz\r\n")
        addon_edit.cut(str(path), "BEGIN\n", "END\n", "new\n")
        self.assertEqual(path.read_bytes(), b"a\r\nnew\r\nz\r\n")


if __name__ == "__main__":
    unittest.main()
