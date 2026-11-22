"""Chat (spec T5-T8, 4.7 "Tweaks"): arrow keys; a URL line and a "Bob:" line;
history saved at logout and back after a reload, in order; timestamps not in
the combat log; chat names coloured by the chat frame (SetChatColorNameByClass), shaman blue.
"""
import unittest
from ftr_env import load

PLAYER = "|Hplayer:Bob:12|h[Bob]|h"


def say(lua, text, frame="ChatFrame1"):
    lua.execute(f"{frame}:AddMessage({text!r}, 1, 1, 0.5, 'extra')")
    return lua.eval(f"lineOf({frame})")


def plain():
    return load("TweaksDB = { timestamps = false, classColors = false }")


class Keys(unittest.TestCase):
    def test_arrow_keys_without_alt_and_back(self):
        lua = load()
        self.assertIs(lua.eval("ChatFrameEditBox.altArrows"), False)
        lua.execute("settingsWindow.use('Tweaks_arrowKeys', false)")
        self.assertIs(lua.eval("ChatFrameEditBox.altArrows"), True)


class Addresses(unittest.TestCase):
    def test_an_address_becomes_a_link_and_the_full_stop_stays_text(self):
        line = say(plain(), "see www.octowow.com/forum.")
        self.assertEqual(line, "see |cffccccff|Hurl:www.octowow.com/forum|h[www.octowow.com/forum]|h|r.")

    def test_each_kind_of_address(self):
        lua = plain()
        for word in ("http://x.org/a?b=1", "http://user@host.com", "me@mail.com", "10.0.0.1:3724", "forum.octowow.com", "example.com/path"):
            self.assertIn(f"|Hurl:{word}|h", say(lua, "a " + word), word)

    def test_what_is_no_address(self):
        lua = plain()
        for text in ("patch 1.12.1 is out", "[1. General] hi", "the end..", "ok...lol", "e.g. this"):
            self.assertEqual(say(lua, text), text)

    def test_the_name_before_a_colon_stays_text(self):
        self.assertEqual(say(plain(), "Bob:me@mail.com"), "Bob:|cffccccff|Hurl:me@mail.com|h[me@mail.com]|h|r")

    def test_links_already_in_the_line_are_left_alone(self):
        text = "|cff1eff00|Hitem:1:0:0:0|h[Tome.of.Doom]|h|r and x.org/a"
        self.assertEqual(say(plain(), text), "|cff1eff00|Hitem:1:0:0:0|h[Tome.of.Doom]|h|r and "
                         "|cffccccff|Hurl:x.org/a|h[x.org/a]|h|r")

    def test_the_extra_values_reach_the_frame(self):
        lua = plain()
        say(lua, "hi")
        self.assertEqual(lua.eval("ChatFrame1.lines[1][5]"), "extra")

    def test_a_click_opens_the_copy_box(self):
        lua = plain()
        lua.execute("SetItemRef('url:www.x.com/a', '[www.x.com/a]', 'LeftButton')")
        self.assertEqual(lua.eval("StaticPopup1WideEditBox:GetText()"), "www.x.com/a")
        self.assertEqual(lua.eval("count('stockRef')"), 0)

    def test_shift_click_on_a_name_puts_a_link_in_the_chat_box(self):
        lua = plain()
        lua.execute("shift = true; ChatFrameEditBox:Show(); SetItemRef('player:Bob:12', '[Bob]', 'LeftButton')")
        self.assertEqual(lua.eval("ChatFrameEditBox.inserted"), "|cffffffff|Hplayer:Bob|h[Bob]|h|r")
        lua.execute("shift = false; SetItemRef('item:1:0:0:0', '[x]', 'LeftButton')")
        self.assertEqual(lua.eval("last('stockRef')"), "item:1:0:0:0")


