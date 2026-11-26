"""Notices, mana gains, the alerts and the ready alerts (spec BattleText.md 4.5,
tests 5, 7, 8 and 9). BattleText 1.0, written new 2026-11-22.
"""
import unittest
from bt_env import load

RED = "|cffff0000-|r"


def notices(lua, code):
    lua.execute("forget() " + code)
    return lua.eval("texts()")


def frame_of(lua, event):
    """Whether any frame of the addon listens to `event` (for the player)."""
    return lua.eval(f"string.find(listening(), ',{event},', 1, true) ~= nil")


class Notices(unittest.TestCase):
    def setUp(self):
        self.lua = load()

    def test_auras_gained_stacked_and_lost(self):
        lua = self.lua
        self.assertEqual(notices(lua, "cleu('SPELL_AURA_APPLIED', priest, you, 1243, 'Power Word: Fortitude', 2, 'BUFF')"),
                         "[Power Word: Fortitude]")
        self.assertEqual(list(lua.eval("last().color").values()), [0.698, 0.698, 0])
        self.assertEqual(lua.eval("areaOf(last())"), "Notification")
        self.assertEqual(notices(lua, "cleu('SPELL_AURA_APPLIED', mob, you, 11597, 'Sunder Armor', 1, 'DEBUFF')"),
                         "[Sunder Armor]")
        self.assertEqual(list(lua.eval("last().color").values()), [0, 0.502, 0.502])
        self.assertEqual(notices(lua, "cleu('SPELL_AURA_APPLIED_DOSE', mob, you, 11597, 'Sunder Armor', 1, 'DEBUFF', 3)"),
                         "[Sunder Armor 3]")
        self.assertEqual(notices(lua, "cleu('SPELL_AURA_REMOVED_DOSE', mob, you, 11597, 'Sunder Armor', 1, 'DEBUFF', 2)"), "")
        self.assertEqual(notices(lua, "cleu('SPELL_AURA_REMOVED', mob, you, 11597, 'Sunder Armor', 1, 'DEBUFF')"),
                         "-[Sunder Armor]")
        self.assertEqual(notices(lua, "cleu('SPELL_AURA_APPLIED', you, mob, 11597, 'Sunder Armor', 1, 'DEBUFF')"), "")

    def test_combat_with_the_crossed_swords(self):
        lua = self.lua
        self.assertEqual(notices(lua, "fire('PLAYER_IN_COMBAT_CHANGED', true)"), "+Combat")
        icon = lua.eval("lineOf(last()).icon")
        self.assertEqual((icon.texture, icon.width, icon.shown), ("Interface\\Icons\\Ability_DualWield", 40, True))
        self.assertEqual(list(icon.color.values())[:3], [1, 0.2, 0.2])
        self.assertEqual(notices(lua, "fire('PLAYER_IN_COMBAT_CHANGED', false)"), "-Combat")
        self.assertEqual(list(lua.eval("lineOf(last()).icon.color").values())[:3], [0.2, 1, 0.2])
        self.assertFalse(frame_of(lua, "PLAYER_REGEN_ENABLED"))

    def test_combo_points(self):
        lua = self.lua
        self.assertEqual(notices(lua, "targetGUID = '0xMOB' combo = 3 fire('PLAYER_COMBO_POINTS')"), "3 CP")
        self.assertEqual(notices(lua, "combo = 5 fire('PLAYER_COMBO_POINTS')"), "5 CP Finish It!")
        self.assertEqual(notices(lua, "combo = 0 fire('PLAYER_COMBO_POINTS')"), "")
        self.assertEqual(notices(lua, "combo = 2 targetGUID = nil fire('PLAYER_COMBO_POINTS')"), "")

    def test_honor_from_both_stock_strings(self):
        lua = self.lua
        self.assertEqual(notices(lua, "fire('CHAT_MSG_COMBAT_HONOR_GAIN', 'Bob dies, honorable kill Rank: Sergeant "
                                      "(Estimated Honor Points: 23)')"), "+23 Honor")
        self.assertEqual(notices(lua, "fire('CHAT_MSG_COMBAT_HONOR_GAIN', 'You have been awarded 198 honor points.')"),
                         "+198 Honor")
        self.assertEqual(notices(lua, "fire('CHAT_MSG_COMBAT_HONOR_GAIN', 'Something else.')"), "")

    def test_a_skill_up(self):
        self.assertEqual(notices(self.lua, "fire('CHAT_MSG_SKILL', 'Your skill in Swords has increased to 120.')"),
                         "Swords: 120")

    def test_reputation_up_down_and_zero(self):
        lua = self.lua
        self.assertEqual(notices(lua, "fire('FACTION_STANDING_CHANGED', 72, 3000, 25)"), "+25 Reputation (Stormwind)")
        self.assertEqual(notices(lua, "fire('FACTION_STANDING_CHANGED', 72, 2990, -10)"), RED + "10 Reputation (Stormwind)")
        self.assertEqual(notices(lua, "fire('FACTION_STANDING_CHANGED', 72, 2990, 0)"), "")

    def test_xp_and_across_a_level_up(self):
        lua = self.lua
        self.assertEqual(notices(lua, "xp = 4900 fire('PLAYER_XP_UPDATE')"), "3900 XP")
        self.assertEqual(lua.eval("last().fontSize"), 26)
        self.assertTrue(lua.eval("lineOf(last()) == __addon_ns.areas.Notification.crits[1]"))
        self.assertEqual(notices(lua, "xp = 200 xpMax = 6000 fire('PLAYER_XP_UPDATE')"), "300 XP")

    def test_killing_blows_on_a_player_never_targeted_and_on_an_npc(self):
        lua = self.lua
        self.assertEqual(notices(lua, "cleu('PARTY_KILL', you, {'0xBOB', 'Bob', 0x548})"), "Killing Blow! (Bob)")
        self.assertEqual(notices(lua, "cleu('PARTY_KILL', you, mob)"), "Killing Blow! (Defias Thug)")
        self.assertEqual(notices(lua, "cleu('PARTY_KILL', priest, mob)"), "")

    def test_power_gained_and_drained(self):
        lua = self.lua
        self.assertEqual(notices(lua, "cleu('SPELL_ENERGIZE', you, you, 14181, 'Relentless Strikes', 1, 25, 3)"),
                         "+25 Energy")
        self.assertEqual(notices(lua, "cleu('SPELL_DRAIN', mob, you, 8129, 'Mana Burn', 64, 300, 0, 0)"),
                         RED + "300 Mana")


