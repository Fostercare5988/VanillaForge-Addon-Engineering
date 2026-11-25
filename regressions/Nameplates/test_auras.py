"""Auras on enemies (spec 4.6, test 9): the first crowd control from anyone, then up
to three of your own debuffs, with the game's countdown numbers. Nameplates 1.0,
written new 2026-11-22.
"""
import unittest
from np_env import load, ENEMY_ROGUE, FRIEND

ICONS = "__addon_ns.byToken.nameplate1.auras.icons"
SIX = """{
    { id = 11, icon = 'own1', mine = true, duration = 12, expires = 110 },
    { id = 12, icon = 'other', duration = 30, expires = 120 },
    { id = 13, icon = 'own2', mine = true, duration = 18, expires = 115 },
    { id = 14, icon = 'gouge', cc = true, duration = 4, expires = 103 },
    { id = 15, icon = 'own3', mine = true },
    { id = 16, icon = 'own4', mine = true, duration = 10, expires = 108 },
}"""


def icons(lua):
    return [lua.eval(f"{ICONS}[{i}].icon") if lua.eval(f"{ICONS}[{i}]:IsShown()") else None for i in range(1, 5)]


def enemy(lua, auras=SIX, d=ENEMY_ROGUE):
    lua.execute(f"d = {d}; d.auras = {auras}; show('nameplate1', d)")


class Auras(unittest.TestCase):
    def test_the_cc_first_then_three_of_yours(self):
        lua = load()
        enemy(lua)
        self.assertEqual(icons(lua), ["gouge", "own1", "own2", "own3"])
        self.assertEqual((lua.eval(f"{ICONS}[1].cd.cdStart"), lua.eval(f"{ICONS}[1].cd.cdDuration")), (99, 4))
        self.assertIsNone(lua.eval(f"{ICONS}[4].cd.cdStart"))  # until cancelled: no timer

    def test_a_cc_of_your_own_is_shown_once(self):
        lua = load()
        enemy(lua, "{ { id = 21, icon = 'sap', mine = true, cc = true, duration = 45, expires = 140 },"
                   " { id = 22, icon = 'own', mine = true, duration = 10, expires = 108 } }")
        self.assertEqual(icons(lua), ["sap", "own", None, None])

    def test_a_friendly_unit_shows_none(self):
        lua = load()
        enemy(lua, d=FRIEND)
        self.assertEqual(icons(lua), [None, None, None, None])

    def test_no_icon_or_run_out_is_skipped(self):
        lua = load()
        enemy(lua, "{ { id = 1, mine = true, duration = 10, expires = 108 },"
                   " { id = 2, icon = 'gone', mine = true, duration = 10, expires = 90 },"
                   " { id = 3, icon = 'live', mine = true, duration = 10, expires = 108 } }")
        self.assertEqual(icons(lua), ["live", None, None, None])

    def test_a_delta_that_changes_nothing_shown_writes_nothing(self):
        lua = load()
        enemy(lua)
        lua.execute("forget(); table.insert(units.nameplate1.auras, { id = 30, icon = 'x', duration = 5, expires = 104 });"
                    " fire('UNIT_AURA_DELTA', 'nameplate1')")
        self.assertEqual(lua.eval("count('SetCooldown')"), 0)
        self.assertEqual(icons(lua), ["gouge", "own1", "own2", "own3"])

    def test_a_refresh_of_a_shown_aura_restarts_its_timer(self):
        lua = load()
        enemy(lua)
        lua.execute("now = 102; units.nameplate1.auras[1].expires = 117; fire('UNIT_AURA_DELTA', 'nameplate1')")
        self.assertEqual(lua.eval(f"{ICONS}[2].cd.cdStart"), 105)

    def test_the_end_of_a_timer_redraws_the_row(self):
        lua = load()
        enemy(lua)
        lua.execute("now = 104; table.remove(units.nameplate1.auras, 4);"
                    f" local cd = {ICONS}[1].cd; cd:GetScript('OnCooldownDone')(cd)")
        self.assertEqual(icons(lua), ["own1", "own2", "own3", None])

    def test_switched_off_none_and_no_event(self):
        lua = load()
        enemy(lua)
        lua.execute("settingsWindow.use('Nameplates_auras', false)")
        self.assertEqual(icons(lua), [None, None, None, None])
        self.assertNotIn("UNIT_AURA_DELTA", lua.eval("listening()"))


if __name__ == "__main__":
    unittest.main()