class Lines(unittest.TestCase):
    def test_timestamps_and_switching_them_off(self):
        lua = load("TweaksDB = { classColors = false }")
        self.assertEqual(say(lua, "hi"), "|cffcccccc[13:07:42]|r hi")
        lua.execute("settingsWindow.use('Tweaks_timestamps', false)")
        self.assertEqual(say(lua, "hi"), "hi")

    def test_the_combat_log_is_left_alone(self):
        self.assertEqual(say(load(), "You hit x.org for 5.", "ChatFrame2"), "You hit x.org for 5.")

    def test_the_chat_frame_colours_names_in_every_sender_type_and_the_line_is_left_alone(self):
        lua = load("TweaksDB = { timestamps = false }")
        for kind in ("SAY", "GUILD", "WHISPER", "CHANNEL1", "CHANNEL10"):
            self.assertIs(lua.eval(f"ChatTypeInfo.{kind}.colorNameByClass"), True, kind)
        self.assertIsNone(lua.eval("ChatTypeInfo.SYSTEM.colorNameByClass"))
        self.assertEqual(say(lua, PLAYER + ": hi"), PLAYER + ": hi")

    def test_switching_names_off_sets_false_for_all_types_and_back_on(self):
        lua = load()
        lua.execute("colorNameCalls = {}; settingsWindow.use('Tweaks_classColors', false)")
        self.assertEqual(lua.eval("#colorNameCalls"), 23)
        for kind in ("SAY", "YELL", "WHISPER", "GUILD", "PARTY", "CHANNEL1", "CHANNEL7", "CHANNEL10"):
            self.assertIs(lua.eval(f"ChatTypeInfo.{kind}.colorNameByClass"), False, kind)
        lua.execute("settingsWindow.use('Tweaks_classColors', true)")
        self.assertIs(lua.eval("ChatTypeInfo.GUILD.colorNameByClass"), True)

    def test_the_option_off_at_login_sets_false(self):
        lua = load("TweaksDB = { classColors = false }")
        self.assertIs(lua.eval("ChatTypeInfo.CHANNEL3.colorNameByClass"), False)

    def test_shamans_blue_and_back(self):
        lua = load()
        self.assertEqual(lua.eval("RAID_CLASS_COLORS.SHAMAN.colorStr"), "ff2459ff")
        lua.execute("settingsWindow.use('Tweaks_blueShaman', false)")
        self.assertEqual(lua.eval("RAID_CLASS_COLORS.SHAMAN.colorStr"), "fff58cba")
        self.assertEqual(lua.eval("RAID_CLASS_COLORS.SHAMAN.r"), 0.96)


class History(unittest.TestCase):
    def test_saved_at_logout_and_back_after_a_reload_in_order(self):
        lua = plain()
        for i in range(1, 36):
            lua.execute(f"ChatFrame1:AddMessage('line {i}', 1, 1, 1)")
        lua.execute("fire('PLAYER_LOGOUT')")
        saved = lua.eval("TweaksDB.chat[1]")
        self.assertEqual(len(saved), 30)
        self.assertEqual(saved[1], "|cffb2b2b2line 35", "newest first, dimmed")
        self.assertIsNone(lua.eval("TweaksDB.chat[2]"), "the combat log is not kept")
        again = load("TweaksDB = { timestamps = false, chat = { [1] = { 'new', 'old' } } }")
        self.assertEqual([again.eval(f"lineOf(ChatFrame1, {i})") for i in (1, 2)], ["old", "new"])
        again.execute("fire('PLAYER_LOGOUT')")
        self.assertEqual(again.eval("TweaksDB.chat[1][1]"), "new", "a restored line is not dimmed twice")

    def test_off_keeps_nothing(self):
        lua = load("TweaksDB = { history = false, chat = { [1] = { 'old' } } }")
        self.assertEqual(lua.eval("ChatFrame1:GetNumMessages()"), 0)
        lua.execute("fire('PLAYER_LOGOUT')")
        self.assertIsNone(lua.eval("TweaksDB.chat"))


if __name__ == "__main__":
    unittest.main()