class Mana(unittest.TestCase):
    def test_a_mage_sees_each_rise_and_no_spell_gain_twice(self):
        lua = load(setup="playerClass = 'MAGE' mana = 1500")
        self.assertTrue(lua.eval("listensFor('UNIT_POWER_UPDATE', 'player')"))
        self.assertFalse(lua.eval("listensFor('UNIT_POWER_UPDATE', 'target')"))
        self.assertEqual(notices(lua, "mana = 1600 fire('UNIT_POWER_UPDATE', 'player', 'MANA')"), "+100 Mana")
        self.assertEqual(notices(lua, "mana = 1400 fire('UNIT_POWER_UPDATE', 'player', 'MANA')"), "")
        self.assertEqual(notices(lua, "cleu('SPELL_ENERGIZE', you, you, 2023, 'Restore Mana', 1, 500, 0)"), "")
        lua.execute("settingsWindow.use('BattleText_manaGains', false)")
        self.assertEqual(notices(lua, "mana = 1900 fire('UNIT_POWER_UPDATE', 'player', 'MANA')"), "")
        self.assertEqual(notices(lua, "cleu('SPELL_ENERGIZE', you, you, 2023, 'Restore Mana', 1, 500, 0)"), "+500 Mana")

    def test_a_rogue_listens_to_no_power(self):
        lua = load()
        self.assertFalse(frame_of(lua, "UNIT_POWER_UPDATE"))
        self.assertFalse(frame_of(lua, "UNIT_HEALTH"))

    def test_a_druids_combo_points_show_no_mana(self):
        lua = load(setup="playerClass = 'DRUID' mana = 1000")
        self.assertEqual(notices(lua, "mana = 1200 fire('UNIT_POWER_UPDATE', 'player', 'COMBO_POINTS')"), "")


