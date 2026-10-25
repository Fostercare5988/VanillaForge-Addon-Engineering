"""Reproductions for the 2026-10-25 MSBT audit (.private/audit-MikScrollingBattleText-2026-10-25.md).

Each test states the desired behaviour and fails on MSBT 1.0.1 (0802282).
Self-contained Lua model (_msbt_runtime.py); no client MPQs. Not in-game proof.
"""
import unittest

import _msbt_runtime as m

PLAYER_FLAGS = 0x400 + 0x100 + 0x40 + 0x8  # enemy player, outsider
NPC_FLAGS = 0x800 + 0x200 + 0x40 + 0x8     # hostile NPC


class KillingBlows(unittest.TestCase):  # P2-1
    def kill(self, lua, name, guid, flags):
        lua.execute(f'''
        sent={{}}
        Fire("COMBAT_LOG_EVENT_UNFILTERED", 1, "PARTY_KILL", nil, "0xPLAYER", "Hero", 0x511, 0,
             "{guid}", "{name}", {flags}, 0)
        Fire("CHAT_MSG_COMBAT_HOSTILE_DEATH", "You have slain {name}!")
        ''')
        return [e.NotificationType for e in lua.globals().sent.values()]

    def test_untargeted_enemy_player_is_a_player_kill(self):
        # An AoE kill on a player you never targeted (battlegrounds).
        lua = m.runtime()
        kinds = self.kill(lua, "Bob", "0xBOB", PLAYER_FLAGS)
        ceh = lua.globals().MikCEH
        self.assertEqual(kinds, [ceh.NOTIFICATIONTYPE_PC_KILLING_BLOW])

    def test_npc_sharing_a_targeted_players_name_is_an_npc_kill(self):
        lua = m.runtime()
        lua.execute('Fire("PLAYER_TARGET_CHANGED")')  # target is the enemy player "Twin"
        kinds = self.kill(lua, "Twin", "0xF130001234", NPC_FLAGS)
        ceh = lua.globals().MikCEH
        self.assertEqual(kinds, [ceh.NOTIFICATIONTYPE_NPC_KILLING_BLOW])


class SharedClientState(unittest.TestCase):  # P2-2
    def test_enabling_msbt_leaves_combat_log_cvar_alone(self):
        lua = m.runtime()
        lua.execute('cvars={}; MikSBT.SetOptionUserDisabled(true); MikSBT.SetOptionUserDisabled(false)')
        self.assertIsNone(lua.globals().cvars["CombatLogPeriodicSpells"])


class ForeignCombatHotPath(unittest.TestCase):  # P2-3
    def test_nearby_combat_between_others_allocates_no_strings(self):
        lua = m.runtime()
        lua.execute('''
        calls={}; sent={}
        for i=1,100 do
          Fire("SPELL_DAMAGE_EVENT_OTHER","0xF13000AAAA","0x0000BBBB",133,500,"0,0,0",0,2,"2,0,0,0")
          Fire("AUTO_ATTACK_OTHER","0x0000BBBB","0xF13000AAAA",120,0,1,1,0,0,0)
        end
        ''')
        g = lua.globals()
        self.assertEqual(len(g.sent), 0)
        self.assertEqual(g.calls["string.lower"], None, "string.lower per foreign event")


class ManaRegenText(unittest.TestCase):  # P3-4
    def test_observed_mana_gain_does_no_name_lookups(self):
        lua = m.runtime()
        lua.execute('''
        MikSBT.CurrentProfile.ShowAllManaGains=true; MikCEH.ResetManaBaseline()
        MikSBT.CombatEventsHandler=RealCombatEventsHandler
        units.player.mana=147; calls={}
        Fire("UNIT_MANA","player"); RunTimers()
        ''')
        g = lua.globals()
        self.assertIsNone(g.calls["GetSpellIdForName"], "spell lookup for a regen tick")
        self.assertIsNone(g.calls["GetItemInfo"], "item lookup for a regen tick")


class DeflectText(unittest.TestCase):  # P3-5
    def test_deflect_is_not_reported_as_reflect(self):
        lua = m.runtime()
        lua.execute('sent={}; Fire("SPELL_MISS_SELF","0xPLAYER","0xENEMY",133,9)')
        g = lua.globals()
        self.assertEqual(len(g.sent), 1)
        self.assertNotEqual(g.sent[1].ActionType, g.MikCEH.ACTIONTYPE_REFLECT)


