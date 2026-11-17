"""The send loop and the Send button (spec tests 6 and 7), Mail 1.0.0."""
import unittest
from mail_env import load, slots

ITEMS = '''
cloth = give(0, 1, "Linen Cloth", 20)
ore = give(0, 2, "Copper Ore", 5)
gem = give(0, 3, "Jade", 1)
'''


def letters(lua):
    return [dict(v) for v in lua.eval("sent").values()]


def form(lua, to="Bagholder", subject="", money=0, cod=False):
    lua.execute(f'''MailFrameTab_OnClick(2)
        SendMailNameEditBox:SetText("{to}"); SendMailSubjectEditBox:SetText("{subject}")
        SendMailMoney.copper = {money}
        {"SendMailRadioButton_OnClick(2)" if cod else ""}''')


class Sending(unittest.TestCase):
    def setUp(self):
        self.lua = load(setup=ITEMS, saved='MailDB = {}')

    def attach(self, *slots_):
        for s in slots_:
            self.lua.execute(f"rightClickBag(0, {s})")

    def test_items_right_clicked_on_the_send_tab_all_go(self):
        """Seen in play 2026-11-17 (Mail 1.0.0): sending several items did not work."""
        form(self.lua)
        self.attach(1, 2, 3)
        self.lua.execute("click(SendMailMailButton); deliverAll()")
        self.assertEqual([l["item"] for l in letters(self.lua)], ["Linen Cloth", "Copper Ore", "Jade"])

    def test_one_letter_per_item_with_the_item_as_subject(self):
        self.attach(1, 2)
        form(self.lua)
        self.lua.execute("click(SendMailMailButton)")
        self.assertEqual(len(letters(self.lua)), 1, "the next letter waits for the first to go")
        self.lua.execute("deliverAll()")
        got = letters(self.lua)
        self.assertEqual([(l["to"], l["subject"], l["item"]) for l in got],
                         [("Bagholder", "Linen Cloth (20)", "Linen Cloth"), ("Bagholder", "Copper Ore (5)", "Copper Ore")])
        self.assertFalse(slots(self.lua).startswith("icon:"))

    def test_a_typed_subject_is_numbered(self):
        self.attach(1, 2, 3)
        form(self.lua, subject="Mats")
        self.lua.execute("click(SendMailMailButton); deliverAll()")
        self.assertEqual([l["subject"] for l in letters(self.lua)], ["Mats [1/3]", "Mats [2/3]", "Mats [3/3]"])

    def test_money_goes_with_the_first_letter_after_the_question(self):
        self.attach(1, 2)
        form(self.lua, money=5000)
        self.lua.execute("click(SendMailMailButton)")
        self.assertEqual(self.lua.eval("#sent"), 0)
        self.assertEqual(self.lua.eval("shownPopup"), "MAIL_SEND_MONEY")
        self.lua.execute("acceptPopup(); deliverAll()")
        self.assertEqual([l.get("money") for l in letters(self.lua)], [5000, None])

    def test_cod_goes_on_each_letter(self):
        self.attach(1, 2)
        form(self.lua, money=700, cod=True)
        self.assertEqual(self.lua.eval("SendMailMoneyText:GetText()"), "C.O.D. each mail:")
        self.lua.execute("click(SendMailMailButton); deliverAll()")
        self.assertEqual(self.lua.eval("shownPopup"), None)
        self.assertEqual([l.get("cod") for l in letters(self.lua)], [700, 700])

    def test_a_letter_without_items(self):
        form(self.lua, subject="Hello")
        self.lua.execute("SendMailBodyEditBox:SetText('Hi there'); click(SendMailMailButton); deliverAll()")
        self.assertEqual([(l["subject"], l["body"]) for l in letters(self.lua)], [("Hello", "Hi there")])

    def test_each_mail_error_stops_and_keeps_the_rest_attached(self):
        for err in ("ERR_MAIL_TO_SELF", "ERR_PLAYER_WRONG_FACTION", "ERR_MAIL_TARGET_NOT_FOUND", "ERR_MAIL_REACHED_CAP"):
            lua = load(setup=ITEMS)
            for s in (1, 2):
                lua.execute(f"rightClickBag(0, {s})")
            form(lua, to="Nobody")
            lua.execute(f"click(SendMailMailButton); refuse({err}); deliverAll()")
            self.assertEqual(lua.eval("#sent"), 1, err)
            self.assertEqual(lua.eval("attached"), None, err + ": the item went back to its bag")
            self.assertEqual(lua.eval("locked(cloth) and locked(ore)"), True, err)
            self.assertTrue(slots(lua).startswith("icon:Linen Cloth,icon:Copper Ore,"), err)

    def test_the_next_letter_goes_a_frame_after_the_last_ones_success(self):
        """Mailroom sent the next letter on the next frame; inside MAIL_SEND_SUCCESS
        the client is still finishing the last one."""
        self.attach(1, 2)
        form(self.lua)
        self.lua.execute("click(SendMailMailButton); fire('MAIL_SEND_SUCCESS')")
        self.assertEqual(self.lua.eval("#sent"), 1, "not inside the event")
        self.lua.execute("step(0)")
        self.assertEqual(self.lua.eval("#sent"), 2)

    def test_a_failure_between_letters_does_not_stop_the_send(self):
        self.attach(1, 2)
        form(self.lua)
        self.lua.execute("click(SendMailMailButton); fire('MAIL_SEND_SUCCESS'); fire('MAIL_FAILED'); step(0); deliverAll()")
        self.assertEqual(self.lua.eval("#sent"), 2)

    def test_a_failure_with_no_message_stops_too(self):
        self.attach(1, 2)
        form(self.lua)
        self.lua.execute("click(SendMailMailButton); fire('MAIL_FAILED'); deliverAll()")
        self.assertEqual(self.lua.eval("#sent"), 1)
        self.assertTrue(slots(self.lua).startswith("icon:Linen Cloth,icon:Copper Ore,"))

    def test_a_letter_with_no_answer_stops_the_send_and_keeps_the_items(self):
        """Seen in play 2026-11-17: after Send, right-click did nothing; a send
        waiting for an answer that never came refused every change silently."""
        self.attach(1, 2)
        form(self.lua)
        self.lua.execute("chat = {}; click(SendMailMailButton); step(9.9)")
        self.assertEqual(self.lua.eval("#chat"), 0)
        self.lua.execute("step(0.2)")
        self.assertIn("server did not answer", self.lua.eval("chatText()"))
        self.assertEqual(self.lua.eval("attached"), None, "the item went back to its bag")
        self.assertTrue(slots(self.lua).startswith("icon:Linen Cloth,icon:Copper Ore,"))
        self.assertEqual(self.lua.eval("locked(cloth) and locked(ore)"), True)
        self.lua.execute("rightClickBag(0, 1)")
        self.assertTrue(slots(self.lua).startswith("icon:Copper Ore,,"), "right-click works again")
        self.lua.execute("click(SendMailMailButton); deliverAll(); step(30)")
        self.assertEqual([l["item"] for l in letters(self.lua)], ["Linen Cloth", "Copper Ore"])
        self.assertEqual(self.lua.eval("chatText()").count("did not answer"), 1, "an answered send never times out")

    def test_an_item_left_in_the_clients_hidden_slot_does_not_spoil_the_send(self):
        """Seen in play 2026-11-17: sends stalled. An item left in the client's
        one (hidden) slot was swapped onto the cursor by the first letter."""
        self.lua.execute("attached = give(2, 1, 'Leftover', 1); locks[attached] = true")  # left there before Mail could see it
        self.attach(1, 2)
        form(self.lua)
        self.lua.execute("click(SendMailMailButton); deliverAll()")
        self.assertEqual([l["item"] for l in letters(self.lua)], ["Linen Cloth", "Copper Ore"])
        self.assertEqual(self.lua.eval("cursor"), None)
        self.assertEqual(self.lua.eval("bags[2][1] ~= nil and not locks[bags[2][1].guid]"), True, "the leftover is back, free")

    def test_attaching_while_letters_go_says_so(self):
        self.attach(1)
        form(self.lua)
        self.lua.execute("chat = {}; click(SendMailMailButton); rightClickBag(0, 2)")
        self.assertIn("Wait until the letters on their way have gone.", self.lua.eval("chatText()"))

    def test_a_failure_while_nothing_is_sent_changes_nothing(self):
        self.attach(1, 2)
        self.lua.execute("fire('MAIL_FAILED')")
        self.assertTrue(slots(self.lua).startswith("icon:Linen Cloth,icon:Copper Ore,"))

    def test_an_item_sold_before_its_turn_is_skipped(self):
        self.attach(1, 2, 3)
        form(self.lua)
        self.lua.execute("click(SendMailMailButton); sell(0, 2); deliverAll()")
        self.assertEqual([l["item"] for l in letters(self.lua)], ["Linen Cloth", "Jade"])

    def test_the_name_box_keeps_the_name_and_it_is_saved(self):
        self.attach(1, 2)
        form(self.lua, to="Bagholder")
        self.lua.execute("click(SendMailMailButton); deliver()")
        self.assertEqual(self.lua.eval("SendMailNameEditBox:GetText()"), "Bagholder")
        self.lua.execute("deliverAll()")
        self.assertEqual(self.lua.eval("MailDB[\"Y'Shaarj|Horde\"].last.Claude"), "Bagholder")
        self.assertEqual(self.lua.eval("MailDB[\"Y'Shaarj|Horde\"].recent[1]"), "Bagholder")


