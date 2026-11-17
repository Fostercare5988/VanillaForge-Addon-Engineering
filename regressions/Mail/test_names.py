"""Recipient names (spec test 8), Mail 1.0.0."""
import unittest
from mail_env import load

SAVED = '''MailDB = { ["Y'Shaarj|Horde"] = { last = { Claude = "Jyskedollars" }, names = {
    Jyskedollars = 1799990000, Jade = 1799999000, Joe = 1799000000, Claude = 1799999999,
    Old = 1700000000 } } }'''


def shown(lua):
    return lua.eval('''(function()
        local out = {}
        for _, w in ipairs(widgets) do
            if w.label and w.parent and w.parent:IsShown() and w:IsShown() then out[#out + 1] = w.label.text end
        end
        return table.concat(out, ",")
    end)()''')


class Names(unittest.TestCase):
    def setUp(self):
        self.lua = load(saved=SAVED, setup='known = { "Jinx", "Joe", "Kim" }')
        self.lua.execute("MailFrameTab_OnClick(2)")

    def test_saved_names_newest_first_then_known_names_never_yourself(self):
        self.lua.execute("typeInto(SendMailNameEditBox, 'j')")
        self.assertEqual(shown(self.lua), "Jade,Jyskedollars,Joe,Jinx")
        self.assertEqual(self.lua.eval("SendMailNameEditBox:GetText()"), "Jade")
        self.assertEqual(list(self.lua.eval("SendMailNameEditBox.highlight").values()), [1, -1])
        self.assertEqual(self.lua.eval("clientGuess"), None, "the client's own guess is replaced")

    def test_tab_cycles_and_enter_takes(self):
        self.lua.execute("typeInto(SendMailNameEditBox, 'j'); run(SendMailNameEditBox, 'OnTabPressed')")
        self.assertEqual(self.lua.eval("SendMailNameEditBox:GetText()"), "Jyskedollars")
        self.lua.execute("shift = 1; run(SendMailNameEditBox, 'OnTabPressed'); run(SendMailNameEditBox, 'OnTabPressed'); shift = nil")
        self.assertEqual(self.lua.eval("SendMailNameEditBox:GetText()"), "Jinx", "Shift-Tab goes back, round the end")
        self.lua.execute("run(SendMailNameEditBox, 'OnEnterPressed')")
        self.assertEqual(shown(self.lua), "")
        self.assertEqual(self.lua.eval("SendMailSubjectEditBox.focus"), None, "Enter took the name, not the next box")
        self.lua.execute("run(SendMailNameEditBox, 'OnEnterPressed')")
        self.assertEqual(self.lua.eval("SendMailSubjectEditBox.focus"), True)

    def test_a_full_match_shows_no_list(self):
        self.lua.execute("typeInto(SendMailNameEditBox, 'Kim')")
        self.assertEqual(shown(self.lua), "")

    def test_names_unseen_for_30_days_drop_off_and_you_are_added(self):
        names = self.lua.eval("MailDB[\"Y'Shaarj|Horde\"].names")
        self.assertIsNone(names["Old"])
        self.assertEqual(names["Claude"], self.lua.eval("clock"))

    def test_the_box_starts_with_the_last_name(self):
        self.assertEqual(self.lua.eval("SendMailNameEditBox:GetText()"), "Jyskedollars")

    def test_a_typed_name_is_capitalised(self):
        self.lua.execute("SendMailNameEditBox:SetText('bAGHOLDER')")
        self.assertEqual(self.lua.eval("SendMailNameEditBox:GetText()"), "Bagholder")

    def test_a_first_login_makes_the_table(self):
        lua = load()
        self.assertEqual(lua.eval("MailDB[\"Y'Shaarj|Horde\"].names.Claude"), lua.eval("clock"))


if __name__ == "__main__":
    unittest.main()
