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


class SavedKeySweep(unittest.TestCase):  # P3-1, KNOWN_PATTERNS KP-64
    # Four retired event keys were cleared one line each, and nothing cleared
    # any other key a release left behind. One sweep clears every saved key no
    # default owns; the player's own triggers and filters keep theirs.

    def test_keys_no_default_owns_are_cleared(self):
        lua = m.runtime('''
        FostercareBattleTextDB = {UserDisabled = false, Junk = 1, Profiles = {Default = {
          OldSwitch = true,
          EventSettings = {MSBT_EVENTTYPE_INCOMING_RESIST = {Show = true}, MSBT_EVENTTYPE_OLD = {Show = true}},
          DisplaySettings = {Old = {Show = true}},
          Triggers = {MSBT_TRIGGER_CUSTOM1 = {EventSettings = {Show = false}, TriggerSettings = {TriggerType = 1}, Extra = 1}},
          Suppressions = {MSBT_SUPPRESSION_CUSTOM1 = {Enabled = true, SearchPattern = "Renew"}},
        }}}''')
        p = lua.eval("FostercareBattleTextDB.Profiles.Default")
        self.assertIsNone(lua.eval("FostercareBattleTextDB.Junk"))
        self.assertIsNone(p.OldSwitch)
        self.assertIsNone(p.EventSettings.MSBT_EVENTTYPE_INCOMING_RESIST)
        self.assertIsNone(p.EventSettings.MSBT_EVENTTYPE_OLD)
        self.assertIsNone(p.DisplaySettings.Old)
        self.assertEqual(p.Triggers.MSBT_TRIGGER_CUSTOM1.Extra, 1)
        self.assertEqual(p.Suppressions.MSBT_SUPPRESSION_CUSTOM1.SearchPattern, "Renew")
        self.assertEqual(lua.eval("FostercareBattleTextDB.UserDisabled"), False)
        self.assertEqual(p.EventSettings.MSBT_EVENTTYPE_INCOMING_DAMAGE.Show, True)


class FontsByName(unittest.TestCase):  # P3-2
    # Fonts were saved by their place in the font list, so no font could leave
    # the list without moving every later font. They are saved by name now;
    # Simhei (a 9.7 MB Chinese font no profile used) has left the list.

    SAVED = '''
    FostercareBattleTextDB = {UserDisabled = false, Profiles = {Default = {
      MasterFontSettings = {Normal = {FontIndex = 37, OutlineIndex = 2, FontSize = 20},
                            Crit = {FontIndex = 40, OutlineIndex = 2, FontSize = 26}},
      BlizzardFontSettings = {Normal = {FontIndex = 6}},
      DisplaySettings = {Incoming = {FontSettings = {Normal = {FontIndex = 31, OutlineIndex = 0, FontSize = 0}}}},
      EventSettings = {MSBT_EVENTTYPE_INCOMING_DAMAGE = {FontSettings = {Normal = {FontIndex = 0, OutlineIndex = 0, FontSize = 0}}}},
    }}}'''

    def test_saved_font_places_become_names(self):
        lua = m.runtime(self.SAVED)
        p = lua.eval("FostercareBattleTextDB.Profiles.Default")
        self.assertEqual(p.MasterFontSettings.Normal.FontName, "Inter Bold")
        self.assertEqual(p.MasterFontSettings.Crit.FontName, "Roboto Mono")
        self.assertEqual(p.BlizzardFontSettings.Normal.FontName, "Friz")
        # Simhei and "inherit" both inherit now.
        self.assertIsNone(p.DisplaySettings.Incoming.FontSettings.Normal.FontName)
        self.assertIsNone(p.EventSettings.MSBT_EVENTTYPE_INCOMING_DAMAGE.FontSettings.Normal.FontName)
        self.assertIsNone(p.MasterFontSettings.Normal.FontIndex)
        self.assertIsNone(p.EventSettings.MSBT_EVENTTYPE_INCOMING_DAMAGE.FontSettings.Normal.FontIndex)

    def test_text_uses_the_inherited_font(self):
        lua = m.runtime(self.SAVED)
        path = lua.eval('FBT.GetFontPath(FBT.scrollAreas.Incoming, FBT.CurrentProfile.EventSettings.MSBT_EVENTTYPE_INCOMING_DAMAGE, false)')
        self.assertTrue(path.endswith("Inter-Bold.ttf"), path)
        self.assertEqual(lua.eval('DAMAGE_TEXT_FONT'), "Fonts\\FRIZQT__.TTF")

    def test_the_font_editor_steps_by_name(self):
        lua = m.runtime()
        lua.execute('''
          FBT.Options.ShowTab(1); FBT_MasterFonts:Click()
          FBT_FontNormalFaceNext:Click()
        ''')
        self.assertEqual(lua.eval("FBT.CurrentProfile.MasterFontSettings.Normal.FontName"), "Inter SemiBold")
        self.assertEqual(lua.eval("FBT_FontNormalFaceText.text"), "Inter SemiBold")


class FontWrites(unittest.TestCase):  # P3-3
    def test_a_slot_sets_its_font_only_when_it_changes(self):
        lua = m.runtime()
        lua.execute('''
          setFonts = 0
          for _, area in pairs(FBT.scrollAreas) do for _, slot in ipairs(area.Slots) do
            local font = slot.FontObject
            font.SetFont = function(self, path) setFonts = setFonts + 1; self.fontPath = path end
            font.GetFont = function(self) return self.fontPath end
          end end
          for i = 1, 25 do FBT.DisplayMessage("x" .. i, FBT.DISPLAYTYPE_NOTIFICATION) end
        ''')
        # Ten scrolling slots take 25 lines of one font: one SetFont each.
        self.assertEqual(lua.eval("setFonts"), 10)


class ClassSwitches(unittest.TestCase):  # P3-4
    # General showed every character the mana and frost-resist switches. On a
    # rogue (Claude) none of them can do anything: no mana, no Frost Nova.

    def general(self, cls, maxmana):
        lua = m.runtime()
        lua.execute(f'units.player.class = "{cls}"; units.player.maxmana = {maxmana}; FBT.Options.ShowTab(1)')
        return lua

    def shown(self, lua, name):
        return lua.eval(f"{name}:IsShown() and true or false")

    def test_a_rogue_sees_no_mana_or_frost_switches(self):
        lua = self.general("ROGUE", 0)
        for name in ("FBT_ShowAllManaGains", "FBT_LowManaSound", "FBT_ResistSound"):
            self.assertFalse(self.shown(lua, name), name)
        self.assertTrue(self.shown(lua, "FBT_LowHealthSound"))
        rogue_y = lua.eval("FBT_ShowGameDamage.pt[5]")
        mage = self.general("MAGE", 100)
        for name in ("FBT_ShowAllManaGains", "FBT_LowManaSound", "FBT_ResistSound"):
            self.assertTrue(self.shown(mage, name), name)
        # The hidden switch takes no room: the next one moves up a line.
        self.assertEqual(rogue_y - mage.eval("FBT_ShowGameDamage.pt[5]"), 36)

    def test_a_priest_sees_mana_but_not_frost(self):
        lua = self.general("PRIEST", 100)
        self.assertTrue(self.shown(lua, "FBT_ShowAllManaGains"))
        self.assertTrue(self.shown(lua, "FBT_LowManaSound"))
        self.assertFalse(self.shown(lua, "FBT_ResistSound"))


if __name__ == "__main__":
    unittest.main()
