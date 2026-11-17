"""The unit frames (spec F1-F7, F13): class colours, numbers, target of target,
raid marks, the two cast bars, energy ticks and the Ctrl+Shift handles."""
import unittest
from ff_env import load, target


class ClassColours(unittest.TestCase):
    def test_player_target_and_party_in_their_class_colour(self):
        lua = load()
        lua.execute("PlayerFrame_Update()")
        self.assertEqual(lua.eval("fill(PlayerFrame)"), "0.4", "a rogue")
        target(lua, "Ann", "PRIEST")
        lua.execute("TargetFrame_CheckFaction()")
        self.assertEqual(lua.eval("fill(TargetFrame)"), "0.2")
        lua.execute("unit('party1', 'Bob', 'MAGE'); PartyMemberFrame_UpdateMember()")
        self.assertAlmostEqual(lua.eval("PartyMemberFrame1Name.color[1]"), 0.3)

    def test_an_npc_keeps_the_games_colour_and_off_takes_them_away(self):
        lua = load()
        target(lua, "Boar", "WARRIOR", player=False)
        lua.execute("TargetFrame_CheckFaction()")
        self.assertEqual(lua.eval("fill(TargetFrame)"), "hidden")
        target(lua, "Ann", "PRIEST")
        lua.execute("TargetFrame_CheckFaction(); unit('party1', 'Bob', 'MAGE'); PartyMemberFrame_UpdateMember()")
        lua.execute("settingsWindow.use('FostercareFrames_classColors', false)")
        self.assertEqual(lua.eval("fill(TargetFrame)"), "hidden")
        self.assertEqual(lua.eval("PartyMemberFrame1Name.color[1]"), 1, "the stock yellow")


class Numbers(unittest.TestCase):
    def numbers(self, lua, bar):
        lua.execute(f"TextStatusBar_UpdateTextString({bar})")
        fs = f"{bar}.TextString"
        return lua.eval(f"{fs}:IsShown() and {fs}.text or 'hidden'")

    def test_exact_health_and_the_targets_percent_while_hurt(self):
        lua = load()
        target(lua, "Ann", "PRIEST", hp=1500, max=3000)
        lua.execute("PlayerFrameManaBar:SetMinMaxValues(0, 100); PlayerFrameManaBar:SetValue(80)")
        self.assertEqual(self.numbers(lua, "PlayerFrameManaBar"), "80")
        self.assertEqual(self.numbers(lua, "TargetFrameHealthBar"), "1.5K - 50%")
        lua.execute("units.target.hp = 3000")
        self.assertEqual(self.numbers(lua, "TargetFrameHealthBar"), "3.0K")

    def test_a_percent_only_unit_shows_its_percent_and_dead_shows_nothing(self):
        lua = load()
        target(lua, "Boar", "WARRIOR", hp=40, max=100, player=False)
        self.assertEqual(self.numbers(lua, "TargetFrameHealthBar"), "40%")
        lua.execute("units.target.hp = 0; TargetFrame_CheckDead()")
        self.assertEqual(lua.eval("TargetFrameHealthBar.TextString:IsShown()"), None)
        self.assertEqual(lua.eval("TargetFrameManaBar.TextString:IsShown()"), None)

    def test_the_stock_target_numbers_are_hidden(self):
        lua = load()
        self.assertEqual(lua.eval("TargetHPText:GetAlpha()"), 0)
        self.assertEqual(lua.eval("TargetHPPercText:GetAlpha()"), 0)


class TargetOfTarget(unittest.TestCase):
    def test_no_stock_redraw_each_frame(self):
        lua = load()
        target(lua, "Ann", "PRIEST")
        lua.execute("unit('targettarget', 'Bob', 'MAGE'); fire('UNIT_TARGET', 'target'); step(0.1); step(0.1)")
        self.assertTrue(lua.eval("TargetofTargetFrame:IsShown()"))
        self.assertEqual(lua.eval("count('TargetofTarget_OnUpdate')"), 0)
        self.assertEqual(lua.eval("count('SetPortraitTexture')"), 1)

    def test_redraws_on_unit_target_and_on_its_units_guid_events_only(self):
        lua = load()
        target(lua, "Ann", "PRIEST")
        lua.execute("unit('targettarget', 'Bob', 'MAGE'); fire('UNIT_TARGET', 'target')")
        before = lua.eval("count('TargetofTarget_Update')")
        lua.execute("fire('UNIT_TARGET', 'party1')")
        self.assertEqual(lua.eval("count('TargetofTarget_Update')"), before, "another unit's target")
        lua.execute("fire('UNIT_HEALTH_GUID', '0xSomeoneElse'); fire('UNIT_HEALTH_GUID', '0xBob')")
        self.assertEqual(lua.eval("count('UnitFrameHealthBar_Update')"), 1)
        lua.execute("fire('UNIT_AURA_GUID', '0xBob')")
        self.assertEqual(lua.eval("count('RefreshBuffs')"), 1)

    def test_the_guid_events_only_while_it_shows(self):
        lua = load()
        self.assertNotIn("UNIT_HEALTH_GUID", lua.eval("listening(listener('UNIT_TARGET'))"))
        target(lua, "Ann", "PRIEST")
        lua.execute("unit('targettarget', 'Bob', 'MAGE'); fire('UNIT_TARGET', 'target')")
        self.assertIn("UNIT_HEALTH_GUID", lua.eval("listening(listener('UNIT_TARGET'))"))
        lua.execute("units.targettarget = nil; fire('UNIT_TARGET', 'target')")
        self.assertFalse(lua.eval("TargetofTargetFrame:IsShown()"))
        self.assertNotIn("UNIT_HEALTH_GUID", lua.eval("listening(listener('UNIT_TARGET'))"))


