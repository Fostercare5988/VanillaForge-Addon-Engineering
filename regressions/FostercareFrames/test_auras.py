"""The auras (spec F8-F12): the rows under the frames, watched auras, the top
right and the weapon enchants."""
import unittest
from ff_env import load, target

ROGUE_WATCH = """FostercareFramesDB = { watched = {
    { name = 'Slice and Dice', spellID = 5171, unit = 'player', icon = true, topRight = false, inRow = false, mine = false, cooldown = true },
    { name = 'Evasion', unit = 'player', icon = true, topRight = true, inRow = false, mine = false, cooldown = true },
    { name = 'Thorns', unit = 'player', icon = false, topRight = true, inRow = false, mine = false, cooldown = true },
    { name = 'Rupture', spellID = 8640, unit = 'target', icon = true, topRight = false, inRow = true, mine = true, cooldown = false },
    { name = 'Expose Armor', unit = 'target', icon = true, topRight = false, inRow = false, mine = false, cooldown = false },
} }"""


class Rows(unittest.TestCase):
    def test_your_auras_under_your_frame_and_the_targets_under_its(self):
        lua = load(setup="aura('player', 'HELPFUL', { name = 'Fort', icon = 'fort', id = 1243, duration = 1800, expires = now + 1000 })"
                         "; aura('player', 'HARMFUL', { name = 'Rend', icon = 'rend', dispel = 'Magic' })")
        self.assertEqual(lua.eval("shownIcons('PlayerBuffs')"), "fort")
        self.assertEqual(lua.eval("shownIcons('PlayerDebuffs')"), "rend")
        self.assertEqual(lua.eval("FostercareFramesPlayerBuffs.buttons[1].cd.cooldown[1]"), 100 + 1000 - 1800)
        self.assertFalse(lua.eval("FostercareFramesTargetBuffs:IsShown()"), "no target")
        lua.execute("aura('target', 'HARMFUL', { name = 'Sunder', icon = 'sunder', stacks = 3 })")
        target(lua)
        self.assertEqual(lua.eval("shownIcons('TargetDebuffs')"), "sunder")
        self.assertEqual(lua.eval("FostercareFramesTargetDebuffs.buttons[1].count.text"), 3)

    def test_one_refresh_rewrites_one_button_and_a_new_aura_rereads_the_row(self):
        lua = load(setup="a1 = aura('player', 'HELPFUL', { name = 'A', icon = 'a', id = 1, duration = 10, expires = now + 10 })"
                         "; a2 = aura('player', 'HELPFUL', { name = 'B', icon = 'b', id = 2, duration = 10, expires = now + 10 })")
        reads = lua.eval("count('GetAuraSlots')")
        lua.execute("a2.expires = now + 20; a2.duration = 20; delta('player', { updatedAuraInstanceIDs = { a2.instance } })")
        self.assertEqual(lua.eval("count('GetAuraSlots')") - reads, 0, "the row is not read again")
        self.assertEqual(lua.eval("FostercareFramesPlayerBuffs.buttons[2].cd.cooldown[2]"), 20)
        lua.execute("aura('player', 'HELPFUL', { name = 'C', icon = 'c', id = 3 }); delta('player', { addedAuraInstanceIDs = { 99 } })")
        self.assertEqual(lua.eval("shownIcons('PlayerBuffs')"), "a b c")

    def test_debuffs_follow_the_buffs_and_take_their_place_when_there_are_none(self):
        lua = load(setup="aura('player', 'HARMFUL', { name = 'Rend', icon = 'rend' })")
        self.assertIs(lua.eval("select(2, FostercareFramesPlayerDebuffs:GetPoint(1)) == PlayerFrame"), True)
        lua.execute("aura('player', 'HELPFUL', { name = 'Fort', icon = 'fort' }); delta('player', { isFullUpdate = true })")
        self.assertIs(lua.eval("select(2, FostercareFramesPlayerDebuffs:GetPoint(1)) == FostercareFramesPlayerBuffs"), True)

    def test_right_click_cancels_your_buff_and_the_stock_target_auras_give_way(self):
        lua = load(setup="aura('player', 'HELPFUL', { name = 'Fort', icon = 'fort', id = 1243 })")
        lua.execute("this = FostercareFramesPlayerBuffs.buttons[1]; this:GetScript('OnClick')()")
        self.assertEqual(lua.eval("count('cancel:1243')"), 1)
        lua.execute("TargetDebuffButton_Update()")
        self.assertFalse(lua.eval("TargetFrameBuff1:IsShown() or TargetFrameDebuff16:IsShown()"))

    def test_borders_buffs_dark_debuffs_in_their_dispel_colour_and_off(self):
        lua = load(setup="aura('player', 'HELPFUL', { name = 'Fort', icon = 'fort' })"
                         "; aura('player', 'HARMFUL', { name = 'Poly', icon = 'poly', dispel = 'Magic' })")
        buff, debuff = "FostercareFramesPlayerBuffs.buttons[1]", "FostercareFramesPlayerDebuffs.buttons[1]"
        self.assertTrue(lua.eval(f"{buff}.edge:IsShown()"))
        self.assertTrue(lua.eval(f"{debuff}.overlay:IsShown()"))
        self.assertEqual(lua.eval(f"{debuff}.overlay.color[1]"), 0.2)
        lua.execute("settingsWindow.use('FostercareFrames_buffBorders', false); settingsWindow.use('FostercareFrames_debuffBorders', false)")
        self.assertFalse(lua.eval(f"{buff}.edge:IsShown()"))
        self.assertFalse(lua.eval(f"{debuff}.overlay:IsShown()"))

    def test_a_row_switched_off_hides_at_once(self):
        lua = load(setup="aura('player', 'HELPFUL', { name = 'Fort', icon = 'fort' })")
        lua.execute("settingsWindow.use('FostercareFrames_playerBuffs', false)")
        self.assertFalse(lua.eval("FostercareFramesPlayerBuffs:IsShown()"))


