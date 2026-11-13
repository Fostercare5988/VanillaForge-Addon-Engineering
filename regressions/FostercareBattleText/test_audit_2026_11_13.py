"""Reproductions for the 2026-11-13 audit (.private/audit-FostercareBattleText-2026-11-13.md).

Each bug test states the wanted behaviour and fails on 2.1.0 (44b0d6e).
Lua model only (_fbt_runtime.py); not in-game proof.
"""
import unittest

import _fbt_runtime as m

TWO_PROFILES = '''
FostercareBattleTextDB = {UserDisabled = false, Profiles = {Default = {}, Raid = {}}}
'''


def display(lua):
    lua.execute("FBT.CombatEventsHandler = RealCombatEventsHandler")


def texts(lua, area):
    return list(lua.eval(f'''(function()
      local out = {{}}
      for _, slot in ipairs(FBT.scrollAreas.{area}.Slots) do
        if slot.IsActive then table.insert(out, slot.FontObject.text) end
      end
      return out end)()''').values())


class ProfilePerCharacter(unittest.TestCase):  # P2-1
    # The profile in use was one account-wide key: picking a profile on one
    # character switched every character of the account. Modern MSBT keeps
    # the choice per character (MSBTProfiles_SavedVarsPerChar).

    def test_each_character_uses_its_own_profile(self):
        lua = m.runtime(TWO_PROFILES + 'FostercareBattleTextCharDB = {CurrentProfile = "Raid"}')
        self.assertEqual(lua.eval("FBT.CurrentProfile == FostercareBattleTextDB.Profiles.Raid"), True)
        lua.execute('FBT.SelectProfile("Default")')
        self.assertEqual(lua.eval("FostercareBattleTextCharDB.CurrentProfile"), "Default")
        # Nothing account-wide changes, so another character keeps its choice.
        self.assertIsNone(lua.eval("FostercareBattleTextDB.CurrentProfile"))

    def test_the_old_account_choice_becomes_this_characters(self):
        lua = m.runtime(TWO_PROFILES + 'FostercareBattleTextDB.CurrentProfile = "Raid"')
        self.assertEqual(lua.eval("FostercareBattleTextCharDB.CurrentProfile"), "Raid")
        self.assertEqual(lua.eval("FBT.CurrentProfile == FostercareBattleTextDB.Profiles.Raid"), True)
        self.assertIsNone(lua.eval("FostercareBattleTextDB.CurrentProfile"))

    def test_a_deleted_profile_falls_back_to_default(self):
        lua = m.runtime(TWO_PROFILES + 'FostercareBattleTextCharDB = {CurrentProfile = "Gone"}')
        self.assertEqual(lua.eval("FostercareBattleTextCharDB.CurrentProfile"), "Default")


class Overheal(unittest.TestCase):  # P2-2
    # Heals showed their whole amount: the log's overhealing (accurate for you
    # and your group, ClassicAPI API.md "COMBAT_LOG_EVENT_UNFILTERED") was
    # dropped. Modern MSBT shows the effective heal with the overheal after it,
    # and skips heal-over-time ticks that heal nothing.

    def heal(self, lua, sub, amount, over, name="Lesser Heal"):
        lua.execute(f'CL("{sub}", "0xHEALER", "Priest", "0xPLAYER", "Hero", 2050, "{name}", 2, {amount}, {over}, 0)')

    def test_a_heal_shows_what_it_healed_and_its_overheal(self):
        lua = m.runtime()
        display(lua)
        self.heal(lua, "SPELL_HEAL", 500, 200)
        lua.execute("RunTimers()")
        shown = texts(lua, "Incoming")
        self.assertEqual(len(shown), 1)
        self.assertIn("+300 (Priest)", shown[0])
        self.assertIn("<200>", shown[0])

    def test_no_overheal_trailer_without_partial_effects(self):
        lua = m.runtime()
        display(lua)
        lua.execute("FBT.CurrentProfile.ShowPartialEffects = false")
        self.heal(lua, "SPELL_HEAL", 500, 200)
        lua.execute("RunTimers()")
        self.assertEqual(texts(lua, "Incoming"), ["+300 (Priest)"])

    def test_a_tick_that_heals_nothing_is_not_shown(self):
        lua = m.runtime()
        display(lua)
        self.heal(lua, "SPELL_PERIODIC_HEAL", 150, 150, "Renew")
        lua.execute("RunTimers()")
        self.assertEqual(texts(lua, "Incoming"), [])
        self.heal(lua, "SPELL_PERIODIC_HEAL", 150, 50, "Renew")
        lua.execute("RunTimers()")
        shown = texts(lua, "Incoming")
        self.assertEqual(len(shown), 1)
        self.assertIn("+100 (Priest)", shown[0])

    def test_a_heal_with_no_overheal_is_unchanged(self):
        lua = m.runtime()
        display(lua)
        self.heal(lua, "SPELL_HEAL", 500, 0)
        lua.execute("RunTimers()")
        self.assertEqual(texts(lua, "Incoming"), ["+500 (Priest)"])


if __name__ == "__main__":
    unittest.main()
