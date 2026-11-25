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


WINDOW = r'''
function rows() local t = {} for _, w in ipairs(widgets) do
    if w.parent == GearRackSetsWindow and w.setName and w.shown then t[#t + 1] = w.text.text end
    end return table.concat(t, ",") end
function windowButton(text) for _, w in ipairs(widgets) do
    if w.parent == GearRackSetsWindow and w.template == "UIPanelButtonTemplate" and w.text == text then return w end end end
function slotButton(slot) for _, w in ipairs(widgets) do
    if w.parent == GearRackSetsWindow and w.slot == slot and w.way then return w end end end
function row(name) for _, w in ipairs(widgets) do
    if w.parent == GearRackSetsWindow and w.setName == name and w.shown then return w end end end
'''


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


class Window(unittest.TestCase):
    """K17 and K22: the Gear sets window."""
    def open(self, setup=SETS, saved=""):
        lua = load(setup=setup, saved=saved)
        lua.execute(WINDOW)
        lua.execute("SlashCmdList.GEARRACK('sets')")
        self.assertTrue(lua.eval("GearRackSetsWindow:IsShown()"))
        return lua

    def test_every_way_in_opens_it(self):
        lua = load(setup=SETS)
        for way in ("click(GearRackSets)", "click(GearRackMinimapGear)", "SlashCmdList.GEARRACK('sets')",
                    ):
            lua.execute(way)
            self.assertTrue(lua.eval("GearRackSetsWindow:IsShown()"), way)
            lua.execute("GearRackSetsWindow:Hide()")
        self.assertIn("GearRackSetsWindow", lua.eval("table.concat(UISpecialFrames, ',')"), "Escape closes it")
        lua.execute("click(GearRackMinimapGear, 'RightButton')")
        self.assertEqual(lua.eval("settingsWindow.opened.name"), "GearRack")

    def test_twenty_slots_and_the_sets_by_name(self):
        lua = self.open()
        self.assertEqual(lua.eval("rows()"), "Instant,PVP no stealth")
        n = lua.eval("(function() local n = 0 for s = 0, 19 do if slotButton(s) then n = n + 1 end end return n end)()")
        self.assertEqual(n, 20)
        self.assertEqual(lua.eval("slotButton(1).icon.texture"), "icon:Headband")
        self.assertEqual(lua.eval("slotButton(4).icon.texture"), "slotTex:ShirtSlot", "the shirt, empty")

    def test_the_worn_set_is_shown_at_opening_and_its_buttons_work(self):
        lua = self.open(SETS + 'wear(16, "0xD") carry(0, 1, "0xA") wear(17, "0xE") carry(0, 2, "0xB")')
        self.assertEqual(lua.eval("GearRackSetName.text"), "Instant")
        self.assertTrue(lua.eval("windowButton('Equip'):IsEnabled()"))
        self.assertTrue(lua.eval("windowButton('Delete'):IsEnabled()"))
        self.assertIsNone(lua.eval("slotButton(16).icon.desaturated"), "the set saves the weapons")
        self.assertTrue(lua.eval("slotButton(1).icon.desaturated"), "and leaves the head out")

    def test_equip_and_delete_follow_the_name(self):
        lua = self.open()
        self.assertEqual(lua.eval("GearRackSetName.text or ''"), "")
        self.assertFalse(lua.eval("windowButton('Equip'):IsEnabled()"))
        self.assertFalse(lua.eval("windowButton('Save'):IsEnabled()"))
        lua.execute('GearRackSetName:SetText("PVP no stealth") run(GearRackSetName, "OnTextChanged")')
        self.assertTrue(lua.eval("windowButton('Equip'):IsEnabled()"))
        self.assertTrue(lua.eval("windowButton('Save'):IsEnabled()"))
        lua.execute("click(windowButton('Equip'))")
        self.assertEqual(lua.eval("usedSets[1]"), "PVP no stealth")

    def test_save_with_a_new_name_leaves_out_the_dark_slots(self):
        lua = self.open()
        lua.execute("click(slotButton(1))")  # the head goes dark
        self.assertTrue(lua.eval("slotButton(1).icon.desaturated"))
        lua.execute('GearRackSetName:SetText("Tank") click(windowButton("Save"))')
        lua.execute('id = C_EquipmentSet.GetEquipmentSetID("Tank")')
        self.assertEqual(lua.eval("sets[id].slots[1]"), "ignored")
        self.assertEqual(lua.eval("sets[id].slots[16]"), "0xA")
        self.assertIsNone(lua.eval("next(ignoreForSave)"), "the ignore state is cleared again")
        self.assertEqual(lua.eval("rows()"), "Instant,PVP no stealth,Tank")

    def test_save_over_a_set_keeps_its_slots_and_takes_the_icon(self):
        lua = self.open()
        lua.execute("click(row('Instant')) step(0)")
        self.assertEqual(lua.eval("GearRackSetName.text"), "Instant")
        self.assertEqual(lua.eval("worn[16]"), "0xD", "a click on a set puts it on, as 1.x did")
        for slot in range(1, 20):
            self.assertEqual(bool(lua.eval(f"slotButton({slot}).icon.desaturated")), slot not in (16, 17), slot)
        lua.execute("click(windowButton('Save'))")
        self.assertEqual(lua.eval("sets[1].slots[16]"), "0xD")
        self.assertEqual(lua.eval("sets[1].slots[1]"), "ignored")
        self.assertEqual(lua.eval("sets[1].icon"), "INV_I")
        self.assertEqual(lua.eval("#setOrder"), 2)

    def test_the_ammo_is_saved_with_the_set_and_put_on_after_it(self):
        lua = self.open(SETS + 'item("0x30", 3030, "Jagged Arrow", "INVTYPE_AMMO", 1) wear(0, "0x30")'
                        ' item("0x31", 3031, "Rough Arrow", "INVTYPE_AMMO", 1) carry(2, 1, "0x31")')
        self.assertEqual(lua.eval("slotButton(0).icon.texture"), "icon:Jagged Arrow")
        lua.execute('GearRackSetName:SetText("Hunt") click(windowButton("Save"))')
        self.assertEqual(lua.eval("GearRackDB.ammo.Hunt"), 3030)
        lua.execute('click(row("Instant")) click(slotButton(0))')  # Instant held no ammo: lit again now
        self.assertIsNone(lua.eval("slotButton(0).icon.desaturated"))
        lua.execute("click(slotButton(0)) click(windowButton('Save'))")
        self.assertIsNone(lua.eval("GearRackDB.ammo.Instant"))
        lua.execute('bags[2][1] = "0x30" worn[0] = "0x31" GearRack.EquipSet("Hunt")')
        self.assertEqual(lua.eval("worn[0]"), "0x30", "the set's arrows go on after it")
        lua.execute('click(row("Hunt")) click(windowButton("Delete")) accept() step(0)')
        self.assertIsNone(lua.eval("GearRackDB.ammo.Hunt"), "a deleted set's ammo goes with it")

    def test_hovering_a_slot_opens_its_menu_away_from_the_window(self):
        lua = self.open()
        lua.execute("hover(slotButton(11))")  # a ring, in the right column
        self.assertEqual(lua.eval("menuItems()"), "0x15,off")
        self.assertEqual(lua.eval("(select(3, GearRackMenu:GetPoint(1)))"), "TOPRIGHT")
        self.assertTrue(lua.eval("GameTooltip.owner == slotButton(11)"))
        lua.execute("pick('0x15')")
        self.assertEqual(lua.eval("worn[11]"), "0x15", "the menu puts the item on")
        lua.execute("leave(slotButton(11)) hover(slotButton(0))")
        self.assertFalse(lua.eval("GearRackMenu:IsShown()"), "the ammo has no menu")

    def test_delete_asks_first(self):
        lua = self.open()
        lua.execute("click(row('PVP no stealth')) click(windowButton('Delete'))")
        self.assertEqual(lua.eval("popup.text"), 'Delete the set "PVP no stealth"?')
        self.assertIsNotNone(lua.eval("sets[2]"))
        lua.execute("accept() step(0)")
        self.assertIsNone(lua.eval("sets[2]"))
        self.assertEqual(lua.eval("rows()"), "Instant")

    def test_a_row_drags_the_set(self):
        lua = self.open()
        lua.execute('run(row("PVP no stealth"), "OnDragStart")')
        self.assertEqual(lua.eval("cursorSet"), "PVP no stealth")

    def test_a_long_name_is_refused_before_the_call(self):
        lua = self.open()
        lua.execute('GearRackSetName:SetText(string.rep("x", 32)) click(windowButton("Save"))')
        self.assertIn("up to 31 letters", lua.eval("chatText()"))
        self.assertEqual(lua.eval("#setOrder"), 2)

    def test_the_picker_lists_the_worn_icons_first(self):
        lua = self.open()
        lua.execute('''for _, w in ipairs(widgets) do if w.parent == GearRackSetsWindow and w.kind == "Button"
            and w.texture and not w.slot and not w.template then run(w, "OnClick") end end''')
        lua.execute('''first = nil for _, w in ipairs(widgets) do
            if w.parent and w.parent.parent == GearRackSetsWindow and w.icon and not first then first = w end end''')
        self.assertEqual(lua.eval("first.icon"), "icon:Headband")
        lua.execute("click(first)")
        lua.execute('GearRackSetName:SetText("New") click(windowButton("Save"))')
        self.assertEqual(lua.eval('sets[C_EquipmentSet.GetEquipmentSetID("New")].icon'), "icon:Headband")

    def test_a_long_list_scrolls_with_the_wheel(self):
        lua = self.open(SETS + 'for i = 1, 14 do makeSet("Z" .. string.format("%02d", i), "INV_Z", {}) end')
        self.assertEqual(lua.eval("select(2, string.gsub(rows(), ',', ''))") + 1, 13)
        lua.execute('for i = 1, 5 do run(GearRackSetsWindow, "OnMouseWheel", -1) end')  # three steps to the end
        self.assertIn("Z14", lua.eval("rows()"))
        self.assertNotIn("Instant", lua.eval("rows()"))

    def test_the_ammo_of_a_gone_set_is_cleared_at_login_but_not_before_sets_are_read(self):
        lua = load(setup=SETS, saved="GearRackDB = { ammo = { Instant = 2512, Gone = 2512 } }")
        self.assertEqual(lua.eval("GearRackDB.ammo.Instant"), 2512)
        self.assertIsNone(lua.eval("GearRackDB.ammo.Gone"))
        lua = load(saved="GearRackDB = { ammo = { Gone = 2512 } }")
        self.assertEqual(lua.eval("GearRackDB.ammo.Gone"), 2512, "no sets read: nothing is cleared")

    def test_nothing_changes_by_itself_while_it_shows(self):
        lua = self.open(saved="GearRackDB = { auto = true, when = { mounted = 'Instant' } }")
        lua.execute("player.mounted = true fire('PLAYER_MOUNT_DISPLAY_CHANGED') step(0)")
        self.assertIsNone(lua.eval("usedSets[1]"))