class Watched(unittest.TestCase):
    def test_a_watched_aura_gets_its_icon_and_leaves_the_row_and_the_top_right(self):
        lua = load(saved=ROGUE_WATCH, setup="""
            aura('player', 'HELPFUL', { name = 'Slice and Dice', icon = 'snd', id = 6774, duration = 21, expires = now + 21 })
            aura('player', 'HELPFUL', { name = 'Fort', icon = 'fort' })
            playerBuffs.HELPFUL = { { id = 6774, icon = 'snd', ends = now + 21 }, { id = 1243, icon = 'fort', ends = now + 1000 } }
            spell(6774, 'Slice and Dice', 'snd'); spell(1243, 'Fort', 'fort')""")
        lua.execute("playerAuras()")
        icon = "watchIcon('player', 'Slice and Dice')"
        self.assertTrue(lua.eval(f"{icon}:IsShown()"), "matched by name: another rank")
        self.assertEqual(lua.eval(f"{icon}.cd.cooldown[2]"), 21)
        self.assertEqual(lua.eval("shownIcons('PlayerBuffs')"), "fort")
        self.assertEqual(lua.eval("topShown('HELPFUL')"), "fort")

    def test_top_right_and_no_icon_keep_it_up_there(self):
        lua = load(saved=ROGUE_WATCH, setup="""
            aura('player', 'HELPFUL', { name = 'Thorns', icon = 'thorns' })
            playerBuffs.HELPFUL = { { id = 467, icon = 'thorns', ends = now + 600 } }; spell(467, 'Thorns', 'thorns')""")
        lua.execute("playerAuras()")
        self.assertIsNone(lua.eval("watchIcon('player', 'Thorns')"))
        self.assertEqual(lua.eval("topShown('HELPFUL')"), "thorns")
        self.assertEqual(lua.eval("shownIcons('PlayerBuffs')"), "")

    def test_only_mine_keeps_another_players_debuff_in_the_row(self):
        lua = load(saved=ROGUE_WATCH, setup="""
            unit('party1', 'Bob', 'ROGUE')
            aura('target', 'HARMFUL', { name = 'Rupture', icon = 'rup', id = 8640, source = 'party1' })""")
        target(lua)
        self.assertFalse(lua.eval("watchIcon('target', 'Rupture'):IsShown()"))
        self.assertEqual(lua.eval("shownIcons('TargetDebuffs')"), "rup")
        lua.execute("auras.target.HARMFUL[1].source = 'player'; delta('target', { isFullUpdate = true })")
        self.assertTrue(lua.eval("watchIcon('target', 'Rupture'):IsShown()"))
        self.assertEqual(lua.eval("shownIcons('TargetDebuffs')"), "rup", "In the row: yes")
        lua.execute("auras.target.HARMFUL[2] = { name = 'Expose Armor', icon = 'ea', instance = 50 }; delta('target', { isFullUpdate = true })")
        self.assertEqual(lua.eval("shownIcons('TargetDebuffs')"), "rup")
        self.assertTrue(lua.eval("watchIcon('target', 'Expose Armor'):IsShown()"))

    def test_a_buff_that_ends_shows_its_spells_cooldown_greyed_until_ready(self):
        lua = load(saved=ROGUE_WATCH, setup="spell(5277, 'Evasion', 'eva'); book[5277] = 12"
                                             "; a = aura('player', 'HELPFUL', { name = 'Evasion', icon = 'eva', duration = 15, expires = now + 15 })")
        icon = "watchIcon('player', 'Evasion')"
        self.assertTrue(lua.eval(f"{icon}:IsShown()"))
        lua.execute("auras.player.HELPFUL = {}; cooldowns[12] = { now, 300 }; delta('player', { removedAuraInstanceIDs = { a.instance } })")
        self.assertTrue(lua.eval(f"{icon}:IsShown()"))
        self.assertTrue(lua.eval(f"{icon}.texture.grey"))
        self.assertEqual(lua.eval(f"{icon}.cd.cooldown[2]"), 300)
        lua.execute(f"cooldowns[12] = nil; {icon}.cd:GetScript('OnCooldownDone')()")
        self.assertFalse(lua.eval(f"{icon}:IsShown()"))

    def test_the_global_cooldown_is_not_shown(self):
        lua = load(saved=ROGUE_WATCH, setup="spell(5277, 'Evasion', 'eva'); book[5277] = 12")
        lua.execute("cooldowns[12] = { now, 1 }; fire('SPELL_UPDATE_COOLDOWN')")
        self.assertFalse(lua.eval("watchIcon('player', 'Evasion'):IsShown()"))

    def test_ctrl_shift_shows_the_icons_to_be_moved(self):
        lua = load(saved=ROGUE_WATCH)
        lua.execute("press(true, true)")
        self.assertTrue(lua.eval("watchIcon('target', 'Rupture'):IsShown()"))
        lua.execute("press(false, false)")
        self.assertFalse(lua.eval("watchIcon('target', 'Rupture'):IsShown()"))


