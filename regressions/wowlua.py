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
  `getn` answers an explicit numeric `t.n` first, then the stored size
  (CLASSICAPI_MASTER_REFERENCE 4.6). A stored size whose last slot is empty is
  healed to a border; a stored size of 0 stays 0.
* `table.insert` and `table.remove` count with `getn` and store the new size,
  as Lua 5.0 does; `#` reads a border and ignores the stored size. So a list
  grown with `t[#t + 1]` and shrunk with `table.remove` stops shrinking once
  the stored size reaches 0: `table.remove` then does nothing. Seen in play in
  Mail, 2026-11-17 (MailTrace); KNOWN_PATTERNS KP-65.
* `ipairs`. Lua 5.0's luaB_ipairs has two forms: with one argument the
  `for` loop's, with a second argument (even nil) one step, returning
  `n + 1, t[n + 1]`. So `for _, v in ipairs(f())` breaks when `f` returns two
  values: the loop gets a number as its function ("attempt to call a number
  value"). Seen in play in GearRack, 2026-11-18 (`ipairs(GR.Sets())`).
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
        local stored = sizes[t]
        if stored == nil then return length(t) end
        if stored > 0 and rawget(t, stored) == nil then return length(t) end -- ClassicAPI's healing
        return stored
    end
    local getn = table.getn
    local function setn(t, n) -- luaL_setn: an explicit numeric t.n, else the stored size
        if type(rawget(t, "n")) == "number" then rawset(t, "n", n) else sizes[t] = n end
    end
    -- Lua 5.0's ltablib.c, luaB_tinsert and luaB_tremove.
    function table.insert(t, ...)
        local n = getn(t) + 1
        local pos, value
        if select("#", ...) == 1 then
            pos, value = n, ...
        else
            pos, value = ...
            if pos > n then n = pos end
        end
        setn(t, n)
        for i = n - 1, pos, -1 do rawset(t, i + 1, rawget(t, i)) end
        rawset(t, pos, value)
    end
    function table.remove(t, pos)
        local n = getn(t)
        pos = pos or n
        if n <= 0 then return end
        setn(t, n - 1)
        local value = rawget(t, pos)
        for i = pos, n - 1 do rawset(t, i, rawget(t, i + 1)) end
        rawset(t, n, nil)
        return value
    end
end

do -- Lua 5.0's luaB_ipairs: a second argument makes it the one-step form.
    local loop = ipairs
    function ipairs(t, ...)
        if select("#", ...) == 0 then return loop(t) end
        local n = (tonumber((...)) or 0) + 1
        return n, rawget(t, n)
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
