"""FostercareNameplates garbage on the per-frame and event paths (audit 2026-10-26).

Lupa is Lua 5.1. In the client's Lua 5.0 every call of a function with `...` in
its parameter list builds an `arg` table (ClassicAPI docs, GetAuraSlots fill
form). The per-plate OnUpdate wrapper and the event wrappers are such functions:
a 40-plate AV scene measured about 320 KB/s at 60 fps from OnUpdate alone. These
tests give each vararg function the table 5.0 builds, in memory only.
Event bursts also built a flags table per queued plate and a new pending table
per flush. Fails on 1.4.2. The real rate stays an in-game /lag check.
"""
import re
import unittest
from lupa.lua51 import LuaRuntime
import fnp_env

# One shared no-op: an __index returning a fresh `function() end` is fake garbage.
BASE = fnp_env.BASE.replace('local Widget = {}', 'local Widget = {}\nlocal NOOP = function() end').replace(
    'if string.find(k, "^%u") then return function() end end', 'if string.find(k, "^%u") then return NOOP end')
VARARG = re.compile(r'(function\b[\w.:\s]*\(([^()]*)\.\.\.\))')
SCENE = '''
    local queue, n = {}, 0
    C_Timer.After = function(_, f) n = n + 1; queue[n] = f end
    local function pump() local k = n; n = 0; for i = 1, k do local f = queue[i]; queue[i] = nil; f() end end
    plates = {}
    for i = 1, 10 do plates[i] = nativePlate(string.format("0xF%02d", i), "nameplate" .. i) end
    local tokens = {}
    for i = 1, 10 do tokens[i] = "nameplate" .. i end
    function run(frames, busy)
        local done = 0
        for f = 1, frames do
            now = now + 1 / 60
            pump()
            for i = 1, 10 do local p = plates[i]; p.scripts.OnUpdate(p, 1 / 60) end
            if busy then for k = 1, 4 do fire("UNIT_HEALTH", tokens[math.mod(f * 4 + k, 10) + 1]) end end
        end
    end
    function garbage(frames, busy)
        run(30, busy)
        collectgarbage("collect"); collectgarbage("stop")
        local before = collectgarbage("count")
        run(frames, busy)
        local kb = collectgarbage("count") - before
        collectgarbage("restart")
        return kb
    end
'''


def load(lua50):
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(BASE)
    lua.execute("FostercareNameplates_Config = { overwrites = { nameplate_health_target = 0 } }")
    ns = lua.table()
    for name in fnp_env.FILES:
        source = (fnp_env.ROOT / name).read_text("utf-8-sig")
        if lua50:
            source = VARARG.sub(lambda m: m.group(1) + ' local __arg = { n = select("#", ...), ... };', source)
        lua.execute(source, "FostercareNameplates", ns)
    lua.execute('fire("VARIABLES_LOADED")')
    lua.execute(SCENE)
    return lua


class Garbage(unittest.TestCase):
    def test_plate_frames_build_no_tables_in_lua50(self):
        """10 plates, 60 frames: 600 OnUpdate calls."""
        kb = load(lua50=True).eval("garbage(60, false)")
        self.assertLess(kb, 2, "%.1f KB for 600 plate frames" % kb)

    def test_health_bursts_build_no_tables(self):
        """Four UNIT_HEALTH a frame for a second, coalesced into one flush a frame."""
        kb = load(lua50=False).eval("garbage(60, true)")
        self.assertLess(kb, 4, "%.1f KB for a second of health events" % kb)


if __name__ == "__main__":
    unittest.main()