class Current(unittest.TestCase):
    """From the second play (2026-11-18): the set the bar names, New, hidden sets."""
    FULL = SETS + ('makeSet("PVE", "INV_PVE", { [1] = "0x16", [11] = "0x14", [13] = "0x11", [14] = "0x12",'
                   ' [15] = "0x18", [16] = "0xA", [17] = "0xB", [18] = "0xC" })')

    def test_the_sets_button_names_the_set_put_on_by_hand_not_a_weapons_set(self):
        # Instant (the two bag daggers) and PVE are both worn after PVE goes on.
        lua = load(setup=self.FULL + ' sets[1].slots[16], sets[1].slots[17] = "0xA", "0xB"')
        lua.execute("step(0)")
        self.assertEqual(lua.eval("GearRackSets.label.text"), "PVE", "the worn set with the most slots")
        lua.execute("GearRack.EquipSet('PVP no stealth') step(0)")
        self.assertEqual(lua.eval("GearRackDB.current"), "PVP no stealth")
        self.assertEqual(lua.eval("GearRackSets.label.text"), "PVP no stealth")
        self.assertEqual(lua.eval("GearRackSets.icon.texture"), "Interface\\Icons\\INV_P")
        lua.execute("wear(1, '0x16') carry(0, 5, '0x17') wear(16, '0xA') carry(0, 1, '0xD')"
                    " fire('PLAYER_EQUIPMENT_CHANGED', 1) step(0)")
        self.assertEqual(lua.eval("GearRackSets.label.text"), "PVE", "another set is worn whole now")

    def test_a_set_for_a_target_leaves_the_name_alone(self):
        lua = load(setup=self.FULL, saved="GearRackDB = { byTarget = true, current = 'PVE', target = { other = 'Instant' } }")
        lua.execute("target.enemy, target.kind = true, 'Humanoid' fire('PLAYER_TARGET_CHANGED') step(0.25) step(0)")
        self.assertEqual(lua.eval("usedSets[1]"), "Instant")
        self.assertEqual(lua.eval("GearRackDB.current"), "PVE")
        self.assertEqual(lua.eval("GearRackSets.label.text"), "PVE")
        self.assertEqual(lua.eval("GearRackSets.label.color[1]"), 0.6, "grey: PVE is not all worn now")

    def test_the_window_opens_on_that_set(self):
        lua = load(setup=self.FULL)
        lua.execute(WINDOW)
        lua.execute("GearRack.EquipSet('PVP no stealth') step(0) click(GearRackSets)")
        self.assertEqual(lua.eval("GearRackSetName.text"), "PVP no stealth")

    def test_new_lights_every_slot_and_empties_the_name(self):
        lua = load(setup=self.FULL)
        lua.execute(WINDOW)
        lua.execute("click(GearRackSets) click(row('Instant'))")
        self.assertTrue(lua.eval("slotButton(1).out:IsShown()"), "a slot left out has the red cross")
        lua.execute("click(windowButton('New'))")
        self.assertEqual(lua.eval("GearRackSetName.text"), "")
        for slot in range(0, 20):
            self.assertFalse(lua.eval(f"slotButton({slot}).out:IsShown()"), slot)
        lua.execute('GearRackSetName:SetText("Fresh") click(windowButton("Save"))')
        self.assertEqual(lua.eval('sets[C_EquipmentSet.GetEquipmentSetID("Fresh")].slots[1]'), "0x16")

    def test_a_hidden_set_is_out_of_the_menu_unless_alt_is_held(self):
        lua = load(setup=self.FULL)
        lua.execute(WINDOW)
        lua.execute("click(GearRackSets) click(row('Instant'))")
        lua.execute("for _, w in ipairs(widgets) do if w.label and w.label.text and string.find(w.label.text, '^Hide')"
                    " and w.parent == GearRackSetsWindow then hideBox = w end end hideBox:SetChecked(1) click(hideBox)")
        self.assertTrue(lua.eval("GearRackDB.hidden.Instant"))
        lua.execute("GearRackSetsWindow:Hide() hover(GearRackSets)")
        self.assertEqual(lua.eval("menuItems()"), "set:PVE,set:PVP no stealth")
        lua.execute("leave(GearRackSets) press('lalt') hover(GearRackSets)")
        self.assertEqual(lua.eval("menuItems()"), "set:Instant,set:PVE,set:PVP no stealth")
        lua.execute("press() leave(GearRackSets) click(GearRackSets) click(row('Instant'))"
                    " click(windowButton('Delete')) accept() step(0)")
        self.assertIsNone(lua.eval("GearRackDB.hidden.Instant"), "a deleted set's mark goes with it")


