"""Ready alerts, automatic sets and sets by target (spec 4.5 tests 9-11)."""
import unittest
from gr_env import load

SETS = '''
local function only(slots) local t = {} for s = 1, 19 do t[s] = slots[s] or "ignored" end return t end
makeSet("Ride", "I", only({ [1] = "0x17" }))
makeSet("Sneak", "I", only({ [16] = "0xD" }))
makeSet("BG", "I", only({ [16] = "0xE" }))
makeSet("Instant", "I", only({ [16] = "0xA", [17] = "0xB" }))
makeSet("Dissolvent", "I", only({ [16] = "0xD", [17] = "0xE" }))
player.forms = { "Stealth" }
'''
ON = 'GearRackDB = { auto = true, when = { mounted = "Ride", ["form Stealth"] = "Sneak", pvp = "BG" } }'


class Ready(unittest.TestCase):
    def test_the_30_second_line_and_the_ready_line(self):
        lua = load()
        lua.execute("cooldowns['0x11'] = { now, 120 } fire('BAG_UPDATE_COOLDOWN')")
        lua.execute("step(89)")
        self.assertNotIn("Insignia", lua.eval("chatText()"))
        lua.execute("step(1)")
        self.assertIn("[Insignia]|h|r is ready in 30 seconds.", lua.eval("chatText()"))
        lua.execute("step(30)")
        self.assertIn("[Insignia]|h|r is ready.", lua.eval("chatText()"))
        self.assertEqual(lua.eval("#sounds"), 2)
        self.assertEqual(lua.eval("timerCount()"), 0)

    def test_a_30_second_cooldown_gives_none(self):
        lua = load()
        lua.execute("cooldowns['0x11'] = { now, 30 } fire('BAG_UPDATE_COOLDOWN') step(31)")
        self.assertEqual(lua.eval("chatText()"), "")

    def test_the_switch_off_gives_none(self):
        lua = load('GearRackDB = { readyAlert = false }')
        lua.execute("cooldowns['0x11'] = { now, 120 } fire('BAG_UPDATE_COOLDOWN') step(121)")
        self.assertEqual(lua.eval("chatText()"), "")

    def test_a_new_start_cancels_the_old_timers(self):
        lua = load()
        lua.execute("cooldowns['0x11'] = { now, 120 } fire('BAG_UPDATE_COOLDOWN') step(10)")
        lua.execute("cooldowns['0x11'] = { now, 120 } fire('BAG_UPDATE_COOLDOWN') step(80)")
        self.assertEqual(lua.eval("chatText()"), "")
        lua.execute("step(10)")
        self.assertEqual(lua.eval("chatText()").count("30 seconds"), 1)

    def test_the_switch_off_arms_nothing_and_on_arms_a_running_cooldown(self):
        lua = load('GearRackDB = { readyAlert = false }')
        lua.execute("cooldowns['0x11'] = { now, 120 } fire('BAG_UPDATE_COOLDOWN')")
        self.assertEqual(lua.eval("timerCount()"), 0, "Parting's switch is off")
        lua.execute('settingsWindow.use("GearRack_readyAlert", true) step(90)')
        self.assertIn("[Insignia]|h|r is ready in 30 seconds.", lua.eval("chatText()"))

    def test_a_cooldown_running_at_login_is_armed(self):
        lua = load(setup="now = 1000 cooldowns['0x12'] = { now - 100, 140 }")
        lua.execute("step(40)")
        self.assertIn("[Arena Grand Master]|h|r is ready.", lua.eval("chatText()"))