class WatchList(unittest.TestCase):
    def test_add_by_name_or_id_switch_and_remove(self):
        lua = load(setup="spell(5277, 'Evasion', 'eva')")
        lua.execute("FostercareFramesWatchName:SetText(' 5277 '); FostercareFramesWatchList:Show()")
        lua.execute("F.WatchList(); F.WatchList()")  # closed, open again
        lua.execute("for _, w in ipairs(widgets) do if w.text == 'Add your buff' then w:GetScript('OnClick')() end end")
        self.assertEqual(lua.eval("FostercareFramesDB.watched[1].name"), "Evasion")
        self.assertEqual(lua.eval("FostercareFramesDB.watched[1].spellID"), 5277)
        self.assertTrue(lua.eval("FostercareFramesDB.watched[1].cooldown"))
        self.assertIsNotNone(lua.eval("watchIcon('player', 'Evasion')"))
        lua.execute("FostercareFramesWatchName:SetText('Blind')")
        lua.execute("for _, w in ipairs(widgets) do if w.text == 'Add target debuff' then w:GetScript('OnClick')() end end")
        self.assertEqual(lua.eval("FostercareFramesDB.watched[2].unit"), "target")
        self.assertTrue(lua.eval("FostercareFramesDB.watched[2].mine"))
        lua.execute("FostercareFramesWatchName:SetText('Blind')")
        lua.execute("for _, w in ipairs(widgets) do if w.text == 'Add target debuff' then w:GetScript('OnClick')() end end")
        self.assertEqual(lua.eval("#FostercareFramesDB.watched"), 2, "no second Blind")
        lua.execute("aura('target', 'HARMFUL', { name = 'Blind', icon = 'blind', source = 'player' })")
        target(lua)
        self.assertEqual(lua.eval("shownIcons('TargetDebuffs')"), "")
        line = "F.lines[2]"
        lua.execute(f"local c = {line}.checks[3]; c:SetChecked(true); c:GetScript('OnClick')()")
        self.assertTrue(lua.eval("FostercareFramesDB.watched[2].inRow"))
        self.assertEqual(lua.eval("shownIcons('TargetDebuffs')"), "blind")
        self.assertFalse(lua.eval(f"{line}.checks[2]:IsShown()"), "Top is for your buffs")
        lua.execute(f"{line}.remove:GetScript('OnClick')()")
        self.assertEqual(lua.eval("#FostercareFramesDB.watched"), 1)
        self.assertFalse(lua.eval("watchIcon('target', 'Blind'):IsShown()"))


