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
          CL("SPELL_DAMAGE","0xF13000AAAA","Ogre","0x0000BBBB","Ally",133,"Fireball",4,500,0,4)
          CL("SWING_DAMAGE","0x0000BBBB","Ally","0xF13000AAAA","Ogre",120,0,1)
        end
        ''')
        g = lua.globals()
        self.assertEqual(len(g.sent), 0)
        self.assertEqual(g.calls["string.lower"], None, "string.lower per foreign event")
        self.assertEqual(g.calls["CombatLogGetCurrentEventInfo"], None, "unpacked a foreign event")


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
        lua.execute('sent={}; CL("SPELL_MISSED","0xPLAYER","Hero","0xENEMY","Twin",133,"Fireball",4,"DEFLECT")')
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
          Suppressions={MSBT_SUPPRESSION_ROGUE_VIGOR={Enabled=false, SearchPattern="Vigor"},
            MSBT_SUPPRESSION_WISDOM_MANA_GAINS={Enabled=true, SearchPattern="+[35][039] Mana"}}}}}
        ''')
        p = lua.globals().MikSBT_Save.Profiles.Default
        self.assertIsNone(p.ShowOverheals)
        self.assertIsNone(p.ShowVigorGains)
        self.assertIsNone(p.CreationVersion)
        self.assertIsNone(p.EventSettings.MSBT_EVENTTYPE_NOTIFICATION_ITEM_BUFF)
        self.assertTrue(p.Suppressions.MSBT_SUPPRESSION_ROGUE_VIGOR.Enabled)
        self.assertEqual(p.Suppressions.MSBT_SUPPRESSION_WISDOM_MANA_GAINS.SearchPattern, "Judgement of Wisdom")
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


RECORD_TRIGGERS = '''
fired={}; MikSBT.TriggerHandler=function(e) table.insert(fired, e.TriggerKey) end
'''


class EventTriggers(unittest.TestCase):  # P3-3
    def test_aura_trigger_fires_from_the_aura_event_not_chat(self):
        lua = m.runtime()
        lua.execute(RECORD_TRIGGERS + '''
        spellNamesMock[8516]="Windfury Totem"
        Fire("CHAT_MSG_SPELL_PERIODIC_SELF_BUFFS", "You gain Windfury Totem.")
        fromChat = table.getn(fired)
        CL("SPELL_AURA_APPLIED_DOSE", "0xPLAYER", "Hero", "0xPLAYER", "Hero", 8516, "Windfury Totem", 8, "BUFF", 2)
        CL("SPELL_AURA_APPLIED", "0xPLAYER", "Hero", "0xPLAYER", "Hero", 8516, "Windfury Totem", 8, "BUFF")
        ''')
        self.assertEqual(lua.globals().fromChat, 0, "trigger still reads chat text")
        self.assertEqual(list(lua.globals().fired.values()), ["MSBT_TRIGGER_WINDFURY"])

    def test_dodge_and_parry_triggers(self):
        lua = m.runtime()
        lua.execute(RECORD_TRIGGERS + '''
        local function add(key, kind)
          MikSBT.CurrentProfile.Triggers[key] = {EventSettings={Show=true, Message=key,
            FontSettings={Color={r=1,g=1,b=1}, Normal={FontIndex=0,OutlineIndex=0,FontSize=0}}},
            TriggerSettings={TriggerType=kind}}
        end
        add("DODGE", MikCEH.TRIGGERTYPE_YOU_DODGE); add("PARRY", MikCEH.TRIGGERTYPE_YOU_PARRY)
        add("TARGET", MikCEH.TRIGGERTYPE_TARGET_DODGES); MikSBT.RegisterTriggers()
        CL("SWING_MISSED", "0xENEMY", "Twin", "0xPLAYER", "Hero", "DODGE")
        CL("SWING_MISSED", "0xENEMY", "Twin", "0xPLAYER", "Hero", "PARRY")
        CL("SPELL_MISSED", "0xENEMY", "Twin", "0xPLAYER", "Hero", 133, "Fireball", 4, "PARRY")
        CL("SWING_MISSED", "0xPLAYER", "Hero", "0xENEMY", "Twin", "DODGE")
        CL("SPELL_MISSED", "0xPLAYER", "Hero", "0xENEMY", "Twin", 78, "Heroic Strike", 1, "DODGE")
        CL("SWING_MISSED", "0xENEMY", "Twin", "0xOTHER", "Ally", "DODGE")        -- not you
        CL("SPELL_MISSED", "0xENEMY", "Twin", "0xPLAYER", "Hero", 133, "Fireball", 4, "DEFLECT")
        ''')
        self.assertEqual(list(lua.globals().fired.values()), ["DODGE", "PARRY", "PARRY", "TARGET", "TARGET"])

    def test_saved_chat_triggers_move_to_event_types(self):
        lua = m.runtime(saved='''
        local function chat(events, patterns) return {EventSettings={Show=true, Message="x",
          FontSettings={Color={r=1,g=1,b=1}, Normal={FontIndex=0,OutlineIndex=0,FontSize=0}}},
          TriggerSettings={TriggerType=6, Classes={WARRIOR=true}, Stance=1, TriggerEvents=events, SearchPatterns=patterns}} end
        MikSBT_Save = {UserDisabled=false, CurrentProfile="Default", Profiles={Default={Triggers={
          MSBT_TRIGGER_OVERPOWER=chat({"CHAT_MSG_COMBAT_SELF_MISSES"}, {"VSDODGESELFOTHER", "SPELLDODGEDSELFOTHER"}),
          MSBT_TRIGGER_CLEARCAST=chat({"CHAT_MSG_SPELL_PERIODIC_SELF_BUFFS"}, {"You gain Clearcasting."}),
          MSBT_TRIGGER_RIPOSTE=chat({"CHAT_MSG_COMBAT_CREATURE_VS_SELF_MISSES"}, {"my own pattern"})}}}}
        ''')
        t = lua.globals().MikSBT_Save.Profiles.Default.Triggers
        ceh = lua.globals().MikCEH
        self.assertEqual(t.MSBT_TRIGGER_OVERPOWER.TriggerSettings.TriggerType, ceh.TRIGGERTYPE_TARGET_DODGES)
        self.assertEqual(t.MSBT_TRIGGER_OVERPOWER.TriggerSettings.Stance, 1)
        self.assertIsNone(t.MSBT_TRIGGER_OVERPOWER.TriggerSettings.SearchPatterns)
        self.assertEqual(t.MSBT_TRIGGER_CLEARCAST.TriggerSettings.TriggerType, ceh.TRIGGERTYPE_AURA_GAIN)
        self.assertEqual(t.MSBT_TRIGGER_CLEARCAST.TriggerSettings.AuraName, "Clearcasting")
        # 2026-10-27: the Search Pattern type is retired; a customised default goes back to its default.
        self.assertEqual(t.MSBT_TRIGGER_RIPOSTE.TriggerSettings.TriggerType, ceh.TRIGGERTYPE_YOU_PARRY)


