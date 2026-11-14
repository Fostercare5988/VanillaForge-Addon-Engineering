#!/usr/bin/env python3
"""Run one addon's regression suite, or some of its files, now or on an older commit.

    python -B tools/run_suite.py FostercareTweaks                        # the whole suite
    python -B tools/run_suite.py FostercareTweaks "test_saved_keys*.py"  # some files
    python -B tools/run_suite.py FostercareTweaks test_x.py --old HEAD~1  # prove they fail before

The addon is read from the AddOns folder in .private/workspace.json (or
--addons), the tests from regressions/<Addon>. The suite sees the addon through
VANILLAFORGE_ADDON_ROOT, as tools/audit_addon.py --run-tests gives it.

--old runs the same tests against the addon as it was at that commit, unpacked
with `git archive` into a temporary folder. Never stash for this: with
core.autocrlf a stash and pop can turn an LF file to CRLF. A new test for a bug
must fail there and pass now (VANILLAFORGE.md section 5). The report gives each
test's first error line, so a failure of the test's own setup (a helper that
slices at a comment the old code lacks) is told apart from the bug it pins.
Exit code: 0 when every test passes (now), or when every test fails (--old).
"""
from __future__ import annotations

import sys
sys.dont_write_bytecode = True
import argparse
import io
import json
import os
import re
import subprocess
import tarfile
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGRESSIONS = ROOT / "regressions"
WORKSPACE = ROOT / ".private" / "workspace.json"

RESULT = re.compile(r"^(test\w*) \(([\w.]+)\)(?:\n.*?)?\s\.\.\.\s(ok|FAIL|ERROR|skipped.*)$", re.M)
BLOCK = re.compile(r"^(?:FAIL|ERROR): (test\w*) \(([\w.]+)\)\n-+\n(.*?)(?=^={10,}|^-{10,}\nRan )", re.M | re.S)


def addons_folder(given=None):
    if given:
        return Path(given)
    if WORKSPACE.is_file():
        return Path(json.loads(WORKSPACE.read_text("utf-8"))["addons"])
    raise SystemExit("No AddOns folder: pass --addons or write .private/workspace.json")


def unpack(addon_dir, rev, into):
    """The addon's tree at `rev`, extracted into `into` (bytes as committed)."""
    data = subprocess.run(["git", "-C", str(addon_dir), "archive", "--format=tar", rev],
                          capture_output=True, check=True).stdout
    with tarfile.open(fileobj=io.BytesIO(data)) as tar:
        tar.extractall(into, filter="data")


def run(suite, pattern, addon_root):
    env = os.environ.copy()
    env["VANILLAFORGE_ADDON_ROOT"] = str(addon_root)
    env["PYTHONPATH"] = os.pathsep.join([str(REGRESSIONS), str(suite)] +
                                        ([env["PYTHONPATH"]] if env.get("PYTHONPATH") else []))
    done = subprocess.run([sys.executable, "-B", "-m", "unittest", "discover", "-s", str(suite), "-p", pattern, "-v"],
                          cwd=REGRESSIONS, capture_output=True, text=True, errors="replace", env=env)
    return done.stdout + done.stderr


def key_of(name, where):
    # Python 3.11+ writes "test_x (module.Class.test_x)", older ones "(module.Class)".
    return where if where.endswith("." + name) else "%s.%s" % (where, name)


def results(output):
    """[(test, outcome, first error line)] from unittest -v output."""
    why = {}
    for name, where, body in BLOCK.findall(output):
        lines = [l.strip() for l in body.strip().splitlines() if l.strip()]
        error = next((l for l in reversed(lines) if re.match(r"^\w*(Error|Exception)\b", l)), lines[-1] if lines else "")
        why[key_of(name, where)] = error[:200]
    found = []
    for name, where, outcome in RESULT.findall(output):
        key = key_of(name, where)
        found.append((key, outcome.split()[0], why.get(key, "")))
    for key, error in why.items():                 # import errors have no "... ok" line
        if all(k != key for k, _, _ in found):
            found.append((key, "ERROR", error))
    return found


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("addon", help="the addon's folder name, as under regressions/")
    parser.add_argument("pattern", nargs="?", default="test*.py", help="test files (unittest -p), default all")
    parser.add_argument("--old", metavar="REV", help="run against the addon at this commit instead")
    parser.add_argument("--addons", help="the AddOns folder; default from .private/workspace.json")
    args = parser.parse_args(argv)
    # A suite drops the folder's load-order "!" (regressions/ErrorLog runs !ErrorLog).
    suite = REGRESSIONS / args.addon.lstrip("!")
    addon_dir = addons_folder(args.addons) / args.addon
    if not addon_dir.is_dir():
        addon_dir = addons_folder(args.addons) / ("!" + args.addon)
    if not suite.is_dir():
        raise SystemExit("No suite at %s" % suite)
    with tempfile.TemporaryDirectory() as tmp:
        root = addon_dir
        if args.old:
            root = Path(tmp) / args.addon
            unpack(addon_dir, args.old, root)
        found = results(run(suite, args.pattern, root))
    if not found:
        print("No tests ran (pattern %r)." % args.pattern)
        return 1
    failed = [f for f in found if f[1] in ("FAIL", "ERROR")]
    label = "on %s" % args.old if args.old else "now"
    for key, outcome, error in found:
        print("%-5s %s%s" % (outcome, key, ("\n      " + error) if error else ""))
    print("%d of %d failed %s." % (len(failed), len(found), label))
    if args.old:
        passing = [k for k, o, _ in found if o == "ok"]
        if passing:
            print("These pass on the old code too (controls, or not a reproduction): " + ", ".join(passing))
        return 0 if not passing else 1
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
