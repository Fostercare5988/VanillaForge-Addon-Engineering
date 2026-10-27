"""Reproductions for the 2026-10-20 OctoMail audit (.private/audit-OctoMail-2026-10-20.md).

Each test fails on OctoMail 1.5.0 (0abd851) for the reason in its docstring.
The selected Script files run under Lua 5.1 with generic widget mocks; they do
not prove native widget behavior, event order or how the server handles mail.
"""
import unittest
from octomail_env import ROOT, SCRIPTS, load


class AuditReproductions(unittest.TestCase):
    def test_p2_classicapi_guard(self):
        """P2-8: without ClassicAPI 1.17.11+ the addon must stop before hooking anything."""
        for version in ("nil", "11710"):
            lua = load("CLASSIC_API_VERSION = %s" % version)
            self.assertIsNone(lua.eval('rawget(_G, "OctoMailFrame")'), version)
            self.assertTrue(lua.eval('string.find(table.concat(messages, " "), "ClassicAPI") ~= nil'), version)

    def test_p2_global_L_is_not_overwritten(self):
        """P2-1: OctoMail.lua assigns the global L, clobbering other addons (and theirs clobbers it)."""
        lua = load('L = "foreign"')
        self.assertEqual(lua.eval("L"), "foreign")

    def test_p2_sent_money_is_logged(self):
        """P2-2: log.add tests state.send_money (typo), so sent gold is never logged."""
        lua = load()
        lua.execute('''
            OctoMail.log_enabled = true
            OctoMail.log.add("Sent", { to = "Bob", sent_subject = "Gold", sent_money = 50000 })
        ''')
        self.assertEqual(lua.eval("OctoMail_Log.Sent[1].money"), 50000)

    def test_p2_inbox_sender_reaches_autocomplete(self):
        """P2-3: the GetInboxHeaderInfo hook reads its arguments, not the returned sender."""
        lua = load()
        lua.execute('inbox = { { sender = "Alice", canReply = 1 } }; GetInboxHeaderInfo(1)')
        self.assertIsNotNone(lua.eval('OctoMail_AutoCompleteNames["OctoWoW|Horde"].Alice'))

    def test_p2_auction_icon_follows_inbox_page(self):
        """P2-4: icons are set only on MAIL_INBOX_UPDATE; InboxNextPage only calls InboxFrame_Update."""
        lua = load()
        lua.execute('''
            inbox = { { sender = "Horde Auction House" } }
            for i = 2, 8 do inbox[i] = { sender = "Bob", canReply = 1 } end
            InboxFrame.pageNum = 1
            fire("MAIL_INBOX_UPDATE"); InboxFrame_Update()
        ''')
        self.assertTrue(lua.eval("OctoMailAuctionIcon1.shown"))
        lua.execute("InboxFrame.pageNum = 2; InboxFrame_Update()")
        self.assertFalse(lua.eval("OctoMailAuctionIcon1.shown"))

    def test_p2_mail_failed_releases_the_send_queue(self):
        """P2-5: MAIL_FAILED is not handled, so the queue and Send button stay locked until the mailbox closes."""
        lua = load()
        lua.execute('''
            bag["0:1"] = { texture = "t" }; bag["0:2"] = { texture = "t" }
            MailAttachment1.item = { 0, 1 }; MailAttachment2.item = { 0, 2 }
            SendMailNameEditBox:SetText("Bob")
            SendMailMailButton_OnClick()
        ''')
        self.assertTrue(lua.eval("OctoMail.sendmail_sending"))
        lua.execute('fire("MAIL_FAILED")')
        self.assertFalse(lua.eval("OctoMail.sendmail_sending"))

    def test_p2_mail_failed_between_mails_keeps_the_queue(self):
        """Regression of P2-5: a MAIL_FAILED with no mail in flight (an empty send slot click) cancelled every mail after the first."""
        lua = load()
        lua.execute('''
            local click = ClickSendMailItemButton
            ClickSendMailItemButton = function()
                if not cursor and not attached then fire("MAIL_FAILED") end
                click()
            end
            bag["0:1"] = { texture = "t" }; bag["0:2"] = { texture = "t" }; bag["0:3"] = { texture = "t" }
            MailAttachment1.item = { 0, 1 }; MailAttachment2.item = { 0, 2 }; MailAttachment3.item = { 0, 3 }
            SendMailNameEditBox:SetText("Bob")
            SendMailMailButton_OnClick()
            fire("MAIL_SEND_SUCCESS"); fire("MAIL_FAILED"); frame()
            fire("MAIL_SEND_SUCCESS"); frame(); fire("MAIL_SEND_SUCCESS"); frame()
        ''')
        self.assertEqual(lua.eval("table.getn(sent)"), 3)
        self.assertFalse(lua.eval("OctoMail.sendmail_sending"))

    def test_p2_cod_is_logged_only_on_mails_that_carry_it(self):
        """P2-6: with "All mails" unchecked only mail 1 is C.O.D., but every later entry logs the C.O.D."""
        lua = load()
        lua.execute('''
            OctoMail.log_enabled = true
            bag["0:1"] = { texture = "t" }; bag["0:2"] = { texture = "t" }
            MailAttachment1.item = { 0, 1 }; MailAttachment2.item = { 0, 2 }
            SendMailCODButton:SetChecked(1); SendMailMoney.copper = 10000
            SendMailNameEditBox:SetText("Bob")
            SendMailMailButton_OnClick()
            fire("MAIL_SEND_SUCCESS"); frame(); fire("MAIL_SEND_SUCCESS")
        ''')
        self.assertEqual(lua.eval("sent[1].cod"), 10000)
        self.assertIsNone(lua.eval("sent[2].cod"))
        self.assertEqual(lua.eval("OctoMail_Log.Sent[1].cod"), 10000)
        self.assertIsNone(lua.eval("OctoMail_Log.Sent[2].cod"))

    def test_p2_calendar_disabled_day_tooltip(self):
        """P2-7: a day with no mail has mails == nil and its OnEnter concatenates nil."""
        lua = load()
        ok = lua.eval('''(pcall(function()
            local cal = OctoMail.Calendar.new()
            cal.show({}, now, newWidget(), function() end)
            OctoMailCalendarDay10Button.scripts.OnEnter()
        end))''')
        self.assertTrue(ok)

    def test_p2_locale_layer_is_gone(self):
        """P2-9: the client is English only; no locale files or GetLocale() branches load."""
        self.assertFalse([s for s in SCRIPTS if "locali" in s.lower()])
        for name in SCRIPTS:
            self.assertNotIn("GetLocale(", (ROOT / name).read_text("utf-8-sig"), name)

    def test_p2_sending_gold_asks_first(self):
        """P2-11: like the native SEND_MONEY popup, gold is sent only after confirmation."""
        lua = load()
        lua.execute('''
            SendMailNameEditBox:SetText("Bob")
            SendMailSendMoneyButton:SetChecked(1); SendMailMoney.copper = 50000
            SendMailMailButton_OnClick()
        ''')
        self.assertEqual(lua.eval("table.getn(sent)"), 0)
        self.assertEqual(lua.eval("popups[1]"), "OCTOMAIL_SEND_MONEY")
        lua.execute('StaticPopupDialogs[popups[1]].OnAccept()')
        self.assertEqual(lua.eval("table.getn(sent)"), 1)
        self.assertEqual(lua.eval("sent[1].money"), 50000)

    def test_p2_cod_cap_blocks_send(self):
        """P2-11: the native 10,000 gold C.O.D. cap stays in force."""
        lua = load()
        lua.execute('''
            SendMailNameEditBox:SetText("Bob")
            SendMailCODButton:SetChecked(1); SendMailMoney.copper = 10000 * 10000 + 1
            SendMailFrame_CanSend()
        ''')
        self.assertFalse(lua.eval("MailMailButton.enabled"))
        self.assertTrue(lua.eval("SendMailErrorText.shown"))
        lua.execute("SendMailMoney.copper = 10000; SendMailFrame_CanSend()")
        self.assertTrue(lua.eval("MailMailButton.enabled"))


if __name__ == "__main__":
    unittest.main()
