"""GearRack is listed in ClassicAPI's AddOn Options, 2026-10-27.

ClassicAPI lists panels given to InterfaceOptions_AddCategory (docs/API.md,
InterfaceOptions). One GearRack page, no sub-entries to expand: its Gear sets
button opens the set editor (/gr sets), Trinkets the trinket options page (the
minimap button's right click). Each closes the options window and the game
menu first. Fails on e138cf7, which had no entry. How the page draws stays an
in-game check.
"""
from pathlib import Path
import os
import unittest
from lupa.lua51 import LuaRuntime

ROOT = Path(os.environ["VANILLAFORGE_ADDON_ROOT"])
SETTINGS = (ROOT / "src/Settings.lua").read_text("utf-8")


def entry():
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(r'''
        local W = {}
        W.__index = function(_, k) return rawget(W, k) or function() end end
        function W:CreateFontString() return setmetatable({}, W) end
        function CreateFrame(_, name) local f = setmetatable({}, W); if name then _G[name] = f end; return f end
        UI = { Select = function(b) return b end,
               Button = function(name, parent, label, x, y, w, onClick)
                   local b = CreateFrame("Button", name); b.label, b.click = label, onClick; return b end }
        categories = {}
        function InterfaceOptions_AddCategory(p) table.insert(categories, p) end
        hidden, opened = {}, {}
        InterfaceOptionsFrame = { IsShown = function() return true end, Hide = function() hidden.options = true end }
        GameMenuFrame = { IsShown = function() return true end }
        function HideUIPanel(f) if f == GameMenuFrame then hidden.menu = true end end
        GearRackTrinkets_OptFrame = {}
        GearRack = { OpenGearSets = function() opened.sets = true end,
                     ShowMenuPage = function(frame, tab)
                         if frame == GearRackTrinkets_OptFrame then opened.trinkets = tab end end }
    ''')
    body = SETTINGS[SETTINGS.index("local function OptionsEntry"):SETTINGS.index("function GearRack.CreateSettings()")]
    lua.execute(body + "OptionsEntry()")
    return lua


class OptionsEntry(unittest.TestCase):
    def test_one_entry_with_both_buttons(self):
        lua = entry()
        self.assertEqual(lua.eval("#categories"), 1)
        self.assertEqual(lua.eval("categories[1].name"), "GearRack")
        self.assertIsNone(lua.eval("rawget(categories[1], 'parent')"))
        self.assertEqual(lua.eval("GearRackOptionsSets.label"), "Gear sets")
        self.assertEqual(lua.eval("GearRackOptionsTrinkets.label"), "Trinkets")

    def test_gear_sets_opens_the_set_editor(self):
        lua = entry()
        lua.execute("GearRackOptionsSets.click()")
        self.assertTrue(lua.eval("opened.sets and hidden.options and hidden.menu"))

    def test_trinkets_opens_the_trinket_options(self):
        lua = entry()
        lua.execute("GearRackOptionsTrinkets.click()")
        self.assertEqual(lua.eval("opened.trinkets"), 1)
        self.assertTrue(lua.eval("hidden.options and hidden.menu"))


if __name__ == "__main__":
    unittest.main()
