"""Attaching items to the queue by GUID (spec tests 4 and 5), Mail 1.0.0."""
import unittest
from mail_env import load, slots

ITEMS = '''
cloth = give(0, 1, "Linen Cloth", 20)
ore = give(0, 2, "Copper Ore", 5)
ring = give(0, 3, "Bound Ring", 1, true)
'''


class Attach(unittest.TestCase):
    def setUp(self):
        self.lua = load(setup=ITEMS)

    def test_a_right_click_attaches_and_opens_the_send_tab(self):
        self.lua.execute("rightClickBag(0, 1)")
        self.assertEqual(self.lua.eval("SendMailFrame:IsShown()"), 1)
        self.assertTrue(slots(self.lua).startswith("icon:Linen Cloth,"))
        self.assertEqual(self.lua.eval("locked(cloth)"), True)
        self.assertEqual(self.lua.eval("attached"), None, "the client's slot is left empty")
        self.assertEqual(self.lua.eval("#used"), 0, "the item is not used")

    def test_a_second_right_click_takes_it_off(self):
        self.lua.execute("rightClickBag(0, 1); rightClickBag(0, 1)")
        self.assertFalse(slots(self.lua).startswith("icon:"))
        self.assertEqual(self.lua.eval("locked(cloth)"), False)

    def test_with_a_modifier_or_away_from_the_mailbox_the_item_is_used(self):
        self.lua.execute("MailFrameTab_OnClick(2); shift = 1; rightClickBag(0, 1); shift = nil")
        self.lua.execute("fire('MAIL_CLOSED'); rightClickBag(0, 2)")
        self.assertEqual(list(self.lua.eval("used").values()), ["0:1", "0:2"])

    def test_on_the_send_tab_items_queue_up_instead_of_swapping_the_clients_slot(self):
        """Seen in play 2026-11-17 (Mail 1.0.0): OctoWoW's own right-click put each
        item in the client's one slot, replacing the last; nothing was queued."""
        self.lua.execute("MailFrameTab_OnClick(2); rightClickBag(0, 1); rightClickBag(0, 2)")
        self.assertTrue(slots(self.lua).startswith("icon:Linen Cloth,icon:Copper Ore,"))
        self.assertEqual(self.lua.eval("attached"), None)
        self.assertEqual(self.lua.eval("#used"), 0)

    def test_soulbound_conjured_and_quest_items_are_refused(self):
        self.lua.execute('''local water = give(1, 1, "Conjured Water", 20); bags[1][1].conjured = true
            local note = give(1, 2, "Quest Note", 1); bags[1][2].quest = true
            chat = {}; rightClickBag(0, 3); rightClickBag(1, 1); rightClickBag(1, 2)''')
        self.assertFalse(slots(self.lua).startswith("icon:"))
        self.assertEqual(self.lua.eval("locked(ring)"), False)
        self.assertEqual(self.lua.eval("cursor"), None)
        self.assertIn("[Bound Ring] cannot be mailed.", self.lua.eval("chatText()"))
        self.assertIn("[Conjured Water] cannot be mailed.", self.lua.eval("chatText()"))

    def test_attaching_and_taking_off_never_touch_the_clients_slot(self):
        """Mail 1.0.0 put every item in the client's one slot and took it out
        again to ask whether it could be mailed."""
        self.lua.execute("clicks = 0; rightClickBag(0, 1); rightClickBag(0, 2); rightClickBag(0, 1)")
        self.assertEqual(self.lua.eval("clicks"), 0)
        self.assertEqual(self.lua.eval("attached"), None)
        self.assertTrue(slots(self.lua).startswith("icon:Copper Ore,,"))
        self.assertEqual(self.lua.eval("locked(cloth)"), False, "the item taken off is free again")

    def test_twenty_one_at_most(self):
        self.lua.execute('''for s = 1, 22 do give(1, s, "Ore " .. s) end
            chat = {}; for s = 1, 22 do rightClickBag(1, s) end''')
        self.assertEqual(slots(self.lua).count("icon:"), 21)
        self.assertIn("All 21 slots are full", self.lua.eval("chatText()"))

    def test_a_dropped_item_is_attached(self):
        self.lua.execute("MailFrameTab_OnClick(2); PickupContainerItem(0, 2); run(SendMailScrollChildFrame, 'OnMouseUp')")
        self.assertTrue(slots(self.lua).startswith("icon:Copper Ore,"))
        self.assertEqual(self.lua.eval("cursor"), None)
        self.lua.execute("PickupContainerItem(0, 1)")
        self.lua.execute("for _, w in ipairs(widgets) do if w.parent == SendMailFrame and w.id == 5 then run(w, 'OnReceiveDrag') end end")
        self.assertTrue(slots(self.lua).startswith("icon:Copper Ore,icon:Linen Cloth,"))

    def test_a_right_click_on_a_slot_takes_the_item_off_whatever_the_cursor_holds(self):
        """Seen in play 2026-11-17: right-clicking an attached item did nothing."""
        self.lua.execute("rightClickBag(0, 1); rightClickBag(0, 2); give(3, 1, 'Held', 1); PickupContainerItem(3, 1)")
        self.lua.execute("for _, w in ipairs(widgets) do if w.parent == SendMailFrame and w.id == 1 then run(w, 'OnClick', 'RightButton') end end")
        self.assertTrue(slots(self.lua).startswith("icon:Copper Ore,,"))
        self.assertEqual(self.lua.eval("locked(cloth)"), False)

    def test_an_item_the_client_puts_in_its_own_slot_joins_the_list(self):
        """Seen in play 2026-11-17: a second round of right-clicks did nothing; the
        client's own right-click (ContainerFrame.lua:616: pick up, then
        ClickSendMailItemButton) had put each stack in its hidden slot."""
        self.lua.execute('''MailFrameTab_OnClick(2)
            PickupContainerItem(0, 1); ClickSendMailItemButton(); ClearCursor()
            PickupContainerItem(0, 2); ClickSendMailItemButton(); ClearCursor()''')
        self.assertTrue(slots(self.lua).startswith("icon:Linen Cloth,icon:Copper Ore,"))
        self.assertEqual(self.lua.eval("attached"), None, "the client's slot is empty again")
        self.assertEqual(self.lua.eval("cursor"), None)
        self.lua.execute("rightClickBag(0, 1)")
        self.assertTrue(slots(self.lua).startswith("icon:Copper Ore,,"), "and right-click takes it off")

    def test_logging_out_or_reloading_lets_the_greyed_items_go(self):
        """Seen in play 2026-11-17: after /reload the stacks were still grey."""
        self.lua.execute("rightClickBag(0, 1); rightClickBag(0, 2); fire('PLAYER_LOGOUT')")
        self.assertEqual(self.lua.eval("locked(cloth) or locked(ore)"), False)

    def test_opening_the_mailbox_gives_back_an_item_left_in_the_clients_slot(self):
        self.lua.execute("fire('MAIL_CLOSED'); PickupContainerItem(0, 3 - 2); ClickSendMailItemButton(); fire('MAIL_SHOW')")
        self.assertEqual(self.lua.eval("attached"), None)
        self.assertEqual(self.lua.eval("cursor"), None)

    def test_a_left_click_on_a_slot_takes_the_item_back_to_the_cursor(self):
        self.lua.execute("rightClickBag(0, 1)")
        self.lua.execute("for _, w in ipairs(widgets) do if w.parent == SendMailFrame and w.id == 1 then run(w, 'OnClick', 'LeftButton') end end")
        self.assertFalse(slots(self.lua).startswith("icon:"))
        self.assertEqual(self.lua.eval("cursor == cloth"), True)

    def test_a_moved_item_stays_attached_and_a_sold_one_drops_off(self):
        self.lua.execute("rightClickBag(0, 1); rightClickBag(0, 2)")
        self.lua.execute("move(0, 1, 2, 7); locks[cloth] = nil; fire('BAG_UPDATE_DELAYED')")
        self.assertEqual(self.lua.eval("locked(cloth)"), True, "the lock comes back after a server update")
        self.assertTrue(slots(self.lua).startswith("icon:Linen Cloth,icon:Copper Ore,"))
        self.lua.execute("sell(0, 2); fire('BAG_UPDATE_DELAYED')")
        self.assertTrue(slots(self.lua).startswith("icon:Linen Cloth,,"))

    def test_a_lock_the_server_clears_comes_back(self):
        self.lua.execute("rightClickBag(0, 1); locks[cloth] = nil; fire('ITEM_LOCK_CHANGED')")
        self.assertEqual(self.lua.eval("locked(cloth)"), True)

    def test_closing_the_mailbox_lets_every_item_go(self):
        self.lua.execute("rightClickBag(0, 1); rightClickBag(0, 2); fire('MAIL_CLOSED')")
        self.assertEqual(self.lua.eval("locked(cloth) or locked(ore)"), False)
        self.assertFalse(slots(self.lua).startswith("icon:"))

    def test_bag_updates_are_heard_only_while_items_wait(self):
        frames = "(function() for _, w in ipairs(widgets) do if w.events.BAG_UPDATE_DELAYED and w.events.ITEM_LOCK_CHANGED and w.events.PLAYER_LOGOUT then return true end end return false end)()"
        self.assertEqual(self.lua.eval(frames), False)
        self.lua.execute("rightClickBag(0, 1)")
        self.assertEqual(self.lua.eval(frames), True)
        self.lua.execute("rightClickBag(0, 1)")
        self.assertEqual(self.lua.eval(frames), False)


if __name__ == "__main__":
    unittest.main()
