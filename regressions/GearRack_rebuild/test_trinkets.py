"""The trinkets (GearRack.md 7, K18-K21): the automatic swap by TrinketMenu's
rules, the Trinkets window, the drawer, the trinket buttons' clicks and mark,
the minimap buttons; and the gear bar's slot list (KP-65)."""
import unittest
from gr_env import load

# Insignia (1008) is worn in the upper slot, Arena Grand Master (1009) in the
# lower, Hand of Justice (1010) is in the bags (GEAR). Earthstrike (1020) has a use.
TRINKETS = '''
items["0x11"].use, items["0x11"].spell = true, "Insignia"
item("0x40", 1020, "Earthstrike", "INVTYPE_TRINKET", 4, { use = true, spell = "Earthstrike" }); carry(2, 2, "0x40")
'''


def switch_on(lua, slot=13):
    lua.execute(f"press('lalt') click(GearRackTrinket{slot}) press() step(0)")


class Queue(unittest.TestCase):
    def start(self, upper, stats="{}", setup=""):
        lua = load(setup=TRINKETS + setup,
                   saved=f"GearRackDB = {{ trinkets = {stats}, queue = {{ [13] = {{ on = false, list = {{ {upper} }} }} }} }}")
        switch_on(lua)
        self.assertTrue(lua.eval("GearRackDB.queue[13].on"))
        return lua

    def test_a_ready_worn_trinket_stays_unless_the_other_is_high_priority(self):
        lua = self.start("1020, 1008, 0")
        self.assertEqual(lua.eval("worn[13]"), "0x11")
        lua = self.start("1020, 1008, 0", stats="{ [1020] = { priority = true } }")
        self.assertEqual(lua.eval("worn[13]"), "0x40")
        self.assertTrue(lua.eval("GearRackDB.queue[13].on"), "a swap of the queue's own leaves it on")

    def test_a_used_trinket_is_replaced_by_the_first_ready_one_above_the_line(self):
        lua = self.start("1008, 1010, 1020, 0")
        lua.execute("cooldowns['0x11'] = { now, 300 } step(1.5) fire('BAG_UPDATE_COOLDOWN') step(0)")
        self.assertEqual(lua.eval("worn[13]"), "0x13", "Hand of Justice has no use, so it is ready")

    def test_nothing_below_the_stop_line_goes_on(self):
        lua = self.start("1008, 0, 1020")
        lua.execute("cooldowns['0x11'] = { now, 300 } step(1.5) fire('BAG_UPDATE_COOLDOWN') step(0)")
        self.assertEqual(lua.eval("worn[13]"), "0x11")

    def test_the_swap_delay_keeps_it_on_then_one_timer_swaps(self):
        lua = self.start("1020, 1008, 0", stats="{ [1008] = { delay = 20 } }")
        lua.execute("cooldowns['0x11'] = { now, 300 } fire('BAG_UPDATE_COOLDOWN') step(0) step(10)")
        self.assertEqual(lua.eval("worn[13]"), "0x11")
        self.assertEqual(lua.eval("GearRackTrinket13.queue.desaturated"), True, "the mark is grey while it holds")
        self.assertEqual(lua.eval("tickers()"), 0)
        lua.execute("step(10.1) step(0)")
        self.assertEqual(lua.eval("worn[13]"), "0x40")

    def test_its_own_buff_keeps_it_on_until_the_buff_ends(self):
        lua = self.start("1020, 1008, 0")
        lua.execute("cooldowns['0x11'] = { now, 300 } player.auras.Insignia = true step(2) fire('BAG_UPDATE_COOLDOWN') step(0)")
        self.assertEqual(lua.eval("worn[13]"), "0x11")
        self.assertIn("UNIT_AURA", lua.eval("allEvents()"))
        lua.execute("player.auras.Insignia = nil fire('UNIT_AURA', 'player') step(0)")
        self.assertEqual(lua.eval("worn[13]"), "0x40")
        self.assertNotIn("UNIT_AURA", lua.eval("allEvents()"))

    def test_pause_while_worn(self):
        lua = self.start("1020, 1008, 0", stats="{ [1008] = { pause = true } }")
        lua.execute("cooldowns['0x11'] = { now, 300 } step(2) fire('BAG_UPDATE_COOLDOWN') step(0)")
        self.assertEqual(lua.eval("worn[13]"), "0x11")

    def test_not_in_combat_nor_while_casting(self):
        lua = self.start("1020, 1008, 0")
        lua.execute("combat = true cooldowns['0x11'] = { now, 300 } step(2) fire('BAG_UPDATE_COOLDOWN') step(0)")
        self.assertEqual(lua.eval("worn[13]"), "0x11")
        lua.execute("combat = false casting = now + 2 fire('PLAYER_REGEN_ENABLED') step(0)")
        self.assertEqual(lua.eval("worn[13]"), "0x11", "a cast runs")
        lua.execute("casting = nil step(2.2) step(0)")
        self.assertEqual(lua.eval("worn[13]"), "0x40", "at the cast's end")

    def test_it_wakes_when_a_listed_trinket_gets_ready(self):
        lua = self.start("1020, 1008, 0", setup="cooldowns['0x40'] = { 100, 120 }")
        lua.execute("cooldowns['0x11'] = { now, 300 } step(2) fire('BAG_UPDATE_COOLDOWN') step(0)")
        self.assertEqual(lua.eval("worn[13]"), "0x11", "Earthstrike has 118 s left")
        lua.execute("step(87) step(0)")
        self.assertEqual(lua.eval("worn[13]"), "0x11")
        lua.execute("step(2) step(0)")  # 30 s left: ready enough
        self.assertEqual(lua.eval("worn[13]"), "0x40")

    def test_an_empty_slot_is_filled(self):
        lua = self.start("1020, 0", setup="worn[13] = nil carry(3, 1, '0x11')")
        self.assertEqual(lua.eval("worn[13]"), "0x40")

    def test_a_choice_by_hand_turns_it_off(self):
        lua = self.start("1020, 1008, 0")
        lua.execute("hover(GearRackTrinket13) pick('0x13')")
        self.assertEqual(lua.eval("worn[13]"), "0x13")
        self.assertFalse(lua.eval("GearRackDB.queue[13].on"))
        self.assertIn("Alt-click the trinket", lua.eval("chatText()"))
        self.assertFalse(lua.eval("GearRackTrinket13.queue:IsShown()"))

    def test_a_set_by_hand_turns_off_the_slots_it_holds_a_situation_does_not(self):
        sets = ('makeSet("All", "INV_A", { [13] = "0x11", [14] = "0x12" }) '
                'local w = {} for s = 1, 19 do w[s] = "ignored" end w[16] = "0xA" makeSet("Weapons", "INV_W", w)')
        lua = self.start("1008, 0", setup=sets)
        lua.execute("GearRack.EquipSet('Weapons') step(0)")
        self.assertTrue(lua.eval("GearRackDB.queue[13].on"))
        lua.execute("GearRack.EquipSet('All') step(0)")
        self.assertFalse(lua.eval("GearRackDB.queue[13].on"))
        lua = self.start("1008, 0", setup=sets)
        lua.execute("settingsWindow.use('GearRack_auto', true) settingsWindow.use('GearRack_when_mounted', 'All')")
        lua.execute("player.mounted = true fire('PLAYER_MOUNT_DISPLAY_CHANGED') step(0) step(0)")
        self.assertEqual(lua.eval("usedSets[1]"), "All")
        self.assertTrue(lua.eval("GearRackDB.queue[13].on"))

    def test_off_it_listens_to_nothing(self):
        lua = self.start("1020, 1008, 0")
        on = lua.eval("allEvents()")
        self.assertIn("BAG_UPDATE_COOLDOWN", on)
        switch_on(lua)  # Alt-click again: off
        self.assertFalse(lua.eval("GearRackDB.queue[13].on"))
        off = lua.eval("allEvents()")
        self.assertEqual(on.count("PLAYER_ALIVE"), 1)
        self.assertNotIn("PLAYER_ALIVE", off)
        self.assertEqual(lua.eval("timerCount()"), 0)