class Alerts(unittest.TestCase):
    def test_windfury_replaces_its_auras_line(self):
        lua = load()
        self.assertEqual(notices(lua, "cleu('SPELL_AURA_APPLIED', nil, you, 8512, 'Windfury Totem', 8, 'BUFF')"),
                         "Windfury!")
        self.assertEqual(lua.eval("last().fontSize"), 26)
        self.assertEqual(lua.eval("lineOf(last()).icon.texture"), "Interface\\Icons\\Spell_Nature_Windfury")
        lua.execute("settingsWindow.use('BattleText_alertWindfury', false)")
        self.assertEqual(notices(lua, "cleu('SPELL_AURA_APPLIED', nil, you, 8512, 'Windfury Totem', 8, 'BUFF')"),
                         "[Windfury Totem]")

    def test_low_health_once_through_the_line_and_again_after_rising(self):
        lua = load()
        self.assertFalse(frame_of(lua, "UNIT_HEALTH"))
        lua.execute("settingsWindow.use('BattleText_alertLowHealth', true)")
        self.assertTrue(frame_of(lua, "UNIT_HEALTH"))
        self.assertEqual(notices(lua, "health = 1100 fire('UNIT_HEALTH', 'player')"), "Low Health! (1100)")
        self.assertEqual(lua.eval("lineOf(last()).icon.texture"), "Interface\\Icons\\Spell_Holy_SealOfSacrifice")
        self.assertEqual(notices(lua, "health = 900 fire('UNIT_HEALTH', 'player')"), "")
        self.assertEqual(notices(lua, "health = 2000 fire('UNIT_HEALTH', 'player') health = 1000 fire('UNIT_HEALTH', 'player')"),
                         "Low Health! (1000)")
        lua.execute("settingsWindow.use('BattleText_alertLowHealth', false)")
        self.assertFalse(frame_of(lua, "UNIT_HEALTH"))

    def test_no_low_health_for_the_killing_blow(self):
        lua = load()
        lua.execute("settingsWindow.use('BattleText_alertLowHealth', true)")
        self.assertEqual(notices(lua, "health = 0 fire('UNIT_HEALTH', 'player')"), "")
        self.assertEqual(notices(lua, "health = 1500 fire('UNIT_HEALTH', 'player')"), "")

    def test_low_mana_at_35_percent(self):
        lua = load(setup="playerClass = 'MAGE'")
        self.assertEqual(notices(lua, "mana = 800 fire('UNIT_POWER_UPDATE', 'player', 'MANA')"), "")
        self.assertEqual(notices(lua, "mana = 600 fire('UNIT_POWER_UPDATE', 'player', 'MANA')"), "Low Mana! (600)")
        self.assertEqual(notices(lua, "mana = 500 fire('UNIT_POWER_UPDATE', 'player', 'MANA')"), "")
        lua.execute("settingsWindow.use('BattleText_alertLowMana', false) settingsWindow.use('BattleText_manaGains', false)")
        self.assertFalse(frame_of(lua, "UNIT_POWER_UPDATE"))

    def test_clearcasting_on_a_mage_not_on_a_rogue(self):
        lua = load(setup="playerClass = 'MAGE'")
        self.assertEqual(notices(lua, "cleu('SPELL_AURA_APPLIED', you, you, 12536, 'Clearcasting', 64, 'BUFF')"),
                         "Clearcasting!")
        lua = load()
        self.assertEqual(notices(lua, "cleu('SPELL_AURA_APPLIED', you, you, 12536, 'Clearcasting', 64, 'BUFF')"),
                         "[Clearcasting]")


