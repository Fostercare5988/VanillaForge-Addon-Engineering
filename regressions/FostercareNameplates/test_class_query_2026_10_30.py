"""FostercareNameplates class colors ask about a non-player once (2026-10-30).

An NPC has no class, so the unresolved-identity retry asked UnitIsPlayer again
every 0.5 s for as long as its plate stood. Fails on 1.4.4.
"""
import unittest
from fnp_env import load

SETUP = '''
    plate = nativePlate("0xF1", "nameplate1")
    asked = 0
    function UnitIsPlayer(u) asked = asked + 1; return isPlayer end
    function UnitClass() return "Rogue", "ROGUE" end
    function runSeconds(n) runFrames(plate, n * 60) end
'''


class ClassQuery(unittest.TestCase):
    def asked_over(self, is_player, seconds=5):
        lua = load(prelude='isPlayer = %s' % ("true" if is_player else "nil"))
        lua.execute(SETUP + 'runSeconds(1); asked = 0; runSeconds(%d)' % seconds)
        return lua.eval("asked")

    def test_npc_is_asked_once(self):
        self.assertEqual(self.asked_over(False), 0)

    def test_player_class_is_asked_once(self):
        self.assertEqual(self.asked_over(True), 0)


if __name__ == "__main__":
    unittest.main()
