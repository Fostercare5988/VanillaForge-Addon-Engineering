"""The Edit menu: rename, icon, action bars (spec 4.6 test 9)."""
import unittest
from test_device import claude


def edit(lua, slot=1):
    lua.execute(f"click(rowFrame({slot}).edit)")


class Edit(unittest.TestCase):
    def test_the_menu_has_rename_icon_and_the_action_bars_list(self):
        lua = claude()
        edit(lua, 2)
        self.assertEqual(lua.eval("menu.items[1].text"), "PVP ASSA")
        self.assertEqual([lua.eval(f"menu.items[{i}].text") for i in (2, 3, 4)], ["Rename", "Icon", "Action bars"])
        # None, then every profile in ActionBars' order.
        self.assertEqual([lua.eval(f"menu:item('Action bars').items[{i}].text") for i in (1, 2, 3, 4)],
                         ["None", "PVE", "pvp", "pveBWL"])
        self.assertTrue(lua.eval("menu:item('Action bars').items[3].isOn()"))
        self.assertFalse(lua.eval("menu:item('Action bars').items[2].isOn()"))

    def test_choosing_a_profile_or_none_is_saved_and_shown(self):
        lua = claude()
        edit(lua)
        lua.execute("menu:item('Action bars').items[4].f()")
        self.assertEqual(lua.eval("BrainwasherDB[1].bars"), "pveBWL")
        self.assertIn("Bars: pveBWL", lua.eval("rowFrame(1).summary.text"))
        lua.execute("menu:item('Action bars').items[1].f()")
        self.assertIsNone(lua.eval("BrainwasherDB[1].bars"))
        self.assertEqual(lua.eval("rowFrame(1).summary.text"), "|cff00ff0041|r/|cffffff0010|r/|cff0077ff0|r")

    def test_rename_asks_with_the_name_and_saves_up_to_twenty_letters(self):
        lua = claude()
        edit(lua)
        lua.execute("menu:item('Rename').f()")
        self.assertEqual(lua.eval("StaticPopupDialogs.BRAINWASHER_RENAME.maxLetters"), 20)
        self.assertEqual(lua.eval("popups.BRAINWASHER_RENAME.box.text"), "PVE ASSA")
        lua.execute("enter('BRAINWASHER_RENAME', 'Burst')")
        self.assertEqual(lua.eval("BrainwasherDB[1].name"), "Burst")
        self.assertEqual(lua.eval("rowFrame(1).name.text"), "Burst")

    def test_rename_with_accept_and_an_empty_name_changes_nothing(self):
        lua = claude()
        edit(lua)
        lua.execute("menu:item('Rename').f(); popups.BRAINWASHER_RENAME.box:SetText('')")
        lua.execute("accept('BRAINWASHER_RENAME')")
        self.assertEqual(lua.eval("BrainwasherDB[1].name"), "PVE ASSA")
        lua.execute("menu:item('Rename').f(); popups.BRAINWASHER_RENAME.box:SetText('Opener')")
        lua.execute("accept('BRAINWASHER_RENAME')")
        self.assertEqual(lua.eval("BrainwasherDB[1].name"), "Opener")

    def test_a_slot_never_edited_gets_a_record_when_renamed(self):
        lua = claude(saved="")
        edit(lua, 3)
        lua.execute("menu:item('Rename').f(); popups.BRAINWASHER_RENAME.box:SetText('Raid')")
        lua.execute("accept('BRAINWASHER_RENAME')")
        self.assertEqual(lua.eval("BrainwasherDB[3].name"), "Raid")
        self.assertEqual(lua.eval("rowFrame(3).name.text"), "Raid")

    def test_the_picker_leads_with_the_spellbook_and_saves_the_chosen_icon(self):
        lua = claude()
        edit(lua)
        lua.execute("menu:item('Icon').f()")
        self.assertTrue(lua.eval("BrainwasherPicker:IsShown()"))
        self.assertEqual(lua.eval("BrainwasherPicker.buttons[2].path"), "Interface\\Icons\\Book2")
        lua.execute("click(BrainwasherPicker.buttons[3])")
        self.assertEqual(lua.eval("BrainwasherDB[1].icon"), "Interface\\Icons\\Book3")
        self.assertEqual(lua.eval("rowFrame(1).icon.texture"), "Interface\\Icons\\Book3")
        self.assertFalse(lua.eval("BrainwasherPicker:IsShown()"))
        self.assertEqual(lua.eval("released"), 1)

    def test_the_mouse_wheel_moves_the_picker_a_row_and_stops_at_the_end(self):
        lua = claude()
        edit(lua)
        lua.execute("menu:item('Icon').f()")
        lua.execute("run(BrainwasherPicker, 'OnMouseWheel', -1)")
        self.assertEqual(lua.eval("BrainwasherPicker.buttons[1].path"), "INTERFACE\\ICONS\\Base7")
        lua.execute("for i = 1, 200 do run(BrainwasherPicker, 'OnMouseWheel', -1) end")
        self.assertEqual(lua.eval("BrainwasherPicker.first"), 503 - 36 + 1)
        lua.execute("for i = 1, 200 do run(BrainwasherPicker, 'OnMouseWheel', 1) end")
        self.assertEqual(lua.eval("BrainwasherPicker.first"), 1)

    def test_closing_the_picker_releases_the_icons(self):
        lua = claude()
        edit(lua)
        lua.execute("menu:item('Icon').f()")
        lua.execute("BrainwasherPicker:Hide()")
        self.assertEqual(lua.eval("released"), 1)


if __name__ == "__main__":
    unittest.main()
