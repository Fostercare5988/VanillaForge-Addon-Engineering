"""Upstream doc fetching selects docs only, honors pinned SHAs and stays inside its folder."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1] / "tools"
SPEC = importlib.util.spec_from_file_location("fetch_upstream_docs", TOOLS / "fetch_upstream_docs.py")
FETCH = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(FETCH)

TREE = ["README.md", "EVENTS.md", "docs/API.md", "docs/raw_globals.txt", "nampower/main.cpp",
        ".github/ISSUE_TEMPLATE/bug_report.md", "Nampower.dll", "dllmain.cpp"]
CONTENT = {path: ("contents of " + path).encode() for path in TREE}


class FetchUpstreamDocsTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.output = Path(temporary.name)
        self.reads = []

    def fetch(self, name, entry, **kwargs):
        def read(repository, commit, path):
            self.reads.append(path)
            return CONTENT[path]
        return FETCH.fetch_entry(name, entry, self.output, tree=lambda r, c: list(TREE), read=read,
                                 wiki=lambda r, d: ("abc123", ["wiki/Home.md"]), **kwargs)

    def test_patterns_select_documentation_only(self):
        self.assertEqual(FETCH.select_docs(TREE, FETCH.DOC_PATTERNS["nampower"]), ["EVENTS.md", "README.md"])
        self.assertEqual(FETCH.select_docs(TREE, FETCH.DOC_PATTERNS["classicapi"]), ["README.md", "docs/API.md"])
        self.assertEqual(FETCH.select_docs(TREE, FETCH.DOC_PATTERNS["unitxp_sp3"]), ["README.md", "dllmain.cpp"])

    def test_binaries_are_never_requested(self):
        for name in FETCH.DOC_PATTERNS:
            self.reads.clear()
            self.fetch(name, {"repository": "o/r", "reference_commit": "c0ffee"}, include_wiki=False)
            self.assertNotIn("Nampower.dll", self.reads)

    def test_files_land_under_the_entry_folder(self):
        record = self.fetch("classicapi", {"repository": "o/r", "reference_commit": "c0ffee"})
        self.assertEqual((self.output / "classicapi" / "docs" / "API.md").read_bytes(), CONTENT["docs/API.md"])
        self.assertEqual([f["path"] for f in record["files"]], ["README.md", "docs/API.md"])
        self.assertNotIn("wiki", record)

    def test_pinned_sha_mismatch_fails(self):
        entry = {"repository": "o/r", "reference_commit": "c0ffee", "file_shas": {"README.md": "0" * 40}}
        with self.assertRaises(FETCH.FetchError):
            self.fetch("nampower", entry)

    def test_pinned_sha_match_is_recorded(self):
        sha = FETCH.git_blob_sha(CONTENT["README.md"])
        entry = {"repository": "o/r", "reference_commit": "c0ffee", "file_shas": {"README.md": sha}}
        record = self.fetch("nampower", entry)
        self.assertTrue(next(f for f in record["files"] if f["path"] == "README.md")["pinned"])

    def test_git_blob_sha_matches_git(self):
        # `git hash-object` of "hello\n"
        self.assertEqual(FETCH.git_blob_sha(b"hello\n"), "ce013625030ba8dba906f756967f9e9ca394464a")

    def test_superwow_wiki_is_recorded_as_unpinned(self):
        record = self.fetch("superwow", {"repository": "o/r", "reference_commit": "c0ffee"})
        self.assertEqual(record["wiki"], {"commit": "abc123", "pinned": False, "pages": ["wiki/Home.md"]})

    def test_unsafe_paths_are_rejected(self):
        for path in ("../escape.md", "/abs.md"):
            with self.assertRaises(FETCH.FetchError):
                FETCH.safe_relative(path)

    def test_stale_files_are_removed_on_refetch(self):
        stale = self.output / "nampower" / "OLD.md"
        stale.parent.mkdir(parents=True)
        stale.write_text("old")
        self.fetch("nampower", {"repository": "o/r", "reference_commit": "c0ffee"})
        self.assertFalse(stale.exists())

    def test_missing_commit_is_an_error(self):
        with self.assertRaises(FETCH.FetchError):
            self.fetch("nampower", {"repository": "o/r"})


if __name__ == "__main__":
    unittest.main()