class SendButton(unittest.TestCase):
    def setUp(self):
        self.lua = load(setup=ITEMS)

    def enabled(self):
        self.lua.execute("SendMailFrame_CanSend()")
        return self.lua.eval("SendMailMailButton:IsEnabled()")

    def test_it_needs_a_name_and_a_subject_or_an_item(self):
        form(self.lua, to="")
        self.lua.execute("rightClickBag(0, 1)")
        self.assertIsNone(self.enabled())
        form(self.lua, to="Bagholder")
        self.assertEqual(self.enabled(), 1)
        self.lua.execute("rightClickBag(0, 1)")
        self.assertIsNone(self.enabled(), "no item and no subject")
        form(self.lua, subject="Hi")
        self.assertEqual(self.enabled(), 1)

    def test_it_needs_the_money_for_every_letter(self):
        self.lua.execute("rightClickBag(0, 1); rightClickBag(0, 2); money = 59")
        form(self.lua)
        self.assertIsNone(self.enabled())
        self.lua.execute("money = 60")
        self.assertEqual(self.enabled(), 1)
        self.assertEqual(self.lua.eval("postage"), 60)

    def test_it_is_off_while_letters_go(self):
        self.lua.execute("rightClickBag(0, 1); rightClickBag(0, 2)")
        form(self.lua)
        self.lua.execute("click(SendMailMailButton)")
        self.assertIsNone(self.enabled())
        self.lua.execute("deliverAll()")
        self.assertIsNone(self.enabled(), "the name stays; a subject or an item is still needed")
        form(self.lua, subject="More")
        self.assertEqual(self.enabled(), 1)


if __name__ == "__main__":
    unittest.main()
