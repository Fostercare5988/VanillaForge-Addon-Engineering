"""Regression coverage for release audit and README reconciliation."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("check_audit_index", ROOT / "tools/check_audit_index.py")
assert SPEC is not None and SPEC.loader is not None
CHECKER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECKER)


class AuditIndexTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "docs").mkdir()
        self.readme = self.root / "README.md"
        self.set_version("1.15.15")
        for version in ("1.15.12", "1.15.13", "1.15.15"):
            self.add_audit(version)
        self.readme.write_text(f"Before\n{CHECKER.BEGIN}\n{CHECKER.END}\nAfter\n", encoding="utf-8")
        CHECKER.reconcile(self.root, write=True)

    def set_version(self, version):
        (self.root / "UPSTREAM_VERSIONS.json").write_text(
            json.dumps({"classicapi": {"reference_version": version}}), encoding="utf-8"
        )

    def add_audit(self, version):
        path = self.root / "docs" / f"CLASSICAPI_{version}_AUDIT.md"
        path.write_text(f"# ClassicAPI v{version} integration audit\n\nSource evidence retained.\n", encoding="utf-8")
        return path

    def test_current_repository_index_is_reconciled(self):
        self.assertFalse(CHECKER.reconcile(ROOT))

    def test_verify_and_write_are_idempotent_on_current_index(self):
        original = self.readme.read_bytes()
        self.assertFalse(CHECKER.reconcile(self.root))
        self.assertFalse(CHECKER.reconcile(self.root, write=True))
        self.assertEqual(self.readme.read_bytes(), original)

    def test_current_audit_cannot_be_replaced_by_old_ci_checkpoint(self):
        (self.root / "docs/CLASSICAPI_1.15.15_AUDIT.md").unlink()
        self.assertTrue((self.root / "docs/CLASSICAPI_1.15.12_AUDIT.md").is_file())
        original = self.readme.read_bytes()
        with self.assertRaisesRegex(CHECKER.AuditIndexError, "Missing current.*1.15.15"):
            CHECKER.reconcile(self.root, write=True)
        self.assertEqual(self.readme.read_bytes(), original)

    def test_new_baseline_requires_its_own_audit(self):
        self.set_version("1.15.16")
        with self.assertRaisesRegex(CHECKER.AuditIndexError, "Missing current.*1.15.16"):
            CHECKER.reconcile(self.root)

    def test_baseline_advance_refreshes_links_and_status(self):
        self.set_version("1.15.16")
        self.add_audit("1.15.16")
        with self.assertRaisesRegex(CHECKER.AuditIndexError, "index is stale"):
            CHECKER.reconcile(self.root)
        CHECKER.reconcile(self.root, write=True)
        text = self.readme.read_text(encoding="utf-8")
        self.assertIn("[v1.15.16 audit](docs/CLASSICAPI_1.15.16_AUDIT.md) | Current reference", text)
        self.assertIn("[v1.15.15 audit](docs/CLASSICAPI_1.15.15_AUDIT.md) | Historical release audit", text)
        self.assertEqual(text.count("| Current reference |"), 1)
        self.assertFalse(CHECKER.reconcile(self.root))

    def test_omitted_historical_audit_is_detected_and_evidence_preserved(self):
        audit = self.add_audit("1.15.14")
        evidence = audit.read_bytes()
        with self.assertRaisesRegex(CHECKER.AuditIndexError, "index is stale"):
            CHECKER.reconcile(self.root)
        CHECKER.reconcile(self.root, write=True)
        text = self.readme.read_text(encoding="utf-8")
        self.assertIn("docs/CLASSICAPI_1.15.14_AUDIT.md", text)
        self.assertLess(text.index("v1.15.15 audit"), text.index("v1.15.14 audit"))
        self.assertLess(text.index("v1.15.14 audit"), text.index("v1.15.13 audit"))
        self.assertEqual(audit.read_bytes(), evidence)

    def test_deleted_historical_audit_leaves_a_detectable_stale_link(self):
        (self.root / "docs/CLASSICAPI_1.15.12_AUDIT.md").unlink()
        with self.assertRaisesRegex(CHECKER.AuditIndexError, "index is stale"):
            CHECKER.reconcile(self.root)
        CHECKER.reconcile(self.root, write=True)
        self.assertNotIn("CLASSICAPI_1.15.12_AUDIT.md", self.readme.read_text(encoding="utf-8"))

    def test_future_audit_is_not_mislabelled_as_historical(self):
        self.add_audit("2.0.0")
        self.add_audit("1.15.9")
        CHECKER.reconcile(self.root, write=True)
        text = self.readme.read_text(encoding="utf-8")
        self.assertIn("[v2.0.0 audit](docs/CLASSICAPI_2.0.0_AUDIT.md) | Other release audit", text)
        self.assertLess(text.index("v1.15.15 audit"), text.index("v1.15.9 audit"))
        self.assertEqual(text.count("| Current reference |"), 1)

    def test_invalid_version_cannot_select_an_outside_path(self):
        for version in (None, 11515, "../../outside", "v1.15.15"):
            with self.subTest(version=version):
                self.set_version(version)
                with self.assertRaisesRegex(CHECKER.AuditIndexError, "reference_version"):
                    CHECKER.reconcile(self.root)

    def test_invalid_audit_filename_is_not_silently_skipped(self):
        (self.root / "docs/CLASSICAPI_latest_AUDIT.md").write_text("Audit", encoding="utf-8")
        with self.assertRaisesRegex(CHECKER.AuditIndexError, "Invalid release audit"):
            CHECKER.reconcile(self.root)

    def test_missing_duplicate_or_reversed_markers_do_not_allow_writes(self):
        variants = (
            "No markers\n",
            CHECKER.BEGIN + "\n",
            CHECKER.BEGIN + CHECKER.BEGIN + CHECKER.END,
            CHECKER.END + CHECKER.BEGIN,
        )
        for text in variants:
            with self.subTest(text=text):
                self.readme.write_text(text, encoding="utf-8")
                original = self.readme.read_bytes()
                with self.assertRaises(CHECKER.AuditIndexError):
                    CHECKER.reconcile(self.root, write=True)
                self.assertEqual(self.readme.read_bytes(), original)

    def test_regeneration_preserves_utf8_surroundings_and_crlf(self):
        prefix = "Before: caf\u00e9.\r\n".encode("utf-8")
        suffix = "\r\nAfter: \u00e6\u00f8\u00e5.\r\n".encode("utf-8")
        self.readme.write_bytes(prefix + f"{CHECKER.BEGIN}\r\n{CHECKER.END}".encode("utf-8") + suffix)
        CHECKER.reconcile(self.root, write=True)
        written = self.readme.read_bytes()
        self.assertTrue(written.startswith(prefix))
        self.assertTrue(written.endswith(suffix))
        self.assertNotIn(b"\n", written.replace(b"\r\n", b""))
        self.assertFalse(CHECKER.reconcile(self.root))

    def test_cli_reports_invalid_config_and_stale_index_with_failure_exit(self):
        self.add_audit("1.15.14")
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            self.assertEqual(CHECKER.main(["--root", str(self.root)]), 1)
        self.assertIn("--write", stderr.getvalue())
        (self.root / "UPSTREAM_VERSIONS.json").write_text("{broken", encoding="utf-8")
        with contextlib.redirect_stderr(stderr):
            self.assertEqual(CHECKER.main(["--root", str(self.root), "--write"]), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
