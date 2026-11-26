"""The review of 2026-11-26 (AutoBG 1.0, before its release): the arena is
AutoArena's since the split, late work of an enemy who left the frames stays
off the rows, base and faction names inside player names, and the busiest
events do only the work they change."""
import unittest
from abg_env import load
from test_enemies import match, seen, ROGUE, MAGE
from test_objectives import labels

# Counts the widget writes a test asks about.
COUNT = """
writes = {}
for _, m in ipairs({ 'SetTexture', 'SetStatusBarColor', 'Show', 'Hide', 'SetAlpha', 'SetTimerDuration' }) do
    local old = Widget[m]
    Widget[m] = function(...) writes[m] = (writes[m] or 0) + 1; return old(...) end
end
function written() local n = 0; for _, v in pairs(writes) do n = n + v end; return n end
"""


def spy_row(lua, name):
    return lua.eval(f"(function() for _, w in ipairs(widgets) do if w.parent == AutoBG_SpyFrame and w.entry and w.entry.name == '{name}' then return w end end end)()")


class Arena(unittest.TestCase):
    def test_an_arena_is_left_to_autoarena(self):
        """Fails on 2e801e2: the split (dbe9221) took the arena's frame away but
        left the enemies followed there, so the first enemy seen in an arena
        broke the distance look (Enemies.lua:447) ten times a second."""
        lua = load()
        lua.execute("enter('Lordaeron Arena', true)")
        lua.execute(f"enemy('{ROGUE}', {{ name = 'Thandril', class = 'ROGUE', yards = 20 }}); plate('{ROGUE}'); step(0.5)")
        self.assertEqual(lua.eval("#__addon_ns.Enemies.roster"), 0)
        self.assertEqual(lua.eval("type(__addon_ns.Enemies.editSize)"), "number")  # the Frames page edits a battleground size
        for size in (10, 15, 40):
            self.assertFalse(lua.eval(f"AutoBG_TargetsMainFrame{size}:IsShown()"))


class LateWork(unittest.TestCase):
    def test_a_removed_enemys_cast_end_leaves_the_row_he_had(self):
        """Fails on 2e801e2: Ashka turns out a teammate mid-cast; Thandril takes
        his row, and the cast's end wrote Ashka back onto it."""
        lua = load()
        match(lua)
        seen(lua, MAGE)
        lua.execute(f"units['{MAGE}'].cast = {{ name = 'Frostbolt', from = now, to = now + 2.5 }}; fireGUID('UNIT_SPELLCAST_START', '{MAGE}')")
        lua.execute(f"units['{MAGE}'].enemy = nil; plate('{MAGE}')")
        self.assertEqual(lua.eval("row(1).name.text"), "Thandril")
        lua.execute("step(3)")
        self.assertEqual(lua.eval("row(1).name.text"), "Thandril")
        self.assertFalse(lua.eval("row(2):IsShown()"))

    def test_spy_yards_go_to_the_row_that_shows_him_while_the_list_holds_still(self):
        """Fails on 2e801e2: under the mouse the list holds still, but a newcomer
        took index 1 and his yards were written on the hovered row."""
        lua = load("AutoBGDB = { queueOnLogin = false }")
        lua.execute("enemy('0x0000000000000C01', { name = 'Near', class = 'ROGUE', yards = 10 }); plate('0x0000000000000C01'); step(0.2)")
        near = spy_row(lua, "Near")
        self.assertIn("10 yd", near.yards.text)
        lua.execute("run(" + "(function() for _, w in ipairs(widgets) do if w.parent == AutoBG_SpyFrame and w.entry then return w end end end)()" + ", 'OnEnter')")
        lua.execute("enemy('0x0000000000000C02', { name = 'Far', class = 'MAGE', yards = 50 }); plate('0x0000000000000C02'); step(0.3)")
        self.assertIn("10 yd", near.yards.text)


class Lines(unittest.TestCase):
    def test_a_base_or_a_side_inside_a_players_name_is_not_read(self):
        """Fails on 2e801e2: the line was searched whole, so Hordeling's name made
        an Alliance assault Horde, and a base in a name could name the base."""
        lua = load()
        lua.execute("enter('Arathi Basin');"
                    " line('Stablehand has assaulted the Farm!', 'CHAT_MSG_BG_SYSTEM_ALLIANCE'); step(1);"
                    " line('Farmhand has assaulted the Stables!', 'CHAT_MSG_BG_SYSTEM_ALLIANCE'); step(1);"
                    " line('Hordeling has assaulted the Blacksmith!', 'CHAT_MSG_BG_SYSTEM_ALLIANCE'); step()")
        self.assertEqual(labels(lua, "AutoBG_NodeFrame"), "Farm|Stables|Blacksmith")
        self.assertIn("Blacksmith_Alliance", lua.eval("AutoBG_NodeFrame.rows[3].icon.texture"))


