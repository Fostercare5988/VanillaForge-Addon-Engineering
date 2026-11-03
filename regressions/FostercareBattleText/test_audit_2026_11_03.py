"""Reproductions for the 2026-11-03 audit (.private/audit-FostercareBattleText-2026-11-03.md).

Each test states the wanted behaviour and fails on MSBT 1.2.2 (dc1d9dd).
Lua model only (_fbt_runtime.py); not in-game proof.
"""
import unittest

import _fbt_runtime as m


def display(lua):
    """Let the real display layer take the events again."""
    lua.execute("FBT.CombatEventsHandler = RealCombatEventsHandler")


class MergeRecovers(unittest.TestCase):  # P2-1
    def test_one_failed_message_does_not_stop_the_scroll_areas(self):
        # An error while a merged batch is shown left the merge flags set for
        # good: no incoming or outgoing text until /reload.
        lua = m.runtime()
        display(lua)
        lua.execute('''
            shown = 0
            local real, failOnce = FBT.AddAnimation, true
            FBT.AddAnimation = function(e)
              if failOnce then failOnce = false; error("boom") end
              shown = shown + 1
              return real(e)
            end
            CL("SWING_DAMAGE", "0xPLAYER", "Hero", "0xENEMY", "Twin", 100, 0, 1)
            pcall(RunTimers)
            CL("SWING_DAMAGE", "0xPLAYER", "Hero", "0xENEMY", "Twin", 120, 0, 1)
            pcall(RunTimers)
        ''')
        self.assertEqual(lua.eval("shown"), 1)


class DamageShieldName(unittest.TestCase):  # P3-1
    def test_a_named_damage_shield_shows_its_spell(self):
        # ClassicAPI names the shield (Thorns, Retribution Aura) when the owner
        # has one damage-shield aura of that school; spellId 0 otherwise.
        lua = m.runtime()
        lua.execute('''
            CL("DAMAGE_SHIELD", "0xPLAYER", "Hero", "0xENEMY", "Twin", 467, "Thorns", 8, 12, 0, 8)
            CL("DAMAGE_SHIELD", "0xPLAYER", "Hero", "0xENEMY", "Twin", 0, nil, 2, 7, 0, 2)
        ''')
        sent = lua.globals().sent
        self.assertEqual((sent[1].EffectName, sent[1].SpellId), ("Thorns", 467))
        self.assertEqual(sent[2].EffectName, "Damage Shield")


class DruidMana(unittest.TestCase):  # P2-2
    def test_mana_gains_in_a_form_show_when_they_happen(self):
        # In bear or cat form UnitMana is rage or energy, so mana was not
        # observed: the regeneration of the whole form came as one lump on
        # leaving it, or not at all.
        lua = m.runtime()
        lua.execute('''
            units.player.class = "DRUID"
            FBT.Options.ShowTab(1); FBT_ShowAllManaGains:Click()
            sent = {}
            units.player.powertype = 1; units.player.power = 0     -- bear form
            units.player.mana = 110
            Fire("UNIT_POWER_UPDATE", "player", "MANA"); Fire("UNIT_MANA", "player")
            inForm = #sent
        ''')
        self.assertEqual(lua.eval("inForm"), 1)
        self.assertEqual(lua.eval("sent[1].Amount"), "10 Mana")


class EventsOnlyWhenNeeded(unittest.TestCase):  # P3-2
    def test_no_health_or_power_events_without_triggers(self):
        # Claude's profile: every health and mana trigger off. UNIT_HEALTH for
        # the player, pet and target reached Lua all fight long for nothing.
        lua = m.runtime()
        lua.execute('''
            for _, trigger in pairs(FBT.CurrentProfile.Triggers) do trigger.EventSettings.Show = false end
            FBT.RegisterTriggers(); FBT.Combat.RegisterEvents()
        ''')
        events = lua.eval("FBT.Combat.frame.events")
        for name in ("UNIT_HEALTH", "UNIT_MANA", "UNIT_POWER_UPDATE", "PLAYER_TARGET_CHANGED"):
            self.assertIsNone(events[name], name)

    def test_a_target_trigger_takes_target_health_only(self):
        lua = m.runtime()
        lua.execute('''
            for _, trigger in pairs(FBT.CurrentProfile.Triggers) do trigger.EventSettings.Show = false end
            local execute = FBT.CurrentProfile.Triggers.MSBT_TRIGGER_EXECUTE
            execute.EventSettings.Show = true; execute.TriggerSettings.Classes = nil
            FBT.RegisterTriggers(); FBT.Combat.RegisterEvents()
        ''')
        self.assertEqual(list(lua.eval("FBT.Combat.frame.events.UNIT_HEALTH").values()), ["target"])
        self.assertTrue(lua.eval("FBT.Combat.frame.events.PLAYER_TARGET_CHANGED"))


class FilterText(unittest.TestCase):  # P3-3
    def test_filters_cost_no_pcall_per_message(self):
        # Every shown message ran two pcalls per enabled filter (Lua patterns).
        lua = m.runtime()
        display(lua)
        lua.execute('''
            local realPcall = pcall
            pcalls = 0
            pcall = function(...) pcalls = pcalls + 1; return realPcall(...) end
            for i = 1, 10 do Fire("PLAYER_REGEN_DISABLED"); Fire("PLAYER_REGEN_ENABLED") end
        ''')
        self.assertEqual(lua.eval("pcalls"), 0)

    def test_a_filter_is_plain_text(self):
        # "[Bless" was a broken Lua pattern that hid nothing; it is text now.
        lua = m.runtime()
        display(lua)
        lua.execute('''
            FBT.CurrentProfile.Suppressions.Mine = {Enabled = true, SearchPattern = "-[Bless"}
            shown = 0
            local real = FBT.GetNextAnimationDisplayInfo
            FBT.GetNextAnimationDisplayInfo = function(e) shown = shown + 1; return real(e) end
            CL("SPELL_AURA_REMOVED", "0xPAL", "Pally", "0xPLAYER", "Hero", 19740, "Blessing of Might", 2, "BUFF")
            CL("SPELL_AURA_REMOVED", "0xPAL", "Pally", "0xPLAYER", "Hero", 20217, "Kings", 2, "BUFF")
        ''')
        self.assertEqual(lua.eval("shown"), 1)


class FontEditorTitle(unittest.TestCase):  # P3-4
    def test_the_font_editor_names_the_event_in_words(self):
        lua = m.runtime()
        lua.execute('FBT.Options.ShowTab(3); FBT_IncomingRow1Font:Click()')
        self.assertEqual(lua.eval("FBT_FontEditor.title.text"), "Melee Damage")


if __name__ == "__main__":
    unittest.main()
