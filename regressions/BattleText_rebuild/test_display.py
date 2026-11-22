"""The engine draws the text: animation groups, the line pools, the overlap push,
the crit stack, a loading screen, what runs at rest and the garbage of a fight
(spec BattleText.md 4.5, tests 10, 11 and 15). BattleText 1.0, written new
2026-11-22. The group timing is the env's model of ### region:CreateAnimationGroup.
"""
import unittest
from bt_env import load


def anchor_y(lua, line):
    return lua.eval(f"select(5, {line}.frame:GetPoint(1))")


class Animation(unittest.TestCase):
    def test_a_line_plays_and_goes_back_to_its_pool_when_it_ends(self):
        lua = load()
        lua.execute("forget() cleu('SPELL_AURA_APPLIED', priest, you, 1243, 'Power Word: Fortitude', 2, 'BUFF') "
                    "line = lineOf(last())")
        self.assertTrue(lua.eval("line.group:IsPlaying() and line.busy and line.frame:IsShown() == 1"))
        self.assertTrue(lua.eval("line.group.unthrottled"))
        self.assertEqual(lua.eval("line.group:GetDuration()"), 2)  # 150 px at 75 px a second
        lua.execute("step(1.9)")
        self.assertTrue(lua.eval("line.busy"))
        lua.execute("step(0.2)")
        self.assertFalse(lua.eval("line.busy"))
        self.assertFalse(lua.eval("line.frame:IsShown()"))
        self.assertEqual(lua.eval("playing()"), 0)

    def test_the_eleventh_line_reuses_the_oldest(self):
        lua = load()
        lua.execute("forget() for i = 1, 11 do cleu('SPELL_AURA_APPLIED', priest, you, i, 'Aura ' .. i, 2, 'BUFF') end")
        area = "__addon_ns.areas.Notification"
        self.assertEqual(lua.eval(f"#{area}.lines"), 10)
        self.assertEqual(lua.eval(f"{area}.lines[1].text.text"), "[Aura 11]")
        self.assertEqual(lua.eval(f"{area}.lines[2].text.text"), "[Aura 2]")
        frames = lua.eval(f'''(function() local n = 0
            for _, w in ipairs(widgets) do if w.parent == {area}.frame then n = n + 1 end end return n end)()''')
        self.assertEqual(frames, 10)

    def test_no_onupdate_and_no_timer_at_rest(self):
        lua = load()
        self.assertEqual(lua.eval("liveTimers()"), 0)
        lua.execute("fire('PLAYER_IN_COMBAT_CHANGED', true) cleu('SWING_DAMAGE', you, mob, 100, 0, 1, nil, nil, nil, 1) "
                    "cleu('SWING_DAMAGE', mob, you, 60, 0, 1) step(0.1) fire('PLAYER_IN_COMBAT_CHANGED', false) step(0.3)")
        self.assertEqual(lua.eval("liveTimers()"), 0)
        lua.execute("step(3)")
        self.assertEqual(lua.eval("playing()"), 0)
        self.assertNotIn(",OnUpdate,", lua.eval("listening()"))
        self.assertFalse(lua.eval("(function() for _, g in ipairs(groups) do if g.scripts.OnUpdate then return true end "
                                  "end return false end)()"))

    def test_a_loading_screen_stops_every_line_and_empties_the_queue(self):
        lua = load()
        lua.execute("forget() fire('PLAYER_IN_COMBAT_CHANGED', true) cleu('SWING_DAMAGE', you, mob, 100, 0, 1, nil, nil, nil, 1) "
                    "step(0.3) forget() cleu('SWING_DAMAGE', mob, you, 60, 0, 1)")
        self.assertGreater(lua.eval("playing()"), 0)
        lua.execute("fire('PLAYER_ENTERING_WORLD')")
        self.assertEqual(lua.eval("playing()"), 0)
        self.assertFalse(lua.eval('''(function() for _, a in pairs(__addon_ns.areas) do for i = 1, 10 do
            local l = a.lines[i] or a.crits[i]
            if l and (l.busy or l.frame:IsShown()) then return true end end end return false end)()'''))
        lua.execute("step(0.3)")
        self.assertEqual(lua.eval("texts()"), "")
        self.assertEqual(lua.eval("liveTimers()"), 0)
        lua.execute("forget() cleu('SWING_DAMAGE', mob, you, 70, 0, 1) step(0.3)")
        self.assertEqual(lua.eval("texts()"), "|cffff0000-|r70")


