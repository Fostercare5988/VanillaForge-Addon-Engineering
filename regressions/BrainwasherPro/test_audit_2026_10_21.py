"""Reproductions for the 2026-10-21 BrainwasherPro modernization.

Mocks only: the device's real option text on OctoWoW, its own confirmations
and how long a talent swap takes stay in-game checks.
"""
import unittest
from bwp_env import load


def device(setup=""):
    lua = load(setup)
    lua.execute("talk(DEVICE, deviceMenu())")
    return lua


class Device(unittest.TestCase):
    def test_hidden_native_menu_cannot_be_clicked(self):
        """1.5 only faded the native menu: its invisible buttons still took clicks."""
        lua = device()
        self.assertEqual(lua.eval("GossipFrame:GetAlpha()"), 0)
        self.assertLessEqual(lua.eval("GossipFrame:GetScale()"), 0.05)

    def test_kept_show_original_restores_native_menu(self):
        """Kept: Show original brings the device's own menu back."""
        lua = device()
        lua.execute("BrainwasherProFrame:Hide()")
        self.assertEqual(lua.eval("GossipFrame:GetAlpha()"), 1)
        self.assertEqual(lua.eval("GossipFrame:GetScale()"), 1)

    def test_buying_a_slot_asks_first(self):
        """Buying a slot spent gold on one click, without a confirmation."""
        lua = device()
        lua.execute("click(BrainwasherProIcon3)")
        self.assertEqual(lua.eval("#selected"), 0)
        self.assertIn("100", lua.eval("popups.BRAINWASHERPRO_BUY_SLOT and popups.BRAINWASHERPRO_BUY_SLOT.text or ''"))
        lua.execute('accept("BRAINWASHERPRO_BUY_SLOT")')
        self.assertEqual(lua.eval("selected[1]"), 33)

    def test_server_confirmed_option_skips_our_popup(self):
        """Options the server confirms itself (boxCoded) are not asked twice."""
        lua = load()
        lua.execute('''
            local menu = deviceMenu(); menu[3].flags = 1
            talk(DEVICE, menu); click(BrainwasherProIcon2)
        ''')
        self.assertEqual(lua.eval("selected[1]"), 22)

    def test_device_is_found_by_its_menu(self):
        """1.5 matched the NPC name; the spec options identify the device."""
        lua = load()
        lua.execute('talk("Gnomish Brainwasher", deviceMenu())')
        self.assertTrue(lua.eval("BrainwasherProFrame ~= nil and BrainwasherProFrame:IsShown()"))

    def test_kept_trainer_reset_option_is_not_the_device(self):
        """Kept: a class trainer's reset option does not open the window."""
        lua = load()
        lua.execute('talk("Rogue Trainer", { { id = 1, name = "Reset my talents" } })')
        self.assertFalse(lua.eval("BrainwasherProFrame ~= nil and BrainwasherProFrame:IsShown()"))

    def test_only_offered_slots_are_shown(self):
        """1.5 showed "Unknown State" for slots the device did not offer."""
        lua = load()
        lua.execute('talk(DEVICE, { { id = 11, name = "Save 1st Specialization" }, { id = 22, name = "Activate 2nd Specialization" } })')
        self.assertNotIn("Unknown State", lua.eval("shownText()"))
        self.assertFalse(lua.eval("BrainwasherProSlot3:IsShown()"))

    def test_kept_save_records_the_talent_split(self):
        """Kept: saving a slot selects its Save option and stores the point split."""
        lua = device("talents = { 31, 20, 0 }")
        lua.execute('(BrainwasherPro.SaveSlot or BrainwasherPro.OnSaveClicked)(BrainwasherPro, 1); accept("BRAINWASHERPRO_SAVE_SPEC")')
        self.assertEqual(lua.eval("selected[1]"), 11)
        self.assertEqual(lua.eval("BrainwasherProDB.specs[1].t1"), 31)


