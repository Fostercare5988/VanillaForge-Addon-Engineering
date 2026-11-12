"""!ErrorLog leaves the game's frame lookup alone (1.8.1, 2026-11-12).

1.8.0 replaced the __index function every frame shares, to time XML scripts.
In game, with the profiler on, FostercareTweaks could not be clicked, Mailroom
never appeared and AutoLazy did nothing, with no Lua error; /lag off fixed all
three at once. The profiler measured 0 XML scripts on this client anyway.

Same mocks as the blind-spot suite, with frames built the way the game does.
"""
from pathlib import Path
import os
import unittest
from wowlua import LuaRuntime
from test_blind_spots_2026_11_03 import BASE, LOAD

ROOT = Path(os.environ["VANILLAFORGE_ADDON_ROOT"])

OLD = "local f = setmetatable({ scripts = {}, name = name }, { __index = index })"
NEW = """SHARED = SHARED or { __index = function(self, key) return self.kindIndex[key] end }
    local f = setmetatable({ scripts = {}, name = name, kindIndex = index }, SHARED)"""
assert OLD in BASE


def load():
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(BASE.replace(OLD, NEW))
    lua.execute("gameLookup = nil; local probe = CreateFrame('Frame'); gameLookup = getmetatable(probe).__index")
    lua.execute((ROOT / "Profiler.lua").read_text("utf-8-sig"))
    lua.execute("db = { profile = true }")
    lua.execute(LOAD)
    return lua


class FrameLookupUntouched(unittest.TestCase):
    def test_the_shared_lookup_is_the_games_own(self):
        lua = load()
        self.assertTrue(lua.eval("getmetatable(TargetFrame).__index == gameLookup"))

    def test_methods_reach_the_game(self):
        lua = load()
        self.assertEqual(lua.eval("TargetFrame:GetName()"), "TargetFrame")
        self.assertTrue(lua.eval("TargetFrame:GetScript('OnEvent') == gameHandler"))

    def test_the_profilers_own_frames_stay_unwrapped(self):
        lua = load()
        self.assertTrue(lua.eval("driver.scripts.OnUpdate == tick"))


if __name__ == "__main__":
    unittest.main()
