"""What the inbox rows and the title show (the user's answer of 2026-11-17:
every extra kept), Mail 1.0.0."""
import unittest
from mail_env import load


class Rows(unittest.TestCase):
    def setUp(self):
        self.lua = load(setup='''
            mail({ sender = "Orgrimmar Auction House", subject = "Auction successful: Ore", money = 5 })
            mail({ sender = "Bob", subject = "Back", returned = 1, item = { "Ore", 1 } })
            mail({ sender = "Ann", subject = "Marks", item = { "Warsong Gulch Mark of Honor", 3 } })
            mail({ sender = "Joe", subject = "Auction won: Sword", item = { "Sword", 1 } })
            for i = 1, 6 do mail({ sender = "S" .. i, money = 1 }) end''')
        self.lua.execute("InboxFrame_Update()")

    def badge(self, row, kind):
        return self.lua.eval(f'''(function()
            for _, w in ipairs(widgets) do
                if w.parent == MailItem{row}ExpireTime and w.kind == "Frame" then
                    for _, t in ipairs(widgets) do
                        if t.parent == w and t.texture == "Interface\\\\AddOns\\\\Mail\\\\{kind}" then return w:IsShown() end
                    end
                end
            end
        end)()''')

    def test_the_count_badge_shows_stacks_only(self):
        counts = self.lua.eval('''(function()
            local out = {}
            for i = 1, 7 do
                for _, w in ipairs(widgets) do
                    if w.parent == _G["MailItem" .. i .. "Button"] and w.kind == "FontString" then out[i] = w.text end
                end
            end
            return out
        end)()''')
        self.assertEqual([counts[i] for i in range(1, 5)], ["", "", 3, ""])

    def test_returned_and_auction_marks(self):
        self.assertEqual(self.badge(1, "Auction"), 1)
        self.assertEqual(self.badge(2, "Returned"), 1)
        self.assertEqual(self.badge(2, "Auction"), None)
        self.assertEqual(self.badge(4, "Auction"), 1, "an auction subject counts too")
        self.assertEqual(self.badge(3, "Returned"), None)

    def test_the_title_has_the_page_and_the_marks(self):
        self.assertEqual(self.lua.eval("InboxTitleText:GetText()"), "Inbox [1/2] - 3 marks")
        self.lua.execute('mail({ sender = "X", item = { "Alterac Valley Mark of Honor", 1 } }); InboxFrame_Update()')
        self.assertEqual(self.lua.eval("InboxTitleText:GetText()"), "Inbox [1/2] - 4 marks (AV 1, WSG 3)")

    def test_an_empty_inbox(self):
        lua = load()
        lua.execute("InboxFrame_Update()")
        self.assertEqual(lua.eval("InboxTitleText:GetText()"), "Inbox [Empty]")


if __name__ == "__main__":
    unittest.main()
