"""Open All and the right-click take (spec tests 1 to 3), Mail 1.0.0."""
import unittest
from mail_env import load


def log(lua):
    return list(lua.eval("log").values())


class OpenAll(unittest.TestCase):
    def test_money_then_item_then_delete_one_step_per_update(self):
        lua = load(setup='mail({ sender = "Bob", subject = "Hi", money = 500, item = { "Linen Cloth", 5 } })')
        lua.execute("click(MailOpenAllButton)")
        self.assertEqual(log(lua), ["money 1"])
        lua.execute("answer()")
        self.assertEqual(log(lua), ["money 1", "item 1"])
        lua.execute("answer()")
        self.assertEqual(log(lua), ["money 1", "item 1", "delete 1"])
        lua.execute("answerAll()")
        self.assertEqual(lua.eval("#inbox"), 0)

    def test_cod_gm_and_plain_letters_are_left(self):
        lua = load(setup='''
            mail({ sender = "Seller", subject = "Pay me", cod = 100, item = { "Sword", 1 } })
            mail({ sender = "GM", subject = "Hello", item = { "Gift", 1 }, gm = 1 })
            mail({ sender = "Bob", subject = "Just words" })
            mail({ sender = "Ann", subject = "Gold", money = 300 })''')
        lua.execute("click(MailOpenAllButton); answerAll()")
        self.assertEqual(log(lua), ["money 4", "delete 4"])
        self.assertEqual([m["sender"] for m in lua.eval("inbox").values()], ["Seller", "GM", "Bob"])
        self.assertEqual(lua.eval("inbox[3].read"), None, "a plain letter is not even read")

    def test_one_chat_line_with_money_and_marks(self):
        lua = load(setup='''
            mail({ sender = "Ann", money = 12345 })
            mail({ sender = "Warsong Gulch", item = { "Warsong Gulch Mark of Honor", 3 } })
            mail({ sender = "Alterac Valley", item = { "Alterac Valley Mark of Honor", 2 } })''')
        lua.execute("chat = {}; click(MailOpenAllButton); answerAll()")
        self.assertEqual(lua.eval("#chat"), 1)
        line = lua.eval("chat[1]")
        self.assertIn("Collected", line)
        self.assertIn("marks AV 2, WSG 3", line)

    def test_an_extra_update_does_not_count_twice(self):
        lua = load(setup='mail({ sender = "Ann", money = 100, item = { "Arathi Basin Mark of Honor", 1 } })')
        lua.execute("chat = {}; click(MailOpenAllButton); fire('MAIL_INBOX_UPDATE'); fire('MAIL_INBOX_UPDATE'); answerAll()")
        self.assertEqual(log(lua), ["money 1", "item 1", "delete 1"], "each request is asked once")
        line = lua.eval("chat[1]")
        self.assertIn("marks AB 1", line)
        self.assertEqual(lua.eval("GetCoinTextureString(100)") in line, True)
        self.assertNotIn(lua.eval("GetCoinTextureString(200)"), line)

    def test_full_bags_stop_with_a_reason(self):
        lua = load(setup='''bagsFull = true
            mail({ sender = "A", item = { "Cloth", 1 } }); mail({ sender = "B", item = { "Ore", 1 } })''')
        lua.execute("chat = {}; click(MailOpenAllButton); answerAll()")
        self.assertEqual(log(lua), ["item 1"])
        self.assertIn("bags are full", lua.eval("chatText()"))
        self.assertEqual(lua.eval("MailOpenAllButton:GetText()"), "Open All")

    def test_an_item_you_carry_the_most_of_is_passed_by(self):
        lua = load(setup='''
            local m = mail({ sender = "A", item = { "Unique", 1 } }); m.max = true
            mail({ sender = "B", item = { "Ore", 1 } })''')
        lua.execute("click(MailOpenAllButton); answerAll()")
        self.assertEqual(log(lua), ["item 1", "item 2", "delete 2"])
        self.assertEqual(lua.eval("#inbox"), 1)

    def test_the_mail_past_fifty_is_asked_for_and_taken(self):
        setup = "for i = 1, 60 do mail({ sender = 'S' .. i, money = 1 }) end"
        lua = load(setup=setup)
        lua.execute("checks = 0; click(MailOpenAllButton); answerAll()")
        self.assertEqual(lua.eval("#inbox"), 0, "the ten past the first fifty are taken too")
        self.assertEqual(lua.eval("checks"), 1, "one more ask, once nothing new came")
        self.assertEqual(lua.eval("MailOpenAllButton:GetText()"), "Open All")

    def test_stop_ends_the_take(self):
        lua = load(setup="mail({ sender = 'A', money = 1 }); mail({ sender = 'B', money = 1 })")
        lua.execute("click(MailOpenAllButton)")
        self.assertEqual(lua.eval("MailOpenAllButton:GetText()"), "Stop")
        lua.execute("click(MailOpenAllButton); answerAll()")
        self.assertEqual(log(lua), ["money 1"])

    def test_a_step_with_no_answer_asks_again_once(self):
        lua = load(setup="mail({ sender = 'A', money = 1 })")
        lua.execute("checks = 0; click(MailOpenAllButton); step(2.9)")
        self.assertEqual(lua.eval("checks"), 0)
        lua.execute("step(0.2)")
        self.assertEqual(lua.eval("checks"), 1)
        lua.execute("step(10)")
        self.assertEqual(lua.eval("checks"), 1, "one ask per step, not a ticker")
        lua.execute("answerAll()")
        self.assertEqual(lua.eval("#inbox"), 0)

    def test_closing_the_mailbox_ends_the_take(self):
        lua = load(setup="mail({ sender = 'A', money = 1 }); mail({ sender = 'B', money = 1 })")
        lua.execute("click(MailOpenAllButton); fire('MAIL_CLOSED'); answerAll()")
        self.assertEqual(log(lua), ["money 1"])

    def test_a_request_with_no_answer_is_asked_again(self):
        lua = load(setup="mail({ sender = 'A', money = 1 })")
        lua.execute("click(MailOpenAllButton); requests = {}; step(3.1); answer()")
        self.assertEqual(log(lua), ["money 1", "money 1"])
        lua.execute("answerAll()")
        self.assertEqual(lua.eval("#inbox"), 0)

    def test_alike_mails_in_a_row_are_each_counted(self):
        lua = load(setup='''for i = 1, 3 do mail({ sender = "Warsong Gulch", subject = "Marks", money = 10,
            item = { "Warsong Gulch Mark of Honor", 1 } }) end''')
        lua.execute("chat = {}; click(MailOpenAllButton); answerAll()")
        self.assertEqual(lua.eval("#inbox"), 0)
        self.assertIn("marks WSG 3", lua.eval("chat[1]"))
        self.assertIn(lua.eval("GetCoinTextureString(30)"), lua.eval("chat[1]"))


