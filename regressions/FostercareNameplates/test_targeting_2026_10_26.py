"""FostercareNameplates "Targeting you" label, from play on 2026-10-26.

The player's screenshot (AV, Commander Randolph): the plate said "Targeting
you" while the target-of-target frame showed the commander on another player.
The label is computed when the plate gets its unit and then waits for
UNIT_TARGET, which 1.12 does not have: no FrameXML file registers it, the stock
target-of-target frame polls in OnUpdate (TargetFrame.lua), and no DLL doc
adds it. So the label keeps whatever was true when the plate appeared.
Fails on 1.4.2. Whether ClassicAPI knows the event stays an in-game check:
/run print(C_EventUtils.IsEventValid("UNIT_TARGET"))
"""
import unittest
from fnp_env import load

TARGETING = '{ overwrites = { nameplate_targeting = 1 } }'
# A creature's target, keyed by the "<guid>target" token Targeting asks for.
PRELUDE = '''
    targets = {}
    function UnitIsUnit(a, b) return b == "player" and targets[a] or false end
'''


class TargetingYou(unittest.TestCase):
    def test_label_clears_when_the_enemy_turns_away(self):
        lua = load(TARGETING, PRELUDE)
        lua.execute('targets["0xF1target"] = true; plate = nativePlate("0xF1", "nameplate1")')
        self.assertTrue(lua.eval('plate.fnpTargeting and plate.fnpTargeting.shown'))
        lua.execute('targets["0xF1target"] = false; runFrames(plate, 60)')
        self.assertFalse(lua.eval('plate.fnpTargeting.shown'), "label still up a second after the enemy turned away")

    def test_label_shows_when_the_enemy_turns_to_you(self):
        lua = load(TARGETING, PRELUDE)
        lua.execute('plate = nativePlate("0xF1", "nameplate1")')
        lua.execute('targets["0xF1target"] = true; runFrames(plate, 60)')
        self.assertTrue(lua.eval('plate.fnpTargeting and plate.fnpTargeting.shown'),
                        "no label a second after the enemy targeted you")

    def test_off_setting_asks_nothing(self):
        lua = load(None, PRELUDE + '''
            asked = 0
            function UnitIsUnit() asked = asked + 1 end
        ''')
        lua.execute('plate = nativePlate("0xF1", "nameplate1"); runFrames(plate, 120)')
        self.assertEqual(lua.eval('asked'), 0)


if __name__ == "__main__":
    unittest.main()
