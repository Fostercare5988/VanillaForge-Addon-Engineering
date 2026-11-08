"""Reproductions for the 2026-11-08 Mailroom audit (.private/audit-Mailroom-2026-11-08.md).

Each test fails on Mailroom 1.6.0 (9c96af5) for the reason in its docstring.
Mocks model the game; the server's mail handling and drawing stay in-game
checks.
"""
import unittest
from mailroom_env import load


class Bugs(unittest.TestCase):

    def test_one_delete_per_mail(self):
        """P3: Open All takes from a mail again on each inbox update, and each
        take queued another delete for the same mail."""
        lua = load()
        lua.execute('''
            inbox = { { sender = "Bob", subject = "Ore", item = 1, read = 1 } }
            Mailroom.inbox_open(1); Mailroom.inbox_open(1); Mailroom.inbox_open(1)
        ''')
        self.assertEqual(lua.eval("#Mailroom.delete_queue"), 1)

    def test_commands_ignore_case(self):
        """P3: \"/mr CLEAR NAMES\" showed the command list instead of clearing the names."""
        lua = load()
        lua.execute('Mailroom.slash_command("CLEAR NAMES")')
        self.assertEqual(lua.eval('next(Mailroom_AutoCompleteNames[Mailroom.names_key])'), None)


NATIVE = '''
nativeHeaderInfo, nativeContainerInfo = GetInboxHeaderInfo, GetContainerItemInfo
'''


def typed(lua, text):
    lua.execute('SendMailNameEditBox:SetText(%r); run(SendMailNameEditBox, "OnChar")' % text)


