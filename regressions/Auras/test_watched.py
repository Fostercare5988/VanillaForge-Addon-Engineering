"""The watched auras: icons, the time left, Only mine, a buff's cooldown after it
ends, the list window; and the rows and top right (FostercareFrames) leaving out
what shows here."""
import unittest
from auras_env import load, target

ROGUE_WATCH = """AurasDB = { watched = {
    { name = 'Slice and Dice', spellID = 5171, unit = 'player', icon = true, topRight = false, inRow = false, mine = false, cooldown = true },
    { name = 'Evasion', unit = 'player', icon = true, topRight = true, inRow = false, mine = false, cooldown = true },
    { name = 'Thorns', unit = 'player', icon = false, topRight = true, inRow = false, mine = false, cooldown = true },
    { name = 'Rupture', spellID = 8640, unit = 'target', icon = true, topRight = false, inRow = true, mine = true, cooldown = false },
    { name = 'Expose Armor', unit = 'target', icon = true, topRight = false, inRow = false, mine = false, cooldown = false },
} }"""


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
        lua = load(saved=ROGUE_WATCH, setup="spell(5277, 'Evasion', 'eva'); book[5277] = 12; base[5277] = 300000"
                                             "; a = aura('player', 'HELPFUL', { name = 'Evasion', icon = 'eva', duration = 15, expires = now + 15 })")
        icon = "watchIcon('player', 'Evasion')"
        self.assertTrue(lua.eval(f"{icon}:IsShown()"))
        lua.execute("auras.player.HELPFUL = {}; cooldowns[12] = { now, 300 }; delta('player', { removedAuraInstanceIDs = { a.instance } })")
        self.assertTrue(lua.eval(f"{icon}:IsShown()"))
        self.assertTrue(lua.eval(f"{icon}.icon.grey"))
        self.assertEqual(lua.eval(f"{icon}.cd.cooldown[2]"), 300)
        lua.execute(f"cooldowns[12] = nil; {icon}.cd:GetScript('OnCooldownDone')()")
        self.assertFalse(lua.eval(f"{icon}:IsShown()"))

    def test_the_global_cooldown_is_not_shown(self):
        lua = load(saved=ROGUE_WATCH, setup="spell(5277, 'Evasion', 'eva'); book[5277] = 12; base[5277] = 300000")
        lua.execute("cooldowns[12] = { now, 1 }; fire('SPELL_UPDATE_COOLDOWN')")
        self.assertFalse(lua.eval("watchIcon('player', 'Evasion'):IsShown()"))

    def test_a_spell_with_no_cooldown_of_its_own_is_not_read_at_each_cast(self):
        # Review 2026-11-18: every cast read Slice and Dice's cooldown, which it has not.
        lua = load(saved=ROGUE_WATCH, setup="spell(5171, 'Slice and Dice', 'snd'); book[5171] = 30")
        reads = lua.eval("count('GetSpellCooldown')")
        for _ in range(3):
            lua.execute("fire('SPELL_UPDATE_COOLDOWN')")
        self.assertEqual(lua.eval("count('GetSpellCooldown')"), reads)
        self.assertFalse(lua.eval("watchIcon('player', 'Slice and Dice'):IsShown()"))

    def test_an_aura_finds_its_entry_by_name_or_by_spell_id(self):
        lua = load(saved=ROGUE_WATCH, setup="aura('player', 'HELPFUL', { name = 'SnD', icon = 'snd', id = 5171 })"
                                             "; aura('player', 'HELPFUL', { name = 'Evasion', icon = 'eva', id = 26669 })")
        self.assertTrue(lua.eval("watchIcon('player', 'Slice and Dice'):IsShown()"), "by spell ID")
        self.assertTrue(lua.eval("watchIcon('player', 'Evasion'):IsShown()"), "by name, any rank")

    def test_ctrl_shift_shows_the_icons_to_be_moved(self):
        lua = load(saved=ROGUE_WATCH)
        lua.execute("press(true, true)")
        self.assertTrue(lua.eval("watchIcon('target', 'Rupture'):IsShown()"))
        lua.execute("press(false, false)")
        self.assertFalse(lua.eval("watchIcon('target', 'Rupture'):IsShown()"))