class Ready(unittest.TestCase):
    RIPOSTE = "known.Riposte = 'Interface\\\\Icons\\\\Ability_Warrior_Challange'"

    def test_riposte_once_per_window(self):
        lua = load(setup=self.RIPOSTE)
        self.assertTrue(frame_of(lua, "SPELL_UPDATE_USABLE"))
        self.assertEqual(notices(lua, "reactive.Riposte = { true } fire('SPELL_UPDATE_USABLE')"), "Riposte!")
        self.assertEqual(lua.eval("lineOf(last()).icon.texture"), "Interface\\Icons\\Ability_Warrior_Challange")
        self.assertEqual(notices(lua, "fire('SPELL_UPDATE_USABLE')"), "")
        self.assertEqual(notices(lua, "reactive.Riposte = { false } fire('SPELL_UPDATE_USABLE') "
                                      "reactive.Riposte = { true } fire('SPELL_UPDATE_USABLE')"), "Riposte!")

    def test_a_window_that_opens_in_the_cooldown_shows_when_it_ends(self):
        lua = load(setup=self.RIPOSTE)
        lua.execute("cooldowns[1] = { GetTime() - 2, 6 }")
        self.assertEqual(notices(lua, "reactive.Riposte = { true } fire('SPELL_UPDATE_USABLE')"), "")
        self.assertEqual(notices(lua, "fire('SPELL_UPDATE_USABLE')"), "")
        self.assertEqual(lua.eval("liveTimers()"), 1)
        self.assertEqual(notices(lua, "step(3.9)"), "")
        self.assertEqual(notices(lua, "cooldowns[1] = nil step(0.2)"), "Riposte!")
        self.assertEqual(lua.eval("liveTimers()"), 0)

    def test_a_window_that_closes_in_the_cooldown_shows_nothing(self):
        lua = load(setup=self.RIPOSTE)
        lua.execute("cooldowns[1] = { GetTime(), 6 }")
        self.assertEqual(notices(lua, "reactive.Riposte = { true } fire('SPELL_UPDATE_USABLE') "
                                      "reactive.Riposte = { false } fire('SPELL_UPDATE_USABLE')"), "")
        self.assertEqual(notices(lua, "cooldowns[1] = nil step(6.1)"), "")

    def test_the_global_cooldown_holds_no_alert(self):
        lua = load(setup=self.RIPOSTE)
        lua.execute("cooldowns[1] = { GetTime(), 1.5, true }")
        self.assertEqual(notices(lua, "reactive.Riposte = { true } fire('SPELL_UPDATE_USABLE')"), "Riposte!")

    def test_overpower_from_a_dodge_on_another_unit_shows_nothing(self):
        lua = load(setup="playerClass = 'WARRIOR' known.Overpower = 'x' targetGUID = '0xMOB'")
        self.assertEqual(notices(lua, "reactive.Overpower = { true, '0xMOB2' } fire('SPELL_UPDATE_USABLE')"), "")
        self.assertEqual(notices(lua, "reactive.Overpower = { true, '0xMOB' } fire('SPELL_UPDATE_USABLE')"), "Overpower!")

    def test_none_known_no_event_and_learning_one_adds_it(self):
        lua = load()
        self.assertFalse(frame_of(lua, "SPELL_UPDATE_USABLE"))
        lua.execute(self.RIPOSTE + " fire('SPELLS_CHANGED')")
        self.assertTrue(frame_of(lua, "SPELL_UPDATE_USABLE"))
        lua.execute("settingsWindow.use('BattleText_alertReady', false)")
        self.assertFalse(frame_of(lua, "SPELL_UPDATE_USABLE"))


if __name__ == "__main__":
    unittest.main()
