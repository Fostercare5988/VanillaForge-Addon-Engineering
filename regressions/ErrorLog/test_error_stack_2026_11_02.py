"""!ErrorLog stacks start at the error (ClassicAPI 1.19), 2026-11-02.

The handler used debugstack(2), which starts inside the engine's error
machinery. GetErrorCallstackHeight names the level of the code that raised the
error, so the saved stack begins there. ClassicAPI's error window is the
previous handler; it opens only with /err popup on. Runs ErrorLog.lua under Lua
5.1 with a recording debugstack; real stacks stay an in-game check.
"""
from pathlib import Path
import os
import unittest
from wowlua import LuaRuntime

ROOT = Path(os.environ["VANILLAFORGE_ADDON_ROOT"])

BASE = r'''
local widget = setmetatable({}, { __index = function(t, k)
    if k == "CreateFontString" or k == "CreateTexture" then return function() return t end end
    if string.find(k, "^%u") then return function() return t end end
end })
function CreateFrame(_, name) local f = setmetatable({ events = {}, scripts = {} }, { __index = widget })
    function f:RegisterEvent(e) self.events[e] = true end
    function f:UnregisterEvent() end
    function f:SetScript(k, fn) self.scripts[k] = fn end
    if name then _G[name] = f end
    return f end
UIParent, GameTooltip, DEFAULT_CHAT_FRAME = widget, widget, { AddMessage = function() end }
SlashCmdList = {}
function InterfaceOptions_AddCategory() end
function date() return "2026-11-02 12:00:00" end
function GetRealZoneText() return "Orgrimmar" end

reported, shown, asked = nil, 0, {}
callHeight, errorHeight = 6, 4
function GetCallstackHeight() return callHeight end
function GetErrorCallstackHeight() return errorHeight end
function debugstack(start) table.insert(asked, start); return "Interface\AddOns\Foo\Bar.lua:1: in function" end
function debuglocals() end
function geterrorhandler() return function(msg) shown = shown + 1 end end
function seterrorhandler(fn) reported = fn end
'''


class ErrorStack(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute(BASE)
        self.lua.execute('''
            local create = CreateFrame
            loaders = {}
            function CreateFrame(kind, name)
                local f = create(kind, name); table.insert(loaders, f); return f
            end
        ''')
        self.lua.execute((ROOT / "ErrorLog.lua").read_text("utf-8-sig"))
        self.lua.execute('''
            for _, f in ipairs(loaders) do
                if f.events.ADDON_LOADED then f.scripts.OnEvent(f, "ADDON_LOADED", "!ErrorLog") end
            end
        ''')

    def test_the_stack_starts_at_the_code_that_raised_the_error(self):
        self.lua.execute('reported("Interface\\AddOns\\Foo\\Bar.lua:1: boom")')
        # 6 levels now, the error at height 4: start at 6 - 4 + 1.
        self.assertEqual(self.lua.eval("asked[1]"), 3)

    def test_a_direct_call_starts_at_the_caller(self):
        self.lua.execute('errorHeight = nil; reported("Interface\\AddOns\\Foo\\Bar.lua:2: direct")')
        self.assertEqual(self.lua.eval("asked[1]"), 2)

    def test_a_repeat_reads_no_stack(self):
        self.lua.execute('reported("same"); reported("same"); reported("same")')
        self.assertEqual(self.lua.eval("#asked"), 1)

    def test_the_classicapi_window_opens_only_with_popup_on(self):
        self.lua.execute('reported("quiet")')
        self.assertEqual(self.lua.eval("shown"), 0)
        self.lua.execute('SlashCmdList.ERRORLOG("popup"); reported("loud")')
        self.assertEqual(self.lua.eval("shown"), 1)


if __name__ == "__main__":
    unittest.main()
