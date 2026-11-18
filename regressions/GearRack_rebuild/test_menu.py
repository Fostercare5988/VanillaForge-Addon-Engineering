"""Menus and one item (spec 4.5 tests 4 and 5): what a menu lists, how it
closes, and a choice that cannot happen now waits."""
import unittest
from gr_env import load


class Menu(unittest.TestCase):
    def test_bag_items_that_fit_and_can_be_worn_never_the_one_in_the_slot(self):
        lua = load()
        lua.execute("hover(GearRackGear16)")
        items = lua.eval("menuItems()").split(",")
        # The off hand's dagger, the bag daggers, both copies of Twin Blade; not
        # the Ripper (worn there), not the axe (cannot be worn); the empty button last.
        self.assertEqual(sorted(items[:-1]), sorted(["0xB", "0xD", "0xE", "0xF1", "0xF2"]))
        self.assertEqual(items[-1], "off")
        self.assertEqual(items[:2], ["0xE", "0xD"], "epic first, then by name")

    def test_a_one_hander_in_the_off_hand_only_with_dual_wield(self):
        lua = load(setup="dualWield = false")
        lua.execute("hover(GearRackGear17)")
        self.assertEqual(lua.eval("menuItems()"), "off")
        lua.execute("leave(GearRackGear17) dualWield = true hover(GearRackGear17)")
        self.assertIn("0xF1", lua.eval("menuItems()"))

    def test_no_empty_button_for_an_empty_slot_and_no_menu_with_nothing(self):
        lua = load(setup="worn[18] = nil")
        lua.execute("hover(GearRackGear18)")
        self.assertFalse(lua.eval("GearRackMenu:IsShown()"))

    def test_the_sets_menu_by_name_with_the_worn_set_marked(self):
        lua = load(setup='makeSet("PVP", "I1", {}) makeSet("Instant", "I2", {})')
        lua.execute("for s = 1, 19 do sets[2].slots[s] = 'ignored' end hover(GearRackSets)")
        self.assertEqual(lua.eval("menuItems()"), "set:Instant,set:PVP")
        self.assertEqual(lua.eval("menuButton(1).edge.border[1]"), 1)
        self.assertEqual(lua.eval("menuButton(1).label.text"), "Instant")
        lua.execute("click(menuButton(2))")
        self.assertEqual(lua.eval("usedSets[1]"), "PVP")

    def test_it_closes_when_the_pointer_leaves_owner_and_menu_and_stays_between(self):
        lua = load()
        lua.execute("hover(GearRackGear16) GearRackGear16.mouse = false GearRackMenu.mouse = true"
                    " run(GearRackGear16, 'OnLeave') step(0.11)")
        self.assertTrue(lua.eval("GearRackMenu:IsShown()"))
        lua.execute("leave(GearRackMenu)")
        self.assertFalse(lua.eval("GearRackMenu:IsShown()"))
        self.assertEqual(lua.eval("tickers()"), 0)
        self.assertFalse(lua.eval("GearRackMenu:IsEventRegistered('BAG_UPDATE_DELAYED')"))

    def test_an_open_menu_follows_the_bags(self):
        lua = load()
        lua.execute("hover(GearRackTrinket13)")
        self.assertEqual(lua.eval("menuItems()"), "0x12,0x13,off")
        lua.execute("bags[0][3] = nil fire('BAG_UPDATE_DELAYED')")
        self.assertEqual(lua.eval("menuItems()"), "0x12,off")

    def test_a_menu_opens_away_from_the_screen_edge(self):
        lua = load()
        lua.execute("hover(GearRackGear16)")  # a bar across, in the lower half
        self.assertEqual(lua.eval("(select(1, GearRackMenu:GetPoint(1)))"), "BOTTOMLEFT")
        lua.execute("leave(GearRackGear16) GearRackTrinket13.left, GearRackTrinket13.top = 100, 500")
        lua.execute("hover(GearRackTrinket13)")  # a bar down, in the left half
        self.assertEqual(lua.eval("(select(3, GearRackMenu:GetPoint(1)))"), "TOPRIGHT")


