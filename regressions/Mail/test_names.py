"""Recipient names (spec test 8). Mail 1.0.0 (ClassicAPI 1.21.1). Your
other characters come from C_AutoComplete's AccountCharacter bit; Mail keeps
only the last ten players you mailed and each character's last recipient."""
import unittest
from mail_env import load

SAVED = '''MailDB = { ["Y'Shaarj|Horde"] = { recent = { "Jade", "Jyskedollars", "Kim" },
    last = { Claude = "Jyskedollars" } } }'''


def shown(lua):
    return lua.eval('''(function()
        local out = {}
        for _, w in ipairs(widgets) do
            if w.label and w.parent and w.parent:IsShown() and w:IsShown() then out[#out + 1] = w.label.text end
        end
        return table.concat(out, ",")
    end)()''')


def recent(lua):
    return list(lua.eval("MailDB[\"Y'Shaarj|Horde\"].recent").values())


class Names(unittest.TestCase):
    def setUp(self):
        self.lua = load(saved=SAVED, setup='known = { "Jinx", "Joe", "Jade" }')
        self.lua.execute("MailFrameTab_OnClick(2)")

    def test_mailed_names_first_then_classicapis_once_each(self):
        self.lua.execute("typeInto(SendMailNameEditBox, 'j')")
        self.assertEqual(shown(self.lua), "Jade,Jyskedollars,Jinx,Joe")
        self.assertEqual(self.lua.eval("SendMailNameEditBox:GetText()"), "Jade")
        self.assertEqual(list(self.lua.eval("SendMailNameEditBox.highlight").values()), [1, -1])
        self.assertEqual(self.lua.eval("clientGuess"), None, "the client's own guess is replaced")

    def test_your_other_characters_are_asked_for(self):
        self.lua.execute('''local Get = C_AutoComplete.GetAutoCompleteResults
            C_AutoComplete.GetAutoCompleteResults = function(t, n, c, f, include, ...) flags = include; return Get(t, n, c, f, include, ...) end
            typeInto(SendMailNameEditBox, "x")''')
        self.assertEqual(self.lua.eval("flags"), 1 + 2 + 4 + 16 + 128, "account characters, group, guild, friends, whispers; not Online")

    def test_tab_cycles_and_enter_takes(self):
        self.lua.execute("typeInto(SendMailNameEditBox, 'j'); run(SendMailNameEditBox, 'OnTabPressed')")
        self.assertEqual(self.lua.eval("SendMailNameEditBox:GetText()"), "Jyskedollars")
        self.lua.execute("shift = 1; run(SendMailNameEditBox, 'OnTabPressed'); run(SendMailNameEditBox, 'OnTabPressed'); shift = nil")
        self.assertEqual(self.lua.eval("SendMailNameEditBox:GetText()"), "Joe", "Shift-Tab goes back, round the end")
        self.lua.execute("run(SendMailNameEditBox, 'OnEnterPressed')")
        self.assertEqual(shown(self.lua), "")
        self.assertEqual(self.lua.eval("SendMailSubjectEditBox.focus"), None, "Enter took the name, not the next box")
        self.lua.execute("run(SendMailNameEditBox, 'OnEnterPressed')")
        self.assertEqual(self.lua.eval("SendMailSubjectEditBox.focus"), True)

    def test_a_full_match_shows_no_list(self):
        self.lua.execute("typeInto(SendMailNameEditBox, 'Kim')")
        self.assertEqual(shown(self.lua), "")

    def test_mailing_puts_the_name_first_and_keeps_ten(self):
        self.lua.execute('''MailFrameTab_OnClick(2); SendMailNameEditBox:SetText("Kim"); SendMailSubjectEditBox:SetText("Hi")
            click(SendMailMailButton); deliverAll()''')
        self.assertEqual(recent(self.lua), ["Kim", "Jade", "Jyskedollars"])
        self.lua.execute('''for i = 1, 12 do SendMailNameEditBox:SetText("Alt" .. string.char(96 + i))
            SendMailSubjectEditBox:SetText("Hi"); click(SendMailMailButton); deliverAll() end''')
        self.assertEqual(len(recent(self.lua)), 10)
        self.assertEqual(recent(self.lua)[0], "Altl")

    def test_the_box_starts_with_the_last_name(self):
        self.assertEqual(self.lua.eval("SendMailNameEditBox:GetText()"), "Jyskedollars")

    def test_a_typed_name_is_capitalised(self):
        self.lua.execute("SendMailNameEditBox:SetText('bAGHOLDER')")
        self.assertEqual(self.lua.eval("SendMailNameEditBox:GetText()"), "Bagholder")

    def test_nothing_is_saved_until_you_mail_someone(self):
        lua = load()
        self.assertEqual(lua.eval("next(MailDB)"), None)


if __name__ == "__main__":
    unittest.main()
