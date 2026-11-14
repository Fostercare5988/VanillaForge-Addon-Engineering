"""Paths moved in the 2026-11-14 rewrite that had no test: FostercareTweaks'
extra rows (called directly now, no pcall), a placement that fails part way,
and the minimap button made in Lua instead of XML. Mocks only.
"""
import unittest
from abp_env import load

TWEAKS = '''
    applied = nil
    FostercareTweaks = { ExtraActions = {
        ProfileVersion = 1,
        GetProfile = function() return { version = 1, rows = { [2] = { [1] = { kind = 'spell', id = 10 } } } } end,
        ValidateProfile = function(_, profile) return profile end,
        ApplyProfile = function(_, profile) applied = profile; return true end,
    } }
'''


class ExtraRows(unittest.TestCase):
    def test_extra_rows_are_saved_and_restored(self):
        lua = load(TWEAKS)
        lua.execute("SlashCmdList.ABP('save Rows'); ABP_LoadProfileByName('Rows')")
        self.assertEqual(lua.eval("ABP_Layout['Player of Realm'][1].fostercareTweaks.rows[2][1].id"), 10)
        self.assertEqual(lua.eval("applied.rows[2][1].id"), 10)
        self.assertIn("Extra Rows 2-7 restored", lua.eval("chatText()"))

    def test_profile_with_extra_rows_needs_fostercaretweaks(self):
        lua = load(TWEAKS)
        lua.execute("SlashCmdList.ABP('save Rows'); FostercareTweaks = nil")
        lua.execute("bars[1] = {kind='SPELL', id=99}; ok = ABP_LoadProfileByName('Rows')")
        self.assertFalse(lua.eval("ok"))
        self.assertEqual(lua.eval("bars[1].id"), 99, "bars are left as they are")
        lua.execute("SlashCmdList.ABP('save Rows')")
        self.assertIsNotNone(lua.eval("ABP_Layout['Player of Realm'][1].fostercareTweaks"),
                             "saving again without FostercareTweaks would lose the rows")


class FailedPlacement(unittest.TestCase):
    def test_load_stops_and_restores_the_failed_slot(self):
        lua = load()
        lua.execute('''
            learn(10, 'Wanted', 'Rank 1'); learn(20, 'Before', 'Rank 1')
            bars[2] = {kind='SPELL', id=20}
            profile({[2] = {kind='SPELL', id=10, name='Wanted'}})
            failPlacement = true
            ok = ABP_LoadProfileByName('Test')
        ''')
        self.assertFalse(lua.eval("ok"))
        self.assertEqual(lua.eval("bars[2] and bars[2].id"), 20)
        self.assertIn("That slot was restored", lua.eval("chatText()"))
        self.assertEqual(lua.eval("cvars.autoSelfCast"), "1", "self-cast is put back")


class MinimapButton(unittest.TestCase):
    def test_right_drag_moves_and_saves_the_button(self):
        lua = load()
        self.assertEqual(lua.eval("ABP_ButtonPosition"), 60)
        lua.execute('''
            cursorX, cursorY = 0, 400
            run(ActionBarProfiles_IconFrame, 'OnDragStart')
            moved = ABP_ButtonPosition
            run(ActionBarProfiles_IconFrame, 'OnDragStop')
        ''')
        self.assertNotEqual(lua.eval("moved"), 60)
        self.assertIsNone(lua.eval("ActionBarProfiles_IconFrame.scripts.OnUpdate"), "no per-frame work after the drag")

    def test_click_opens_the_menu(self):
        lua = load("ABP_Layout = {['Player of Realm'] = {{profileName = 'PVE', actions = {}}}}")
        lua.execute("run(ActionBarProfiles_IconFrame, 'OnClick')")
        self.assertIn("PVE", [b["text"] for b in lua.eval("menu[1]").values()])


if __name__ == "__main__":
    unittest.main()
