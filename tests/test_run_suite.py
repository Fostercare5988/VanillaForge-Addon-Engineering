"""run_suite.py reads unittest's verbose output into one line per test."""
import importlib.util
import sys
import unittest
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main()