class SavedData(unittest.TestCase):
    def test_unused_talent_snapshot_is_cleared(self):
        """1.5 saved every talent of each spec and never read it back."""
        lua = load("BrainwasherProDB = { specs = { [2] = { name = 'PVE ASSA', talents = { { { name = 'Malice' } } } } } }")
        self.assertIsNone(lua.eval("BrainwasherProDB.specs[2].talents"))
        self.assertEqual(lua.eval("BrainwasherProDB.specs[2].name"), "PVE ASSA")

    def test_saved_split_is_shown(self):
        """The 31/20/0 summary was built but never displayed."""
        lua = device("BrainwasherProDB = { specs = { [2] = { name = 'PvP', t1 = 31, t2 = 20, t3 = 0 } } }")
        self.assertIn("31", lua.eval("shownText()"))


class Icons(unittest.TestCase):
    def test_icons_are_not_read_at_login(self):
        """1.5 read every macro icon at login on every character."""
        lua = load()
        self.assertEqual(lua.eval("calls.icon or 0"), 0)

    def test_edit_window_builds_one_page_of_icons(self):
        """1.5 built a button for each of the 600 icons on the first Edit."""
        lua = device()
        before = lua.eval('count("Button")')
        lua.execute("BrainwasherPro:OnEditClicked(2)")
        self.assertLess(lua.eval('count("Button")') - before, 100)


class ActionBars(unittest.TestCase):
    def setup_swap(self, extra=""):
        lua = device("BrainwasherProDB = { specs = { [2] = { name = 'PvP', actionProfile = 'PvP' } } }" + extra)
        lua.execute('click(BrainwasherProIcon2); accept("BRAINWASHERPRO_LOAD_SPEC"); leave()')
        return lua

    def test_profile_loads_after_the_talents_change(self):
        """Activating a spec loads its ActionBarProfiles profile once the talents settle."""
        lua = self.setup_swap()
        self.assertEqual(lua.eval("selected[1]"), 22)
        lua.execute('fire("CHARACTER_POINTS_CHANGED"); advance(1); fire("SPELLS_CHANGED"); advance(1)')
        self.assertEqual(lua.eval("#abpLoaded"), 0, "must wait until the events stop")
        lua.execute("advance(1)")
        self.assertEqual(lua.eval("abpLoaded[1]"), "PvP")
        self.assertEqual(lua.eval("#abpLoaded"), 1)

    def test_unrelated_spell_events_do_not_load_bars(self):
        lua = self.setup_swap()
        lua.execute('fire("SPELLS_CHANGED"); advance(5)')
        self.assertEqual(lua.eval("#abpLoaded"), 0)

    def test_profile_waits_for_combat_to_end(self):
        lua = self.setup_swap()
        lua.execute('inCombat = true; fire("CHARACTER_POINTS_CHANGED"); advance(2)')
        self.assertEqual(lua.eval("#abpLoaded"), 0)
        lua.execute('inCombat = false; fire("PLAYER_REGEN_ENABLED")')
        self.assertEqual(lua.eval("abpLoaded[1]"), "PvP")

    def test_no_talent_change_leaves_bars_alone(self):
        lua = self.setup_swap()
        lua.execute('advance(61); fire("CHARACTER_POINTS_CHANGED"); advance(5)')
        self.assertEqual(lua.eval("#abpLoaded"), 0)
        self.assertIn("left as they are", lua.eval("table.concat(messages, '\\n')"))

    def test_edit_window_cycles_through_profiles(self):
        lua = device()
        lua.execute('''
            BrainwasherPro:OnEditClicked(2)
            click(BrainwasherProEditBars); click(BrainwasherProEditBars)
            click(BrainwasherProEditConfirm)
        ''')
        self.assertEqual(lua.eval("BrainwasherProDB.specs[2].actionProfile"), "PvP")


if __name__ == "__main__":
    unittest.main()
