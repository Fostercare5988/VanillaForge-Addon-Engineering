#!/usr/bin/env python3
"""
Tests for upstream configuration and check_upstream.py helpers.
"""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
CHECKER_PATH = ROOT / "tools" / "check_upstream.py"
CONFIG_PATH = ROOT / "UPSTREAM_VERSIONS.json"


def load_checker():
    if not CHECKER_PATH.is_file():
        raise FileNotFoundError(f"Expected check_upstream.py at: {CHECKER_PATH}")
    spec = importlib.util.spec_from_file_location("check_upstream", CHECKER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load check_upstream.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CHECKER = load_checker()


class UpstreamConfigTests(unittest.TestCase):
    def test_config_loads_and_contains_expected_keys(self):
        self.assertTrue(CONFIG_PATH.is_file(), f"Missing config at {CONFIG_PATH}")
        config = CHECKER.load_config(CONFIG_PATH)

        expected_components = {"classicapi", "superwow", "nampower", "unitxp_sp3"}
        self.assertTrue(expected_components.issubset(set(config.keys())))

        for name in expected_components:
            entry = config[name]
            self.assertIn("minimum_version", entry, f"{name} missing minimum_version")
            self.assertIn("repository", entry, f"{name} missing repository")
            owner, repo = CHECKER.parse_repo(entry["repository"])
            self.assertTrue(owner and repo, f"Invalid repository for {name}")

    def test_all_components_have_reference_commit_and_file_shas(self):
        config = CHECKER.load_config(CONFIG_PATH)

        for name in ("classicapi", "superwow", "nampower", "unitxp_sp3"):
            entry = config[name]
            self.assertIn("reference_commit", entry, f"{name} missing reference_commit")
            self.assertEqual(len(entry["reference_commit"]), 40, f"{name} commit SHA must be 40 hex chars")
            self.assertIn("file_shas", entry, f"{name} missing file_shas")
            self.assertIsInstance(entry["file_shas"], dict, f"{name} file_shas must be a dict")
            self.assertGreater(len(entry["file_shas"]), 0, f"{name} file_shas must not be empty")
            for filename, sha in entry["file_shas"].items():
                self.assertEqual(len(sha), 40, f"{name} file_sha for {filename} must be 40 hex chars")


class CheckUpstreamHelperTests(unittest.TestCase):
    def test_parse_repo(self):
        self.assertEqual(CHECKER.parse_repo("owner/repo"), ("owner", "repo"))
        self.assertEqual(CHECKER.parse_repo("https://github.com/owner/repo"), ("owner", "repo"))
        self.assertEqual(CHECKER.parse_repo("https://github.com/owner/repo.git"), ("owner", "repo"))
        with self.assertRaises(CHECKER.CheckError):
            CHECKER.parse_repo("invalid")

    def test_normalize_version(self):
        self.assertEqual(CHECKER.normalize_version("v1.15.12"), "1.15.12")
        self.assertEqual(CHECKER.normalize_version("V2.2"), "2.2")
        self.assertEqual(CHECKER.normalize_version("4.6.2"), "4.6.2")
        self.assertIsNone(CHECKER.normalize_version(None))

    def test_version_key(self):
        self.assertEqual(CHECKER.version_key("1.15.12"), (1, 15, 12))
        self.assertEqual(CHECKER.version_key("v2.2"), (2, 2))
        self.assertGreater(CHECKER.version_key("1.15.12"), CHECKER.version_key("1.15.11"))
        self.assertGreater(CHECKER.version_key("4.6.3"), CHECKER.version_key("4.6.2"))
        self.assertIsNone(CHECKER.version_key(None))


class CheckUpstreamSnapshotTests(unittest.TestCase):
    def test_tracked_files_use_resolved_commit_when_branch_advances(self):
        commit = "a" * 40
        branch = "review/api"
        snapshot = {"docs/API.md": "b" * 40, "README.md": "c" * 40}
        config = {
            "repository": "owner/repo",
            "branch": branch,
            "reference_version": "1.0",
            "reference_commit": commit,
            "tracked_files": list(snapshot),
            "file_shas": snapshot,
        }

        def api(path, token):
            if path == "/repos/owner/repo/releases/latest":
                return {"tag_name": "v1.0"}
            if path == "/repos/owner/repo/commits/review%2Fapi":
                return {"sha": commit}
            for filename, sha in snapshot.items():
                if path == f"/repos/owner/repo/contents/{filename}?ref={commit}":
                    return {"sha": sha}
                if path == f"/repos/owner/repo/contents/{filename}?ref=review%2Fapi":
                    # The branch advanced after its commit was resolved.
                    return {"sha": "d" * 40}
            raise AssertionError(f"Unexpected GitHub API request: {path}")

        with mock.patch.object(CHECKER, "github_api", side_effect=api) as github:
            result = CHECKER.check_component("example", config, None, False)

        github.assert_any_call("/repos/owner/repo/commits/review%2Fapi", None)
        self.assertEqual(result["branch"], branch)
        self.assertEqual(result["upstream_commit"], commit)
        self.assertEqual(result["file_shas"], snapshot)
        self.assertFalse(result["changed"])
        for filename in snapshot:
            github.assert_any_call(
                f"/repos/owner/repo/contents/{filename}?ref={commit}", None
            )


class UpstreamAuditTemplateTests(unittest.TestCase):
    def test_audit_template_defines_capability_displacement_review(self):
        template_path = ROOT / "agent" / "UPSTREAM_AUDIT_TEMPLATE.md"
        self.assertTrue(template_path.is_file(), f"Missing audit template at {template_path}")
        text = template_path.read_text(encoding="utf-8")
        self.assertIn("PORTFOLIO CAPABILITY DISPLACEMENT REVIEW:", text)
        for classification in (
            "REPLACE",
            "RETAIN",
            "PARTIAL REPLACEMENT",
            "NO OVERLAP",
            "RUNTIME VERIFICATION REQUIRED",
        ):
            self.assertIn(classification, text)
        self.assertIn("Candidate Displacement Matrix:", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
