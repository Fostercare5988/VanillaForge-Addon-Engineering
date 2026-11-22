"""What a plate shows of its unit (spec 4.6, tests 3 to 8): the plate's unit as the
game moves it, the class bar, the health text, the target glow and combo points,
"Targeting you" and the raid mark. Nameplates 1.0, written new 2026-11-22.
"""
import unittest
from np_env import load, ENEMY_ROGUE, ENEMY_NPC, FRIEND

P = "__addon_ns.byToken"


def shown(lua, expr):
    return bool(lua.eval(f"({expr}):IsShown()"))


class Units(unittest.TestCase):
    def test_added_draws_everything_at_once(self):
        lua = load()
        lua.execute(f"show('nameplate1', {ENEMY_ROGUE})")
        self.assertTrue(shown(lua, f"{P}.nameplate1.classBar"))
        self.assertEqual(lua.eval(f"{P}.nameplate1.health.text"), "3K")

    def test_a_unit_moving_to_another_frame_leaves_nothing_on_the_old_one(self):
        lua = load()
        lua.execute(f"old = show('nameplate1', {ENEMY_ROGUE}); target('nameplate1')")
        lua.execute(f"hide('nameplate1'); new = show('nameplate1', {ENEMY_ROGUE})")
        self.assertTrue(lua.eval(f"{P}.nameplate1.frame == new"))
        lua.execute("target('nameplate1')")
        self.assertTrue(shown(lua, f"{P}.nameplate1.glow"))

    def test_the_games_rebuild_on_the_same_frame_leaves_no_stale_state(self):
        lua = load()
        lua.execute(f"f = show('nameplate1', {ENEMY_ROGUE}); hide('nameplate1'); show('nameplate1', {ENEMY_NPC}, f)")
        self.assertFalse(shown(lua, f"{P}.nameplate1.classBar"))
        self.assertEqual(lua.eval(f"{P}.nameplate1.health.text"), "72%")

    def test_plates_up_at_a_reload_are_drawn(self):
        lua = load(world=False)
        lua.execute(f"units.nameplate3 = {ENEMY_ROGUE}; units.nameplate3.guid = '0xA'; units.nameplate3.frame = nativePlate()")
        lua.execute("fire('VARIABLES_LOADED'); fire('PLAYER_LOGIN'); fire('PLAYER_ENTERING_WORLD')")
        self.assertEqual(lua.eval(f"{P}.nameplate3.health.text"), "3K")

    def test_a_plate_before_the_first_loading_screen_waits_for_it(self):
        lua = load(world=False)
        lua.execute(f"show('nameplate1', {ENEMY_ROGUE})")
        self.assertIsNone(lua.eval(f"{P}.nameplate1"))
        lua.execute("fire('VARIABLES_LOADED'); fire('PLAYER_ENTERING_WORLD')")
        self.assertEqual(lua.eval(f"{P}.nameplate1.health.text"), "3K")

    def test_a_player_not_yet_cached_has_no_class_bar_and_no_error(self):
        lua = load()
        lua.execute("show('nameplate1', { player = true, enemy = true, hp = 0, max = 0 })")
        self.assertIsNone(lua.eval(f"{P}.nameplate1.classBar"))
        self.assertFalse(shown(lua, f"{P}.nameplate1.health"))