class TopRight(unittest.TestCase):
    def setUp(self):
        self.lua = load(setup="""
            playerBuffs.HELPFUL = { { id = 1, icon = 'fort', ends = now + 600 }, { id = 2, icon = 'aura', permanent = true } }
            playerBuffs.HARMFUL = { { id = 3, icon = 'rend', ends = now + 20 } }
            spell(1, 'Fort', 'fort'); spell(2, 'Aura', 'aura'); spell(3, 'Rend', 'rend')""")
        self.lua.execute("playerAuras(); runTimers()")

    def test_the_time_left_counts_down_on_the_icon_with_no_redraw_each_frame(self):
        lua = self.lua
        self.assertEqual(lua.eval("BuffButton0.cd.cooldown[2]"), 600)
        self.assertIsNone(lua.eval("BuffButton1.cd.cooldown"), "a buff with no end")
        self.assertEqual(lua.eval("BuffButton0Duration:GetAlpha()"), 0)
        self.assertIsNone(lua.eval("BuffButton0.scripts.OnUpdate"))
        self.assertIsNone(lua.eval("BuffButton1.scripts.OnUpdate"))
        lua.execute("step(0.1)")
        self.assertEqual(lua.eval("count('BuffButton_OnUpdate')"), 1, "only the flashing debuff")

    def test_the_stock_redraw_runs_while_it_flashes_or_holds_the_tooltip(self):
        lua = self.lua
        self.assertIsNotNone(lua.eval("BuffButton24.scripts.OnUpdate"), "20 s left: it flashes")
        self.assertIsNotNone(lua.eval("BuffFrame.scripts.OnUpdate"), "the flash clock")
        lua.execute("step(600 - 31 + 0.1)")
        self.assertIsNotNone(lua.eval("BuffButton0.scripts.OnUpdate"), "Fort's last 31 seconds")
        lua.execute("playerBuffs.HELPFUL[1] = nil; playerBuffs.HARMFUL = {}; playerAuras()")
        self.assertIsNone(lua.eval("BuffFrame.scripts.OnUpdate"))
        lua.execute("GameTooltip:SetOwner(BuffButton1); BuffButton1:GetScript('OnEnter')()")
        self.assertIsNotNone(lua.eval("BuffButton1.scripts.OnUpdate"))
        lua.execute("GameTooltip:Hide(); BuffButton1:GetScript('OnLeave')()")
        self.assertIsNone(lua.eval("BuffButton1.scripts.OnUpdate"))

    def test_the_tooltip_leaves_the_countdown_alone(self):
        lua = self.lua
        lua.execute("step(5)")
        starts = lua.eval("count('SetCooldown')")
        lua.execute("GameTooltip:SetOwner(BuffButton0); BuffButton0:GetScript('OnEnter')(); step(1)")
        lua.execute("GameTooltip:Hide(); BuffButton0:GetScript('OnLeave')()")
        self.assertEqual(lua.eval("count('SetCooldown')"), starts)
        self.assertIsNone(lua.eval("BuffButton0.scripts.OnUpdate"))

    def test_refreshed_auras_make_no_new_timers(self):
        # 2026-11-17 /lag: a timer and a closure per aura change, 0.5 KB/s.
        lua = self.lua
        before = lua.eval("#timers")
        for n in range(5):
            lua.execute(f"playerBuffs.HELPFUL[1].ends = now + 700 + {n}; playerAuras()")
        self.assertEqual(lua.eval("#timers"), before, "the wake is already sooner")
        lua.execute("step(700 + 4 - 31 + 0.1)")
        self.assertIsNotNone(lua.eval("BuffButton0.scripts.OnUpdate"), "it still flashes on time")

    def test_a_duration_that_arrives_later_reaches_the_icon(self):
        # 2026-11-18, Arathi Basin: the second Cheap Shot had no time at the top right.
        lua = self.lua
        lua.execute("playerBuffs.HARMFUL[2] = { id = 4, icon = 'stun' }; spell(4, 'Cheap Shot', 'stun'); playerAuras()")
        self.assertIsNone(lua.eval("BuffButton25.cd.cooldown"), "no time known yet")
        lua.execute("playerBuffs.HARMFUL[2].ends = now + 2; delta('player', { updatedAuraInstanceIDs = { 4 } })")
        self.assertEqual(lua.eval("BuffButton25.cd.cooldown[2]"), 2)
        lua.execute("playerBuffs.HARMFUL[2].ends = now + 9; delta('player', { addedAuraInstanceIDs = { 5 } })")
        self.assertEqual(lua.eval("BuffButton25.cd.cooldown[2]"), 2, "an added aura waits for the stock update")

    def test_a_buff_gone_before_it_flashes_wakes_nothing(self):
        lua = self.lua
        lua.execute("playerBuffs.HELPFUL = {}; playerBuffs.HARMFUL = {}; playerAuras(); step(600)")
        self.assertIsNone(lua.eval("BuffButton0.scripts.OnUpdate"))
        self.assertIsNone(lua.eval("BuffFrame.scripts.OnUpdate"))

    def test_right_to_left_closing_up_and_each_area_its_switch(self):
        lua = self.lua
        self.assertIs(lua.eval("BuffButton0:GetParent() == FostercareFramesTopBuffs"), True)
        self.assertIs(lua.eval("BuffButton24:GetParent() == FostercareFramesTopDebuffs"), True)
        self.assertEqual(lua.eval("(select(4, BuffButton1:GetPoint(1)))"), -35)
        lua.execute("table.remove(playerBuffs.HELPFUL, 1); playerAuras(); runTimers()")
        self.assertEqual(lua.eval("(select(4, BuffButton0:GetPoint(1)))"), 0)
        lua.execute("settingsWindow.use('FostercareFrames_topDebuffs', false)")
        self.assertFalse(lua.eval("FostercareFramesTopDebuffs:IsShown()"))
        self.assertTrue(lua.eval("FostercareFramesTopBuffs:IsShown()"))

    def test_an_aura_with_no_icon_takes_no_button(self):
        # 2026-11-17: Find Herbs (a tracking aura, no icon) was a bare grey edge.
        lua = self.lua
        lua.execute("table.insert(playerBuffs.HELPFUL, 1, { id = 2383 }); spell(2383, 'Find Herbs'); playerAuras(); runTimers()")
        self.assertFalse(lua.eval("BuffButton0:IsShown()"))
        self.assertEqual(lua.eval("topShown('HELPFUL')"), "fort aura")
        self.assertEqual(lua.eval("(select(4, BuffButton1:GetPoint(1)))"), 0, "the next one closes up")

    def test_debuff_borders_are_the_stock_dispel_border(self):
        lua = self.lua
        self.assertEqual(lua.eval("BuffButton24Border:GetAlpha()"), 1)
        lua.execute("settingsWindow.use('FostercareFrames_debuffBorders', false)")
        self.assertEqual(lua.eval("BuffButton24Border:GetAlpha()"), 0)