class WatchList(unittest.TestCase):
    def test_cd_is_dimmed_for_a_spell_with_no_cooldown_of_its_own(self):
        # 2026-11-18: Slice and Dice had CD ticked, a switch that can show nothing.
        lua = load(saved=ROGUE_WATCH, setup="spell(5171, 'Slice and Dice', 'snd'); book[5171] = 30"
                                             "; spell(5277, 'Evasion', 'eva'); book[5277] = 12; base[5277] = 300000")
        lua.execute("A.List()")
        snd, evasion = "A.lines[1].checks[5]", "A.lines[2].checks[5]"
        self.assertFalse(lua.eval(f"{snd}:IsEnabled()"))
        self.assertLess(lua.eval(f"{snd}:GetAlpha()"), 1)
        self.assertIn("no cooldown", lua.eval(f"{snd}.tip"))
        self.assertTrue(lua.eval(f"{evasion}:IsEnabled()"))
        self.assertEqual(lua.eval(f"{evasion}:GetAlpha()"), 1)

    def test_add_by_name_or_id_switch_and_remove(self):
        lua = load(setup="spell(5277, 'Evasion', 'eva')")
        lua.execute("AurasListName:SetText(' 5277 '); AurasList:Show()")
        lua.execute("A.List(); A.List()")  # closed, open again
        lua.execute("for _, w in ipairs(widgets) do if w.text == 'Add your buff' then w:GetScript('OnClick')() end end")
        self.assertEqual(lua.eval("AurasDB.watched[1].name"), "Evasion")
        self.assertEqual(lua.eval("AurasDB.watched[1].spellID"), 5277)
        self.assertTrue(lua.eval("AurasDB.watched[1].cooldown"))
        self.assertIsNotNone(lua.eval("watchIcon('player', 'Evasion')"))
        lua.execute("AurasListName:SetText('Blind')")
        lua.execute("for _, w in ipairs(widgets) do if w.text == 'Add target debuff' then w:GetScript('OnClick')() end end")
        self.assertEqual(lua.eval("AurasDB.watched[2].unit"), "target")
        self.assertTrue(lua.eval("AurasDB.watched[2].mine"))
        lua.execute("AurasListName:SetText('Blind')")
        lua.execute("for _, w in ipairs(widgets) do if w.text == 'Add target debuff' then w:GetScript('OnClick')() end end")
        self.assertEqual(lua.eval("#AurasDB.watched"), 2, "no second Blind")
        lua.execute("aura('target', 'HARMFUL', { name = 'Blind', icon = 'blind', source = 'player' })")
        target(lua)
        self.assertEqual(lua.eval("shownIcons('TargetDebuffs')"), "")
        line = "A.lines[2]"
        lua.execute(f"local c = {line}.checks[3]; c:SetChecked(true); c:GetScript('OnClick')()")
        self.assertTrue(lua.eval("AurasDB.watched[2].inRow"))
        self.assertEqual(lua.eval("shownIcons('TargetDebuffs')"), "blind")
        self.assertFalse(lua.eval(f"{line}.checks[2]:IsShown()"), "Top is for your buffs")
        lua.execute(f"{line}.remove:GetScript('OnClick')()")
        self.assertEqual(lua.eval("#AurasDB.watched"), 1)
        self.assertFalse(lua.eval("watchIcon('target', 'Blind'):IsShown()"))


class WithoutFrames(unittest.TestCase):
    def test_top_and_row_dim_without_fostercareframes(self):
        lua = load(saved=ROGUE_WATCH, frames=False)
        lua.execute("A.List()")
        evasion = "A.lines[2].checks"
        self.assertFalse(lua.eval(f"{evasion}[2]:IsEnabled()"), "Top")
        self.assertFalse(lua.eval(f"{evasion}[3]:IsEnabled()"), "Row")
        self.assertIn("FostercareFrames", lua.eval(f"{evasion}[3].tip"))
        self.assertTrue(lua.eval(f"{evasion}[1]:IsEnabled()"), "Icon")

    def test_the_icons_work_alone(self):
        lua = load(saved=ROGUE_WATCH, frames=False,
                   setup="aura('player', 'HELPFUL', { name = 'Evasion', icon = 'eva', duration = 15, expires = now + 15 })")
        self.assertTrue(lua.eval("watchIcon('player', 'Evasion'):IsShown()"))


if __name__ == "__main__":
    unittest.main()
