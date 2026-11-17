"""At rest Mail listens for the mailbox only and leaves only its own names
(spec test 9), Mail 1.0.0."""
import unittest
import wowkit
from mail_env import load, MOCK, ROOT

GLOBALS = ["MailDB", "MailOpenAllButton"]
# Client functions Mail takes over, each calling the client's own when it is not Mail's turn.
TAKEN = ["ContainerFrameItemButton_OnClick", "SendMailFrame_Update"]


class AtRest(unittest.TestCase):
    def test_only_the_mailbox_is_heard_at_rest(self):
        lua = load(show=False)
        self.assertEqual(lua.eval("busy()"), "MAIL_SHOW,MAIL_SHOW")
        lua.execute("fire('MAIL_SHOW'); answerAll(); fire('MAIL_CLOSED')")
        self.assertEqual(lua.eval("busy()"), "MAIL_SHOW,MAIL_SHOW")

    def test_only_the_listed_globals(self):
        lua = wowkit.runtime()
        lua.execute(MOCK)
        lua.execute("before = {} for k, v in pairs(_G) do before[k] = v end")
        wowkit.load_addon(lua, ROOT, "Mail")
        new = lua.eval('''(function()
            local out = {}
            for k, v in pairs(_G) do if before[k] ~= v and k ~= '__addon_ns' and k ~= 'hooked' and not hooked[k] then out[#out + 1] = k end end
            table.sort(out)
            return table.concat(out, ',')
        end)()''')
        self.assertEqual(new.split(","), sorted(GLOBALS + TAKEN))
        self.assertEqual(list(lua.eval("(function() local o = {} for k in pairs(StaticPopupDialogs) do o[#o + 1] = k end return o end)()").values()),
                         ["MAIL_SEND_MONEY"])

    def test_without_classicapi_it_stops_with_one_message(self):
        lua = wowkit.runtime()
        lua.execute(MOCK)
        lua.execute("CLASSIC_API_VERSION = nil")
        with self.assertRaises(Exception) as raised:
            wowkit.load_addon(lua, ROOT, "Mail")
        self.assertIn("Mail needs ClassicAPI.", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