class Enchants(unittest.TestCase):
    def test_each_hands_poison_main_hand_left_and_no_redraw_each_frame(self):
        lua = load(setup="bags[0] = { { itemName = 'Instant Poison VI', iconFileID = 'instant' } }; quality[16] = 4")
        self.assertIsNone(lua.eval("TemporaryEnchantFrame.scripts.OnUpdate"))
        lua.execute("enchant[16] = { id = 323, ends = now + 1800 }; enchant[17] = { id = 7, ends = now + 1700 }")
        lua.execute("fire('WEAPON_ENCHANT_CHANGED')")
        self.assertEqual(lua.eval("TempEnchant1:GetID()"), 17)
        self.assertEqual(lua.eval("TempEnchant2:GetID()"), 16)
        self.assertEqual(lua.eval("(select(4, TempEnchant2:GetPoint(1)))"), -35, "main hand left")
        self.assertEqual(lua.eval("TempEnchant2.poison.texture"), "instant")
        self.assertEqual(lua.eval("TempEnchant2.cd.cooldown[2]"), 1800)
        self.assertEqual(lua.eval("TempEnchant2.edge.color[1]"), 0.4, "an epic weapon")
        self.assertIsNone(lua.eval("TemporaryEnchantFrame.scripts.OnUpdate"))
        reads = lua.eval("count('GetContainerItemInfo')")
        lua.execute("fire('WEAPON_ENCHANT_CHANGED')")
        self.assertEqual(lua.eval("count('GetContainerItemInfo')"), reads, "the poison's icon is known")
        lua.execute("step(1800 - 31 + 0.1)")
        self.assertIsNotNone(lua.eval("TemporaryEnchantFrame.scripts.OnUpdate"), "it flashes")
        lua.execute("enchant[16], enchant[17] = nil, nil; fire('WEAPON_ENCHANT_CHANGED')")
        self.assertFalse(lua.eval("TempEnchant1:IsShown() or TempEnchant2:IsShown()"))
        self.assertIsNone(lua.eval("TemporaryEnchantFrame.scripts.OnUpdate"))


if __name__ == "__main__":
    unittest.main()
