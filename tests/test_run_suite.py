"""run_suite.py reads unittest's verbose output into one line per test, and
--all tells a dead suite from a passing one."""
import contextlib
import importlib.util
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

TOOLS = Path(__file__).resolve().parents[1] / "tools"
SPEC = importlib.util.spec_from_file_location("run_suite", TOOLS / "run_suite.py")
SUITE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SUITE)

OUTPUT = """test_a (test_x.Case.test_a) ... ok
test_b (test_x.Case.test_b) ... FAIL
test_c (test_x.Case.test_c) ... ERROR
test_d (test_x.Other) ... ok

======================================================================
FAIL: test_b (test_x.Case.test_b)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "x.py", line 3, in test_b
    self.assertEqual(1, 2)
AssertionError: 1 != 2

======================================================================
ERROR: test_c (test_x.Case.test_c)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "x.py", line 9, in test_c
ValueError: substring not found

----------------------------------------------------------------------
Ran 4 tests in 0.001s

FAILED (failures=1, errors=1)
"""


class ReadsResults(unittest.TestCase):
    def test_each_test_with_its_outcome_and_first_error(self):
        self.assertEqual(SUITE.results(OUTPUT), [
            ("test_x.Case.test_a", "ok", ""),
            ("test_x.Case.test_b", "FAIL", "AssertionError: 1 != 2"),
            ("test_x.Case.test_c", "ERROR", "ValueError: substring not found"),
            ("test_x.Other.test_d", "ok", ""),          # the older "(module.Class)" form
        ])


PASS = "test_a (test_x.Case.test_a) ... ok\ntest_b (test_x.Case.test_b) ... ok\n"
GONE = """test_a (test_x.Case.test_a) ... ERROR

======================================================================
ERROR: test_a (test_x.Case.test_a)
----------------------------------------------------------------------
FileNotFoundError: [Errno 2] No such file or directory: 'AutoBG_Timers.lua'

----------------------------------------------------------------------
Ran 1 test in 0.001s
"""


class RunsEverySuite(unittest.TestCase):
    def test_verdicts(self):
        self.assertEqual(SUITE.verdict(SUITE.results(PASS)), (True, "2 passed"))
        self.assertEqual(SUITE.verdict(SUITE.results(OUTPUT)), (False, "2 of 4 failed"))
        self.assertEqual(SUITE.verdict(SUITE.results(GONE)),
                         (False, "all 1 failed: does the suite test code that is gone?"))
        self.assertEqual(SUITE.verdict([]), (False, "no tests ran"))

    def test_a_suite_with_no_addon_or_with_every_test_failing_is_named(self):
        # The five suites of the addons before their rebuilds: EasyPoisons had no
        # addon any more, the old AutoBG suite failed every test (2026-11-25).
        with tempfile.TemporaryDirectory() as tmp:
            regressions, addons = Path(tmp) / "regressions", Path(tmp) / "AddOns"
            for suite in ("Bags", "EasyPoisons", "AutoBG", "ErrorLog"):
                (regressions / suite).mkdir(parents=True)
                (regressions / suite / "test_x.py").write_text("", encoding="utf-8")
            for addon in ("Bags", "AutoBG", "!ErrorLog"):
                (addons / addon).mkdir(parents=True)
            (regressions / "__pycache__").mkdir()          # no test files: not a suite
            outputs = {"Bags": PASS, "AutoBG": GONE, "ErrorLog": PASS}
            seen = {}

            def run(suite, pattern, addon_root):
                seen[suite.name] = addon_root.name
                return outputs[suite.name]
            with mock.patch.object(SUITE, "run", side_effect=run), \
                    contextlib.redirect_stdout(io.StringIO()) as printed:
                code = SUITE.run_all(addons, regressions)
        self.assertEqual(code, 1)
        self.assertEqual(seen, {"Bags": "Bags", "AutoBG": "AutoBG", "ErrorLog": "!ErrorLog"})
        lines = printed.getvalue().splitlines()
        self.assertIn("EasyPoisons  no installed addon: the suite tests nothing", lines)
        self.assertIn("AutoBG       all 1 failed: does the suite test code that is gone?", lines)
        self.assertIn("ErrorLog     2 passed", lines)
        self.assertEqual(lines[-1], "4 suites, 2 not passing: AutoBG, EasyPoisons.")


if __name__ == "__main__":
    unittest.main()
