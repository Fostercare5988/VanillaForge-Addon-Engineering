"""game_checks.py collects the open checks and carries them to the game and back."""
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1] / "tools"
SPEC = importlib.util.spec_from_file_location("game_checks", TOOLS / "game_checks.py")
GC = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GC)

try:
    import lupa  # noqa: F401
    HAVE_LUPA = True
except ImportError:
    HAVE_LUPA = False

AUDIT = """# Audit
## Findings
1. Not a check.

## In-game checks still needed
1. Bars move continuously; a rank swap
   slides.
2. Answer source: `/run print(GetSpellInfo(14983))` and report it.
- Opening icon: `/run print(SpellInfo(<id>))` once the ID is known.

## In-game checks (closed by the player)
1. Already done.
"""

CODE = """local x = 1
-- The arena (2026-11-03). UNVERIFIED: the instance type an arena reports;
-- test in the arena with /run print(GetRealZoneText()).
local y = 2
"""


class GameChecks(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        root = Path(self.dir.name)
        self.private, self.regressions, self.addons = root / "private", root / "regressions", root / "AddOns"
        for folder in (self.private, self.regressions / "Demo", self.regressions / "Empty", self.addons / "Demo", self.addons / "Other"):
            folder.mkdir(parents=True)
        (self.private / "audit-Demo-2026-11-07.md").write_text(AUDIT, "utf-8")
        (self.private / "audit-MikScrollingBattleText-2026-10-25.md").write_text("## In-game checks\n1. Renamed addon.\n", "utf-8")
        (self.regressions / "Demo" / "test_demo.py").write_text("", "utf-8")
        (self.addons / "Demo" / "Demo.lua").write_text(CODE, "utf-8")
        (self.addons / "Other" / "Other.lua").write_text("-- UNVERIFIED: not maintained here\n", "utf-8")
        self.checks = GC.collect(self.addons, self.private, self.regressions)

    def tearDown(self):
        self.dir.cleanup()

    def by_text(self, start):
        return next(c for c in self.checks if c["text"].startswith(start))

    def test_audit_items_and_code_notes(self):
        texts = sorted(c["text"] for c in self.checks)
        self.assertEqual(len(texts), 5, texts)
        self.assertIn("Bars move continuously; a rank swap slides.", texts)
        self.assertNotIn("Already done.", " ".join(texts))
        self.assertNotIn("Not a check.", " ".join(texts))
        self.assertNotIn("not maintained here", " ".join(texts))
        self.assertEqual(self.by_text("Renamed").get("addon"), "FostercareBattleText")

    def test_a_code_note_starts_at_unverified_and_keeps_its_continuation(self):
        c = self.by_text("UNVERIFIED")
        self.assertEqual(c["where"], "Demo.lua:2")
        self.assertEqual(c["run"], "/run print(GetRealZoneText())")
        self.assertIn("test in the arena", c["text"])

    def test_run_lines(self):
        self.assertEqual(self.by_text("Answer source")["run"], "/run print(GetSpellInfo(14983))")
        self.assertIsNone(self.by_text("Opening icon")["run"], "a placeholder is for the player to fill in")
        self.assertIsNone(self.by_text("Bars")["run"])

    def test_ids_are_stable(self):
        again = GC.collect(self.addons, self.private, self.regressions)
        self.assertEqual([c["id"] for c in self.checks], [c["id"] for c in again])

    def test_answered_checks_are_not_open(self):
        ledger = {}
        GC.record(ledger, self.by_text("Bars")["id"], "ok", when="2026-11-07")
        self.assertEqual(len(GC.open_checks(self.checks, ledger)), 4)
        self.assertIn("4 open game checks", GC.show(self.checks, ledger))

    def test_push_replaces_its_block_and_keeps_the_rest(self):
        saved = self.private / "ErrorLog.lua"
        saved.write_bytes(b'ErrorLog_DB = {\r\n\t["errors"] = {\r\n\t},\r\n}\r\n')
        GC.write_checks(saved, self.checks, today="2026-11-07")
        GC.write_checks(saved, self.checks[:1], today="2026-11-08")
        raw = saved.read_bytes()
        self.assertEqual(raw.count(GC.BEGIN.encode()), 1)
        self.assertNotIn(b"\n", raw.replace(b"\r\n", b""), "the file keeps its CRLF endings")
        self.assertTrue(raw.startswith(b'ErrorLog_DB = {\r\n\t["errors"]'))
        self.assertIn(b"2026-11-08", raw)

    @unittest.skipUnless(HAVE_LUPA, "lupa is not installed")
    def test_round_trip_through_the_saved_data(self):
        saved = self.private / "ErrorLog.lua"
        saved.write_text('ErrorLog_DB = { ["errors"] = {} }\n', "utf-8")
        GC.write_checks(saved, self.checks)
        from lupa.lua51 import LuaRuntime
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute(saved.read_text("utf-8"))
        self.assertEqual(lua.eval("#ErrorLog_DB.checks"), 5)
        self.assertEqual(lua.eval("ErrorLog_DB.checks[2].run"), self.checks[1]["run"])
        # The game answers one and saves its own way.
        target = self.checks[1]["id"]
        saved.write_text('ErrorLog_DB = { ["errors"] = {}, ["checks"] = { { ["id"] = "%s", ["verdict"] = "bad", '
                         '["note"] = "no", ["at"] = "2026-11-07 20:00", ["who"] = "Claude", ["output"] = "x" } } }\n'
                         % target, "utf-8")
        self.assertEqual(GC.read_answers(saved), [{"id": target, "verdict": "bad", "note": "no",
                                                   "at": "2026-11-07 20:00", "who": "Claude", "output": "x"}])
        wtf = self.private / "WTF"
        (wtf / "Account" / "ME" / "SavedVariables").mkdir(parents=True)
        (wtf / "Account" / "ME" / "SavedVariables" / "!ErrorLog.lua").write_bytes(saved.read_bytes())
        ledger = {}
        self.assertEqual(GC.pull(wtf, ledger), 1)
        self.assertEqual(ledger[target]["verdict"], "bad")
        self.assertIn("Answered bad (1)", GC.show(self.checks, ledger))

    def test_strings_survive_lua(self):
        self.assertEqual(GC.lua_string('a "b" c\\d\ne'), '"a \\"b\\" c\\\\d\\ne"')


if __name__ == "__main__":
    unittest.main()
