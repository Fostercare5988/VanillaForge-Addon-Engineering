"""!ErrorLog saves the locals of an error (ClassicAPI 1.20), 2026-11-07.

ClassicAPI 1.20 adds debuglocals(level, skipFunctionsAndUserdata), which answers
only while an error handler runs. The handler asks for the locals at the same
level as the stack (the code that raised the error), leaves out functions and
userdata, saves them with the error and shows them in the window. A repeat and
a direct call of the handler read none. Fails on 1.3.1. Runs ErrorLog.lua under
Lua 5.1 with recording debugstack and debuglocals; real values stay an in-game
check.
"""
from pathlib import Path
import os
import unittest
from lupa.lua51 import LuaRuntime

ROOT = Path(os.environ["VANILLAFORGE_ADDON_ROOT"])

BASE = r'''
local widget = setmetatable({}, { __index = function(t, k)
    if k == "CreateFontString" or k == "CreateTexture" then return function() return t end end
    if string.find(k, "^%u") then return function() return t end end
end })
editText = nil
function CreateFrame(kind, name) local f = setmetatable({ events = {}, scripts = {} }, { __index = widget })
    function f:RegisterEvent(e) self.events[e] = true end
    function f:UnregisterEvent() end
    function f:SetScript(k, fn) self.scripts[k] = fn end
    if kind == "EditBox" then function f:SetText(t) editText = t end end
    if name then _G[name] = f end
    table.insert(loaders, f)
    return f end
loaders = {}
UIParent, GameTooltip, DEFAULT_CHAT_FRAME = widget, widget, { AddMessage = function() end }
UISpecialFrames, ChatFontNormal = {}, widget
ErrorLogScroll = widget
function tinsert(t, v) table.insert(t, v) end
SlashCmdList = {}
function InterfaceOptions_AddCategory() end
function date() return "2026-11-07 12:00:00" end
function GetRealZoneText() return "Orgrimmar" end

callHeight, errorHeight = 6, 4
stackAt, localsAsked = {}, {}
function GetCallstackHeight() return callHeight end
function GetErrorCallstackHeight() return errorHeight end
function debugstack(start) table.insert(stackAt, start); return "Interface\AddOns\Foo\Bar.lua:1: in function" end
function debuglocals(level, skip)
    table.insert(localsAsked, { level = level, skip = skip })
    if errorHeight then return "count=3\nname=\"Bob\"\n" end
end
function geterrorhandler() return function() end end
function seterrorhandler(fn) reported = fn end
'''


class ErrorLocals(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute(BASE)
        self.lua.execute((ROOT / "ErrorLog.lua").read_text("utf-8-sig"))
        self.lua.execute('''
            for _, f in ipairs(loaders) do
                if f.events.ADDON_LOADED then f.scripts.OnEvent(f, "ADDON_LOADED", "!ErrorLog") end
            end
        ''')

    def test_locals_come_from_the_level_of_the_stack(self):
        self.lua.execute('reported("Interface\\AddOns\\Foo\\Bar.lua:1: boom")')
        self.assertEqual(self.lua.eval("#localsAsked"), 1)
        self.assertEqual(self.lua.eval("localsAsked[1].level"), self.lua.eval("stackAt[1]"))
        self.assertEqual(self.lua.eval("localsAsked[1].level"), 3)
        self.assertTrue(self.lua.eval("localsAsked[1].skip"))

    def test_the_locals_are_saved_with_the_error(self):
        self.lua.execute('reported("saved")')
        self.assertEqual(self.lua.eval("ErrorLog_DB.errors[1].locals"), 'count=3\nname="Bob"\n')

    def test_the_window_shows_the_locals(self):
        self.lua.execute('reported("shown"); SlashCmdList.ERRORLOG("")')
        text = self.lua.eval("editText")
        self.assertIn("Locals:", text)
        self.assertIn('name="Bob"', text)

    def test_a_repeat_reads_no_locals(self):
        self.lua.execute('reported("same"); reported("same"); reported("same")')
        self.assertEqual(self.lua.eval("#localsAsked"), 1)
        self.assertEqual(self.lua.eval("ErrorLog_DB.errors[1].count"), 3)

    def test_a_direct_call_asks_for_no_locals(self):
        self.lua.execute('errorHeight = nil; reported("direct"); SlashCmdList.ERRORLOG("")')
        self.assertEqual(self.lua.eval("#localsAsked"), 0)
        self.assertIsNone(self.lua.eval("ErrorLog_DB.errors[1].locals"))
        self.assertIn("Locals:\n(none)", self.lua.eval("editText"))


if __name__ == "__main__":
    unittest.main()
