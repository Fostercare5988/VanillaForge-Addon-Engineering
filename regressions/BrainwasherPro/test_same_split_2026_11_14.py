"""Two specs with one talent split (audit 2026-11-14).

Claude's saved specs: slot 1 "PVE ASSA" and slot 3 "BWL" are both 41/10/0.
The point split was the only record of a spec, so both showed Active, the
other could not be activated ("already active"), and a swap between them
changed no split and never loaded its bars. The talent ranks tell them apart.
Mocks only: the device's swap and its events stay in-game checks.
"""
import unittest
from bwp_env import load

# Two 41/10/0 builds that differ in tree 1.
BUILD_A = "{ { 5, 5, 5, 5, 5, 5, 5, 5, 1 }, { 5, 5 }, {} }"
BUILD_B = "{ { 5, 5, 5, 5, 5, 5, 5, 3, 3 }, { 5, 5 }, {} }"
SPECS = ("BrainwasherProDB = { specs = { [1] = { name = 'PVE ASSA', actionProfile = 'PvE' },"
         " [3] = { name = 'BWL', actionProfile = 'PvP' } } }")
MENU = '''{
    { id = 21, name = "Activate 1st Specialization  (41/10/0)" },
    { id = 11, name = "Save 1st Specialization." },
    { id = 23, name = "Activate 3rd Specialization  (41/10/0)" },
    { id = 13, name = "Save 3rd Specialization." },
}'''


def device(setup=""):
    lua = load(SPECS + "; " + setup)
    lua.execute(f"setBuild({BUILD_A}); talk(DEVICE, {MENU})")
    return lua


def active(lua, slot):
    return bool(lua.eval(f"BrainwasherProSlot{slot}.active:IsShown()"))


def save(lua, slot):
    lua.execute(f'click(BrainwasherProSlot{slot}Save); accept("BRAINWASHERPRO_SAVE_SPEC")')


class SameSplit(unittest.TestCase):
    def test_other_spec_with_the_same_split_can_be_activated(self):
        lua = device()
        lua.execute("click(BrainwasherProIcon3)")
        self.assertNotIn("already active", lua.eval("table.concat(messages, '\\n')"))
        self.assertTrue(lua.eval("popups.BRAINWASHERPRO_LOAD_SPEC ~= nil"))

    def test_swap_between_same_split_specs_loads_its_bars(self):
        lua = device()
        save(lua, 1)
        self.assertTrue(active(lua, 1))
        self.assertFalse(active(lua, 3))
        lua.execute('click(BrainwasherProIcon3); accept("BRAINWASHERPRO_LOAD_SPEC"); leave()')
        self.assertIn(23, list(lua.eval("selected").values()))
        lua.execute(f'setBuild({BUILD_B}); fire("SPELLS_CHANGED"); advance(2)')
        self.assertEqual(lua.eval("abpLoaded[1]"), "PvP")
        lua.execute(f"talk(DEVICE, {MENU})")
        self.assertTrue(active(lua, 3))
        self.assertFalse(active(lua, 1))

    def test_last_saved_of_two_identical_builds_is_active(self):
        lua = device()
        save(lua, 1)
        save(lua, 3)
        self.assertTrue(active(lua, 3))
        self.assertFalse(active(lua, 1))

    def test_build_saved_elsewhere_is_forgotten(self):
        """A slot saved again from the device's own menu gets a new split: the
        build recorded for it no longer describes it."""
        lua = device()
        save(lua, 1)
        lua.execute('leave(); talk(DEVICE, { { id = 21, name = "Activate 1st Specialization  (32/0/19)" } })')
        self.assertFalse(active(lua, 1))
        self.assertIsNone(lua.eval("BrainwasherProDB.specs[1].build"))

    def test_identical_build_loads_its_bars_without_waiting(self):
        """Nothing changes when the other slot holds the same talents: its bars
        load once the events stop, not after the 60 s timeout."""
        lua = device()
        save(lua, 3)
        save(lua, 1)
        lua.execute('click(BrainwasherProIcon3); accept("BRAINWASHERPRO_LOAD_SPEC"); leave(); advance(2)')
        self.assertEqual(lua.eval("abpLoaded[1]"), "PvP")
        self.assertEqual(lua.eval("BrainwasherProDB.current"), 3)

    def test_swap_without_events_is_seen_at_the_timeout(self):
        """If a swap inside one split sends no talent or spell event, the
        timeout still sees the new build and loads the bars."""
        lua = device()
        save(lua, 1)
        lua.execute(f'click(BrainwasherProIcon3); accept("BRAINWASHERPRO_LOAD_SPEC"); leave()'
                    f'; setBuild({BUILD_B}); advance(61)')
        self.assertEqual(lua.eval("abpLoaded[1]"), "PvP")
        self.assertNotIn("left as they are", lua.eval("table.concat(messages, '\\n')"))

    def test_swap_without_bars_records_the_spec(self):
        lua = load("BrainwasherProDB = { specs = { [1] = { name = 'A' }, [3] = { name = 'B' } } }")
        lua.execute(f"setBuild({BUILD_A}); talk(DEVICE, {MENU})")
        save(lua, 1)
        lua.execute(f'click(BrainwasherProIcon3); accept("BRAINWASHERPRO_LOAD_SPEC"); leave()'
                    f'; setBuild({BUILD_B}); fire("SPELLS_CHANGED"); advance(2)')
        self.assertEqual(lua.eval("BrainwasherProDB.current"), 3)
        self.assertEqual(lua.eval("BrainwasherProDB.specs[3].build"), "555555533-55-")
        self.assertEqual(lua.eval("#abpLoaded"), 0)


class IconPicker(unittest.TestCase):
    def test_item_icons_are_offered(self):
        """The stock GetMacroIconInfo list has no INV_ item icons (API.md)."""
        lua = device()
        lua.execute("click(BrainwasherProSlot1Edit); for i = 1, 10 do click(BrainwasherProEditNext) end")
        paths = [lua.eval(f"BrainwasherProEditFrame.icons[{i}].path") for i in (1, 2)]
        self.assertTrue(all(p.startswith("Interface\\Icons\\INV_") for p in paths), paths)
        lua.execute("click(BrainwasherProEditFrame.icons[1]); click(BrainwasherProEditConfirm)")
        self.assertEqual(lua.eval("BrainwasherProDB.specs[1].icon"), paths[0])


if __name__ == "__main__":
    unittest.main()