class Automatic(unittest.TestCase):
    def test_mounting_wears_the_set_and_dismounting_brings_the_gear_back(self):
        lua = load(ON, setup=SETS)
        lua.execute("player.mounted = true fire('PLAYER_MOUNT_DISPLAY_CHANGED') step(0)")
        self.assertEqual(lua.eval("worn[1]"), "0x17")
        self.assertEqual(lua.eval("GearRackDB.before[1]"), "0x16")
        lua.execute("player.mounted = false fire('PLAYER_MOUNT_DISPLAY_CHANGED') step(0)")
        self.assertEqual(lua.eval("worn[1]"), "0x16")
        self.assertIsNone(lua.eval("GearRackDB.before"))

    def test_not_mounted_in_a_raid(self):
        lua = load(ON, setup=SETS + 'player.instance = "raid"')
        lua.execute("player.mounted = true fire('PLAYER_MOUNT_DISPLAY_CHANGED') step(0)")
        self.assertIsNone(lua.eval("usedSets[1]"))

    def test_stealth_in_a_battleground_then_the_battleground_set_then_the_old_gear(self):
        lua = load(ON, setup=SETS)
        lua.execute('player.instance = "pvp" fire("ZONE_CHANGED_NEW_AREA") step(0)')
        self.assertEqual(lua.eval("worn[16]"), "0xE")
        lua.execute("player.form = 1 fire('UPDATE_SHAPESHIFT_FORM') step(0)")
        self.assertEqual(lua.eval("worn[16]"), "0xD")
        lua.execute("player.form = 0 fire('UPDATE_SHAPESHIFT_FORM') step(0)")
        self.assertEqual(lua.eval("worn[16]"), "0xE")
        lua.execute('player.instance = "none" fire("ZONE_CHANGED_NEW_AREA") step(0)')
        self.assertEqual(lua.eval("worn[16]"), "0xA")

    def test_a_logout_in_town_brings_the_gear_back_on_leaving(self):
        lua = load('GearRackDB = { auto = true, when = { resting = "Ride" }, before = { [1] = "0x16" } }',
                   setup=SETS + 'player.resting = true wear(1, "0x17") carry(0, 5, "0x16")')
        self.assertEqual(lua.eval("worn[1]"), "0x17")
        lua.execute("player.resting = false fire('PLAYER_UPDATE_RESTING') step(0)")
        self.assertEqual(lua.eval("worn[1]"), "0x16")

    def test_low_mana_on_under_half_off_over_three_quarters(self):
        lua = load('GearRackDB = { auto = true, when = { lowMana = "Ride" } }',
                   setup=SETS + 'player.class = "MAGE" player.power = 0 player.mana = 100 player.maxMana = 100')
        for mana, head in ((60, "0x16"), (40, "0x17"), (70, "0x17"), (80, "0x16")):
            lua.execute(f"player.mana = {mana} fire('UNIT_POWER_UPDATE', 'player', 'MANA') step(0)")
            self.assertEqual(lua.eval("worn[1]"), head, mana)

    def test_food_and_drink(self):
        lua = load('GearRackDB = { auto = true, when = { food = "Ride" } }', setup=SETS)
        lua.execute("player.auras.Drink = true fire('UNIT_AURA', 'player') step(0)")
        self.assertEqual(lua.eval("worn[1]"), "0x17")
        lua.execute("player.auras.Drink = nil fire('UNIT_AURA', 'player') step(0)")
        self.assertEqual(lua.eval("worn[1]"), "0x16")
        reads = lua.eval("auraReads")
        lua.execute("fire('UNIT_AURA', 'target')")
        self.assertEqual(lua.eval("auraReads"), reads, "the target's auras wake nothing")

    def test_under_water_on_and_off(self):
        lua = load('GearRackDB = { auto = true, when = { water = "Ride" } }', setup=SETS)
        lua.execute("fire('MIRROR_TIMER_START', 'EXHAUSTION') step(0)")
        self.assertIsNone(lua.eval("usedSets[1]"))
        lua.execute("fire('MIRROR_TIMER_START', 'BREATH') step(0)")
        self.assertEqual(lua.eval("worn[1]"), "0x17")
        lua.execute("fire('MIRROR_TIMER_STOP', 'BREATH') step(0)")
        self.assertEqual(lua.eval("worn[1]"), "0x16")

    def test_the_switch_off_brings_the_gear_back(self):
        lua = load(ON, setup=SETS)
        lua.execute("player.mounted = true fire('PLAYER_MOUNT_DISPLAY_CHANGED') step(0)")
        self.assertEqual(lua.eval("worn[1]"), "0x17")
        lua.execute('settingsWindow.use("GearRack_auto", false) step(0)')
        self.assertEqual(lua.eval("worn[1]"), "0x16")
        self.assertIsNone(lua.eval("GearRackDB.before"), "a kept `before` held the trinket queue for good")

    def test_a_choice_by_hand_during_a_situation_survives_its_end(self):
        lua = load(ON, setup=SETS)
        lua.execute("player.mounted = true fire('PLAYER_MOUNT_DISPLAY_CHANGED') step(0)")
        lua.execute("hover(GearRackGear16) pick('0xF1') leave(GearRackGear16)")
        lua.execute("player.mounted = false fire('PLAYER_MOUNT_DISPLAY_CHANGED') step(0)")
        self.assertEqual(lua.eval("worn[16]"), "0xF1")
        self.assertEqual(lua.eval("worn[1]"), "0x16")

    def test_nothing_while_the_switch_is_off_or_the_panel_is_open(self):
        lua = load(ON.replace("auto = true", "auto = false"), setup=SETS)
        lua.execute("player.mounted = true fire('PLAYER_MOUNT_DISPLAY_CHANGED') step(0)")
        self.assertIsNone(lua.eval("usedSets[1]"))
        lua.execute('settingsWindow.use("GearRack_auto", true) step(0)')
        self.assertEqual(lua.eval("usedSets[1]"), "Ride")
        lua.execute("player.mounted = false fire('PLAYER_MOUNT_DISPLAY_CHANGED') step(0)")
        lua.execute("click(GearRackSets)")
        lua.execute("player.mounted = true fire('PLAYER_MOUNT_DISPLAY_CHANGED') step(0)")
        self.assertEqual(lua.eval("#usedSets"), 1)
        lua.execute("click(GearRackSets) step(0)")
        self.assertEqual(lua.eval("#usedSets"), 2, "the panel closed: the situation is read again")

    def test_only_the_events_of_rows_in_use(self):
        lua = load('GearRackDB = { auto = true, when = { mounted = "Ride" } }', setup=SETS)
        events = lua.eval("allEvents()").split(",")
        self.assertIn("PLAYER_MOUNT_DISPLAY_CHANGED", events)
        for e in ("UNIT_AURA", "UNIT_POWER_UPDATE", "UPDATE_SHAPESHIFT_FORM", "MIRROR_TIMER_START",
                  "PLAYER_UPDATE_RESTING", "PLAYER_TARGET_CHANGED"):
            self.assertNotIn(e, events)
        lua.execute('settingsWindow.use("GearRack_when_mounted", "")')
        self.assertNotIn("PLAYER_MOUNT_DISPLAY_CHANGED", lua.eval("allEvents()"))