class Marks(unittest.TestCase):
    def test_on_the_portrait_and_a_solo_mark_redraws_the_frame(self):
        lua = load()
        self.assertEqual(lua.eval("(TargetRaidTargetIcon:GetPoint(1))"), "CENTER")
        self.assertEqual(lua.eval("select(2, TargetRaidTargetIcon:GetPoint(1)) == TargetPortrait"), True)
        lua.execute("SetRaidTarget('target', 8)")
        self.assertEqual(lua.eval("count('TargetFrame_UpdateRaidTargetIcon')"), 1)
        lua.execute("party = 2; SetRaidTarget('target', 8)")
        self.assertEqual(lua.eval("count('TargetFrame_UpdateRaidTargetIcon')"), 1, "in a group the event does it")


class TargetCastBar(unittest.TestCase):
    def cast(self, lua, channel=False, locked=False):
        lua.execute(f"casts.target = {{ name = 'Frostbolt', icon = 'frost', start = now * 1000, "
                    f"finish = (now + 3) * 1000, channel = {str(channel).lower()}, locked = {str(locked).lower()} }}")
        lua.execute(f"fire('{'UNIT_SPELLCAST_CHANNEL_START' if channel else 'UNIT_SPELLCAST_START'}', 'target')")

    def test_starts_greys_when_it_cannot_be_interrupted_and_ends_on_stop(self):
        lua = load()
        target(lua, "Ann", "MAGE")
        self.cast(lua)
        bar = "FostercareFramesTargetCast"
        self.assertTrue(lua.eval(f"{bar}:IsShown()"))
        self.assertEqual(lua.eval(f"{bar}.text.text"), "Frostbolt")
        self.assertEqual(lua.eval(f"{bar}.barColor[1]"), 1)
        self.assertEqual(lua.eval(f"{bar}.timer[2]"), 0, "a cast fills")
        lua.execute("casts.target.locked = true; fire('UNIT_SPELLCAST_NOT_INTERRUPTIBLE', 'target')")
        self.assertEqual(lua.eval(f"{bar}.barColor[1]"), 0.65)
        lua.execute("casts.target = nil; fire('UNIT_SPELLCAST_STOP', 'target')")
        self.assertFalse(lua.eval(f"{bar}:IsShown()"))

    def test_a_channel_drains_another_units_cast_is_not_shown_and_a_missed_stop_ends_it(self):
        lua = load()
        target(lua, "Ann", "MAGE")
        lua.execute("casts.party1 = { name = 'Heal', start = now * 1000, finish = (now + 3) * 1000 }")
        lua.execute("fire('UNIT_SPELLCAST_START', 'party1')")
        self.assertFalse(lua.eval("FostercareFramesTargetCast:IsShown()"))
        self.cast(lua, channel=True)
        self.assertEqual(lua.eval("FostercareFramesTargetCast.timer[2]"), 1)
        lua.execute("step(3.1)")
        self.assertFalse(lua.eval("FostercareFramesTargetCast:IsShown()"))

    def test_off_listens_to_nothing(self):
        lua = load()
        lua.execute("settingsWindow.use('FostercareFrames_targetCastbar', false)")
        self.assertIsNone(lua.eval("listener('UNIT_SPELLCAST_START')"))
        target(lua, "Ann", "MAGE")
        self.cast(lua)
        self.assertFalse(lua.eval("FostercareFramesTargetCast:IsShown()"))

    def test_lower_while_the_target_of_target_shows(self):
        lua = load()
        target(lua, "Ann", "MAGE")
        self.cast(lua)
        self.assertEqual(lua.eval("(select(5, FostercareFramesTargetCast:GetPoint(1)))"), -4)
        lua.execute("unit('targettarget', 'Bob', 'MAGE'); fire('UNIT_TARGET', 'target')")
        self.assertEqual(lua.eval("(select(5, FostercareFramesTargetCast:GetPoint(1)))"), -24)