class BusyEvents(unittest.TestCase):
    def test_an_enemys_health_moves_his_bar_and_percent_only(self):
        lua = load(setup=COUNT)
        match(lua)
        seen(lua, ROGUE)
        lua.execute(f"writes = {{}}; units['{ROGUE}'].hp = 40; fireGUID('UNIT_HEALTH', '{ROGUE}')")
        self.assertEqual(lua.eval("written()"), 0)
        self.assertEqual(lua.eval("row(2).status.text"), "40%")
        self.assertAlmostEqual(lua.eval("row(2).health.value"), 0.4)
        lua.execute(f"units['{ROGUE}'].dead = true; fireGUID('UNIT_HEALTH', '{ROGUE}')")  # a death redraws the row
        self.assertEqual(lua.eval("row(2).status.text"), "DEAD")
        self.assertEqual(lua.eval("AutoBG_TargetsMainFrame10.title.text"), "Enemies 1/2")

    def test_a_new_target_redraws_only_the_borders(self):
        lua = load(setup=COUNT)
        match(lua)
        seen(lua, ROGUE)
        lua.execute(f"writes = {{}}; setTarget('{ROGUE}')")
        self.assertEqual(lua.eval("writes.SetStatusBarColor or 0"), 0)
        self.assertEqual(lua.eval("writes.SetTimerDuration or 0"), 0)
        self.assertTrue(lua.eval("row(2).edge:IsShown()"))

    def test_an_enemy_coming_into_view_reads_his_auras_with_no_table_each(self):
        lua = load()
        match(lua)
        seen(lua, ROGUE)
        lua.execute(f"aura('{ROGUE}', 1787); n = 0; local old = C_UnitAuras.GetAuraDataBySlot;"
                    " C_UnitAuras.GetAuraDataBySlot = function(...) n = n + 1; return old(...) end;"
                    f" units['{ROGUE}'].visible = false; fireGUID('UNIT_VISIBILITY_CHANGED', '{ROGUE}', false);"
                    f" units['{ROGUE}'].visible = true; fireGUID('UNIT_VISIBILITY_CHANGED', '{ROGUE}', true)")
        self.assertEqual(lua.eval("n"), 0)
        self.assertIn("STEALTH", lua.eval("row(2).status.text"))

    def test_a_carriers_health_reads_no_aura_and_his_stacks_come_with_his_auras(self):
        lua = load()
        match(lua)
        seen(lua, ROGUE)
        lua.execute("line('The Horde flag was picked up by Thandril-NZ!', 'CHAT_MSG_BG_SYSTEM_ALLIANCE')")
        lua.execute("n = 0; local old = C_UnitAuras.GetAuraDataBySpellName;"
                    " C_UnitAuras.GetAuraDataBySpellName = function(...) n = n + 1; return old(...) end")
        lua.execute(f"units['{ROGUE}'].hp = 30; fireGUID('UNIT_HEALTH', '{ROGUE}'); units['{ROGUE}'].yards = 33; step(0.2)")
        self.assertEqual(lua.eval("n"), 0)
        self.assertAlmostEqual(lua.eval("AutoBG_AllianceFC.health.value"), 0.3)
        self.assertIn("33 yd", lua.eval("AutoBG_AllianceFC.info.text"))
        lua.execute(f"local id = aura('{ROGUE}', 1, 'Focused Assault', 'HARMFUL'); units['{ROGUE}'].auras[1].applications = 3;"
                    f" auraEvent('{ROGUE}', {{ id }})")
        self.assertIn("3x", lua.eval("AutoBG_AllianceFC.info.text"))
        self.assertIn("33 yd", lua.eval("AutoBG_AllianceFC.info.text"))

    def test_spy_redraws_nothing_for_an_aura_and_follows_a_known_enemy_once(self):
        lua = load("AutoBGDB = { queueOnLogin = false }", setup=COUNT)
        lua.execute("enemy('0x0000000000000C01', { name = 'Leuka', class = 'PALADIN' }); plate('0x0000000000000C01')")
        lua.execute("regs = 0; local old = Widget.RegisterGUIDEvent; Widget.RegisterGUIDEvent = function(...) regs = regs + 1; return old(...) end")
        lua.execute("writes = {}; auraEvent('0x0000000000000C01', { aura('0x0000000000000C01', 25218) })")
        self.assertEqual(lua.eval("written()"), 0)
        lua.execute("setTarget('0x0000000000000C01'); tokens.mouseover = '0x0000000000000C01'; fire('UPDATE_MOUSEOVER_UNIT')")
        self.assertEqual(lua.eval("regs"), 0)
        self.assertEqual(lua.eval("AutoBG_SpyFrame.title.text"), "Spy  1")

    def test_an_exact_wave_ends_the_raids_health_watch(self):
        """The rough wave (a member back alive) never moves an exact one, so once
        the healer's own countdown is read, the raid's health is not listened to."""
        lua = load()
        lua.execute("enter('Arathi Basin')")
        watching = "(function() for _, w in ipairs(widgets) do if receives(w, 'UNIT_HEALTH', 'raid3') then return true end end return false end)()"
        self.assertTrue(lua.eval(watching))
        lua.execute("healerTime = 20; fire('AREA_SPIRIT_HEALER_IN_RANGE')")
        self.assertFalse(lua.eval(watching))
        lua.execute("enter(nil); enter('Arathi Basin')")  # a new match listens again
        self.assertTrue(lua.eval(watching))


if __name__ == "__main__":
    unittest.main()
