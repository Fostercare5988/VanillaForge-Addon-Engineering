"""Auto Stance (spec T11, 4.3 GAP): on the client's "Must be in ..." text a
warrior or druid takes the first form it can; nothing on any other text.
"""
import unittest
from ftr_env import load

FORMS = ("forms = { { name = 'Battle Stance', active = 1, castable = 1 }, "
         "{ name = 'Defensive Stance', castable = 1 }, { name = 'Berserker Stance', castable = 1 } }")


class AutoStance(unittest.TestCase):
    def test_the_needed_stance_is_taken(self):
        lua = load(setup=FORMS, cls="WARRIOR")
        lua.execute("fire('UI_ERROR_MESSAGE', 'Must be in Berserker Stance, Defensive Stance')")
        self.assertEqual(lua.eval("last('CastShapeshiftForm')"), 2, "the first one on the bar it names")

    def test_nothing_on_other_text_or_a_part_of_a_name(self):
        lua = load(setup=FORMS, cls="WARRIOR")
        lua.execute("fire('UI_ERROR_MESSAGE', 'Not enough rage')")
        lua.execute("fire('UI_ERROR_MESSAGE', 'Must be in Stance')")
        self.assertEqual(lua.eval("count('CastShapeshiftForm')"), 0)

    def test_off_stops_listening(self):
        lua = load(setup=FORMS, cls="DRUID")
        lua.execute("settingsWindow.use('FostercareTweaks_autoStance', false)")
        self.assertNotIn("UI_ERROR_MESSAGE", lua.eval("listening()"))
        lua.execute("settingsWindow.use('FostercareTweaks_autoStance', true)")
        self.assertIn("UI_ERROR_MESSAGE", lua.eval("listening()"))

    def test_other_classes_never_listen(self):
        lua = load(setup=FORMS, cls="ROGUE")
        lua.execute("settingsWindow.use('FostercareTweaks_autoStance', true)")
        self.assertNotIn("UI_ERROR_MESSAGE", lua.eval("listening()"))


if __name__ == "__main__":
    unittest.main()