class OwnCastBar(unittest.TestCase):
    def test_moved_and_kept_there_when_the_game_lays_out_the_screen(self):
        lua = load()
        self.assertTrue(lua.eval("CastingBarFrame.dontSave"))
        lua.execute("press(true, true)")
        self.assertTrue(lua.eval("CastingBarFrame:IsShown()"), "shown to be grabbed")
        lua.execute("local h = handleOf(CastingBarFrame); h:GetScript('OnMouseDown')()")
        lua.execute("CastingBarFrame.left, CastingBarFrame.top = 767, 181")
        lua.execute("press(false, false)")
        self.assertFalse(lua.eval("CastingBarFrame:IsShown()"), "hidden again: no cast")
        self.assertEqual(lua.eval("FostercareFramesDB.castbar[1]"), 767)
        self.assertEqual(lua.eval("FostercareFramesDB.castbar[2]"), 181 - 768)
        lua.execute("UIParent_ManageFramePositions()")
        self.assertEqual(lua.eval("(select(3, CastingBarFrame:GetPoint(1)))"), "TOPLEFT")
        self.assertEqual(lua.eval("(select(5, CastingBarFrame:GetPoint(1)))"), 181 - 768)


class Handles(unittest.TestCase):
    def test_ctrl_shift_shows_them_on_the_stock_frames_and_a_drag_places_the_frame(self):
        lua = load()
        self.assertFalse(lua.eval("handleOf(PlayerFrame):IsShown()"))
        lua.execute("press(true, false)")
        self.assertFalse(lua.eval("handleOf(PlayerFrame):IsShown()"), "Shift alone")
        lua.execute("press(true, true)")
        self.assertTrue(lua.eval("handleOf(PlayerFrame):IsShown()"))
        self.assertTrue(lua.eval("handleOf(TargetFrame) ~= nil and handleOf(TargetofTargetFrame) ~= nil"))
        lua.execute("handleOf(PlayerFrame):GetScript('OnMouseDown')()")
        self.assertTrue(lua.eval("PlayerFrame.moving"))
        lua.execute("press(false, false)")
        self.assertTrue(lua.eval("PlayerFrame:IsUserPlaced()"), "letting go of the keys drops it")
        self.assertFalse(lua.eval("handleOf(PlayerFrame):IsShown()"))


class EnergyTicks(unittest.TestCase):
    def test_animates_only_while_it_shows(self):
        lua = load()
        self.assertIsNotNone(lua.eval("tickLine().scripts.OnUpdate"))
        lua.execute("PlayerFrame:Hide()")
        self.assertIsNone(lua.eval("tickLine().scripts.OnUpdate"))
        lua.execute("PlayerFrame:Show()")
        self.assertIsNotNone(lua.eval("tickLine().scripts.OnUpdate"))
        lua.execute("settingsWindow.use('FostercareFrames_energyTicks', false)")
        self.assertIsNone(lua.eval("tickLine().scripts.OnUpdate"))

    def test_rage_shows_no_line(self):
        lua = load(setup="unit('player', 'Grom', 'WARRIOR', { power = 1 })")
        self.assertIsNone(lua.eval("tickLine().scripts.OnUpdate"))

    def test_a_tick_sets_the_clock_and_a_spells_energy_does_not(self):
        lua = load(setup="unit('player', 'Claude', 'ROGUE', { mana = 50 })")
        lua.execute("step(0.7); units.player.mana = 70; fire('UNIT_POWER_UPDATE', 'player'); step(0.2)")
        self.assertAlmostEqual(lua.eval("(F.Tick())"), 100.7)
        lua.execute("step(1.0); fire('SPELL_ENERGIZE_ON_SELF', '0xClaude', '0xClaude', 1, 3, 20, 0)")
        lua.execute("units.player.mana = 90; fire('UNIT_POWER_UPDATE', 'player'); step(0.2)")
        self.assertAlmostEqual(lua.eval("(F.Tick())"), 100.7, msg="Relentless Strikes' energy is not a tick")

    def test_mana_spent_waits_five_seconds(self):
        lua = load(setup="unit('player', 'Ann', 'PRIEST', { power = 0, mana = 500, maxMana = 1000 })")
        lua.execute("units.player.mana = 400; fire('UNIT_POWER_UPDATE', 'player')")
        self.assertEqual(lua.eval("(select(2, F.Tick()))"), 5)
        lua.execute("step(5.1)")
        self.assertEqual(lua.eval("(select(2, F.Tick()))"), 2)


if __name__ == "__main__":
    unittest.main()
