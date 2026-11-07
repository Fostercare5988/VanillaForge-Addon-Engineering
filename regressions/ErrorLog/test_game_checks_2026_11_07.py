"""!ErrorLog 1.5.0 asks the open game checks in game, 2026-11-07.

VanillaForge's tools/game_checks.py writes the open checks into ErrorLog_DB.checks
with the game closed; /check shows them one at a time, runs a check's /run line
and keeps what it printed, and records ok or bad with a note, the date and the
character, for the tool to read back. Runs ErrorLog.lua and Checks.lua on the
shared game model; the chat frame and the saved data in game stay a game check.
"""
from pathlib import Path
import os
import unittest

import wowkit

ROOT = Path(os.environ["VANILLAFORGE_ADDON_ROOT"])

BASE = r'''
function geterrorhandler() return function() end end
function seterrorhandler() end
function date() return "2026-11-07 20:00" end
function GetRealZoneText() return "Orgrimmar" end
function UnitName() return "Claude" end
function GetCallstackHeight() return 2 end
function GetErrorCallstackHeight() return 2 end
function debugstack() return "" end
function debuglocals() end
GameTooltip = newWidget("GameTooltip", "GameTooltip")
printed = {}
function print(...)
    local parts = {}
    for i = 1, select("#", ...) do parts[i] = tostring((select(i, ...))) end
    printed[#printed + 1] = table.concat(parts, " ")
end
realPrint, realAdd = print, DEFAULT_CHAT_FRAME.AddMessage
ErrorLog_DB = { errors = {}, session = 3, checks = {
    { id = "a1", addon = "AutoBG", where = "AutoBG.lua:37", text = "Arena instance type.", run = "/run print(GetRealZoneText(), 7)" },
    { id = "b2", addon = "TWThreat", where = "audit-TWThreat-2026-11-07.md:78", text = "Bars move continuously." },
    { id = "c3", addon = "AutoBG", where = "AutoBG.lua:90", text = "Done before.", verdict = "ok" },
} }
'''


def load(saved=None):
    lua = wowkit.runtime()
    lua.execute(BASE)
    if saved is not None:
        lua.execute(saved)
    wowkit.load_files(lua, ROOT, ["ErrorLog.lua", "Checks.lua"], "!ErrorLog")
    lua.execute('fire("ADDON_LOADED", "!ErrorLog"); fire("PLAYER_ENTERING_WORLD"); chat = {}')
    return lua


def check(lua, text=""):
    lua.globals().SlashCmdList.ERRORLOGCHECK(text)
    return " / ".join(lua.eval("chat").values())


class GameChecks(unittest.TestCase):
    def test_in_toc_after_the_profiler(self):
        lines = [l.strip() for l in (ROOT / "!ErrorLog.toc").read_text("utf-8-sig").splitlines()]
        self.assertGreater(lines.index("Checks.lua"), lines.index("Profiler.lua"))

    def test_login_says_how_many_are_open(self):
        lua = wowkit.runtime()
        lua.execute(BASE)
        wowkit.load_files(lua, ROOT, ["ErrorLog.lua", "Checks.lua"], "!ErrorLog")
        lua.execute('fire("ADDON_LOADED", "!ErrorLog"); fire("PLAYER_ENTERING_WORLD")')
        self.assertIn("2 game checks are open: type /check.", " / ".join(lua.eval("chat").values()))

    def test_shows_the_first_open_check_with_its_run_line(self):
        lua = load()
        shown = check(lua)
        self.assertIn("2 open.", shown)
        self.assertIn("AutoBG", shown)
        self.assertIn("Arena instance type.", shown)
        self.assertIn("/check run tries: /run print(GetRealZoneText(), 7)", shown)

    def test_run_keeps_what_it_printed(self):
        lua = load()
        check(lua)
        check(lua, "run")
        self.assertEqual(lua.eval("ErrorLog_DB.checks[1].output"), "Orgrimmar 7")
        self.assertEqual(list(lua.eval("printed").values()), ["Orgrimmar 7"])
        self.assertTrue(lua.eval("print == realPrint"))

    def test_run_keeps_chat_lines_and_errors(self):
        lua = load('ErrorLog_DB.checks[1].run = "/run DEFAULT_CHAT_FRAME:AddMessage(\'hello\') error(\'boom\')"')
        check(lua)
        check(lua, "run")
        output = lua.eval("ErrorLog_DB.checks[1].output")
        self.assertTrue(output.startswith("hello | error: "), output)
        self.assertIn("boom", output)
        self.assertTrue(lua.eval("DEFAULT_CHAT_FRAME.AddMessage == realAdd and print == realPrint"))

    def test_ok_and_bad_record_the_answer_and_move_on(self):
        lua = load()
        check(lua)
        after_ok = check(lua, "ok looks right")
        self.assertEqual(lua.eval("ErrorLog_DB.checks[1].verdict"), "ok")
        self.assertEqual(lua.eval("ErrorLog_DB.checks[1].note"), "looks right")
        self.assertEqual(lua.eval("ErrorLog_DB.checks[1].at"), "2026-11-07 20:00")
        self.assertEqual(lua.eval("ErrorLog_DB.checks[1].who"), "Claude")
        self.assertIn("Bars move continuously.", after_ok)
        lua.execute("chat = {}")
        self.assertIn("say what you saw", check(lua, "bad"))
        self.assertIsNone(lua.eval("ErrorLog_DB.checks[2].verdict"))
        lua.execute("chat = {}")
        self.assertIn("no game checks are open.", check(lua, "bad bars stop and go"))
        self.assertEqual(lua.eval("ErrorLog_DB.checks[2].note"), "bars stop and go")

    def test_skip_wraps_and_list_counts_per_addon(self):
        lua = load()
        check(lua)
        self.assertIn("TWThreat", check(lua, "skip"))
        lua.execute("chat = {}")
        self.assertIn("AutoBG", check(lua, "skip"))
        lua.execute("chat = {}")
        self.assertEqual(check(lua, "list").count("1 open"), 2)

    def test_no_checks_yet(self):
        lua = load("ErrorLog_DB.checks = nil")
        self.assertIn("no game checks yet.", check(lua))


if __name__ == "__main__":
    unittest.main()
