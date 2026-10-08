"""Regression coverage for compact startup instructions and documentation links."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("check_framework_docs", ROOT / "tools/check_framework_docs.py")
assert SPEC is not None and SPEC.loader is not None
CHECKER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECKER)


class FrameworkDocsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.write("AGENTS.md", "# Router\n")
        self.write("VANILLAFORGE_SYSTEM_PROMPT.md", "# Contract\n")

    def write(self, name, text):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def test_budget_boundary_and_uncapped_technical_reference(self):
        for name, limit in CHECKER.WORD_LIMITS.items():
            self.write(name, "word " * limit)
        self.write("ENGINE_REFERENCE.md", "detail " * 10000)
        self.assertEqual(CHECKER.check(self.root), [])

    def test_each_startup_document_cannot_exceed_its_budget(self):
        for name, limit in CHECKER.WORD_LIMITS.items():
            self.write(name, "word " * (limit + 1))
        errors = CHECKER.check(self.root)
        self.assertEqual(len(errors), 2)
        for name, limit in CHECKER.WORD_LIMITS.items():
            self.assertIn(f"{name}: {limit + 1} words exceeds startup budget of {limit}", errors)

    def test_missing_mandatory_document_fails(self):
        (self.root / "AGENTS.md").unlink()
        self.assertIn("AGENTS.md: missing mandatory entry document", CHECKER.check(self.root))

    def test_relative_encoded_and_same_document_links(self):
        self.write("docs/Engine Notes.md", "# Résumé: `GetState()` & **UI**\n# Repeat\n# Repeat\nSetext title\n---\n")
        self.write("docs/start.md", "# Start\n[Self](#start)\n[Parent](../AGENTS.md#router)\n"
                   "[API](Engine%20Notes.md#résumé-getstate--ui)\n[Duplicate](<Engine Notes.md#repeat-1>)\n"
                   "[Setext](Engine%20Notes.md#setext-title)\n[Top](Engine%20Notes.md)\n")
        self.assertEqual(CHECKER.check(self.root), [])

    def test_missing_file_and_heading_report_document_and_line(self):
        self.write("docs/start.md", "[Missing](lost.md)\n[Typo](../AGENTS.md#rouetr)\n")
        errors = CHECKER.check(self.root)
        self.assertEqual(len(errors), 2)
        self.assertIn("docs/start.md:1: [lost.md] has no local target", errors)
        self.assertIn("docs/start.md:2: [../AGENTS.md#rouetr] has no heading anchor", errors)

    def test_fenced_and_inline_examples_do_not_create_links_or_headings(self):
        self.write("docs/start.md", "```markdown\n[Example](missing.md)\n# Hidden\n```\n"
                   "~~~~\n[Example](another.md)\n~~~~\n`[Example](inline.md)`\n[Hidden](#hidden)\n")
        errors = CHECKER.check(self.root)
        self.assertEqual(len(errors), 1)
        self.assertIn("[hidden]", str(errors).lower().replace("#", ""))

    def test_external_links_reference_definitions_and_file_assets(self):
        self.write("assets/icon.png", "image fixture")
        self.write("docs/start.md", "[Web](https://example.test/missing#heading)\n"
                   "[Mail](mailto:maintainer@example.test)\n[Network](//example.test/doc)\n"
                   "![Icon](../assets/icon.png)\n[Contract][core]\n[core]: ../VANILLAFORGE_SYSTEM_PROMPT.md#contract\n")
        self.assertEqual(CHECKER.check(self.root), [])
        self.write("docs/broken.md", "[core]: missing.md\n")
        self.assertEqual(CHECKER.check(self.root), ["docs/broken.md:1: [missing.md] has no local target"])

    def test_ignored_directories_and_repository_escape(self):
        for directory in ("ChatGPT", ".git", "__pycache__", "node_modules", ".private"):
            self.write(f"{directory}/draft.md", "[Missing](none.md)\n")
        self.assertEqual(CHECKER.check(self.root), [])
        self.write("README.md", "[Outside](../external.md)\n")
        self.assertIn("points outside the repository", CHECKER.check(self.root)[0])

    def test_cli_reports_failure_without_modifying_document(self):
        path = self.write("README.md", "[Missing](lost.md)\n")
        before = path.read_bytes()
        with contextlib.redirect_stderr(io.StringIO()) as output:
            self.assertEqual(CHECKER.main(["--root", str(self.root)]), 1)
        self.assertIn("has no local target", output.getvalue())
        self.assertEqual(path.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
