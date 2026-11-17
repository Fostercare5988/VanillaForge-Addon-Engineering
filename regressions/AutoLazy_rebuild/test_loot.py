"""Rolls, bind-on-pickup warnings and the roll lines (spec K1-K4; tests 2-4).
"""
import unittest
from al_env import load

LINK = "|cff1eff00|Hitem:50203:0:0:0|h[Corrupted Sand]|h|r"


def roll(lua, item, where, roll_id=7):
    lua.execute(f"instance = {where!r}; rollItems[{roll_id}] = {item}; fire('START_LOOT_ROLL', {roll_id})")
    return lua.eval("last('RollOnLoot')")


class Rolls(unittest.TestCase):
    def test_a_listed_item_in_its_instance_rolls_the_chosen_way(self):
        lua = load()
        self.assertEqual(roll(lua, 19710, "Zul'Gurub"), "7:1")          # a Bijou: Need
        self.assertEqual(roll(lua, 50203, "The Black Morass", 8), "8:0")  # Corrupted Sand: Pass
        self.assertEqual(roll(lua, 50203, "Opening of the Dark Portal", 9), "9:0")
        lua.execute("settingsWindow.use('AutoLazy_rollScraps', 'GREED')")
        self.assertEqual(roll(lua, 22376, "Naxxramas", 10), "10:2")

    def test_manual_leaves_the_roll(self):
        self.assertIsNone(roll(load(), 20860, "Ruins of Ahn'Qiraj"))

    def test_outside_its_instance_or_unlisted_it_is_not_touched(self):
        lua = load("AutoLazyDB = { rollScarabs = 'NEED' }")
        self.assertIsNone(roll(lua, 20860, "Ahn'Qiraj"))       # AQ40's scarabs
        self.assertIsNone(roll(lua, 19710, "Kalimdor"))
        self.assertIsNone(roll(lua, 12345, "Zul'Gurub"))
        self.assertIsNone(roll(lua, None, "Zul'Gurub"))

    def test_auto_roll_off_rolls_nothing(self):
        self.assertIsNone(roll(load("AutoLazyDB = { roll = false }"), 19710, "Zul'Gurub"))


class BindOnPickup(unittest.TestCase):
    def test_a_roll_warning_is_confirmed_and_its_popup_hidden(self):
        lua = load("AutoLazyDB = { roll = false }")  # works with auto-roll off, anywhere
        lua.execute("fire('CONFIRM_LOOT_ROLL', 4, 1)")
        self.assertEqual(lua.eval("last('ConfirmLootRoll')"), "4:1")
        self.assertEqual(lua.eval("last('StaticPopup_Hide')"), "CONFIRM_LOOT_ROLL:4")

    def test_a_loot_warning_takes_each_slot_once_per_loot_window(self):
        lua = load()
        lua.execute("fire('LOOT_BIND_CONFIRM', 2) fire('LOOT_BIND_CONFIRM', 2) fire('LOOT_BIND_CONFIRM', 3)")
        self.assertEqual(lua.eval("count('LootSlot')"), 2)
        self.assertEqual(lua.eval("last('StaticPopup_Hide')"), "LOOT_BIND:3")
        lua.execute("fire('LOOT_CLOSED') fire('LOOT_BIND_CONFIRM', 2)")
        self.assertEqual(lua.eval("count('LootSlot')"), 3)

    def test_the_switch_off_leaves_both_popups(self):
        lua = load("AutoLazyDB = { confirmBind = false }")
        lua.execute("fire('CONFIRM_LOOT_ROLL', 4, 1) fire('LOOT_BIND_CONFIRM', 2)")
        self.assertEqual(lua.eval("count('ConfirmLootRoll') + count('LootSlot') + count('StaticPopup_Hide')"), 0)


class RollChat(unittest.TestCase):
    LINES = ["Rolling started on: " + LINK, "Claude has selected Need for: " + LINK,
             "You passed on: " + LINK, "Need Roll - 57 for " + LINK + " by Claude",
             "You roll a 12 (Greed) on: " + LINK, "Everyone passed on: " + LINK]
    KEPT = ["Claude won: " + LINK, "You won: " + LINK, "You receive loot: " + LINK, "You loot 5 Silver"]

    def shown(self, lua, text):
        lua.execute("forget()")
        lua.eval("chatLine")("CHAT_MSG_LOOT", text)
        return lua.eval("count('shown')")

    def test_roll_lines_leave_every_window_and_the_rest_stays(self):
        lua = load()
        for line in self.LINES:
            self.assertEqual(self.shown(lua, line), 0, line)
        for line in self.KEPT:
            self.assertEqual(self.shown(lua, line), 3, line)

    def test_the_switch_off_keeps_all(self):
        lua = load("AutoLazyDB = { hideRollChat = false }")
        for line in self.LINES:
            self.assertEqual(self.shown(lua, line), 3, line)

    def test_other_chat_is_never_looked_at(self):
        lua = load()
        lua.execute("forget()")
        lua.eval("chatLine")("CHAT_MSG_SAY", "Rolling started on: " + LINK)
        self.assertEqual(lua.eval("count('shown')"), 3)


if __name__ == "__main__":
    unittest.main()