class Window(unittest.TestCase):
    TOOLS = r'''
    function trow(i) local n = 0 for _, w in ipairs(widgets) do
        if w.parent == GearRackTrinkets and w.index and w.shown then n = n + 1 if n == i then return w end end end end
    function tlist() local t = {} for _, v in ipairs(GearRackDB.queue[13].list) do t[#t + 1] = v end return table.concat(t, ",") end
    function tbutton(text) for _, w in ipairs(widgets) do
        if w.parent == GearRackTrinkets and w.text == text and w.template then return w end end end
    function tcheck(text) for _, w in ipairs(widgets) do
        if w.parent == GearRackTrinkets and w.label and w.label.text == text then return w end end end
    '''

    def open(self):
        lua = load(setup=TRINKETS)
        lua.execute(self.TOOLS)
        lua.execute("click(GearRackTrinket13, 'RightButton')")
        self.assertTrue(lua.eval("GearRackTrinkets:IsShown()"))
        return lua

    def test_the_list_fills_with_the_worn_and_carried_trinkets_and_the_stop_line(self):
        lua = self.open()
        self.assertEqual(lua.eval("tlist()").split(",")[:2], ["1008", "1009"])
        self.assertEqual(sorted(lua.eval("tlist()").split(",")[2:4]), ["1010", "1020"])
        self.assertEqual(lua.eval("tlist()").split(",")[4], "0")
        lua.execute("item('0x41', 1021, 'New Trinket', 'INVTYPE_TRINKET', 3) carry(3, 1, '0x41') fire('BAG_UPDATE_DELAYED')")
        self.assertEqual(lua.eval("tlist()").split(",")[-1], "1021", "a new trinket joins below the line")

    def test_up_down_and_remove(self):
        lua = self.open()
        lua.execute("click(trow(2)) click(tbutton('Up'))")
        self.assertEqual(lua.eval("tlist()").split(",")[:2], ["1009", "1008"])
        lua.execute("click(tbutton('Down'))")
        self.assertEqual(lua.eval("tlist()").split(",")[:2], ["1008", "1009"])
        lua.execute("click(trow(5))")  # the stop line cannot be removed
        self.assertFalse(lua.eval("tbutton('Remove'):IsEnabled()"))
        lua.execute("click(trow(1)) click(tbutton('Remove'))")
        self.assertEqual(lua.eval("#GearRackDB.queue[13].list"), 4)
        self.assertEqual(lua.eval("tlist()").split(",")[0], "1009")

    def test_a_trinkets_settings(self):
        lua = self.open()
        lua.execute("click(trow(1)) c = tcheck('High priority') c:SetChecked(1) click(c)")
        self.assertTrue(lua.eval("GearRackDB.trinkets[1008].priority"))
        lua.execute("c = tcheck('Pause the queue while worn') c:SetChecked(1) click(c)")
        self.assertTrue(lua.eval("GearRackDB.trinkets[1008].pause"))
        self.assertEqual(lua.eval("trow(1).marks.text"), "High, Pause")
        lua.execute("c:SetChecked(nil) click(c) c = tcheck('High priority') c:SetChecked(nil) click(c)")
        self.assertIsNone(lua.eval("GearRackDB.trinkets[1008]"), "an empty setting goes")

    def test_the_switch_and_the_two_slots(self):
        lua = self.open()
        lua.execute("c = tcheck('Swap automatically') c:SetChecked(1) click(c)")
        self.assertTrue(lua.eval("GearRackDB.queue[13].on"))
        self.assertTrue(lua.eval("GearRackTrinket13.queue:IsShown()"))
        lua.execute("click(tbutton('Lower'))")
        self.assertIsNone(lua.eval("tcheck('Swap automatically'):GetChecked()"))
        self.assertFalse(lua.eval("tbutton('Lower'):IsEnabled()"))
        lua.execute("click(GearRackMinimapTrinkets)")
        self.assertTrue(lua.eval("GearRackTrinkets:IsShown()"), "the minimap button opens the upper list")
        self.assertIn("GearRackTrinkets", lua.eval("table.concat(UISpecialFrames, ',')"))