class ByTarget(unittest.TestCase):
    ROGUE = ('GearRackDB = { byTarget = true, target = { Elemental = "Dissolvent", Giant = "Dissolvent", '
             'Mechanical = "Dissolvent", Undead = "Dissolvent", other = "Instant" } }')

    def test_an_elemental_wears_dissolvent_a_humanoid_instant(self):
        lua = load(self.ROGUE, setup=SETS)
        lua.execute('target = { enemy = true, kind = "Elemental" } fire("PLAYER_TARGET_CHANGED") step(0.2)')
        self.assertEqual(lua.eval("worn[16]"), "0xD")
        lua.execute('target = { enemy = true, kind = "Humanoid" } fire("PLAYER_TARGET_CHANGED") step(0.2)')
        self.assertEqual(lua.eval("worn[16]"), "0xA")
        lua.execute('target = { enemy = true, kind = "Critter" } fire("PLAYER_TARGET_CHANGED") step(0.2)')
        self.assertEqual(lua.eval("#usedSets"), 2, "Instant is worn already")

    def test_a_friendly_or_dead_target_nothing(self):
        lua = load(self.ROGUE, setup=SETS)
        lua.execute('target = { kind = "Undead" } fire("PLAYER_TARGET_CHANGED") step(0.2)')
        lua.execute('target = { enemy = true, dead = true, kind = "Undead" } fire("PLAYER_TARGET_CHANGED") step(0.2)')
        self.assertIsNone(lua.eval("usedSets[1]"))

    def test_tabbing_through_four_targets_swaps_once(self):
        lua = load(self.ROGUE, setup=SETS)
        for kind in ("Undead", "Humanoid", "Giant", "Elemental"):
            lua.execute(f'target = {{ enemy = true, kind = "{kind}" }} fire("PLAYER_TARGET_CHANGED") step(0.05)')
        lua.execute("step(0.2)")
        self.assertEqual(lua.eval("#usedSets"), 1)
        self.assertEqual(lua.eval("usedSets[1]"), "Dissolvent")

    def test_no_gear_comes_back_and_nothing_after_combat(self):
        lua = load(self.ROGUE, setup=SETS + "combat = true")
        lua.execute('target = { enemy = true, kind = "Undead" } fire("PLAYER_TARGET_CHANGED") step(0.2)')
        lua.execute("combat = false fire('PLAYER_REGEN_ENABLED') target = {} fire('PLAYER_TARGET_CHANGED') step(0.3)")
        self.assertEqual(lua.eval("#usedSets"), 1)
        self.assertEqual(lua.eval("worn[16]"), "0xD")
        self.assertIsNone(lua.eval("GearRackDB.before"))

    def test_a_swap_still_running_waits_then_both_weapons_change(self):
        lua = load(self.ROGUE, setup=SETS + "combat = true")
        lua.execute('swapping = true target = { enemy = true, kind = "Giant" } fire("PLAYER_TARGET_CHANGED") step(0.2)')
        self.assertIsNone(lua.eval("usedSets[1]"), "no call while ClassicAPI says it is busy")
        lua.execute('swapping = false fire("EQUIPMENT_SWAP_FINISHED", 1, 1) step(0)')
        self.assertEqual((lua.eval("worn[16]"), lua.eval("worn[17]")), ("0xD", "0xE"))

    def test_a_refused_weapon_is_tried_again_three_times_then_a_line(self):
        lua = load(self.ROGUE, setup=SETS + "combat = true")
        lua.execute('refuse["0xE"] = true target = { enemy = true, kind = "Giant" } fire("PLAYER_TARGET_CHANGED") step(0.2)')
        lua.execute("step(0) step(0) step(0) step(0)")
        self.assertEqual(lua.eval("#usedSets"), 3)
        self.assertEqual(lua.eval("worn[16]"), "0xD")
        self.assertIn("Could not put on all of Dissolvent.", lua.eval("table.concat(chat, ' ')"))
        self.assertNotIn("ITEM_LOCK_CHANGED", lua.eval("allEvents()"), "it stops listening")

    def test_a_set_missing_an_item_goes_on_once_with_no_line(self):
        lua = load(self.ROGUE.replace('Undead = "Dissolvent"', 'Undead = "Gone"'),
                   setup=SETS + 'makeSet("Gone", "I", only({ [16] = "0xD", [17] = "0x99" }))')
        lua.execute('target = { enemy = true, kind = "Undead" } fire("PLAYER_TARGET_CHANGED") step(0.2)')
        lua.execute("step(0) step(0) step(0) step(0)")
        self.assertEqual(lua.eval("#usedSets"), 1, "it swapped three times at every target")
        self.assertEqual(lua.eval("worn[16]"), "0xD")
        self.assertNotIn("Could not put on", lua.eval("chatText()"))

    def test_a_whole_set_in_combat_is_done_when_the_weapons_are_on(self):
        lua = load(self.ROGUE.replace('Undead = "Dissolvent"', 'Undead = "Full"'),
                   setup=SETS + 'makeSet("Full", "I", only({ [1] = "0x17", [16] = "0xD", [17] = "0xE" })) combat = true')
        lua.execute('target = { enemy = true, kind = "Undead" } fire("PLAYER_TARGET_CHANGED") step(0.2)')
        lua.execute("step(0) step(0) step(0) step(0)")
        self.assertEqual(lua.eval("#usedSets"), 1)
        self.assertEqual((lua.eval("worn[16]"), lua.eval("worn[17]"), lua.eval("worn[1]")), ("0xD", "0xE", "0x16"))
        self.assertNotIn("Could not put on", lua.eval("chatText()"))

    def test_the_events_button_switches_both_and_shows_it(self):
        lua = load(self.ROGUE.replace("byTarget = true", "byTarget = false"), setup=SETS)
        self.assertTrue(lua.eval("GearRackEvents.icon.desaturated"), "dark while both are off")
        lua.execute("click(GearRackEvents)")
        self.assertTrue(lua.eval("GearRackDB.auto and GearRackDB.byTarget"))
        self.assertIsNone(lua.eval("GearRackEvents.icon.desaturated"))
        self.assertTrue(lua.eval('settingsWindow.find("Sets by target") and Settings.GetValue("GearRack_byTarget")'))
        self.assertIn("PLAYER_TARGET_CHANGED", lua.eval("allEvents()"))
        self.assertIn("Events on", lua.eval("chatText()"))
        lua.execute('target = { enemy = true, kind = "Undead" } fire("PLAYER_TARGET_CHANGED") step(0.2)')
        self.assertEqual(lua.eval("usedSets[1]"), "Dissolvent")
        lua.execute("GearRack.ToggleEvents()")  # the key
        self.assertFalse(lua.eval("GearRackDB.auto or GearRackDB.byTarget"))
        self.assertNotIn("PLAYER_TARGET_CHANGED", lua.eval("allEvents()"))
        lua.execute("SlashCmdList.GEARRACK('events')")
        self.assertTrue(lua.eval("GearRackDB.byTarget"))

    def test_either_switch_on_lights_it_and_a_click_turns_both_off(self):
        lua = load(self.ROGUE, setup=SETS)
        self.assertIsNone(lua.eval("GearRackEvents.icon.desaturated"))
        lua.execute("click(GearRackEvents)")
        self.assertFalse(lua.eval("GearRackDB.auto or GearRackDB.byTarget"))
        self.assertTrue(lua.eval("GearRackEvents.icon.desaturated"))

    def test_its_own_switch_not_the_automatic_sets_one(self):
        lua = load(self.ROGUE.replace("byTarget = true", "auto = true, byTarget = false"), setup=SETS)
        self.assertNotIn("PLAYER_TARGET_CHANGED", lua.eval("allEvents()"))
        lua.execute('settingsWindow.use("GearRack_byTarget", true)')
        self.assertIn("PLAYER_TARGET_CHANGED", lua.eval("allEvents()"))
        lua.execute('settingsWindow.use("GearRack_auto", false)')
        lua.execute('target = { enemy = true, kind = "Undead" } fire("PLAYER_TARGET_CHANGED") step(0.2)')
        self.assertEqual(lua.eval("usedSets[1]"), "Dissolvent", "Automatic sets off does not stop it")


if __name__ == "__main__":
    unittest.main()