class ClassicAPIDoesIt(unittest.TestCase):
    def test_names_come_from_classicapi(self):
        """P2: completion walked the friends list and the whole guild roster on
        every key, and never offered group members or people you whispered.
        ClassicAPI's C_AutoComplete knows all four; saved names still come first."""
        lua = load()
        lua.execute('''
            roster = 0
            function GetNumGuildMembers() return 500 end
            function GetGuildRosterInfo() roster = roster + 1; return "Guildie" end
            known = { "Gina", "Walt" }
            Mailroom.add_auto_complete_name("Garry")
        ''')
        typed(lua, "G")
        self.assertEqual(lua.eval("MailAutoCompleteButton1.text"), "Garry")
        self.assertEqual(lua.eval("MailAutoCompleteButton2.text"), "Gina")
        self.assertEqual(lua.eval("roster"), 0)
        # group, guild, friends and whispers; offline guild members get mail too
        self.assertEqual(lua.eval("autocompleteInclude"), 1 + 2 + 4 + 16)

    def test_inbox_senders_without_replacing_a_global(self):
        """P2: Mailroom replaced GetInboxHeaderInfo for every addon to note
        senders. It reads the inbox on its own update instead."""
        lua = load(NATIVE)
        self.assertTrue(lua.eval("rawequal(GetInboxHeaderInfo, nativeHeaderInfo)"))
        lua.execute('inbox = { { sender = "Alice", canReply = 1 }, { sender = "Horde Auction House" } }; fire("MAIL_INBOX_UPDATE")')
        self.assertIsNotNone(lua.eval('Mailroom_AutoCompleteNames["OctoWoW|Horde"].Alice'))
        self.assertIsNone(lua.eval('Mailroom_AutoCompleteNames["OctoWoW|Horde"]["Horde Auction House"]'))

    def test_queued_items_locked_by_classicapi(self):
        """P2: Mailroom replaced GetContainerItemInfo for every bag addon to show
        queued attachments as locked. ClassicAPI's client-side lock does it, and
        every lock is let go when the item leaves the queue."""
        lua = load(NATIVE)
        self.assertTrue(lua.eval("rawequal(GetContainerItemInfo, nativeContainerInfo)"))
        lua.execute('''
            for i = 1, 3 do bag["0:" .. i] = { texture = "t" } end
            UseContainerItem(0, 1); UseContainerItem(0, 2); UseContainerItem(0, 3)
        ''')
        self.assertEqual(lua.eval("MailAttachment3.item[2]"), 3)
        for slot in (1, 2, 3):
            self.assertTrue(lua.eval('locks["0:%d"]' % slot), slot)
        # right-click takes one off again
        lua.execute('arg1 = "RightButton"; PickupContainerItem(0, 3); arg1 = nil')
        self.assertIsNone(lua.eval('locks["0:3"]'))
        self.assertIsNone(lua.eval("MailAttachment3.item"))
        # sending: each item is let go just before it is attached
        lua.execute('''
            SendMailNameEditBox:SetText("Bob")
            SendMailMailButton_OnClick()
        ''')
        self.assertEqual(lua.eval("table.getn(sent)"), 1)
        self.assertTrue(lua.eval('locks["0:2"]'))
        lua.execute('fire("MAIL_SEND_SUCCESS"); frame()')
        self.assertEqual(lua.eval("table.getn(sent)"), 2)
        self.assertIsNone(lua.eval('next(locks)'))

    def test_queued_items_stay_grey_after_a_server_update(self):
        """The attach flow put the item back on the cursor after locking it, so
        it never showed grey; a server update for the item also clears the lock.
        The lock is set after the cursor is cleared and set again after a bag change."""
        lua = load(NATIVE)
        lua.execute('''
            for i = 1, 2 do bag["0:" .. i] = { texture = "t" } end
            UseContainerItem(0, 1); UseContainerItem(0, 2)
        ''')
        self.assertTrue(lua.eval('locks["0:1"]'))
        lua.execute('locks["0:1"] = nil; fire("BAG_UPDATE_DELAYED")')
        self.assertTrue(lua.eval('locks["0:1"]'))
        self.assertTrue(lua.eval('locks["0:2"]'))

    def test_closing_the_mailbox_lets_every_lock_go(self):
        lua = load()
        lua.execute('''
            for i = 1, 3 do bag["0:" .. i] = { texture = "t" } end
            UseContainerItem(0, 1); UseContainerItem(0, 2); UseContainerItem(0, 3)
            SendMailNameEditBox:SetText("Bob")
            SendMailMailButton_OnClick()
            fire("MAIL_CLOSED")
        ''')
        self.assertIsNone(lua.eval("next(locks)"))
        self.assertIsNone(lua.eval("Mailroom.sendmail_state"))

    def test_bag_updates_once_per_frame(self):
        """P3: a burst of BAG_UPDATE was coalesced by hand on OnUpdate.
        ClassicAPI's BAG_UPDATE_DELAYED is that event, once per frame."""
        lua = load()
        self.assertFalse(lua.eval('receives(MailroomFrame, "BAG_UPDATE")'))
        self.assertTrue(lua.eval('receives(MailroomFrame, "BAG_UPDATE_DELAYED")'))

    def test_cursor_item_without_a_frame_delay(self):
        """P3: the picked-up item was stored a frame late (CURSOR_UPDATE cleared
        it first) through OnUpdate. It is now checked when read: still on the
        cursor, and its bag slot locked."""
        lua = load()
        self.assertFalse(lua.eval('receives(MailroomFrame, "CURSOR_UPDATE")'))
        lua.execute('bag["0:4"] = { texture = "t" }; PickupContainerItem(0, 4)')
        self.assertEqual(lua.eval("Mailroom.get_cursor_item()[2]"), 4)
        lua.execute("ClearCursor()")
        self.assertIsNone(lua.eval("Mailroom.get_cursor_item()"))

    def test_no_inbox_polling_while_idle(self):
        """P2: the inbox was fetched from the server every 3 seconds while the
        mailbox stood open. New mail now asks for it, and only a delete still
        waiting on the server keeps a retry going."""
        lua = load()
        lua.execute('fire("MAIL_SHOW"); checks = 0')
        self.assertEqual(lua.eval("table.getn(timers)"), 0)
        lua.execute('fire("UPDATE_PENDING_MAIL")')
        self.assertEqual(lua.eval("checks"), 1)
        lua.execute('''
            inbox = { { sender = "Bob", subject = "Ore", item = 1, read = 1 } }
            Mailroom.inbox_open(1, true)
            checks = 0; step(3)
        ''')
        self.assertEqual(lua.eval("checks"), 1)
        lua.execute('inbox[1].item = nil; fire("MAIL_INBOX_UPDATE"); step(3); step(3)')
        self.assertEqual(lua.eval("#Mailroom.delete_queue"), 0)
        self.assertEqual(lua.eval("checks"), 1)

    def test_open_all_asks_for_the_rest_when_done(self):
        """Without the 3-second refresh, mail beyond the 50 the server sends
        appears once Open All has emptied the shown ones."""
        lua = load()
        lua.execute('''
            fire("MAIL_SHOW"); inbox = {}; checks = 0
            Mailroom.inbox_open_all(); frame()
        ''')
        self.assertEqual(lua.eval("checks"), 1)