class Buttons(unittest.TestCase):
    def test_the_drawer_lists_the_bag_trinkets_left_upper_right_lower(self):
        lua = load(setup=TRINKETS)
        lua.execute("hover(GearRackTrinket14)")
        self.assertEqual(lua.eval("menuItems()"), "0x40,0x13")
        lua.execute("pick('0x13')")
        self.assertEqual(lua.eval("worn[13]"), "0x13", "left-click: the upper slot")
        lua.execute("leave(GearRackTrinket14) hover(GearRackTrinket13) pick('0x40', 'RightButton')")
        self.assertEqual(lua.eval("worn[14]"), "0x40", "right-click: the lower slot")

    def test_right_click_opens_the_window_and_uses_nothing(self):
        lua = load(setup=TRINKETS)
        lua.execute("click(GearRackTrinket14, 'RightButton')")
        self.assertTrue(lua.eval("GearRackTrinkets:IsShown()"))
        self.assertIsNone(lua.eval("used[1]"))
        lua.execute("click(GearRackGear16, 'RightButton')")
        self.assertIsNone(lua.eval("used[1]"), "a right-click on other buttons does nothing")

    def test_the_tooltip_is_on_the_side_away_from_the_menu(self):
        lua = load()
        lua.execute("hover(GearRackGear16)")  # a bar across in the lower half: the menu goes up
        self.assertEqual(lua.eval("GameTooltip.anchor"), "ANCHOR_BOTTOMRIGHT")
        lua.execute("leave(GearRackGear16) GearRackGearBar.top = 700 GearRackGear16.top = 700 hover(GearRackGear16)")
        self.assertEqual(lua.eval("GameTooltip.anchor"), "ANCHOR_RIGHT")

    def test_slots_toggled_many_times_stay_a_clean_list(self):
        lua = load()
        lua.execute("ToggleCharacter() press('lalt')")
        for slot in ("Back", "Legs", "Back", "MainHand", "Legs", "Neck", "Back", "Neck", "MainHand", "Legs"):
            lua.execute(f"click(Character{slot}Slot)")
        self.assertEqual(lua.eval("table.concat(GearRackDB.slots, ',')"), "17,18,15,16,7")
        lua.execute("n = 0 for k in pairs(GearRackDB.slots) do n = n + 1 end")
        self.assertEqual(lua.eval("n"), 5)


class MinimapButtons(unittest.TestCase):
    def test_a_drag_moves_it_round_the_minimap_and_saves_the_angle(self):
        lua = load()
        lua.execute("b = GearRackMinimapGear run(b, 'OnDragStart')")
        self.assertIsNotNone(lua.eval("b.scripts.OnUpdate"))
        lua.execute("cx, cy = Minimap:GetCenter() cursorX, cursorY = cx, cy + 50 step(0.02)")
        self.assertEqual(lua.eval("GearRackDB.angles.gear"), 90)
        lua.execute("run(b, 'OnDragStop')")
        self.assertIsNone(lua.eval("b.scripts.OnUpdate"), "no OnUpdate once let go")
        lua2 = load(saved="GearRackDB = { angles = { gear = 90 } }")
        point = lua2.eval("{ GearRackMinimapGear:GetPoint(1) }")
        self.assertEqual((round(point[4]), round(point[5])), (0, 80))


if __name__ == "__main__":
    unittest.main()
