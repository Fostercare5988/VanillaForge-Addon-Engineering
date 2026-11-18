"""Cleanup 2026-10-27: MSBT keeps no chat-text triggers and counts XP itself.

- The Search Pattern trigger type (6) matched chat text. No character used it,
  so it is retired with its editor, chat event list and `/msbt search`. A
  default trigger still on it goes back to its default; others are removed.
- Experience Gains comes from PLAYER_XP_UPDATE as the change in UnitXP, so
  quest and exploration XP show too (the chat line covered kills only), and a
  level-up counts the rest of the old level plus the new.
"""
import unittest

import _fbt_runtime as m


def xp_gains(lua):
    return [e.Amount for e in lua.globals().sent.values()
            if e.NotificationType == lua.globals().FBT.Combat.NOTIFICATIONTYPE_EXPERIENCE_GAIN]


class ExperienceTests(unittest.TestCase):
    def runtime(self):
        lua = m.runtime()
        lua.execute('units.player.xp, units.player.maxxp = 100, 1000; Fire("PLAYER_ENTERING_WORLD"); sent = {}')
        return lua

    def test_any_xp_gain_shows_its_amount(self):
        lua = self.runtime()
        lua.execute('units.player.xp = 350; Fire("PLAYER_XP_UPDATE", "player")')
        self.assertEqual(xp_gains(lua), [250])

    def test_level_up_counts_both_levels(self):
        lua = self.runtime()
        lua.execute('units.player.xp, units.player.maxxp = 40, 1200; Fire("PLAYER_XP_UPDATE", "player")')
        self.assertEqual(xp_gains(lua), [940])

    def test_no_change_shows_nothing_and_chat_xp_is_not_read(self):
        lua = self.runtime()
        lua.execute('Fire("PLAYER_XP_UPDATE", "player"); '
                    'Fire("CHAT_MSG_COMBAT_XP_GAIN", "Wolf dies, you gain 50 experience.")')
        self.assertEqual(xp_gains(lua), [])
        self.assertIsNone(lua.eval('FBT.Combat.frame.events.CHAT_MSG_COMBAT_XP_GAIN'))


class RetiredSearchPatternTests(unittest.TestCase):
    def test_no_chat_event_list_or_search_command(self):
        lua = m.runtime()
        self.assertIsNone(lua.eval('FBT.Options.TRIGGER_EVENTS'))
        self.assertIsNone(lua.eval('FBT.COMMAND_SEARCH'))
        self.assertIsNone(lua.eval('FBT.Combat.EnableEventSearching'))
        self.assertIsNone(lua.eval('FBT.Combat.TRIGGERTYPE_SEARCH_PATTERN'))

    def test_editor_type_cycle_skips_the_retired_type(self):
        lua = m.runtime()
        lua.execute('''
        seen = {}
        FBT.Options.EditTrigger("MSBT_TRIGGER_LOW_HEALTH")
        for i = 1, 9 do FBT_TriggerTypeNext:Click(); table.insert(seen, FBT_TriggerType.text:GetText()) end
        ''')
        names = list(lua.eval('seen').values())
        self.assertNotIn("Search Pattern", names)
        self.assertEqual(len(set(names)), 9)


if __name__ == "__main__":
    unittest.main()
