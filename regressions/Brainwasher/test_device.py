"""The device's menu on screen, the active slot and the four actions (spec 4.6 tests 1-4, 6-8, 10)."""
import unittest
from sp_env import load, CLAUDE_SAVED, BUILD_32_0_19

ROWS = '''
function rowFrame(n)
    local k = 0
    for _, w in ipairs(widgets) do
        if w.parent == SpecsPanel and w.scripts.OnEnter then k = k + 1; if k == n then return w end end
    end
end
function panelButton(text)
    for _, w in ipairs(widgets) do if w.parent == SpecsPanel and w.text == text then return w end end
end
'''


def claude(talents="setBuild(points(41), points(10), {})", saved=None, setup=""):
    lua = load(saved if saved is not None else CLAUDE_SAVED % BUILD_32_0_19, setup=ROWS + setup)
    lua.execute(talents)
    lua.execute("talk(device(CLAUDE))")
    return lua


def active(lua):
    return [bool(lua.eval(f"rowFrame({i}).active:IsShown()")) for i in (1, 2, 3)]


class Panel(unittest.TestCase):
    def test_another_npc_changes_nothing(self):
        lua = load(setup=ROWS)
        lua.execute("talk({ { 1, 'I want to train.' }, { 2, 'Make this inn your home.' } })")
        self.assertIsNone(lua.eval("SpecsPanel"))
        self.assertTrue(lua.eval("GossipGreetingScrollFrame:IsShown()"))

    def test_the_menu_becomes_rows_in_the_gossip_window(self):
        lua = claude()
        self.assertEqual(lua.eval("SpecsPanel:GetParent():GetName()"), "GossipFrame")
        self.assertFalse(lua.eval("GossipGreetingScrollFrame:IsShown()"))
        self.assertEqual(lua.eval("rowFrame(1).name.text"), "PVE ASSA")
        self.assertEqual(lua.eval("rowFrame(2).icon.texture"), "Interface\\Icons\\Ability_Rogue_Garrote")
        # Most points green, fewest blue; the profile after it.
        self.assertEqual(lua.eval("rowFrame(2).summary.text"),
                         "|cff00ff0032|r/|cff0077ff0|r/|cffffff0019|r  Bars: pvp")
        self.assertEqual(lua.eval("rowFrame(4).name.text"), "Buy slot 4 (200g)")
        self.assertEqual(lua.eval("rowFrame(4).icon.texture"), "Interface\\Icons\\INV_Misc_Coin_01")
        self.assertEqual(lua.eval("SpecsPanel.reset.text"), "Reset talents (1g)")

    def test_show_original_brings_the_stock_list_back(self):
        lua = claude()
        lua.execute("click(panelButton('Show original'))")
        self.assertFalse(lua.eval("SpecsPanel:IsShown()"))
        self.assertTrue(lua.eval("GossipGreetingScrollFrame:IsShown()"))

    def test_closing_the_conversation_hides_the_panel_and_our_popups(self):
        lua = claude()
        lua.execute("click(rowFrame(1).button)")
        self.assertTrue(lua.eval("popups.SPECS_LOAD ~= nil"))
        lua.execute("leave()")
        self.assertFalse(lua.eval("SpecsPanel:IsShown()"))
        self.assertIsNone(lua.eval("popups.SPECS_LOAD"))
        self.assertTrue(lua.eval("GossipGreetingScrollFrame:IsShown()"))

    def test_a_slot_without_a_record_shows_its_trees_icon(self):
        lua = load(setup=ROWS)
        lua.execute("talk(device(CLAUDE))")
        self.assertEqual(lua.eval("rowFrame(1).name.text"), "Spec 1")
        self.assertEqual(lua.eval("rowFrame(1).icon.texture"), "Interface\\Icons\\Tree1")
        lua.execute("talk(device({ '0/5/9' }))")
        self.assertEqual(lua.eval("rowFrame(1).icon.texture"), "Interface\\Icons\\Tree3")

    def test_an_activate_line_without_a_split_still_gets_a_row(self):
        lua = load(setup=ROWS)
        lua.execute("talk({ { 21, 'Activate 1st Specialization' }, { 11, 'Save 1st Specialization.' } })")
        self.assertEqual(lua.eval("rowFrame(1).name.text"), "Spec 1")
        self.assertEqual(lua.eval("rowFrame(1).summary.text"), "")
        self.assertEqual(lua.eval("rowFrame(1).icon.texture"), "Interface\\Icons\\INV_Misc_QuestionMark")

    def test_a_long_name_is_cut_by_the_engine_and_whole_in_the_tooltip(self):
        lua = claude(saved='SpecsDB = { [1] = { name = "Assassination for the long fights" } }')
        self.assertEqual(lua.eval("rowFrame(1).name.maxLines"), 1)
        lua.execute("run(rowFrame(1), 'OnEnter')")
        self.assertEqual(lua.eval("GameTooltip.lines[1]"), "Assassination for the long fights")