class Overlap(unittest.TestCase):
    def test_a_new_line_pushes_the_newest_up_and_the_push_runs_down_the_chain(self):
        lua = load()
        area = "__addon_ns.areas.Notification"
        aura = "cleu('SPELL_AURA_APPLIED', priest, you, {0}, 'Aura {0}', 2, 'BUFF')"
        lua.execute(aura.format(1) + " step(0.1) " + aura.format(2))
        # The first had moved 150 * 0.1 / 2 = 7.5 px; the second needs 20 + 2 above its bottom.
        self.assertAlmostEqual(anchor_y(lua, f"{area}.lines[1]"), 14.5)
        self.assertEqual(anchor_y(lua, f"{area}.lines[2]"), 0)
        lua.execute(aura.format(3))
        self.assertAlmostEqual(anchor_y(lua, f"{area}.lines[2]"), 22)
        self.assertAlmostEqual(anchor_y(lua, f"{area}.lines[1]"), 36.5)
        self.assertEqual(anchor_y(lua, f"{area}.lines[3]"), 0)

    def test_a_line_far_enough_up_is_left_alone(self):
        lua = load()
        area = "__addon_ns.areas.Notification"
        lua.execute("cleu('SPELL_AURA_APPLIED', priest, you, 1, 'A', 2, 'BUFF') step(0.5) "
                    "cleu('SPELL_AURA_APPLIED', priest, you, 2, 'B', 2, 'BUFF')")
        self.assertEqual(anchor_y(lua, f"{area}.lines[1]"), 0)

    def test_crits_stack_around_the_middle(self):
        lua = load()
        lua.execute("for i = 1, 3 do cleu('SWING_DAMAGE', you, i == 1 and mob or i == 2 and mob2 or priest, 100 + i, 0, 1, "
                    "nil, nil, nil, 1) end step(0.3)")
        area = "__addon_ns.areas.Outgoing"
        self.assertEqual([anchor_y(lua, f"{area}.crits[{i}]") for i in (1, 2, 3)], [106, 136, 76])
        lua.execute("step(3) cleu('SWING_DAMAGE', you, mob, 1, 0, 1, nil, nil, nil, 1) step(0.3)")
        self.assertEqual(anchor_y(lua, f"{area}.crits[4]"), 106)


class Garbage(unittest.TestCase):
    def test_a_fight_makes_no_table_per_event(self):
        lua = load(setup="playerClass = 'MAGE'")
        # The kit's C_Timer.After makes a table per call (its own, not the addon's):
        # one fixed slot here, run by hand at the end of each window.
        lua.execute("C_Timer.After = function(_, fn) due = fn end "
                    "function window() local f = due; due = nil; if f then f() end end")
        # Measured with the collector stopped (it would run inside the loop), after a
        # warm-up that fills the pools and makes each text once.
        code = ("collectgarbage('collect') collectgarbage('stop') before = collectgarbage('count') "
                "for i = 1, {n} do "
                "cleu('SWING_DAMAGE', you, mob, 100, 0, 1) cleu('SWING_DAMAGE', you, mob, 120, 0, 1, nil, nil, nil, 1) "
                "cleu('SPELL_DAMAGE', you, mob, 133, 'Fireball', 4, 300, 0, 4) cleu('SWING_MISSED', mob, you, 'DODGE') "
                "cleu('SWING_DAMAGE', mob, you, 80, 0, 1, nil, nil, 20) "
                "cleu('SPELL_HEAL', priest, you, 2054, 'Heal', 2, 500, 200, 0) "
                "cleu('SPELL_AURA_APPLIED', mob, you, 11597, 'Sunder Armor', 1, 'DEBUFF') "
                "cleu('SPELL_AURA_APPLIED_DOSE', mob, you, 11597, 'Sunder Armor', 1, 'DEBUFF', 2) "
                "mana = 1000 fire('UNIT_POWER_UPDATE', 'player', 'MANA') mana = 1100 fire('UNIT_POWER_UPDATE', 'player', 'MANA') "
                "window() forget() end "
                "grown = collectgarbage('count') - before collectgarbage('restart')")
        lua.execute(code.replace("{n}", "50"))
        lua.execute(code.replace("{n}", "50"))
        few = lua.eval("grown")
        lua.execute(code.replace("{n}", "500"))
        many = lua.eval("grown")
        self.assertLess(many - few, 0.5, f"{few:.1f} KB for 50 rounds, {many:.1f} KB for 500")


if __name__ == "__main__":
    unittest.main()
