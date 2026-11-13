"""The FostercareTweaks regressions on the shared game model (wowkit).

`world(files)` loads Defaults.lua, Core.lua and Helpers.lua as the client does,
then the module files named (paths as in the TOC, mods/x.lua), and returns the
runtime; `start(lua)` delivers VARIABLES_LOADED, so Core's Initialize runs the
saved-key sweep and starts each module whose switch is on. Saved settings go in
before `start` (`FostercareTweaks_Config = {...}`).

Added on top of the kit, and only what the addon's core needs: a
hooksecurefunc that runs the hook after the function (the kit's is a no-op),
the error handler, the screen size, ClassicAPI's number formatter and class
colours, and the frames Core and Helpers touch. A test adds the FrameXML
functions and frames its module uses, as stand-ins with the stock fields.

Older test files keep their own inline worlds (BASE in test_audit_2026_10_26.py
and others); they move here when next touched. Slice a file at a function's
definition (`local function Name`, `function FT.Name`), never at a comment:
comments change in cleanups.
"""
from pathlib import Path
import os

import wowkit

ROOT = Path(os.environ["VANILLAFORGE_ADDON_ROOT"])

CORE = r'''
CLASSIC_API_VERSION, SUPERWOW_VERSION = 12006, "2.2"
errors = {}
function geterrorhandler() return function(e) errors[#errors + 1] = e; return e end end
-- After the function, with its arguments; `this` is whatever the caller set.
function hooksecurefunc(target, name, hook)
    if type(target) == "string" then target, name, hook = _G, target, name end
    local original = target[name]
    target[name] = function(...)
        local a, b, c, d = original(...)
        hook(...)
        return a, b, c, d
    end
end
function GetScreenWidth() return 1920 end
function GetScreenHeight() return 1080 end
function IsAddOnLoaded() return nil end
SlashCmdList = SlashCmdList or {}
-- ClassicAPI: the numeric-rule formatter (Helpers' FT.Countdown) and class colours.
Enum = { NumericRuleFormatRounding = { Up = 1 } }
C_StringUtil = { CreateNumericRuleFormatter = function()
    local f = {}
    function f:SetBreakpoints(b) self.breakpoints = b end
    function f:FormatNumber(n) return tostring(math.ceil(n)) end
    return f
end }
C_ClassColor = { GetClassColor = function(class)
    local c = RAID_CLASS_COLORS and RAID_CLASS_COLORS[class]
    if not c then return nil end
    return { GenerateHexColorMarkup = function() return "|c" .. (c.colorStr or "ffffffff") end,
             WrapTextInColorCode = function(_, text) return "|c" .. (c.colorStr or "ffffffff") .. text .. "|r" end }
end }
'''


def world(files=(), extra=""):
    """A runtime with the kit, the core of FostercareTweaks and `files` loaded."""
    lua = wowkit.runtime(unpack_returned_tuples=True)
    lua.execute(CORE)
    if extra:
        lua.execute(extra)
    wowkit.load_files(lua, ROOT, ["Defaults.lua", "Core.lua", "Helpers.lua"] + list(files), "FostercareTweaks")
    lua.execute("FT = FostercareTweaks; FT.ActionBars = FT.ActionBars or { Initialize = function() end }")
    return lua


def start(lua):
    """VARIABLES_LOADED: Core's Initialize (the sweep, then each module's start)."""
    lua.execute('fire("VARIABLES_LOADED")')
    return lua
