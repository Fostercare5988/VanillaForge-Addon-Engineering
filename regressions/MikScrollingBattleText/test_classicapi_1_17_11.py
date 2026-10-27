"""ClassicAPI 1.17.11 pass, 2026-10-27: health and mana triggers take unit
events only for the units that have triggers (player, pet, target; mana for
the player). Other tokens, such as nameplates and raid members, never reach Lua.
"""
import unittest

import _msbt_runtime as m


class UnitEventScopeTests(unittest.TestCase):
    def test_health_and_mana_events_are_unit_filtered(self):
        l = m.runtime()
        l.execute('MikCEH.RegisterEvents()')
        self.assertEqual(list(l.eval('MCEHEventFrame.events.UNIT_HEALTH').values()), ["player", "pet", "target"])
        self.assertEqual(list(l.eval('MCEHEventFrame.events.UNIT_MANA').values()), ["player"])

    def test_nameplate_health_never_reaches_the_handler(self):
        l = m.runtime()
        l.execute('''
            MikCEH.RegisterEvents()
            reached = false
            local h = MCEHEventFrame.scripts.OnEvent
            MCEHEventFrame.scripts.OnEvent = function(...) if event == "UNIT_HEALTH" then reached = true end return h(...) end
            Fire("UNIT_HEALTH", "nameplate1")
        ''')
        self.assertFalse(l.eval('reached'))


if __name__ == "__main__":
    unittest.main()