class StickyHoldWrites(unittest.TestCase):  # P3-13
    def test_still_sticky_writes_nothing_while_holding(self):
        lua = m.runtime()
        lua.execute('''
        MikSBT.DisplayMessage("held", MikSBT.DISPLAYTYPE_NOTIFICATION, true)
        local frame = MSBTFrameNotification
        writes = 0
        for i = 1, 20 do
          local font = getglobal("MSBTFrameNotificationText" .. i)
          for _, k in ipairs({"SetPoint", "SetAlpha", "SetTextHeight", "SetWidth", "SetHeight"}) do
            font[k] = function() writes = writes + 1 end
          end
        end
        now = now + 0.5; MikSBT.OnUpdateAnimationFrame(frame)   -- enter hold
        writes = 0
        for i = 1, 100 do now = now + 0.01; MikSBT.OnUpdateAnimationFrame(frame) end
        ''')
        self.assertEqual(lua.globals().writes, 0)


class Reputation(unittest.TestCase):  # P3-4
    def test_reputation_comes_from_the_structured_event(self):
        lua = m.runtime()
        lua.execute('sent={}; Fire("FACTION_STANDING_CHANGED", 72, 3100, -25); Fire("FACTION_STANDING_CHANGED", 72, 3200, 100)')
        g = lua.globals()
        got = [(e.NotificationType, e.Amount, e.EffectName) for e in g.sent.values()]
        self.assertEqual(got, [(g.MikCEH.NOTIFICATIONTYPE_REP_LOSS, 25, "Faction72"),
                               (g.MikCEH.NOTIFICATIONTYPE_REP_GAIN, 100, "Faction72")])


class RetiredSettings(unittest.TestCase):  # P3-6, P3-7
    def test_retired_settings_are_cleared_and_vigor_choice_kept(self):
        lua = m.runtime(saved='''
        MikSBT_Save = {UserDisabled=false, CurrentProfile="Default", Profiles={Default={
          ShowOverheals=true, ShowVigorGains=false, CreationVersion=6.52,
          EventSettings={MSBT_EVENTTYPE_NOTIFICATION_ITEM_BUFF={Show=true}},
          Suppressions={MSBT_SUPPRESSION_ROGUE_VIGOR={Enabled=false, SearchPattern="Vigor"}}}}}
        ''')
        p = lua.globals().MikSBT_Save.Profiles.Default
        self.assertIsNone(p.ShowOverheals)
        self.assertIsNone(p.ShowVigorGains)
        self.assertIsNone(p.CreationVersion)
        self.assertIsNone(p.EventSettings.MSBT_EVENTTYPE_NOTIFICATION_ITEM_BUFF)
        self.assertTrue(p.Suppressions.MSBT_SUPPRESSION_ROGUE_VIGOR.Enabled)
        self.assertIsNotNone(p.EventSettings.MSBT_EVENTTYPE_INCOMING_DAMAGE)


class PowerLoss(unittest.TestCase):  # Power Losses now has a source
    def test_mana_drained_from_you_is_a_power_loss(self):
        lua = m.runtime()
        lua.execute('''
        sent={}
        Fire("COMBAT_LOG_EVENT_UNFILTERED", 1, "SPELL_PERIODIC_DRAIN", nil, "0xENEMY", "Twin", 0x548, 0,
             "0xPLAYER", "Hero", 0x511, 0, 3034, "Viper Sting", 8, 120, 0, 0)
        Fire("COMBAT_LOG_EVENT_UNFILTERED", 1, "SPELL_PERIODIC_DRAIN", nil, "0xENEMY", "Twin", 0x548, 0,
             "0xOTHER", "Ally", 0x514, 0, 3034, "Viper Sting", 8, 120, 0, 0)
        ''')
        g = lua.globals()
        got = [(e.NotificationType, e.Amount, e.EffectName) for e in g.sent.values()]
        self.assertEqual(got, [(g.MikCEH.NOTIFICATIONTYPE_POWER_LOSS, "120 Mana", "Viper Sting")])


if __name__ == "__main__":
    unittest.main()