class TriggerEditor(unittest.TestCase):  # P3-3, ForgeUI trigger editor
    def test_aura_trigger_edits_its_aura_name(self):
        lua = m.runtime()
        lua.execute('''
        MikSBTOpt.EditTrigger("MSBT_TRIGGER_WINDFURY")
        assert(MSBT_TriggerAura:IsShown() and MSBT_TriggerAura:GetText() == "Windfury Totem")
        assert(not MSBT_TriggerThreshold:IsShown() and MSBT_TriggerPattern1 == nil)
        MSBT_TriggerAura:SetText("Windfury Weapon")
        MSBT_TriggerSave:Click()
        local t = MikSBT.CurrentProfile.Triggers.MSBT_TRIGGER_WINDFURY.TriggerSettings
        assert(t.TriggerType == 7 and t.AuraName == "Windfury Weapon" and t.SearchPatterns == nil)
        MikSBTOpt.EditTrigger("MSBT_TRIGGER_LOW_HEALTH")
        assert(MSBT_TriggerThreshold:IsShown() and not MSBT_TriggerStance:IsShown())
        MSBT_TriggerSave:Click()
        assert(MikSBT.CurrentProfile.Triggers.MSBT_TRIGGER_LOW_HEALTH.TriggerSettings.Threshold == 40)
        ''')

    def test_cancel_keeps_the_saved_trigger(self):
        lua = m.runtime()
        lua.execute('''
        MikSBTOpt.EditTrigger("MSBT_TRIGGER_EXECUTE")
        MSBT_TriggerTypeNext:Click(); MSBT_TriggerAllClasses:Click()
        MSBT_TriggerCancel:Click()
        local t = MikSBT.CurrentProfile.Triggers.MSBT_TRIGGER_EXECUTE.TriggerSettings
        assert(t.TriggerType == 4 and t.Classes.WARRIOR and t.Threshold == 20)
        ''')


