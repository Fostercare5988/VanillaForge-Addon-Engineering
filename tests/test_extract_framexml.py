"""FrameXML extraction stays private, follows archive order and reports gaps."""
import contextlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))
SPEC = importlib.util.spec_from_file_location("extract_framexml", TOOLS / "extract_framexml.py")
EXTRACT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(EXTRACT)

UNIT = "Interface\\FrameXML\\UnitFrame.lua"


class FakeArchive:
    contents = {}

    def __init__(self, path):
        if self.contents.get(Path(path).name) is None:
            raise ValueError("not an MPQ")
        self.files = self.contents[Path(path).name]

    def read_file(self, name):
        return self.files.get(name)

    def close(self):
        pass


class ExtractFrameXMLTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.client = self.root / "client"
        (self.client / "Data").mkdir(parents=True)
        self.output = self.root / "private-framexml"

    def archives(self, contents):
        for name in contents:
            (self.client / "Data" / name).write_bytes(b"fixture")
        return mock.patch.object(FakeArchive, "contents", contents)

    def run_main(self, *extra):
        with mock.patch.object(EXTRACT, "MPQArchive", FakeArchive), \
             contextlib.redirect_stdout(io.StringIO()) as out, contextlib.redirect_stderr(io.StringIO()) as err:
            code = EXTRACT.main(["--client", str(self.client), "--output", str(self.output), *extra])
        return code, out.getvalue(), err.getvalue()

    def test_later_archive_wins_and_sources_are_recorded_without_hashes(self):
        everything = {name: b"base " + name.encode() for name in EXTRACT.REQUIRED}
        with self.archives({"interface.MPQ": everything, "patch-4.mpq": {UNIT: b"patched"}}):
            code, out, _ = self.run_main()
        self.assertEqual(code, 0)
        self.assertTrue(out.startswith("FrameXML: 7 extracted, 0 missing, 0 archive errors"))
        self.assertEqual((self.output / "Interface" / "FrameXML" / "UnitFrame.lua").read_bytes(), b"patched")
        record = json.loads((self.output / "sources.json").read_text("utf-8"))
        self.assertEqual(record["files"][UNIT]["archive"], "patch-4.mpq")
        self.assertNotIn("sha256", json.dumps(record))

    def test_missing_files_and_damaged_archives_fail_but_keep_other_archives(self):
        with self.archives({"interface.MPQ": {UNIT: b"x"}, "patch.MPQ": None}):
            code, out, _ = self.run_main("--file", "Interface/FrameXML/BuffFrame.lua")
        self.assertEqual(code, 1)
        record = json.loads((self.output / "sources.json").read_text("utf-8"))
        self.assertIn("Interface\\FrameXML\\BuffFrame.lua", record["missing"])
        self.assertEqual(record["archive_errors"][0]["archive"], "patch.MPQ")
        self.assertIn(UNIT, record["files"])

    def test_output_cannot_enter_repository_outside_private_or_the_client(self):
        for destination in (EXTRACT.ROOT / "regressions" / "framexml", self.client / "extracted"):
            with self.subTest(destination=destination):
                self.output = destination
                code, _, err = self.run_main()
                self.assertEqual(code, 2)
                self.assertIn("FrameXML extraction failed", err)
                self.assertFalse(destination.exists())

    def test_invalid_archive_closes_handle_when_constructor_fails(self):
        path = self.client / "Data" / "bad.mpq"
        path.write_bytes(b"not an MPQ")
        handle = path.open("rb")
        self.addCleanup(handle.close)
        with mock.patch("builtins.open", return_value=handle):
            with self.assertRaises(ValueError):
                EXTRACT.MPQArchive(path)
        self.assertTrue(handle.closed)

    def test_default_output_is_ignored_private_folder(self):
        self.assertEqual(EXTRACT.DEFAULT_OUTPUT, EXTRACT.ROOT / ".private" / "framexml")
        self.assertIn("/.private/", (EXTRACT.ROOT / ".gitignore").read_text("utf-8").splitlines())


if __name__ == "__main__":
    unittest.main()
