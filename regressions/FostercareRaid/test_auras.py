"""Icons inside each member and the heal-over-time corner (spec R4-R5, 4.7
"Raid"): icon counts and sizes from the page; heals and your own first,
dispellable debuffs first; +N for what did not fit; one delta rewrites its
own record without reading the member again.
"""
import unittest
from fr_env import in_party

RENEW, FORT, CURSE, POISON = 139, 1243, 980, 3034


def with_auras(saved="", setup=""):
    """Ann (party1) with Fortitude, then Renew (a heal over time), then two
    debuffs: a plain one first, then a Magic one."""
    return in_party(saved, setup + """
        spellFx[139] = { 8 }; spellFx[1243] = { 29 }
        aura('party1', 'HELPFUL', { id = 1243, icon = 'fort' })
        aura('party1', 'HELPFUL', { id = 139, icon = 'renew', duration = 15, expires = 110, source = 'party2' })
        aura('party1', 'HARMFUL', { id = 980, icon = 'agony' })
        aura('party1', 'HARMFUL', { id = 3034, icon = 'poly', dispel = 'Magic', stacks = 3 })
    """)


class Icons(unittest.TestCase):
    def test_heals_first_then_the_games_order_and_dispellable_debuffs_first(self):
        lua = with_auras()
        self.assertEqual(lua.eval("iconsOf(btn(1, 2))"), "renew@14 poly@12",
                         "58 wide: one debuff and the one buff kept room for")
        self.assertEqual(lua.eval("btn(1, 2).more.text"), "+2")

    def test_the_counts_and_sizes_from_the_page(self):
        lua = with_auras("FostercareRaidDB = { width = 120 }")
        self.assertEqual(lua.eval("iconsOf(btn(1, 2))"), "renew@14 fort@14 poly@12 agony@12")
        self.assertEqual(lua.eval("btn(1, 2).more.text"), "")
        lua.execute("settingsWindow.use('FostercareRaid_buffCount', 1)")
        self.assertEqual(lua.eval("iconsOf(btn(1, 2))"), "renew@14 poly@12 agony@12")
        lua.execute("settingsWindow.use('FostercareRaid_debuffSize', 9)")
        self.assertEqual(lua.eval("iconsOf(btn(1, 2))"), "renew@14 poly@9 agony@9")

    def test_switches_off_the_buffs_and_the_debuffs(self):
        lua = with_auras("FostercareRaidDB = { width = 120 }")
        lua.execute("settingsWindow.use('FostercareRaid_buffs', false)")
        self.assertEqual(lua.eval("iconsOf(btn(1, 2))"), "poly@12 agony@12")
        lua.execute("settingsWindow.use('FostercareRaid_debuffs', false)")
        self.assertEqual(lua.eval("iconsOf(btn(1, 2))"), "")

    def test_a_dispel_type_colours_the_border_and_a_stack_shows(self):
        lua = with_auras("FostercareRaidDB = { width = 120 }")
        icon = "btn(1, 2).icons[3]"
        self.assertEqual(lua.eval(f"{icon}.path"), "poly")
        self.assertEqual(lua.eval(f"{icon}.c.b"), 1, "Magic is blue")
        self.assertEqual(lua.eval(f"{icon}.count.text"), 3)
        self.assertEqual(lua.eval(f"{icon}.cd.hideNumbers"), True, "a 12 px icon with stacks hides its numbers")
        self.assertEqual(lua.eval("btn(1, 2).icons[1].cd.cooldown[1]"), 95, "Renew's sweep from its start")

    def test_icons_are_made_only_as_auras_need_them(self):
        lua = with_auras()
        self.assertEqual(lua.eval("#btn(1, 2).icons"), 2)
        self.assertEqual(lua.eval("#btn(1, 3).icons"), 0)


class HealCorner(unittest.TestCase):
    def test_a_heal_over_time_by_its_spell_effect(self):
        lua = with_auras()
        self.assertTrue(lua.eval("btn(1, 2).hot:IsShown()"))
        self.assertEqual(lua.eval("btn(1, 2).hot.texture"), "renew")
        self.assertFalse(lua.eval("btn(1, 3).hot:IsShown()"))

    def test_each_spell_is_asked_once(self):
        lua = with_auras()
        before = lua.eval("count('GetSpellEffectInfo')")
        lua.execute("delta('party1', { isFullUpdate = true })")
        self.assertEqual(lua.eval("count('GetSpellEffectInfo')"), before)

    def test_off_hides_the_corner_but_keeps_the_buffs(self):
        lua = with_auras()
        lua.execute("settingsWindow.use('FostercareRaid_hots', false)")
        self.assertFalse(lua.eval("btn(1, 2).hot:IsShown()"))
        self.assertIn("renew@14", lua.eval("iconsOf(btn(1, 2))"))


class Deltas(unittest.TestCase):
    def test_a_refresh_rewrites_its_own_record_without_reading_again(self):
        lua = with_auras()
        lua.execute("calls.GetAuraSlots = 0; auras.party1.HELPFUL[2].expires = 125")
        lua.execute("delta('party1', { updatedAuraInstanceIDs = { 2 } })")
        self.assertEqual(lua.eval("count('GetAuraSlots')"), 0)
        self.assertEqual(lua.eval("btn(1, 2).icons[1].cd.cooldown[1]"), 110)

    def test_a_new_aura_reads_the_member_again(self):
        lua = with_auras()
        lua.execute("calls.GetAuraSlots = 0; aura('party1', 'HELPFUL', { id = 1, icon = 'new' })")
        lua.execute("delta('party1', { addedAuraInstanceIDs = { 3 } })")
        self.assertEqual(lua.eval("count('GetAuraSlots')"), 2)
        lua.execute("table.remove(auras.party1.HARMFUL, 2); delta('party1', { removedAuraInstanceIDs = { 102 } })")
        self.assertEqual(lua.eval("iconsOf(btn(1, 2))"), "renew@14 agony@12")

    def test_another_members_delta_is_not_ours(self):
        lua = with_auras()
        lua.execute("calls.GetAuraSlots = 0; delta('nameplate1', { isFullUpdate = true })")
        self.assertEqual(lua.eval("count('GetAuraSlots')"), 0)


if __name__ == "__main__":
    unittest.main()
