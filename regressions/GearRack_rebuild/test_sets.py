"""Sets and the panel (spec 4.5 tests 6 and 7), and the character window
(test 8)."""
import unittest
from gr_env import load

# Two sets: the bag daggers (weapons only) and a head-and-weapons set.
SETS = '''
local function only(slots) local t = {} for s = 1, 19 do t[s] = slots[s] or "ignored" end return t end
makeSet("Instant", "INV_I", only({ [16] = "0xD", [17] = "0xE" }))
makeSet("PVP no stealth", "INV_P", only({ [1] = "0x17", [16] = "0xD" }))
'''


def panel_rows(lua):
    return lua.eval('''(function() local t = {} for _, w in ipairs(widgets) do
        if w.parent == GearRackSetsPanel and w.id and w.shown and w.setName then t[#t + 1] = w.text.text end
        end return table.concat(t, ",") end)()''')


class Sets(unittest.TestCase):
    def test_out_of_combat_the_set_is_used(self):
        lua = load(setup=SETS)
        lua.execute("SlashCmdList.GEARRACK('equip PVP no stealth')")
        self.assertEqual(lua.eval("usedSets[1]"), "PVP no stealth")
        self.assertEqual(lua.eval("worn[1]"), "0x17")

    def test_an_unknown_name_says_so(self):
        lua = load(setup=SETS)
        lua.execute("SlashCmdList.GEARRACK('equip Nope')")
        self.assertIsNone(lua.eval("usedSets[1]"))
        self.assertIn('No set is named "Nope"', lua.eval("chatText()"))

    def test_in_combat_the_rest_follows_after_combat(self):
        lua = load(setup=SETS + "combat = true")
        lua.execute("GearRack.EquipSet('PVP no stealth') step(0)")
        self.assertEqual(lua.eval("worn[16]"), "0xD")
        self.assertEqual(lua.eval("worn[1]"), "0x16")
        self.assertIn("follows when combat ends", lua.eval("chatText()"))
        lua.execute("combat = false fire('PLAYER_REGEN_ENABLED') step(0)")
        self.assertEqual(lua.eval("worn[1]"), "0x17")
        self.assertEqual(lua.eval("#usedSets"), 2)

    def test_a_weapons_only_set_in_combat_needs_no_second_go(self):
        lua = load(setup=SETS + "combat = true")
        lua.execute("GearRack.EquipSet('Instant') step(0) combat = false fire('PLAYER_REGEN_ENABLED')")
        self.assertEqual(lua.eval("#usedSets"), 1)
        self.assertNotIn("follows", lua.eval("chatText()"))

    def test_an_action_bar_set_button_in_combat_is_finished_after_it(self):
        lua = load(setup=SETS + "combat = true")
        lua.execute("fire('WEAR_EQUIPMENT_SET', 2) combat = false fire('PLAYER_REGEN_ENABLED')")
        self.assertEqual(lua.eval("usedSets[1]"), "PVP no stealth")

    def test_dead_the_set_waits_until_alive(self):
        lua = load(setup=SETS + "dead = true")
        lua.execute("GearRack.EquipSet('Instant')")
        self.assertIsNone(lua.eval("usedSets[1]"))
        lua.execute("dead = false fire('PLAYER_UNGHOST')")
        self.assertEqual(lua.eval("usedSets[1]"), "Instant")