class Active(unittest.TestCase):
    def test_current_slot_with_its_build_is_the_only_active_one(self):
        lua = claude("setBuild(points(32), {}, points(19))")
        self.assertEqual(active(lua), [False, True, False])

    def test_two_slots_with_one_split_are_told_apart_by_current(self):
        lua = claude(saved='SpecsDB = { current = 3 }')
        self.assertEqual(active(lua), [False, False, True])

    def test_without_current_neither_of_two_equal_splits_is_active(self):
        lua = claude(saved='SpecsDB = {}')
        self.assertEqual(active(lua), [False, False, False])

    def test_a_build_that_differs_from_the_devices_split_is_forgotten(self):
        lua = claude(saved=CLAUDE_SAVED % ("1" * 41 + "-" + "1" * 10 + "-"))
        self.assertIsNone(lua.eval("SpecsDB[2].build"))


class Actions(unittest.TestCase):
    def test_activate_asks_then_picks_the_slots_option(self):
        lua = claude()
        lua.execute("click(rowFrame(1).button)")
        self.assertEqual(lua.eval("popups.SPECS_LOAD.text"), "Activate PVE ASSA? This causes a brainwasher debuff.")
        self.assertEqual(lua.eval("#selected"), 0)
        lua.execute("accept('SPECS_LOAD')")
        self.assertEqual(lua.eval("selected[1]"), 21)

    def test_the_active_slot_says_so_and_picks_nothing(self):
        lua = claude("setBuild(points(32), {}, points(19))")
        lua.execute("click(rowFrame(2).button)")
        self.assertIsNone(lua.eval("popups.SPECS_LOAD"))
        self.assertIn("PVP ASSA is already active.", lua.eval("say()"))

    def test_a_popup_of_an_older_menu_picks_nothing(self):
        lua = claude()
        lua.execute("click(rowFrame(1).button); old = popups.SPECS_LOAD")
        lua.execute("talk(device(CLAUDE))")
        lua.execute("popups.SPECS_LOAD = old; accept('SPECS_LOAD')")
        self.assertEqual(lua.eval("#selected"), 0)

    def test_save_names_what_it_replaces_and_records_the_build(self):
        lua = claude()
        lua.execute("click(rowFrame(1).save)")
        self.assertEqual(lua.eval("popups.SPECS_SAVE.text"),
                         "Save your current talents to PVE ASSA, replacing what it holds?")
        lua.execute("accept('SPECS_SAVE')")
        self.assertEqual(lua.eval("selected[1]"), 11)
        self.assertEqual(lua.eval("SpecsDB[1].build"), "1" * 41 + "-" + "1" * 10 + "-")
        self.assertEqual(lua.eval("SpecsDB.current"), 1)
        self.assertEqual(active(lua), [True, False, False])

    def test_buy_and_reset_ask_with_the_price_from_the_menu(self):
        lua = claude()
        lua.execute("click(rowFrame(4).button)")
        self.assertEqual(lua.eval("popups.SPECS_BUY.text"), "Buy talent slot 4 for 200 gold?")
        lua.execute("accept('SPECS_BUY')")
        self.assertEqual(lua.eval("selected[1]"), 34)
        lua.execute("click(SpecsPanel.reset)")
        self.assertEqual(lua.eval("popups.SPECS_RESET.text"), "Reset all your talents for 1g? This causes a debuff.")
        lua.execute("accept('SPECS_RESET')")
        self.assertEqual(lua.eval("selected[2]"), 90)

    def test_bars_that_no_longer_exist_show_missing_and_are_not_loaded(self):
        lua = claude(setup="profiles = { 'Niko' }")
        self.assertIn("Bars: |cffff4d4dmissing|r", lua.eval("rowFrame(1).summary.text"))
        lua.execute("click(rowFrame(1).button); accept('SPECS_LOAD')")
        self.assertIn('Action bar profile "PVE" no longer exists', lua.eval("say()"))
        lua.execute("setBuild(points(8), {}, points(43)); fire('CHARACTER_POINTS_CHANGED'); step(2)")
        self.assertEqual(lua.eval("#barsLoaded"), 0)

    def test_without_actionbars_no_bars_text_no_entry_and_no_call(self):
        lua = claude(setup="ActionBars = nil")
        self.assertEqual(lua.eval("rowFrame(2).summary.text"), "|cff00ff0032|r/|cff0077ff0|r/|cffffff0019|r")
        lua.execute("click(rowFrame(1).button); accept('SPECS_LOAD')")
        lua.execute("setBuild(points(8), {}, points(43)); fire('CHARACTER_POINTS_CHANGED'); step(2)")
        self.assertEqual(lua.eval("SpecsDB.current"), 1)
        lua.execute("click(rowFrame(1).edit)")
        self.assertIsNone(lua.eval("menu:item('Action bars')"))


if __name__ == "__main__":
    unittest.main()
