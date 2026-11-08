"""Operation counts for the P3 repairs of the 2026-10-20 Mailroom audit.

Each test fails on Mailroom 1.5.0 (0abd851). Counts are Lua-level work under
mocks; they say nothing about frame times in the client.
"""
import unittest
from mailroom_env import load


class PerformanceReproductions(unittest.TestCase):
    def test_p3_1_no_per_frame_work_while_idle(self):
        """P3-1: no OnUpdate while nothing is pending. Since 2026-11-08 no inbox
        refresh runs while idle; a retry for a waiting delete stops on close."""
        lua = load()
        lua.execute('fire("MAIL_SHOW")')
        self.assertIsNone(lua.eval("MailroomFrame.scripts.OnUpdate"))
        self.assertEqual(lua.eval("table.getn(tickers)"), 0)
        lua.execute('''
            inbox = { { sender = "Bob", subject = "Ore", item = 1, read = 1 } }
            Mailroom.inbox_open(1, true)
        ''')
        self.assertEqual(lua.eval("table.getn(tickers)"), 1)
        lua.execute('fire("MAIL_CLOSED")')
        self.assertTrue(lua.eval("tickers[1].cancelled"))

    def test_p3_1_deferred_work_runs_then_sleeps(self):
        """P3-1: a queued send still goes out on the next frame, then the frame goes idle."""
        lua = load()
        lua.execute('''
            bag["0:1"] = { texture = "t" }; bag["0:2"] = { texture = "t" }
            MailAttachment1.item = { 0, 1 }; MailAttachment2.item = { 0, 2 }
            SendMailNameEditBox:SetText("Bob")
            SendMailMailButton_OnClick()
            fire("MAIL_SEND_SUCCESS"); frame(); fire("MAIL_SEND_SUCCESS"); frame()
        ''')
        self.assertEqual(lua.eval("table.getn(sent)"), 2)
        self.assertIsNone(lua.eval("MailroomFrame.scripts.OnUpdate"))

    def test_p3_2_closed_mailbox_container_info_allocates_nothing(self):
        """P3-2: the global GetContainerItemInfo replacement built a table per call for every addon."""
        lua = load()
        delta = lua.eval('''(function()
            MailFrame:Hide(); bag["0:1"] = { texture = "t", count = 3 }
            collectgarbage("collect"); collectgarbage("stop")
            local before = collectgarbage("count")
            for i = 1, 20000 do GetContainerItemInfo(0, 1) end
            local after = collectgarbage("count")
            collectgarbage("restart")
            return after - before
        end)()''')
        self.assertLess(delta, 64)
        self.assertEqual(lua.eval("(select(2, GetContainerItemInfo(0, 1)))"), 3)

    def test_p3_3_bag_burst_refreshes_send_page_once(self):
        """P3-3: every BAG_UPDATE redrew the whole Send Mail page, even on the Inbox tab.
        Since 2026-11-08 ClassicAPI's BAG_UPDATE_DELAYED comes once per frame."""
        lua = load()
        lua.execute('''
            calls = 0
            SendMailFrame_Update = function() calls = calls + 1 end
            SendMailFrame:Hide()
            fire("BAG_UPDATE_DELAYED")
        ''')
        self.assertEqual(lua.eval("calls"), 0)
        lua.execute('''
            SendMailFrame:Show()
            fire("BAG_UPDATE_DELAYED")
        ''')
        self.assertEqual(lua.eval("calls"), 1)



if __name__ == "__main__":
    unittest.main()
