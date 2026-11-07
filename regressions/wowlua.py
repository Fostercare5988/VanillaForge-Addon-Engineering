"""The game's Lua for the regression tests: a lupa Lua 5.1 runtime shaped like
WoW 1.12.1 with ClassicAPI loaded.

Every suite builds its runtime with this module (`from wowlua import LuaRuntime`),
never with `lupa.lua51` directly, so a test cannot pass on Lua the game does not
have. lupa is stock 5.1 with the 5.0 compatibility switches on (`arg`,
`table.getn`, `string.gfind`, `math.mod`), which is close to the game; the
differences that change results are fixed here:

* The base library. Blizzard's is the stock 5.0 set minus `dofile`, `loadfile`
  and `require`, plus `date` and `time`; only the base, string, table and math
  libraries are opened, so there is no `os`, `io`, `debug` or `package`
  (.private/upstream/classicapi/docs/BlizzardScriptAPI.md section 3).
  `coroutine` and `difftime` are ClassicAPI backports (API.md).
* `string.gsub`. A replacement function that returns anything but a string or a
  number removes the match, `nil` and `false` included; stock 5.1 keeps it
  (API.md, "string.gsub replacements"). The global `gsub` and `s:gsub` are the
  same function.
* `table.setn` and `table.getn`. 5.1 throws on `setn`; the game keeps it, and
  `getn` answers an explicit numeric `t.n` first, then the `setn` size
  (CLASSICAPI_MASTER_REFERENCE 4.6).
* The short global aliases. Upstream does not list them (they come from an
  embedded chunk, BlizzardScriptAPI.md section 3), so only aliases FrameXML
  calls as globals are given, plus ClassicAPI's documented `wipe`, `strmatch`
  and `gmatch`. Trigonometry aliases are left out on purpose: the game's take
  degrees.

Not modelled: ClassicAPI's table-length healing (CLASSICAPI_MASTER_REFERENCE
4.6) and the engine's widgets and events (wowkit.py has the shared widget
model). A suite still mocks every game function it calls.
"""
from lupa import lua51

PRELUDE = r'''
date, time, difftime = os.date, os.time, os.difftime
os, io, debug, package = nil, nil, nil, nil
require, module, dofile, loadfile = nil, nil, nil, nil

do
    local stock = string.gsub
    function string.gsub(s, pattern, repl, n)
        if type(repl) == "function" then
            local f = repl
            repl = function(...)
                local v = f(...)
                local kind = type(v)
                if kind == "string" or kind == "number" then return v end
                return ""
            end
        end
        return stock(s, pattern, repl, n)
    end
end

function table.wipe(t)
    for k in pairs(t) do t[k] = nil end
    return t
end

do
    local sizes, length = setmetatable({}, { __mode = "k" }), table.getn
    function table.setn(t, n) sizes[t] = n end
    function table.getn(t)
        local n = rawget(t, "n")
        if type(n) == "number" then return n end
        return sizes[t] or length(t)
    end
end

function getglobal(name) return _G[name] end
function setglobal(name, value) _G[name] = value end

wipe = table.wipe
tinsert, tremove, getn = table.insert, table.remove, table.getn
strfind, strsub, strlen = string.find, string.sub, string.len
strlower, strupper, format, gsub = string.lower, string.upper, string.format, string.gsub
strmatch, gmatch = string.match, string.gmatch
floor, ceil, abs, sqrt, random = math.floor, math.ceil, math.abs, math.sqrt, math.random
max, min, mod = math.max, math.min, math.mod
'''


class LuaRuntime(lua51.LuaRuntime):
    """lupa's LuaRuntime with the game's library. Tuples unpack by default."""

    def __new__(cls, *args, **kwargs):
        kwargs.setdefault("unpack_returned_tuples", True)
        return super().__new__(cls, *args, **kwargs)

    def __init__(self, *args, **kwargs):
        self.execute(PRELUDE)