class SecondPlay(unittest.TestCase):
    """The third screenshot (2026-11-18)."""
    def test_twenty_of_twenty_with_no_ammo_worn_stays_lit(self):
        lua = load(setup=SETS)
        lua.execute(WINDOW)
        lua.execute('SlashCmdList.GEARRACK("sets") click(windowButton("New")) GearRackSetName:SetText("All") click(windowButton("Save"))')
        self.assertEqual(lua.eval("GearRackDB.ammo.All"), 0, "the ammo slot is saved, empty")
        self.assertFalse(lua.eval("slotButton(0).out:IsShown()"), "no red cross after Save")
        lua.execute('GearRack.EquipSet("All") step(0)')
        self.assertNotIn(">nil", lua.eval("table.concat(equips, ',')"), "no ammo to put on")

    def test_the_set_list_has_no_worn_ticks(self):
        lua = load(setup=SETS)
        lua.execute(WINDOW)
        lua.execute('SlashCmdList.GEARRACK("sets")')
        n = lua.eval("(function() local n = 0 for _, w in ipairs(widgets) do"
                     " if type(w.texture) == 'string' and string.find(w.texture, 'CheckBox%-Check') then n = n + 1 end end return n end)()")
        self.assertEqual(n, 0)

    def test_no_button_of_ours_on_the_character_window(self):
        lua = load()
        self.assertIsNone(lua.eval("GearRackSheetButton"))
        n = lua.eval("(function() local n = 0 for _, w in ipairs(widgets) do"
                     " if w.parent == PaperDollFrame and w.kind == 'Button' and not string.find(w.name or '', '^Character') then"
                     " n = n + 1 end end return n end)()")
        self.assertEqual(n, 0)

    def test_the_sets_menu_has_no_item_colours_left_over(self):
        lua = load(setup=SETS)
        lua.execute("hover(GearRackGear16) leave(GearRackGear16) hover(GearRackSets)")
        self.assertEqual(lua.eval("menuItems()"), "set:Instant,set:PVP no stealth")
        for i in (1, 2):
            self.assertEqual(lua.eval(f"menuButton({i}).edge.border[1]"), 0, i)
            self.assertIsNone(lua.eval(f"menuButton({i}).cooldown.cd"), i)

    def test_a_trinket_slot_anywhere_is_left_upper_right_lower(self):
        lua = load()
        lua.execute(WINDOW)
        lua.execute("ToggleCharacter() hover(CharacterTrinket1Slot)")
        self.assertEqual(lua.eval("menuItems()"), "0x13", "the bag trinkets")
        lua.execute("pick('0x13')")
        self.assertEqual(lua.eval("worn[13]"), "0x13", "left-click on the lower slot's menu: the upper slot")
        lua.execute("leave(CharacterTrinket1Slot) SlashCmdList.GEARRACK('sets') hover(slotButton(13))")
        lua.execute("pick('0x11', 'RightButton')")
        self.assertEqual(lua.eval("worn[14]"), "0x11", "right-click on the upper slot's menu: the lower slot")


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

    def test_a_slot_with_nothing_to_offer_reads_the_bags_once_not_each_frame(self):
        lua = load()
        lua.execute("ToggleCharacter() hover(CharacterTabardSlot)")
        self.assertFalse(lua.eval("GearRackMenu:IsShown()"), "no tabard worn or carried")
        reads = lua.eval("calls.forSlot")
        for _ in range(3):  # the slot's OnUpdate, while it owns the tooltip (PaperDollFrame.lua:750)
            lua.execute("this = CharacterTabardSlot PaperDollItemSlotButton_OnEnter() this = nil")
        self.assertEqual(lua.eval("calls.forSlot"), reads)

    def test_alt_click_adds_a_slot_at_the_end_or_takes_it_off(self):
        lua = load()
        lua.execute("ToggleCharacter() press('lalt') click(CharacterBackSlot)")
        self.assertEqual(lua.eval("GearRackDB.slots[4]"), 15)
        self.assertEqual(lua.eval("GearRackGearBar:GetWidth()"), 6 * 40 - 4)
        self.assertIn("is on the gear bar", lua.eval("chatText()"))
        lua.execute("press('ralt') click(CharacterMainHandSlot)")
        self.assertEqual(lua.eval("GearRackDB.slots[1]"), 17)
        self.assertIn("is off the gear bar", lua.eval("chatText()"))
        self.assertIsNone(lua.eval("stockClicks[1]"), "an Alt+click never picks the item up")

    def test_a_click_without_alt_is_the_slots_own(self):
        lua = load()
        lua.execute("ToggleCharacter() press() click(CharacterBackSlot, 'RightButton')")
        self.assertEqual(lua.eval("stockClicks[1]"), "15:RightButton")
        self.assertEqual(lua.eval("#GearRackDB.slots"), 3)

    def test_character_menus_open_right_and_the_weapons_down(self):
        lua = load()
        for slot, point in (("Head", "TOPLEFT"), ("Finger0", "TOPLEFT"), ("MainHand", "TOPLEFT")):
            lua.execute(f"hover(Character{slot}Slot)")
            self.assertEqual(lua.eval("(select(3, GearRackMenu:GetPoint(1)))"),
                             "BOTTOMLEFT" if slot == "MainHand" else "TOPRIGHT", slot)
            lua.execute(f"leave(Character{slot}Slot)")

if __name__ == "__main__":
    unittest.main()
