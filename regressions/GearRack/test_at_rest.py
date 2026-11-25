"""Moving the bars and the addon at rest (spec 4.5 tests 12 and 13)."""
import unittest
import wowkit
from gr_env import load, MOCK, GEAR, ROOT, GLOBALS

# The events at rest (spec 4.1 "Events at rest"), with the switch off.
AT_REST = sorted([
    "PLAYER_EQUIPMENT_CHANGED", "PLAYER_EQUIPMENT_CHANGED", "PLAYER_EQUIPMENT_CHANGED",  # Core, Bars, Ready
    "PLAYER_EQUIPMENT_CHANGED", "WEAPON_ENCHANT_CHANGED",  # Poison
    "BAG_UPDATE_COOLDOWN", "BAG_UPDATE_COOLDOWN",  # Bars, Ready
    "EQUIPMENT_SETS_CHANGED", "EQUIPMENT_SETS_CHANGED", "EQUIPMENT_SWAP_FINISHED", "EQUIPMENT_SWAP_FINISHED",
    "WEAR_EQUIPMENT_SET", "PLAYER_REGEN_ENABLED", "UPDATE_BINDINGS",
    "MODIFIER_STATE_CHANGED",  # the bars' handles
    "PLAYER_ENTERING_WORLD", "PLAYER_ENTERING_WORLD", "PLAYER_ENTERING_WORLD",  # Bars, Auto, Ready
])


class Moving(unittest.TestCase):
    def test_ctrl_shift_shows_a_handle_on_each_shown_bar_and_a_drag_moves_it(self):
        lua = load('GearRackDB = { trinketBar = "OFF" }')
        lua.execute('''for _, w in ipairs(widgets) do
            if w.parent == GearRackGearBar and w.scripts.OnMouseDown then gearHandle = w end
            if w.parent == GearRackTrinketBar and w.scripts.OnMouseDown then trinketHandle = w end end''')
        lua.execute("press('lshift')")
        self.assertFalse(lua.eval("gearHandle:IsShown()"))
        lua.execute("press('lshift', 'rctrl')")
        self.assertTrue(lua.eval("gearHandle:IsVisible()"))
        self.assertFalse(lua.eval("trinketHandle:IsVisible()"), "a bar that is off has no handle to see")
        lua.execute("run(gearHandle, 'OnMouseDown')")
        self.assertTrue(lua.eval("GearRackGearBar.moving"))
        lua.execute("press('lshift')")  # Ctrl let go mid-drag
        self.assertIsNone(lua.eval("GearRackGearBar.moving"))
        self.assertTrue(lua.eval("GearRackGearBar:IsUserPlaced()"))
        self.assertFalse(lua.eval("gearHandle:IsShown()"))


class AtRest(unittest.TestCase):
    def test_the_events_at_rest_no_onupdate_and_no_timer(self):
        lua = load()
        self.assertEqual(lua.eval("allEvents()").split(","), AT_REST)
        self.assertEqual(lua.eval("timerCount()"), 0)

    def test_nothing_repeats_after_a_swap_combat_and_a_situation(self):
        lua = load('GearRackDB = { auto = true, when = { mounted = "Ride" } }',
                   setup='makeSet("Ride", "I", { [1] = "0x17" }) for s = 2, 19 do sets[1].slots[s] = "ignored" end')
        lua.execute("combat = true GearRack.EquipSet('Ride') step(0) combat = false fire('PLAYER_REGEN_ENABLED') step(0)")
        lua.execute("player.mounted = true fire('PLAYER_MOUNT_DISPLAY_CHANGED') step(0)")
        lua.execute("player.mounted = false fire('PLAYER_MOUNT_DISPLAY_CHANGED') step(0) step(1)")
        self.assertEqual(lua.eval("timerCount()"), 0)
        self.assertNotIn("OnUpdate", lua.eval("allEvents()"))
        self.assertNotIn("ITEM_LOCK_CHANGED", lua.eval("allEvents()"))

    def test_a_mounted_situation_makes_no_garbage_per_event(self):
        lua = load('GearRackDB = { auto = true, when = { mounted = "Ride" } }',
                   setup='makeSet("Ride", "I", { [1] = "0x17" }) for s = 2, 19 do sets[1].slots[s] = "ignored" end')
        # Ten times the events make no more garbage than once: nothing per event. One
        # chunk each (compiling the test's code is garbage too); no step: the kit's
        # timer objects are not the addon's (one Sets-button redraw per frame is the design).
        code = ("collectgarbage('collect') before = collectgarbage('count') "
                "for i = 1, {n} do fire('BAG_UPDATE_COOLDOWN') fire('PLAYER_EQUIPMENT_CHANGED', 5) end "
                "grown = collectgarbage('count') - before")
        lua.execute(code.replace("{n}", "200"))
        few = lua.eval("grown")
        lua.execute(code.replace("{n}", "2000"))
        many = lua.eval("grown")
        self.assertLess(many - few, 0.5, f"{few:.1f} KB for 200 rounds, {many:.1f} KB for 2000")

    def test_only_the_listed_globals(self):
        lua = wowkit.runtime()
        lua.execute(MOCK)
        lua.execute(GEAR)
        lua.execute("before = {} for k in pairs(_G) do before[k] = true end")
        wowkit.load_addon(lua, ROOT, "GearRack")
        lua.execute("login()")
        made = lua.eval('''(function() local t = {} for k in pairs(_G) do
            if not before[k] then t[#t + 1] = k end end table.sort(t) return table.concat(t, ",") end)()''')
        extra = [g for g in made.split(",") if g and g not in GLOBALS + ("__addon_ns", "event") and not g.startswith("GearRackGear")
                 and not g.startswith("GearRackTrinket1") and not g.startswith("GearRackSets")]
        self.assertEqual(extra, [])


if __name__ == "__main__":
    unittest.main()
