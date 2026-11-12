"""!ErrorLog times scripts when frames look their methods up through a function (1.8.0, 2026-11-12).

In game, 1.7.1's self-check: 12750 frames walked, 0 of a known widget type, 0
scripts wrapped, and every label ever saved was a timer or a hook. The player's
probe printed "MT table function true true true": every frame shares one
metatable and its __index is a function, so the profiler found no SetScript
field to replace and no addon or game script had been timed. The lookup is now
wrapped, and answers SetScript and GetScript with the profiler's own.

Same mocks as the blind-spot suite, with frames built the way the game does.
Whether the game lets its metatable's __index be replaced is the in-game check;
a frame that stops answering gets the game's lookup back.
"""
from pathlib import Path
import os
import unittest
from wowlua import LuaRuntime
from test_blind_spots_2026_11_03 import BASE, LOAD, DEATH

ROOT = Path(os.environ["VANILLAFORGE_ADDON_ROOT"])

OLD = "local f = setmetatable({ scripts = {}, name = name }, { __index = index })"
NEW = """SHARED = SHARED or { __index = function(self, key) lookups = (lookups or 0) + 1; return self.kindIndex[key] end }
    local f = setmetatable({ scripts = {}, name = name, kindIndex = index }, SHARED)"""
assert OLD in BASE


def load(base=BASE.replace(OLD, NEW)):
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(base)
    lua.execute((ROOT / "Profiler.lua").read_text("utf-8-sig"))
    lua.execute("db = { profile = true }")
    lua.execute(LOAD)
    return lua


class FunctionIndex(unittest.TestCase):
    def test_game_and_addon_scripts_are_timed(self):
        lua = load()
        lua.execute(r"""
            stack = "Interface\\AddOns\\ThreatMeter\\Core.lua:10: in function"
            local f = CreateFrame("Frame")
            f:SetScript("OnEvent", function() clockv = clockv + 40 end)
            addonHandler = f.scripts.OnEvent
            stack = "Interface\\AddOns\\!ErrorLog\\Profiler.lua:1: in function"
        """ + DEATH.replace("TargetFrame.scripts.OnEvent()", "TargetFrame.scripts.OnEvent(); addonHandler()"))
        top = lua.eval("db.hitches[1].top")
        self.assertIn("FostercareTweaks 150.0 ms over 1 calls (worst x.lua:117 hook TargetFrame_Update)", top)
        self.assertIn("ThreatMeter 40.0 ms over 1 calls (worst Core.lua:10 OnEvent)", top)
        self.assertIn("Game UI and XML 5.0 ms over 1 calls (worst TargetFrame OnEvent)", top)

    def test_the_self_check_counts_them(self):
        lua = load()
        lua.execute('event = "PLAYER_LOGOUT"; driver.scripts.OnEvent()')
        self.assertEqual(lua.eval("db.xml.index"), "function")
        self.assertEqual(lua.eval("db.xml.scripts"), 1)
        self.assertEqual(lua.eval("db.xml.failed"), 0)
        self.assertEqual(lua.eval("db.xml.error"), None)

    def test_getscript_hands_back_the_original(self):
        lua = load()
        self.assertTrue(lua.eval("TargetFrame:GetScript('OnEvent') == gameHandler"))
        self.assertTrue(lua.eval("TargetFrame.scripts.OnEvent ~= gameHandler"))

    def test_other_methods_still_reach_the_game(self):
        lua = load()
        self.assertEqual(lua.eval("TargetFrame:GetName()"), "TargetFrame")

    def test_the_profilers_own_frames_stay_unwrapped(self):
        lua = load()
        self.assertTrue(lua.eval("driver.scripts.OnUpdate == tick"))

    def test_one_odd_frame_does_not_end_the_pass(self):
        lua = load(BASE.replace(OLD, NEW).replace(
            "function index:GetScript(s) return self.scripts[s] end",
            "function index:GetScript(s) if self.name == 'Odd' then error('odd frame') end return self.scripts[s] end"))
        lua.execute(r"""
            stack = GAME
            CreateFrame("Frame", "Odd")
            local late = CreateFrame("Frame", "LateFrame")
            late:SetScript("OnShow", function() end)
            lateHandler = late.scripts.OnShow
            stack = "Interface\\AddOns\\!ErrorLog\\Profiler.lua:1: in function"
            event = "PLAYER_LOGIN"; driver.scripts.OnEvent()
            event = "PLAYER_LOGOUT"; driver.scripts.OnEvent()
        """)
        self.assertTrue(lua.eval("LateFrame.scripts.OnShow ~= lateHandler"))
        self.assertEqual(lua.eval("db.xml.failed"), 1)
        self.assertIn("odd frame", lua.eval("db.xml.error"))


if __name__ == "__main__":
    unittest.main()