class OneItem(unittest.TestCase):
    def test_a_click_equips_that_copy(self):
        lua = load()
        lua.execute("hover(GearRackGear16) pick('0xF2')")
        self.assertEqual(lua.eval("equips[1]"), "0xF2>16")
        self.assertEqual(lua.eval("worn[16]"), "0xF2")
        self.assertFalse(lua.eval("GearRackMenu:IsShown()"))

    def test_right_click_on_a_trinket_gives_the_other_slot(self):
        lua = load()
        lua.execute("hover(GearRackTrinket13) pick('0x13', 'RightButton')")  # Hand of Justice
        self.assertEqual(lua.eval("equips[1]"), "0x13>14")

    def test_in_combat_a_weapon_at_once_and_armor_after_combat(self):
        lua = load(setup="combat = true")
        lua.execute("hover(GearRackGear16) pick('0xD')")
        self.assertEqual(lua.eval("worn[16]"), "0xD")
        lua.execute("hover(CharacterHeadSlot) pick('0x17')")
        self.assertEqual(lua.eval("worn[1]"), "0x16")
        lua.execute("combat = false fire('PLAYER_REGEN_ENABLED')")
        self.assertEqual(lua.eval("worn[1]"), "0x17")

    def test_dead_until_alive(self):
        lua = load(setup="dead = true")
        lua.execute("hover(GearRackGear16) pick('0xD')")
        self.assertEqual(lua.eval("worn[16]"), "0xA")
        self.assertEqual(lua.eval("GearRackGear16.wait.texture"), "icon:Satyr Claw")
        self.assertTrue(lua.eval("GearRackGear16.wait:IsShown()"))
        lua.execute("dead = false fire('PLAYER_ALIVE')")
        self.assertEqual(lua.eval("worn[16]"), "0xD")
        self.assertFalse(lua.eval("GearRackGear16.wait:IsShown()"))

    def test_a_locked_item_at_item_lock_changed(self):
        lua = load(setup="locked['0xD'] = true")
        lua.execute("hover(GearRackGear16) pick('0xD')")
        self.assertIsNone(lua.eval("equips[1]"))
        lua.execute("locked['0xD'] = nil fire('ITEM_LOCK_CHANGED')")
        self.assertEqual(lua.eval("worn[16]"), "0xD")

    def test_a_new_choice_replaces_and_the_same_again_cancels(self):
        lua = load(setup="dead = true")
        lua.execute("hover(GearRackGear16) pick('0xD') hover(GearRackGear16) pick('0xE')")
        self.assertEqual(lua.eval("GearRackGear16.wait.texture"), "icon:Anasterian's Legacy")
        lua.execute("leave(GearRackGear16) hover(GearRackGear16) pick('0xE')")
        self.assertFalse(lua.eval("GearRackGear16.wait:IsShown()"))
        lua.execute("dead = false fire('PLAYER_ALIVE')")
        self.assertEqual(lua.eval("worn[16]"), "0xA")

    def test_an_item_gone_from_the_bags_drops_the_choice(self):
        lua = load(setup="dead = true")
        lua.execute("hover(GearRackGear16) pick('0xD')")
        lua.execute("bags[0][1] = nil fire('BAG_UPDATE_DELAYED')")
        self.assertFalse(lua.eval("GearRackGear16.wait:IsShown()"))
        self.assertNotIn("ITEM_LOCK_CHANGED", lua.eval("allEvents()"))

    def test_three_refusals_give_up_with_a_chat_line(self):
        lua = load(setup="refuse['0xD'] = true")
        lua.execute("hover(GearRackGear16) pick('0xD')")
        for _ in range(3):
            lua.execute("fire('ITEM_LOCK_CHANGED')")
        self.assertEqual(lua.eval("#equips"), 3)
        self.assertIn("Could not put on", lua.eval("chatText()"))
        self.assertFalse(lua.eval("GearRackGear16.wait:IsShown()"))

    def test_the_waiting_events_go_when_nothing_waits(self):
        lua = load(setup="dead = true")
        waiting = ("ITEM_LOCK_CHANGED", "PLAYER_ALIVE", "PLAYER_UNGHOST", "BAG_UPDATE_DELAYED")
        for e in waiting:
            self.assertNotIn(e, lua.eval("allEvents()").split(","))
        lua.execute("hover(GearRackGear16) pick('0xD') leave(GearRackGear16)")
        for e in waiting:
            self.assertIn(e, lua.eval("allEvents()").split(","))
        lua.execute("dead = false fire('PLAYER_UNGHOST')")
        for e in waiting:
            self.assertNotIn(e, lua.eval("allEvents()").split(","))

    def test_the_empty_button_takes_the_item_off_into_a_free_bag(self):
        lua = load(setup="for s = 1, 16 do if not bags[0][s] then bags[0][s] = 'full' end end bagFamily[1] = 0")
        lua.execute("items.full = { name = 'x' } hover(CharacterBackSlot) pick('off')")
        self.assertIsNone(lua.eval("worn[15]"))
        self.assertEqual(lua.eval("bags[1][4]"), "0x18")

    def test_take_off_with_full_bags_says_so(self):
        lua = load(setup="for b = 0, 4 do for s = 1, 16 do bags[b][s] = bags[b][s] or 'full' end end")
        lua.execute("items.full = { name = 'x' } hover(CharacterBackSlot) pick('off')")
        self.assertEqual(lua.eval("worn[15]"), "0x18")
        self.assertIn("bags are full", lua.eval("chatText()"))


if __name__ == "__main__":
    unittest.main()
