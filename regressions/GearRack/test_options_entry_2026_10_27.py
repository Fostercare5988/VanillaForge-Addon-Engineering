"""GearRack is listed in ClassicAPI's AddOn Options with Gear Sets and Trinkets
under its "+", 2026-10-27.

ClassicAPI lists a panel whose `parent` names another under that entry,
collapsed at first (docs/API.md, InterfaceOptions). Gear Sets opens the gear
set editor (/gr sets) and Trinkets the trinket options page (the minimap
button's right click). Each button closes the options window and the game
menu first. Fails on e138cf7, which had no entries. How the list draws and
expands stays an in-game check.
"""
from pathlib import Path
import os
import unittest
from lupa.lua51 import LuaRuntime

ROOT = Path(os.environ["VANILLAFORGE_ADDON_ROOT"])
SETTINGS = (ROOT / "src/Settings.lua").read_text("utf-8")


def entries():
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(r'''
        local W = {}
        W.__index = function(_, k) return rawget(W, k) or function() end end
        function W:CreateFontString() return setmetatable({}, W) end
        function W:SetText(t) self.text = t end
        function CreateFrame(_, name) local f = setmetatable({ name_ = name }, W); if name then _G[name] = f end; return f end
        UI = { Select = function(b) b.selected = true; return b end,
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
                     ShowMenuPage = function(frame, tab, restart)
                         if frame == GearRackTrinkets_OptFrame then opened.trinkets = tab end end }
        function By(name) for _, p in ipairs(categories) do if p.name == name then return p end end end
    ''')
    start = SETTINGS.index("local function OptionsEntry")
    body = SETTINGS[start:SETTINGS.index("function GearRack.CreateSettings()")]
    calls = SETTINGS[SETTINGS.index('    OptionsEntry("GearRackOptionsEntry"'):]
    calls = calls[:calls.index("\nend")]
    lua.execute(body + calls)
    return lua


class OptionsEntries(unittest.TestCase):
    def test_gearrack_lists_gear_sets_and_trinkets_under_it(self):
        lua = entries()
        self.assertEqual(lua.eval("categories[1].name"), "GearRack")
        self.assertIsNone(lua.eval("rawget(categories[1], 'parent')"))
        self.assertEqual(lua.eval("By('Gear Sets').parent"), "GearRack")
        self.assertEqual(lua.eval("By('Trinkets').parent"), "GearRack")
        self.assertEqual(lua.eval("#categories"), 3)

    def test_gear_sets_opens_the_set_editor(self):
        lua = entries()
        lua.execute("GearRackOptionsSetsOpen.click()")
        self.assertTrue(lua.eval("opened.sets and hidden.options and hidden.menu"))

    def test_trinkets_opens_the_trinket_options(self):
        lua = entries()
        lua.execute("GearRackOptionsTrinketsOpen.click()")
        self.assertEqual(lua.eval("opened.trinkets"), 1)
        self.assertTrue(lua.eval("hidden.options and hidden.menu"))


if __name__ == "__main__":
    unittest.main()