SAVED = '''
Mailroom_AutoCompleteNames = { ["OctoWoW|Horde"] = { Old = 4000, Recent = now - 60 } }
'''


class OldCode(unittest.TestCase):
    def test_no_chat_line_at_login(self):
        """P3: every login printed "Mailroom: Loaded (v1.6.0)."."""
        lua = load(saved=SAVED)
        self.assertFalse(lua.eval('string.find(table.concat(chat, " "), "Loaded") ~= nil'))

    def test_old_names_are_dropped(self):
        """P3: a name stamped by a pre-2026 build (GetTime, not time) is now
        dropped like any old one."""
        lua = load(saved=SAVED)
        self.assertIsNone(lua.eval('Mailroom_AutoCompleteNames["OctoWoW|Horde"].Old'))
        self.assertIsNotNone(lua.eval('Mailroom_AutoCompleteNames["OctoWoW|Horde"].Recent'))

    def test_any_auction_house_is_marked(self):
        """P3: Auction House senders came from a hand list of eight names (one
        with a doubled space); any "... Auction House" sender is one."""
        lua = load()
        lua.execute('''
            inbox = { { sender = "Gadgetzan Auction House", subject = "Hello" }, { sender = "Bob", subject = "Hello", canReply = 1 } }
            InboxFrame.pageNum = 1; InboxFrame_Update()
        ''')
        self.assertTrue(lua.eval("MailroomAuctionIcon1.shown"))
        self.assertFalse(lua.eval("MailroomAuctionIcon2.shown"))

    def test_inbox_rows_are_not_hidden_and_shown(self):
        """P3: each inbox update hid and showed all seven rows to refresh one
        tooltip. Only a row whose tooltip is up refreshes it."""
        lua = load()
        lua.execute('''
            shows, enters = 0, 0
            for i = 1, 7 do _G["MailItem" .. i].scripts.OnShow = function() shows = shows + 1 end end
            owner = MailItem2Button
            function GameTooltip:IsOwned(f) return f == owner end
            local enter = Mailroom.orig.InboxFrameItem_OnEnter
            Mailroom.orig.InboxFrameItem_OnEnter = function() if this == owner then enters = enters + 1 end end
            inbox = { { sender = "Bob" }, { sender = "Ann" } }
            InboxFrame.pageNum = 1; InboxFrame_Update()
        ''')
        self.assertEqual(lua.eval("shows"), 0)
        self.assertEqual(lua.eval("enters"), 1)

    def test_send_page_layout_only_when_rows_change(self):
        """P3: every Send Mail refresh re-anchored all 21 slots and re-sized the
        letter, though the number of rows had not changed."""
        lua = load()
        lua.execute('''
            bag["0:1"] = { texture = "t" }
            MailAttachment1.item = { 0, 1 }
            SendMailFrame_Update()
            before = #MailAttachment1.points
            SendMailFrame_Update(); SendMailFrame_Update()
        ''')
        self.assertEqual(lua.eval("#MailAttachment1.points"), lua.eval("before"))



class NoLog(unittest.TestCase):
    def test_mail_log_is_gone(self):
        """Mailroom only opens, sends and completes: no log tab, frame, saved
        table or command, and mail sent or received writes nothing down."""
        lua = load()
        self.assertIsNone(lua.eval('rawget(_G, "Mailroom_Log")'))
        self.assertIsNone(lua.eval('rawget(_G, "MailFrameTab3")'))
        self.assertIsNone(lua.eval('rawget(_G, "MailroomLogFrame")'))
        self.assertIsNone(lua.eval("Mailroom.log"))
        lua.execute('Mailroom.slash_command("log")')
        self.assertFalse(lua.eval('string.find(table.concat(chat, " "), "enabled") ~= nil'))


if __name__ == "__main__":
    unittest.main()
