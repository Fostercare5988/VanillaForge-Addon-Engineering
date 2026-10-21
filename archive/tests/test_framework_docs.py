"""Regression coverage for compact startup instructions and documentation links."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
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


class SupportedBaselineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config = {
            "classicapi": {"minimum_version": "1.15.16"},
            "superwow": {"minimum_version": "2.2"},
            "nampower": {"minimum_version": "4.6.2"},
            "unitxp_sp3": {"minimum_version": "89", "reference_version": "90"},
        }
        self.save_config()
        self.write("TARGET_ENVIRONMENT.json", (ROOT / "TARGET_ENVIRONMENT.json").read_text(encoding="utf-8"))
        declarations = [f"{label} v{self.config[key]['minimum_version']}+"
                        for key, label in CHECKER.COMPONENTS.items()]
        self.write("AGENTS.md", "# Router\n")
        revision = "OctoWoW client revision `2026.10.10`\n"
        (self.root / "docs").mkdir()
        self.write("docs/TARGET_ENVIRONMENT.md", revision)
        self.write("VANILLAFORGE_SYSTEM_PROMPT.md", "## Target\n" + revision + ", ".join(declarations))
        self.write("README.md", "## Target\n" + revision + "\n".join(
            f"| [{label}](https://example.test/{key}) | v{self.config[key]['minimum_version']}+ |"
            for key, label in CHECKER.COMPONENTS.items()))
        self.write("ENGINE_REFERENCE.md", "\n".join(declarations) +
                   "\n---\n## 7. UnitXP SP3\n**Baseline:** v89+\n### 7.1 Evidence\nPinned build 90.\n")

    def write(self, name, text):
        (self.root / name).write_text(text, encoding="utf-8")

    def test_target_revision_drift_and_required_dll_removal_fail(self):
        self.assertEqual(CHECKER.check_target(self.root), [])
        path = self.root / "TARGET_ENVIRONMENT.json"
        profile = json.loads(path.read_text(encoding="utf-8"))
        profile["client"]["distribution_revision"] = "2026.11.01"
        self.write(path.name, json.dumps(profile))
        errors = CHECKER.check_target(self.root)
        self.assertEqual(len(errors), 3)
        self.assertTrue(all("expected exactly one 2026.11.01" in error for error in errors))
        del profile["required_extensions"]["unitxp_sp3"]
        self.write(path.name, json.dumps(profile))
        with contextlib.redirect_stderr(io.StringIO()) as output:
            self.assertEqual(CHECKER.main(["--root", str(self.root)]), 1)
        self.assertIn("must require the canonical", output.getvalue())

    def test_missing_target_profile_is_a_cli_diagnostic(self):
        (self.root / "TARGET_ENVIRONMENT.json").unlink()
        with contextlib.redirect_stderr(io.StringIO()) as output:
            self.assertEqual(CHECKER.main(["--root", str(self.root)]), 1)
        self.assertIn("TARGET_ENVIRONMENT.json", output.getvalue())

    def save_config(self):
        self.write("UPSTREAM_VERSIONS.json", json.dumps(self.config))

    def test_support_89_and_reference_90_are_distinct_and_read_only(self):
        before = {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        self.assertEqual(CHECKER.check_baselines(self.root), [])
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(CHECKER.main(["--root", str(self.root)]), 0)
        self.assertEqual(before, {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob("*") if p.is_file()})

    def test_each_component_drift_is_reported_in_all_current_declarations(self):
        for key, label in CHECKER.COMPONENTS.items():
            with self.subTest(component=key):
                original = self.config[key]["minimum_version"]
                self.config[key]["minimum_version"] = "999"
                self.save_config()
                errors = CHECKER.check_baselines(self.root)
                for name in ("README.md", "VANILLAFORGE_SYSTEM_PROMPT.md", "ENGINE_REFERENCE.md"):
                    self.assertTrue(any(e.startswith(f"{name}: {label}") for e in errors), errors)
                self.config[key]["minimum_version"] = original

    def test_unitxp_detail_cannot_retain_the_old_support_floor(self):
        path = self.root / "ENGINE_REFERENCE.md"
        self.write(path.name, path.read_text().replace("**Baseline:** v89+", "**Baseline:** v90+"))
        self.assertEqual(len(CHECKER.check_baselines(self.root)), 1)
        self.assertIn("UnitXP section baseline", CHECKER.check_baselines(self.root)[0])

    def test_absent_or_duplicate_support_declaration_fails(self):
        path = self.root / "VANILLAFORGE_SYSTEM_PROMPT.md"
        original = path.read_text()
        for text in (original.replace("ClassicAPI v1.15.16+", "ClassicAPI"),
                     original + "\nClassicAPI v1.15.16+"):
            self.write(path.name, text)
            self.assertEqual(len(CHECKER.check_baselines(self.root)), 1)

    def test_dated_evidence_and_addon_guards_do_not_become_support_floors(self):
        path = self.root / "VANILLAFORGE_SYSTEM_PROMPT.md"
        self.write(path.name, path.read_text() + "\n## Evidence\nUnitXP SP3 v90+\nMIN_CLASSIC_API=11512\n")
        self.write("old-audit.md", "UnitXP SP3 v88+\nClassicAPI v1.15.9+\n")
        self.assertEqual(CHECKER.check_baselines(self.root), [])

    def test_invalid_minimum_is_a_diagnostic(self):
        for value in (None, 89, "v89", "89+", "", True):
            with self.subTest(value=value):
                self.config["unitxp_sp3"]["minimum_version"] = value
                self.save_config()
                self.assertEqual(len(CHECKER.check_baselines(self.root)), 1)
                self.assertIn("unitxp_sp3.minimum_version", CHECKER.check_baselines(self.root)[0])

    def test_missing_document_and_component_are_diagnostics(self):
        (self.root / "README.md").unlink()
        del self.config["nampower"]
        self.save_config()
        errors = CHECKER.check_baselines(self.root)
        self.assertEqual(len(errors), 2)
        self.assertIn("README.md: missing supported baseline document", errors)

    def test_cli_fails_for_drift_and_malformed_or_missing_registry(self):
        self.config["unitxp_sp3"]["minimum_version"] = "90"
        self.save_config()
        with contextlib.redirect_stderr(io.StringIO()) as output:
            self.assertEqual(CHECKER.main(["--root", str(self.root)]), 1)
        self.assertIn("expected exactly one v90+", output.getvalue())
        for content in ("{", "[]"):
            self.write("UPSTREAM_VERSIONS.json", content)
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(CHECKER.main(["--root", str(self.root)]), 1)
        (self.root / "UPSTREAM_VERSIONS.json").unlink()
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(CHECKER.main(["--root", str(self.root)]), 1)


if __name__ == "__main__":
    unittest.main()
