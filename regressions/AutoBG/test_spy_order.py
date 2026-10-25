"""Spy order in crowds: newest on top, no churn when full, still under the mouse.

2026-10-25, Blackrock Mountain with many enemies: the list kept jumping. With
20 enemies tracked, each newcomer pushed out the bottom one even while still in
view, which came straight back on top and pushed out the next. The complete
AutoBG_Spy.lua runs with the Spy Nearby mocks; the feel stays an in-game check.
"""
import unittest

from test_spy_nearby import FLUSH, advance, runtime as spy_runtime

EXTRA = r'''
hidden = {}
function UnitIsVisible(u) return visible and not hidden[u] end
function guidOf(i) return string.format("0x%016X", 100 + i) end
function meet(i)
    local guid = guidOf(i)
    names[guid] = "Enemy" .. i
    AutoBG_Spy:RecordEnemy("Enemy" .. i, "WARRIOR", 60, guid, 100, nil, nil, "Orc")
end
function rowNames()
    local t = {}
    for i = 1, 5 do t[i] = _G["AutoBG_SpyRow" .. i].targetName end
    return table.concat(t, ",")
end
'''


def runtime():
    lua = spy_runtime()
    lua.execute(EXTRA)
    return lua


def fill(lua):
    """Grom plus Enemy1..Enemy19: twenty enemies, all in view."""
    for i in range(1, 20):
        lua.execute('meet(%d)' % i)
    lua.execute(FLUSH)


class SpyOrderTests(unittest.TestCase):
    def test_newest_enemy_is_on_top(self):
        lua = runtime()
        lua.execute('meet(1); ' + FLUSH)
        self.assertEqual(lua.eval('AutoBG_SpyRow1.targetName'), "Enemy1")
        self.assertEqual(lua.eval('AutoBG_SpyRow2.targetName'), "Grom")

    def test_full_list_keeps_enemies_in_view(self):
        lua = runtime()
        fill(lua)
        before = lua.eval('rowNames()')
        for i in range(20, 26):
            lua.execute('meet(%d)' % i)
        lua.execute(FLUSH)
        advance(lua, 2)
        self.assertEqual(lua.eval('rowNames()'), before)

    def test_full_list_replaces_an_enemy_gone_from_view(self):
        lua = runtime()
        fill(lua)
        lua.execute('hidden["0x0000000000000001"] = true')  # Grom walks away
        advance(lua, 7)
        lua.execute('meet(20); ' + FLUSH)
        self.assertEqual(lua.eval('AutoBG_SpyRow1.targetName'), "Enemy20")
        names = [lua.eval('_G["AutoBG_SpyRow%d"].targetName' % i) for i in range(1, 6)]
        self.assertNotIn("Grom", names)

    def test_rows_hold_still_under_the_mouse(self):
        lua = runtime()
        lua.execute('AutoBG_SpyRow1.scripts.OnEnter(AutoBG_SpyRow1)')
        lua.execute('meet(1); ' + FLUSH)
        self.assertEqual(lua.eval('AutoBG_SpyRow1.targetName'), "Grom")
        lua.execute('AutoBG_SpyRow1.scripts.OnLeave(AutoBG_SpyRow1); ' + FLUSH)
        self.assertEqual(lua.eval('AutoBG_SpyRow1.targetName'), "Enemy1")

    def test_enemy_who_left_dims_under_the_mouse(self):
        lua = runtime()
        lua.execute('AutoBG_SpyRow1.scripts.OnEnter(AutoBG_SpyRow1)')
        lua.execute('visible = false')
        advance(lua, 35)  # past the 30 s timeout
        self.assertEqual(lua.eval('AutoBG_SpyRow1.targetName'), "Grom")
        self.assertEqual(lua.eval('AutoBG_SpyRow1.alpha'), 0.45)


if __name__ == '__main__':
    unittest.main()
