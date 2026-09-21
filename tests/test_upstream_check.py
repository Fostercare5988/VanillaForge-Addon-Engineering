#!/usr/bin/env python3
"""
Tests for upstream configuration and check_upstream.py helpers.
"""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path


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


if __name__ == "__main__":
    unittest.main(verbosity=2)
