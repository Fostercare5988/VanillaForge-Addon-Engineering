"""The regression runtime is the game's Lua, and every suite uses it."""
import re
import sys
import unittest
from pathlib import Path

REGRESSIONS = Path(__file__).resolve().parents[1] / "regressions"
sys.path.insert(0, str(REGRESSIONS))

try:
    import lupa  # noqa: F401
    HAVE_LUPA = True
except ImportError:
    HAVE_LUPA = False

# A suite may build a runtime from lupa directly only to measure, never to play the game.
DIRECT_LUPA = re.compile(r"^\s*(from lupa\b|import lupa\b)", re.M)
INSTRUMENT = "# noqa: wowlua"


class EverySuiteUsesTheGameLua(unittest.TestCase):
    def test_no_suite_imports_lupa_directly(self):
        offenders = []
        for path in REGRESSIONS.rglob("*.py"):
            if path.name == "wowlua.py":
                continue
            for line in path.read_text("utf-8").splitlines():
                if DIRECT_LUPA.match(line) and INSTRUMENT not in line:
                    offenders.append(f"{path.relative_to(REGRESSIONS)}: {line.strip()}")
        self.assertEqual(offenders, [], "import LuaRuntime from wowlua")


@unittest.skipUnless(HAVE_LUPA, "lupa is not installed")
class GameLua(unittest.TestCase):
    def setUp(self):
        from wowlua import LuaRuntime
        self.lua = LuaRuntime()

    def test_gsub_function_returning_nothing_removes_the_match(self):
        self.assertEqual(self.lua.eval('(string.gsub("a-b", "%-", function() end))'), "ab")
        self.assertEqual(self.lua.eval('(("a-b"):gsub("%-", function() return false end))'), "ab")
        self.assertEqual(self.lua.eval('(gsub("a-b", "%-", function() return true end))'), "ab")
        self.assertEqual(self.lua.eval('(gsub("a-b", "%-", function() return 7 end))'), "a7b")

    def test_gsub_table_value_nil_or_false_keeps_the_match(self):
        self.assertEqual(self.lua.eval('(gsub("$a $b", "%$(%w)", { a = "A", b = false }))'), "A $b")

    def test_libraries_the_game_does_not_open_are_gone(self):
        for name in ("os", "io", "debug", "package", "require", "module", "dofile", "loadfile"):
            self.assertIsNone(self.lua.eval(name), name)

    def test_game_base_library_and_backports_are_there(self):
        for name in ("date", "time", "difftime", "coroutine", "select", "gcinfo", "loadstring",
                     "table.maxn", "table.wipe", "string.match", "string.gmatch", "string.gfind",
                     "math.mod", "math.fmod", "getglobal", "setglobal"):
            self.assertIsNotNone(self.lua.eval(name), name)

    def test_short_aliases(self):
        self.assertEqual(self.lua.eval("mod(7, 3)"), 1)
        self.assertEqual(self.lua.eval("strmatch('ab1', '%d')"), "1")
        self.assertEqual(self.lua.eval("getn({1, 2})"), 2)
        self.assertTrue(self.lua.execute("local t = {1}; return wipe(t) == t and next(t) == nil"))
        self.assertIsNone(self.lua.eval("sin"), "trigonometry aliases take degrees in game")

    def test_lua50_varargs_still_work(self):
        self.assertEqual(self.lua.eval("(function(...) return arg.n end)(1, nil, 3)"), 3)

    def test_tuples_unpack_by_default(self):
        self.assertEqual(self.lua.eval("1, 2"), (1, 2))


if __name__ == "__main__":
    unittest.main()