class CombatLogSource(unittest.TestCase):  # item 1: the combat log is the only combat source
    def events(self, code):
        lua = m.runtime()
        lua.execute("sent={}; " + code)
        return lua, [dict(e.items()) for e in lua.globals().sent.values()]

    def test_melee_hit_crit_and_partials(self):
        lua, got = self.events('''
        CL("SWING_DAMAGE", "0xPLAYER", "Hero", "0xENEMY", "Twin", 150, 0, 1, nil, nil, nil, 1)
        CL("SWING_DAMAGE", "0xENEMY", "Twin", "0xPLAYER", "Hero", 90, 0, 1, nil, 30, nil, nil, nil, 1)
        CL("SWING_DAMAGE", "0xPLAYER", "Hero", "0xENEMY", "Twin", 60, 0, 1, nil, nil, 20, nil, 1)
        ''')
        c = lua.globals().MikCEH
        self.assertEqual([(e["DirectionType"], e["Amount"], e["HitType"], e.get("EffectName"), e.get("Name")) for e in got],
                         [(c.DIRECTIONTYPE_PLAYER_OUTGOING, 150, c.HITTYPE_CRIT, None, "Twin"),
                          (c.DIRECTIONTYPE_PLAYER_INCOMING, 90, c.HITTYPE_NORMAL, None, "Twin"),
                          (c.DIRECTIONTYPE_PLAYER_OUTGOING, 60, c.HITTYPE_NORMAL, None, "Twin")])
        self.assertEqual(got[1]["PartialActionType"], c.PARTIALACTIONTYPE_CRUSHING)  # crushing wins over block
        self.assertEqual(got[2]["PartialActionType"], c.PARTIALACTIONTYPE_GLANCING)

    def test_spells_dots_and_partial_resist(self):
        lua, got = self.events('''
        CL("SPELL_DAMAGE", "0xPLAYER", "Hero", "0xENEMY", "Twin", 133, "Fireball", 4, 400, 0, 4, 100)
        CL("SPELL_PERIODIC_DAMAGE", "0xPLAYER", "Hero", "0xENEMY", "Twin", 172, "Corruption", 32, 80, 0, 32)
        CL("SPELL_DAMAGE", "0xENEMY", "Twin", "0xPLAYER", "Hero", 116, "Frostbolt", 16, 0, 0, 16, nil, nil, 250)
        ''')
        c = lua.globals().MikCEH
        self.assertEqual([(e["EffectName"], e["Amount"], e["HitType"], e["DamageType"], e["SpellId"]) for e in got],
                         [("Fireball", 400, c.HITTYPE_NORMAL, c.DAMAGETYPE_FIRE, 133),
                          ("Corruption", 80, c.HITTYPE_OVER_TIME, c.DAMAGETYPE_SHADOW, 172),
                          ("Frostbolt", 0, c.HITTYPE_NORMAL, c.DAMAGETYPE_FROST, 116)])
        self.assertEqual((got[0]["PartialActionType"], got[0]["PartialAmount"]), (c.PARTIALACTIONTYPE_RESIST, 100))
        self.assertEqual(got[2]["ActionType"], c.ACTIONTYPE_ABSORB)  # fully absorbed

    def test_heals_power_environment_shield_and_pet(self):
        lua, got = self.events('''
        CL("SPELL_HEAL", "0xPLAYER", "Hero", "0xPLAYER", "Hero", 2061, "Flash Heal", 2, 900, 0, 0, 1)
        CL("SPELL_PERIODIC_HEAL", "0xOTHER", "Ally", "0xPLAYER", "Hero", 139, "Renew", 2, 120, 0, 0)
        CL("SPELL_ENERGIZE", "0xPLAYER", "Hero", "0xPLAYER", "Hero", 29166, "Innervate", 8, 300, 0)
        CL("SPELL_ENERGIZE", "0xPLAYER", "Hero", "0xPLAYER", "Hero", 1, "Focus thing", 1, 30, 2)
        CL("ENVIRONMENTAL_DAMAGE", nil, nil, "0xPLAYER", "Hero", "FALLING", 220, 0, 1)
        CL("DAMAGE_SHIELD", "0xPLAYER", "Hero", "0xENEMY", "Twin", 0, nil, 8, 18, 0, 8)
        CL("SWING_DAMAGE", "0xPET", "Wolf", "0xENEMY", "Twin", 40, 0, 1)
        ''')
        c = lua.globals().MikCEH
        self.assertEqual(len(got), 6)  # focus is not shown
        self.assertEqual((got[0]["DirectionType"], got[0]["HealType"], got[0]["Amount"]),
                         (c.DIRECTIONTYPE_PLAYER_INCOMING, c.HEALTYPE_CRIT, 900))  # self-heal shown once
        self.assertEqual((got[1]["HealType"], got[1]["Name"]), (c.HEALTYPE_OVER_TIME, "Ally"))
        self.assertEqual((got[2]["Amount"], got[2]["EffectName"], got[2]["IsSpellManaGain"]), ("300 Mana", "Innervate", True))
        self.assertEqual((got[3]["ActionType"], got[3]["Amount"]), (c.ACTIONTYPE_FALLING, 220))
        self.assertEqual((got[4]["EffectName"], got[4]["DamageType"], got[4]["DirectionType"]),
                         ("Damage Shield", c.DAMAGETYPE_NATURE, c.DIRECTIONTYPE_PLAYER_OUTGOING))
        self.assertEqual(got[5]["DirectionType"], c.DIRECTIONTYPE_PET_OUTGOING)

    def test_auras_stacks_and_fades(self):
        lua, got = self.events('''
        CL("SPELL_AURA_APPLIED", "0xENEMY", "Twin", "0xPLAYER", "Hero", 11597, "Sunder Armor", 1, "DEBUFF")
        CL("SPELL_AURA_APPLIED_DOSE", "0xENEMY", "Twin", "0xPLAYER", "Hero", 11597, "Sunder Armor", 1, "DEBUFF", 2)
        CL("SPELL_AURA_REMOVED_DOSE", "0xENEMY", "Twin", "0xPLAYER", "Hero", 11597, "Sunder Armor", 1, "DEBUFF", 1)
        CL("SPELL_AURA_REMOVED", "0xENEMY", "Twin", "0xPLAYER", "Hero", 11597, "Sunder Armor", 1, "DEBUFF")
        CL("SPELL_AURA_APPLIED", "0xPLAYER", "Hero", "0xENEMY", "Twin", 11597, "Sunder Armor", 1, "DEBUFF")
        ''')
        c = lua.globals().MikCEH
        self.assertEqual([e["NotificationType"] for e in got],
                         [c.NOTIFICATIONTYPE_DEBUFF, c.NOTIFICATIONTYPE_DEBUFF, c.NOTIFICATIONTYPE_BUFF_FADE])


