"""ClassicAPI 1.17.11 pass, 2026-10-27: the slash command splits its words
with strsplittable, which returns the array directly.
"""
import unittest
from lupa.lua51 import LuaRuntime

from test_audit_2026_10_25 import source


class SlashSplitTests(unittest.TestCase):
    def test_reset_word_reaches_its_command(self):
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute('''
            CLASSIC_API_VERSION, SUPERWOW_VERSION = 11711, "2.2"
            function SetCVar() end
            function CreateFrame() return { RegisterEvent = function() end, SetScript = function() end } end
            SlashCmdList = {}
            FostercareTweaks_Config = { overwrites = { x = 1 } }
            reloaded = false
            function ReloadUI() reloaded = true end
            splits = 0
            function strsplittable(sep, str)
                splits = splits + 1
                local t = {}
                for w in string.gmatch(str, "[^" .. sep .. "]+") do table.insert(t, w) end
                return t
            end
        ''')
        lua.execute(source("Core.lua"))
        lua.execute('SlashCmdList["FOSTERCARETWEAKS"]("reset")')
        self.assertEqual(lua.eval('splits'), 1)
        self.assertTrue(lua.eval('reloaded'))
        self.assertIsNone(lua.eval('next(FostercareTweaks_Config.overwrites)'))


if __name__ == "__main__":
    unittest.main()
