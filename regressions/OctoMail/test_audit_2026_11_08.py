"""Reproductions for the 2026-11-08 OctoMail audit (.private/audit-OctoMail-2026-11-08.md).

Each test fails on OctoMail 1.6.0 (9c96af5) for the reason in its docstring.
Mocks model the game; the server's mail handling and drawing stay in-game
checks.
"""
import unittest
from octomail_env import load


class Bugs(unittest.TestCase):
    def test_options_button_says_what_it_does(self):
        """P2: the AddOn Options button read "Mail log", but it turned logging on
        or off without saying so, and closed the menus."""
        lua = load()
        lua.execute('run(OctoMailOptionsEntry, "OnShow")')
        self.assertEqual(lua.eval("OctoMailOptionsEntryOpen.text"), "Turn mail log on")
        lua.execute('run(OctoMailOptionsEntryOpen, "OnClick")')
        self.assertTrue(lua.eval("OctoMail_Log.Settings.Enabled"))
        self.assertEqual(lua.eval("OctoMailOptionsEntryOpen.text"), "Turn mail log off")

    def test_one_delete_per_mail(self):
        """P3: Open All takes from a mail again on each inbox update, and each
        take queued another delete for the same mail."""
        lua = load()
        lua.execute('''
            inbox = { { sender = "Bob", subject = "Ore", item = 1, read = 1 } }
            OctoMail.inbox_open(1); OctoMail.inbox_open(1); OctoMail.inbox_open(1)
        ''')
        self.assertEqual(lua.eval("#OctoMail.delete_queue"), 1)

    def test_commands_ignore_case(self):
        """P3: "/om LOG" showed the command list instead of turning the log on."""
        lua = load()
        lua.execute('OctoMail.slash_command("LOG")')
        self.assertTrue(lua.eval("OctoMail_Log.Settings.Enabled"))


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
            OctoMail.add_auto_complete_name("Garry")
        ''')
        typed(lua, "G")
        self.assertEqual(lua.eval("MailAutoCompleteButton1.text"), "Garry")
        self.assertEqual(lua.eval("MailAutoCompleteButton2.text"), "Gina")
        self.assertEqual(lua.eval("roster"), 0)
        # group, guild, friends and whispers; offline guild members get mail too
        self.assertEqual(lua.eval("autocompleteInclude"), 1 + 2 + 4 + 16)

    def test_inbox_senders_without_replacing_a_global(self):
        """P2: OctoMail replaced GetInboxHeaderInfo for every addon to note
        senders. It reads the inbox on its own update instead."""
        lua = load(NATIVE)
        self.assertTrue(lua.eval("rawequal(GetInboxHeaderInfo, nativeHeaderInfo)"))
        lua.execute('inbox = { { sender = "Alice", canReply = 1 }, { sender = "Horde Auction House" } }; fire("MAIL_INBOX_UPDATE")')
        self.assertIsNotNone(lua.eval('OctoMail_AutoCompleteNames["OctoWoW|Horde"].Alice'))
        self.assertIsNone(lua.eval('OctoMail_AutoCompleteNames["OctoWoW|Horde"]["Horde Auction House"]'))

    def test_queued_items_locked_by_classicapi(self):
        """P2: OctoMail replaced GetContainerItemInfo for every bag addon to show
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
        self.assertIsNone(lua.eval("OctoMail.sendmail_state"))

    def test_bag_updates_once_per_frame(self):
        """P3: a burst of BAG_UPDATE was coalesced by hand on OnUpdate.
        ClassicAPI's BAG_UPDATE_DELAYED is that event, once per frame."""
        lua = load()
        self.assertFalse(lua.eval('receives(OctoMailFrame, "BAG_UPDATE")'))
        self.assertTrue(lua.eval('receives(OctoMailFrame, "BAG_UPDATE_DELAYED")'))

    def test_cursor_item_without_a_frame_delay(self):
        """P3: the picked-up item was stored a frame late (CURSOR_UPDATE cleared
        it first) through OnUpdate. It is now checked when read: still on the
        cursor, and its bag slot locked."""
        lua = load()
        self.assertFalse(lua.eval('receives(OctoMailFrame, "CURSOR_UPDATE")'))
        lua.execute('bag["0:4"] = { texture = "t" }; PickupContainerItem(0, 4)')
        self.assertEqual(lua.eval("OctoMail.get_cursor_item()[2]"), 4)
        lua.execute("ClearCursor()")
        self.assertIsNone(lua.eval("OctoMail.get_cursor_item()"))

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
            OctoMail.inbox_open(1, true)
            checks = 0; step(3)
        ''')
        self.assertEqual(lua.eval("checks"), 1)
        lua.execute('inbox[1].item = nil; fire("MAIL_INBOX_UPDATE"); step(3); step(3)')
        self.assertEqual(lua.eval("#OctoMail.delete_queue"), 0)
        self.assertEqual(lua.eval("checks"), 1)

    def test_open_all_asks_for_the_rest_when_done(self):
        """Without the 3-second refresh, mail beyond the 50 the server sends
        appears once Open All has emptied the shown ones."""
        lua = load()
        lua.execute('''
            fire("MAIL_SHOW"); inbox = {}; checks = 0
            OctoMail.inbox_open_all(); frame()
        ''')
        self.assertEqual(lua.eval("checks"), 1)


if __name__ == "__main__":
    unittest.main()
