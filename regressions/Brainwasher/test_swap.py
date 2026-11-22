"""The swap after Activate, and nothing at rest (spec 4.6 tests 5 and 11)."""
import unittest
from sp_env import load, CLAUDE_SAVED, BUILD_32_0_19
from test_device import ROWS, claude

PVP = "setBuild(points(32), {}, points(19))"
EVENTS = "CHARACTER_POINTS_CHANGED,PLAYER_REGEN_ENABLED,SPELLS_CHANGED"


def activate(lua, slot):
    lua.execute(f"click(rowFrame({slot}).button); accept('SPECS_LOAD')")


def swap_to_pvp(lua):
    lua.execute(PVP + "; fire('CHARACTER_POINTS_CHANGED')")


def loaded(lua):
    return [lua.eval(f"barsLoaded[{i}]") for i in range(1, lua.eval("#barsLoaded") + 1)]


class Swap(unittest.TestCase):
    def test_the_profile_loads_once_after_the_last_talent_event(self):
        lua = claude(saved='SpecsDB = { current = 1, [2] = { bars = "pvp" } }')
        activate(lua, 2)
        self.assertEqual(lua.eval("selected[1]"), 22)
        swap_to_pvp(lua)
        lua.execute("step(1)")
        lua.execute("fire('SPELLS_CHANGED'); step(1.4)")
        self.assertEqual(loaded(lua), [])
        lua.execute("step(0.2)")
        self.assertEqual(loaded(lua), ["pvp"])
        lua.execute("step(5)")
        self.assertEqual(loaded(lua), ["pvp"])
        self.assertEqual(lua.eval("SpecsDB.current"), 2)
        self.assertEqual(lua.eval("SpecsDB[2].build"), BUILD_32_0_19)

    def test_the_swap_events_are_registered_only_during_the_swap(self):
        lua = claude(saved='SpecsDB = { current = 1, [2] = { bars = "pvp" } }')
        self.assertEqual(lua.eval("listening()"), "GOSSIP_CLOSED,GOSSIP_SHOW")
        activate(lua, 2)
        self.assertEqual(lua.eval("listening()"), "CHARACTER_POINTS_CHANGED,GOSSIP_CLOSED,GOSSIP_SHOW,"
                         "PLAYER_REGEN_ENABLED,SPELLS_CHANGED")
        swap_to_pvp(lua)
        lua.execute("step(2)")
        self.assertEqual(lua.eval("listening()"), "GOSSIP_CLOSED,GOSSIP_SHOW")

    def test_a_swap_that_keeps_the_points_is_seen_by_its_build(self):
        # Only spells were unlearned and learned (seen in play, 2026-10-22).
        lua = claude(saved='SpecsDB = { current = 1, [3] = { bars = "pveBWL" } }',
                     talents="setBuild(points(41), points(10), {})")
        activate(lua, 3)
        lua.execute("setBuild(points(10), points(41), {}); fire('SPELLS_CHANGED'); step(2)")
        self.assertEqual(loaded(lua), ["pveBWL"])

    def test_in_combat_the_profile_waits_for_the_end_of_combat(self):
        lua = claude(saved='SpecsDB = { current = 1, [2] = { bars = "pvp" } }')
        activate(lua, 2)
        lua.execute("inCombat = true")
        swap_to_pvp(lua)
        lua.execute("step(3)")
        self.assertEqual(loaded(lua), [])
        lua.execute("inCombat = false; fire('PLAYER_REGEN_ENABLED')")
        self.assertEqual(loaded(lua), ["pvp"])
        self.assertEqual(lua.eval("listening()"), "GOSSIP_CLOSED,GOSSIP_SHOW")

    def test_a_slot_that_holds_your_talents_loads_without_a_change(self):
        # Slots 2 and 3 hold one build and current is 1: neither is active, yet the
        # talents will not change.
        saved = ('SpecsDB = { current = 1, [2] = { build = "%s" }, [3] = { bars = "pveBWL", build = "%s" } }'
                 % (BUILD_32_0_19, BUILD_32_0_19))
        lua = claude(PVP, saved=saved, setup="CLAUDE = { '41/10/0', '32/0/19', '32/0/19' }")
        activate(lua, 3)
        lua.execute("step(1.6)")
        self.assertEqual(loaded(lua), ["pveBWL"])

    def test_talents_that_do_not_change_load_nothing_and_say_so(self):
        lua = claude(saved='SpecsDB = { current = 1, [2] = { bars = "pvp" } }')
        activate(lua, 2)
        lua.execute("step(61)")
        self.assertEqual(loaded(lua), [])
        self.assertIn("Talents did not change", lua.eval("say()"))
        self.assertEqual(lua.eval("listening()"), "GOSSIP_CLOSED,GOSSIP_SHOW")

    def test_a_change_without_an_event_is_found_at_the_limit(self):
        lua = claude(saved='SpecsDB = { current = 1, [2] = { bars = "pvp" } }')
        activate(lua, 2)
        lua.execute(PVP + "; step(61)")
        lua.execute("step(2)")
        self.assertEqual(loaded(lua), ["pvp"])

    def test_a_slot_without_bars_still_records_the_swap(self):
        lua = claude(saved='SpecsDB = { current = 1 }')
        activate(lua, 2)
        swap_to_pvp(lua)
        lua.execute("step(2)")
        self.assertEqual(loaded(lua), [])
        self.assertEqual(lua.eval("SpecsDB.current"), 2)


class Rest(unittest.TestCase):
    def test_a_first_login_registers_two_events_and_no_timer(self):
        lua = load(setup=ROWS)
        self.assertEqual(lua.eval("listening()"), "GOSSIP_CLOSED,GOSSIP_SHOW")
        self.assertEqual(lua.eval("liveTimers()"), 0)
        self.assertIsNone(lua.eval("SpecsPanel"))
        self.assertEqual(lua.eval("type(SpecsDB)"), "table")

    def test_a_visit_leaves_no_timer_and_no_update(self):
        lua = claude()
        lua.execute("click(panelButton('Show original'))")
        self.assertEqual(lua.eval("liveTimers()"), 0)
        self.assertEqual(lua.eval("listening()"), "GOSSIP_CLOSED,GOSSIP_SHOW")


if __name__ == "__main__":
    unittest.main()
