"""Saving the 120 slots under a name (spec K1, K3, K10; tests 1 and 2)."""
import unittest
from fb_env import load, profiles


class Save(unittest.TestCase):
    def test_spells_items_macros_and_sets_are_read_from_the_slots(self):
        lua = load(setup='''
            macros[3] = { name = 'Kick', body = '/cast Kick' }
            sets[7] = 'PvP'
            bars[1] = { kind = 'spell', id = 11305 }
            bars[2] = { kind = 'item', id = 13446 }
            bars[3] = { kind = 'macro', id = 3 }
            bars[120] = { kind = 'equipmentset', id = 'PvP' }
        ''')
        lua.execute("StaticPopup_Show('ACTIONBARS_NEW') accept('PVP')")
        a = "ActionBarsDB.profiles.PVP.actions"
        self.assertEqual(lua.eval(f"{a}[1].kind .. ' ' .. {a}[1].id"), "spell 11305")
        self.assertEqual(lua.eval(f"{a}[2].kind .. ' ' .. {a}[2].id"), "item 13446")
        self.assertEqual(lua.eval(f"{a}[3].name .. '|' .. {a}[3].body"), "Kick|/cast Kick")
        self.assertIsNone(lua.eval(f"{a}[3].id"), "a macro's index moves, so it is not saved")
        self.assertEqual(lua.eval(f"{a}[120].kind .. ' ' .. {a}[120].name"), "equipmentset PvP")
        self.assertIsNone(lua.eval(f"{a}[4]"), "an empty slot is not saved")
        self.assertIsNone(lua.eval(f"{a}[1].name"), "names are read from the game for chat")
        self.assertIn('Saved "PVP".', lua.eval("chatText()"))

    def test_the_same_name_saves_over_it_and_case_tells_names_apart(self):
        lua = load(setup="bars[1] = { kind = 'spell', id = 1 }")
        lua.execute('''
            StaticPopup_Show('ACTIONBARS_NEW') accept('PVP')
            bars[1] = { kind = 'spell', id = 2 }
            StaticPopup_Show('ACTIONBARS_NEW') accept('  pvp ')
            bars[1] = { kind = 'spell', id = 3 }
            StaticPopup_Show('ACTIONBARS_NEW') pressEnter('PVP')
        ''')
        self.assertEqual(profiles(lua), ["PVP", "pvp"])
        self.assertEqual(lua.eval("ActionBarsDB.profiles.PVP.actions[1].id"), 3)
        self.assertEqual(lua.eval("ActionBarsDB.profiles.pvp.actions[1].id"), 2)
        self.assertIn('Saved over "PVP".', lua.eval("chatText()"))
        self.assertFalse(lua.eval("popupShown()"), "Enter saves and closes the popup")

    def test_an_empty_name_is_refused_and_the_popup_stays(self):
        lua = load()
        lua.execute("StaticPopup_Show('ACTIONBARS_NEW') accept('   ')")
        self.assertEqual(profiles(lua), [])
        self.assertEqual(lua.eval("popupShown()"), "ACTIONBARS_NEW")
        self.assertIn("A profile needs a name.", lua.eval("chatText()"))


if __name__ == "__main__":
    unittest.main()