class SettingsWindow(unittest.TestCase):  # item 2: ForgeUI settings write the profile
    def test_rows_inline_edit_filters_areas_and_profiles(self):
        lua = m.runtime()
        lua.execute('''
        local p = MikSBT.CurrentProfile
        MikSBTOpt.ShowTab(3)
        MSBT_IncomingRow1Show:Click(); assert(p.EventSettings.MSBT_EVENTTYPE_INCOMING_DAMAGE.Show == false)
        MSBT_IncomingRow1Message:Click(); assert(MSBT_InlineEdit:IsShown())
        MSBT_InlineEdit:SetText("-%a!"); MSBT_InlineEdit:PressEnter()
        assert(p.EventSettings.MSBT_EVENTTYPE_INCOMING_DAMAGE.Message == "-%a!" and not MSBT_InlineEdit:IsShown())
        MSBT_IncomingRow2Message:Click(); MSBT_InlineEdit:SetText("lost"); MSBT_InlineEdit:PressEscape()
        assert(p.EventSettings.MSBT_EVENTTYPE_INCOMING_MISS.Message ~= "lost")
        MSBT_IncomingRowPagerNext:Click(); assert(MSBT_IncomingRow1ShowText:GetText() ~= "Melee Damage")

        MikSBTOpt.ShowTab(5); MSBT_NotificationRow1Sticky:Click()
        assert(p.EventSettings.MSBT_EVENTTYPE_NOTIFICATION_DEBUFF.IsSticky == true)

        MikSBTOpt.ShowTab(7); local before = 0; for _ in pairs(p.Suppressions) do before = before + 1 end
        MSBT_FilterAdd:Click(); local after = 0; for _ in pairs(p.Suppressions) do after = after + 1 end
        assert(after == before + 1)

        MikSBTOpt.ShowTab(2); MSBT_Area2:Click(); MSBT_AreaStyle3:Click(); MSBT_AreaDirection2:Click()
        assert(p.DisplaySettings.Outgoing.AnimationStyle == 3 and p.DisplaySettings.Outgoing.ScrollDirection == 2)
        assert(p.DisplaySettings.Incoming.AnimationStyle == 1)

        MikSBTOpt.ShowTab(8); MSBT_ProfileName:SetText("Raid"); MSBT_ProfileCreate:Click()
        assert(MikSBT_Save.Profiles.Raid and MikSBT_Save.CurrentProfile == "Default")
        for i = 1, 10 do local row = getglobal("MSBT_ProfileRow" .. i); if row.name == "Raid" then getglobal("MSBT_ProfileRow" .. i .. "Delete"):Click() end end
        assert(MikSBT_Save.Profiles.Raid == nil)
        ''')


if __name__ == "__main__":
    unittest.main()