class Panel(unittest.TestCase):
    def open(self, setup=SETS):
        lua = load(setup=setup)
        lua.execute("GR_open = SlashCmdList.GEARRACK ToggleCharacter() GearRackSheetButton:Show() click(GearRackSheetButton)")
        self.assertTrue(lua.eval("GearRackSetsPanel:IsShown()"))
        return lua

    def test_the_sets_by_name(self):
        lua = self.open()
        self.assertEqual(panel_rows(lua), "Instant,PVP no stealth")

    def test_save_with_a_new_name_leaves_out_the_unticked_slots(self):
        lua = self.open()
        lua.execute("CharacterHeadSlot_tick = nil")
        lua.execute('''for _, w in ipairs(widgets) do
            if w.template == "UICheckButtonTemplate" and w.parent == CharacterHeadSlot then w:SetChecked(nil) end end''')
        lua.execute('GearRackSetName:SetText("Tank")')
        lua.execute('for _, w in ipairs(widgets) do if w.template == "UIPanelButtonTemplate" and w.text == "Save" then click(w) end end')
        lua.execute('id = C_EquipmentSet.GetEquipmentSetID("Tank")')
        self.assertEqual(lua.eval("sets[id].slots[1]"), "ignored")
        self.assertEqual(lua.eval("sets[id].slots[16]"), "0xA")
        self.assertIsNone(lua.eval("next(ignoreForSave)"), "the ignore state is cleared again")
        self.assertEqual(panel_rows(lua), "Instant,PVP no stealth,Tank")

    def test_save_over_a_set_keeps_its_slots_and_takes_the_icon(self):
        lua = self.open()
        lua.execute('for _, w in ipairs(widgets) do if w.parent == GearRackSetsPanel and w.id == 1 then click(w) end end')
        self.assertEqual(lua.eval("GearRackSetName.text"), "Instant")
        lua.execute('''for _, w in ipairs(widgets) do
            if w.template == "UICheckButtonTemplate" then assert(w:GetChecked() == ((w.parent == CharacterMainHandSlot
            or w.parent == CharacterSecondaryHandSlot) and 1 or nil)) end end''')
        lua.execute('for _, w in ipairs(widgets) do if w.template == "UIPanelButtonTemplate" and w.text == "Save" then click(w) end end')
        self.assertEqual(lua.eval("sets[1].slots[16]"), "0xA")
        self.assertEqual(lua.eval("sets[1].slots[1]"), "ignored")
        self.assertEqual(lua.eval("sets[1].icon"), "INV_I")
        self.assertEqual(lua.eval("#setOrder"), 2)

    def test_delete_asks_first(self):
        lua = self.open()
        lua.execute('for _, w in ipairs(widgets) do if w.parent == GearRackSetsPanel and w.id == 2 then click(w) end end')
        lua.execute('for _, w in ipairs(widgets) do if w.template == "UIPanelButtonTemplate" and w.text == "Delete" then click(w) end end')
        self.assertEqual(lua.eval("popup.text"), 'Delete the set "PVP no stealth"?')
        self.assertIsNotNone(lua.eval("sets[2]"))
        lua.execute("accept() step(0)")
        self.assertIsNone(lua.eval("sets[2]"))
        self.assertEqual(panel_rows(lua), "Instant")

    def test_a_row_drags_the_set(self):
        lua = self.open()
        lua.execute('for _, w in ipairs(widgets) do if w.parent == GearRackSetsPanel and w.id == 2 then run(w, "OnDragStart") end end')
        self.assertEqual(lua.eval("cursorSet"), "PVP no stealth")

    def test_a_long_name_is_refused_before_the_call(self):
        lua = self.open()
        lua.execute('GearRackSetName:SetText(string.rep("x", 32))')
        lua.execute('for _, w in ipairs(widgets) do if w.template == "UIPanelButtonTemplate" and w.text == "Save" then click(w) end end')
        self.assertIn("up to 31 letters", lua.eval("chatText()"))
        self.assertEqual(lua.eval("#setOrder"), 2)

    def test_the_picker_lists_the_worn_icons_first(self):
        lua = self.open()
        lua.execute('''for _, w in ipairs(widgets) do if w.parent == GearRackSetsPanel and w.kind == "Button"
            and w.texture then run(w, "OnClick") end end''')
        lua.execute('''first = nil for _, w in ipairs(widgets) do
            if w.parent and w.parent.parent == GearRackSetsPanel and w.icon and not first then first = w end end''')
        self.assertEqual(lua.eval("first.icon"), "icon:Headband")
        lua.execute("click(first)")
        lua.execute('GearRackSetName:SetText("New") for _, w in ipairs(widgets) do if w.template == "UIPanelButtonTemplate" and w.text == "Save" then click(w) end end')
        self.assertEqual(lua.eval('sets[C_EquipmentSet.GetEquipmentSetID("New")].icon'), "icon:Headband")


class Sheet(unittest.TestCase):
    def test_hovering_a_slot_opens_its_menu_and_leaving_closes_it(self):
        lua = load()
        lua.execute("ToggleCharacter() hover(CharacterFinger0Slot)")
        self.assertEqual(lua.eval("menuItems()"), "0x15,off")
        reads = lua.eval("calls.forSlot")
        lua.execute("this = CharacterFinger0Slot PaperDollItemSlotButton_OnEnter() this = nil")  # again each frame while it owns the tooltip
        self.assertEqual(lua.eval("calls.forSlot"), reads)
        lua.execute("leave(CharacterFinger0Slot)")
        self.assertFalse(lua.eval("GearRackMenu:IsShown()"))

    def test_alt_shows_the_overlays_and_alt_click_adds_or_removes_a_slot(self):
        lua = load()
        lua.execute("press('lalt')")
        self.assertIsNone(lua.eval("next(GearRackGearBar) and nil"))
        lua.execute("ToggleCharacter() press('ralt')")
        lua.execute('''for _, w in ipairs(widgets) do
            if w.parent == CharacterBackSlot and w.tint then back = w end
            if w.parent == CharacterMainHandSlot and w.tint then main = w end end''')
        self.assertTrue(lua.eval("back:IsVisible()"))
        self.assertEqual(lua.eval("main.tint.color[1]"), 0.2)  # on the bar
        lua.execute("click(back)")
        self.assertEqual(lua.eval("GearRackDB.slots[4]"), 15)
        self.assertEqual(lua.eval("GearRackGearBar:GetWidth()"), 5 * 40 - 4)
        lua.execute("click(main)")
        self.assertEqual(lua.eval("GearRackDB.slots[1]"), 17)
        lua.execute("press()")
        self.assertFalse(lua.eval("back:IsShown()"))

    def test_nothing_happens_with_the_window_closed(self):
        lua = load()
        lua.execute("press('lalt')")
        self.assertFalse(lua.eval('''(function() for _, w in ipairs(widgets) do
            if w.tint and w.shown then return true end end return false end)()'''))


if __name__ == "__main__":
    unittest.main()
