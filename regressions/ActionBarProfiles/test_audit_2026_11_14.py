"""Audit 2026-11-14: deleting from the menu, and the paths moved onto
ClassicAPI (GetActionInfo, FindSpellBookSlotByID, C_Item). Mocks only;
native placement stays an in-game check.
"""
import unittest
from abp_env import load

TWO = '''
    ABP_Layout['Player of Realm'] = {{profileName = 'PVE', actions = {}}, {profileName = 'pvp', actions = {}}}
    ToggleDropDownMenu(2, 'ABP_DELETE', ABP_DropDownMenu)
'''


def names(lua):
    return list(lua.eval("ABP_GetProfileNames()").values())


class Delete(unittest.TestCase):
    def test_menu_delete_asks_first(self):
        """One click in the Delete submenu removed the profile, with nothing to
        stop a slip; BrainwasherPro specs linked to it then lost their bars."""
        lua = load()
        lua.execute(TWO + "choose(2, 'pvp')")
        self.assertEqual(names(lua), ["PVE", "pvp"])
        self.assertTrue(lua.eval("popups.ABP_DeleteProfile ~= nil"))
        lua.execute("accept('ABP_DeleteProfile')")
        self.assertEqual(names(lua), ["PVE"])
        self.assertIn('"pvp" removed', lua.eval("chatText()"))

    def test_kept_slash_delete_needs_no_popup(self):
        lua = load()
        lua.execute(TWO + "SlashCmdList.ABP('delete pvp')")
        self.assertEqual(names(lua), ["PVE"])


class SaveAndLoad(unittest.TestCase):
    def test_save_reads_every_kind_from_the_slot(self):
        lua = load()
        lua.execute('''
            learn(10, 'Wanted', 'Rank 1')
            macros[3] = {name = 'Garrote', body = '/cast Garrote'}
            sets[7] = 'PVP'
            bars[1] = {kind='SPELL', id=10}; bars[2] = {kind='ITEM', id=13452}
            bars[3] = {kind='MACRO', id=3}; bars[4] = {kind='EQUIPMENTSET', name='PVP'}
            SlashCmdList.ABP('save Bars')
            saved = ABP_Layout['Player of Realm'][1].actions
        ''')
        self.assertEqual(lua.eval("saved[1].kind .. saved[1].id .. saved[1].name"), "SPELL10Wanted")
        self.assertEqual(lua.eval("saved[2].kind .. saved[2].id"), "ITEM13452")
        self.assertEqual(lua.eval("saved[3].kind .. saved[3].id .. saved[3].body"), "MACRO3/cast Garrote")
        self.assertEqual(lua.eval("saved[4].kind .. saved[4].name"), "EQUIPMENTSETPVP")
        self.assertIsNone(lua.eval("saved[1].rank"), "nothing reads the rank")
        self.assertIsNone(lua.eval("saved[2].link"), "nothing reads the link")

    def test_profile_restores_every_kind(self):
        lua = load()
        lua.execute('''
            learn(10, 'Wanted', 'Rank 1')
            macros[5] = {name = 'Garrote', body = '/cast Garrote'}
            sets[7] = 'PVP'
            equipment[13] = {id = 18820}; bags[0] = {{id = 13452}}
            profile({[1] = {kind='SPELL', id=10, name='Wanted'},
                     [2] = {kind='ITEM', id=13452, name='Elixir'},
                     [3] = {kind='MACRO', id=3, name='Garrote', body='/cast Garrote'},
                     [4] = {kind='EQUIPMENTSET', name='PVP'},
                     [5] = {kind='ITEM', id=18820, name='Talisman'}})
            ok = ABP_LoadProfileByName('Test')
        ''')
        self.assertTrue(lua.eval("ok"), lua.eval("chatText()"))
        self.assertEqual(lua.eval("bars[1].id"), 10)
        self.assertEqual(lua.eval("bars[2].id"), 13452)
        self.assertEqual(lua.eval("bars[3].id"), 5, "the macro is found by name and text")
        self.assertEqual(lua.eval("bars[4].name"), "PVP")
        self.assertEqual(lua.eval("bars[5].id"), 18820, "an equipped item counts")

    def test_saved_fields_nothing_reads_are_cleared_on_load(self):
        lua = load('''ABP_LayoutVersion = 4
            ABP_Layout = {['Player of Realm'] = {{profileName = 'Old', actions = {
                [1] = {kind='SPELL', id=10, name='Wanted', rank='Rank 1'},
                [2] = {kind='ITEM', id=5, name='Thing', link='|Hitem:5|h'}}}}}''')
        self.assertIsNone(lua.eval("ABP_Layout['Player of Realm'][1].actions[1].rank"))
        self.assertIsNone(lua.eval("ABP_Layout['Player of Realm'][1].actions[2].link"))
        self.assertEqual(lua.eval("ABP_Layout['Player of Realm'][1].actions[1].name"), "Wanted")


if __name__ == "__main__":
    unittest.main()