class ClassBar(unittest.TestCase):
    def test_a_player_gets_the_class_colour_and_the_health_value(self):
        lua = load()
        lua.execute(f"show('nameplate1', {FRIEND})")
        bar = f"{P}.nameplate1.classBar"
        self.assertEqual(lua.eval(f"{bar}.barColor"), "0.96,0.55,0.73")
        self.assertEqual((lua.eval(f"{bar}.max"), lua.eval(f"{bar}.value")), (2500, 2500))
        lua.execute("units.nameplate1.hp = 1000; fire('UNIT_HEALTH', 'nameplate1')")
        self.assertEqual(lua.eval(f"{bar}.value"), 1000)
        self.assertIsNone(lua.eval(f"{bar}.alpha"))

    def test_an_npc_has_none_and_its_bar_is_never_written(self):
        lua = load()
        lua.execute(f"show('nameplate1', {ENEMY_NPC}); fire('UNIT_HEALTH', 'nameplate1')")
        self.assertIsNone(lua.eval(f"{P}.nameplate1.classBar"))
        self.assertIsNone(lua.eval("units.nameplate1.frame.bar.value"))
        self.assertIsNone(lua.eval("units.nameplate1.frame.bar.barColor"))

    def test_switched_off_it_hides(self):
        lua = load()
        lua.execute(f"show('nameplate1', {ENEMY_ROGUE}); settingsWindow.use('Nameplates_classColors', false)")
        self.assertFalse(shown(lua, f"{P}.nameplate1.classBar"))


class Health(unittest.TestCase):
    def test_value_percent_and_nothing_for_max_zero(self):
        lua = load()
        lua.execute(f"show('nameplate1', {ENEMY_ROGUE}); show('nameplate2', {ENEMY_NPC});"
                    " show('nameplate3', { enemy = true, hp = 0, max = 0 })")
        self.assertEqual(lua.eval(f"{P}.nameplate1.health.text"), "3K")
        self.assertEqual(lua.eval(f"{P}.nameplate2.health.text"), "72%")
        self.assertFalse(shown(lua, f"{P}.nameplate3.health"))

    def test_unchanged_numbers_set_no_text(self):
        lua = load()
        lua.execute(f"show('nameplate1', {ENEMY_NPC}); forget(); fire('UNIT_HEALTH', 'nameplate1');"
                    " fire('UNIT_MAXHEALTH', 'nameplate1')")
        self.assertEqual(lua.eval("count('SetText')"), 0)
        lua.execute("units.nameplate1.hp = 40; fire('UNIT_HEALTH', 'nameplate1')")
        self.assertEqual(lua.eval(f"{P}.nameplate1.health.text"), "40%")

    def test_switched_off_it_hides(self):
        lua = load()
        lua.execute(f"show('nameplate1', {ENEMY_NPC}); settingsWindow.use('Nameplates_health', false)")
        self.assertFalse(shown(lua, f"{P}.nameplate1.health"))


class Target(unittest.TestCase):
    def test_the_glow_follows_the_target(self):
        lua = load()
        lua.execute(f"show('nameplate1', {ENEMY_ROGUE}); show('nameplate2', {ENEMY_NPC}); target('nameplate1')")
        self.assertTrue(shown(lua, f"{P}.nameplate1.glow"))
        self.assertFalse(shown(lua, f"{P}.nameplate2.glow"))
        lua.execute("target('nameplate2')")
        self.assertFalse(shown(lua, f"{P}.nameplate1.glow"))
        self.assertTrue(shown(lua, f"{P}.nameplate2.glow"))
        lua.execute("target(nil)")
        self.assertFalse(shown(lua, f"{P}.nameplate2.glow"))

    def test_the_targets_plate_coming_into_view_glows(self):
        lua = load()
        lua.execute("targetGUID = '0xT'")
        lua.execute(f"d = {ENEMY_ROGUE}; d.guid = '0xT'; show('nameplate4', d)")
        self.assertTrue(shown(lua, f"{P}.nameplate4.glow"))

    def test_combo_pips_on_the_target_only(self):
        lua = load()
        lua.execute(f"show('nameplate1', {ENEMY_ROGUE}); show('nameplate2', {ENEMY_NPC}); target('nameplate1')")
        lua.execute("combo = 3; fire('PLAYER_COMBO_POINTS')")
        pips = [shown(lua, f"{P}.nameplate1.combo[{i}]") for i in range(1, 6)]
        self.assertEqual(pips, [True, True, True, False, False])
        self.assertFalse(any(shown(lua, f"{P}.nameplate2.combo[{i}]") for i in range(1, 6)))
        lua.execute("combo = 0; target('nameplate2')")
        self.assertFalse(any(shown(lua, f"{P}.nameplate1.combo[{i}]") for i in range(1, 6)))

    def test_a_warrior_shows_no_pips(self):
        lua = load(setup="playerClass = 'WARRIOR'")
        lua.execute(f"show('nameplate1', {ENEMY_ROGUE}); combo = 3; target('nameplate1')")
        self.assertFalse(shown(lua, f"{P}.nameplate1.combo[1]"))