class RightClick(unittest.TestCase):
    def test_a_right_click_takes_that_mail_only(self):
        lua = load(setup='''mail({ sender = "A", money = 5 })
            mail({ sender = "B", money = 7, item = { "Ore", 2 } })''')
        lua.execute("rightClickRow(2); answerAll()")
        self.assertEqual(log(lua), ["money 2", "item 2", "delete 2"])
        self.assertEqual(lua.eval("inbox[1].money"), 5)
        self.assertEqual(lua.eval("opened"), None)

    def test_cod_and_plain_rows_are_left(self):
        lua = load(setup='''mail({ sender = "A", cod = 5, item = { "Ore", 1 } }); mail({ sender = "B" })''')
        lua.execute("rightClickRow(1); rightClickRow(2); answerAll()")
        self.assertEqual(log(lua), [])

    def test_a_left_click_opens_as_before(self):
        lua = load(setup='mail({ sender = "A", money = 5 })')
        lua.execute("leftClickRow(1)")
        self.assertEqual(lua.eval("opened"), 1)
        self.assertEqual(log(lua), [])

    def test_the_tooltip_says_right_click_to_take(self):
        lua = load(setup='mail({ sender = "A", item = { "Ore", 1 } }); mail({ sender = "B", cod = 5, item = { "Ore", 1 } })')
        lua.execute("run(MailItem1Button, 'OnEnter')")
        self.assertIn("Right-click to take", list(lua.eval("GameTooltip.lines").values()))
        lua.execute("run(MailItem2Button, 'OnEnter')")
        self.assertNotIn("Right-click to take", list(lua.eval("GameTooltip.lines").values()))


if __name__ == "__main__":
    unittest.main()