class TargetingYou(unittest.TestCase):
    def test_a_hostile_npc_that_turns_to_you(self):
        lua = load()
        lua.execute(f"show('nameplate1', {ENEMY_NPC})")
        self.assertFalse(shown(lua, f"{P}.nameplate1.targeting"))
        lua.execute("units.nameplate1.target = '0xPLAYER'; fire('UNIT_TARGET', 'nameplate1')")
        self.assertTrue(shown(lua, f"{P}.nameplate1.targeting"))
        lua.execute("units.nameplate1.target = nil; fire('UNIT_TARGET', 'nameplate1')")
        self.assertFalse(shown(lua, f"{P}.nameplate1.targeting"))

    def test_never_an_enemy_player_or_a_friendly_npc(self):
        lua = load()
        lua.execute(f"show('nameplate1', {ENEMY_ROGUE}); show('nameplate2', {{ hp = 50, max = 100 }})")
        lua.execute("for _, t in ipairs({'nameplate1', 'nameplate2'}) do units[t].target = '0xPLAYER';"
                    " fire('UNIT_TARGET', t) end")
        self.assertFalse(shown(lua, f"{P}.nameplate1.targeting"))
        self.assertFalse(shown(lua, f"{P}.nameplate2.targeting"))

    def test_switched_off_unregisters_unit_target(self):
        lua = load()
        lua.execute("settingsWindow.use('Nameplates_targeting', false)")
        self.assertNotIn("UNIT_TARGET", lua.eval("listening()"))


class Marks(unittest.TestCase):
    def test_our_mark_in_the_place_and_size_set(self):
        lua = load()
        lua.execute(f"d = {ENEMY_ROGUE}; d.mark = 8; show('nameplate1', d)")
        mark = f"{P}.nameplate1.mark"
        self.assertTrue(shown(lua, mark))
        self.assertEqual(lua.eval(f"{mark}.markIndex"), 8)
        self.assertAlmostEqual(lua.eval(f"{mark}.width"), 27)  # 30 at 90 %
        self.assertEqual(lua.eval(f"({mark}:GetPoint(1))"), "BOTTOM")
        self.assertEqual(lua.eval("units.nameplate1.frame.regions[6].alpha"), 0)
        lua.execute("settingsWindow.use('Nameplates_markPlace', 'LEFT')")
        self.assertEqual(lua.eval(f"({mark}:GetPoint(1))"), "RIGHT")

    def test_switched_off_the_games_mark_comes_back(self):
        lua = load()
        lua.execute(f"d = {ENEMY_ROGUE}; d.mark = 8; show('nameplate1', d); settingsWindow.use('Nameplates_marks', false)")
        self.assertFalse(shown(lua, f"{P}.nameplate1.mark"))
        self.assertEqual(lua.eval("units.nameplate1.frame.regions[6].alpha"), 1)
        self.assertNotIn("RAID_TARGET_UPDATE", lua.eval("listening()"))

    def test_a_mark_moves_to_another_plate(self):
        lua = load()
        lua.execute(f"d = {ENEMY_ROGUE}; d.mark = 1; show('nameplate1', d); show('nameplate2', {ENEMY_NPC})")
        self.assertFalse(shown(lua, f"{P}.nameplate2.mark"))
        lua.execute("units.nameplate1.mark = nil; units.nameplate2.mark = 1; fire('RAID_TARGET_UPDATE')")
        self.assertFalse(shown(lua, f"{P}.nameplate1.mark"))
        self.assertTrue(shown(lua, f"{P}.nameplate2.mark"))


if __name__ == "__main__":
    unittest.main()
