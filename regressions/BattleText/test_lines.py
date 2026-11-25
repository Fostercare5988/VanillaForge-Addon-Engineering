"""Lines about you and your attacks, merging, the hidden spells and the game's odd
data (spec BattleText.md 4.5, tests 3, 4, 6 and 14). BattleText 1.0, written new
2026-11-22. Values are in the order of ### COMBAT_LOG_EVENT_UNFILTERED's prefix
and suffix tables; nil is the doc's "nil when 0".
"""
import unittest
from bt_env import load

RED = "|cffff0000-|r"


def flush(lua, code):
    """Run the events, then let the merge window close."""
    lua.execute("forget() " + code + " step(0.3)")


class Lines(unittest.TestCase):
    def setUp(self):
        self.lua = load()

    def say(self, code, area=None):
        flush(self.lua, code)
        return self.lua.eval(f"texts({repr(area) if area else ''})")

    def test_a_melee_hit_on_you(self):
        self.assertEqual(self.say("cleu('SWING_DAMAGE', mob, you, 120, 0, 1)", "Incoming"), RED + "120")
        line = self.lua.eval("lineOf(last())")
        self.assertEqual(line.size, 20)
        self.assertTrue(self.lua.eval("lineOf(last()).group:IsPlaying()"))

    def test_your_crit_pops_shakes_and_is_large(self):
        self.assertEqual(self.say("cleu('SWING_DAMAGE', you, mob, 250, 0, 1, nil, nil, nil, 1)", "Outgoing"), "250")
        self.assertEqual(self.lua.eval("last().fontSize"), 26)
        self.assertTrue(self.lua.eval("lineOf(last()) == __addon_ns.areas.Outgoing.crits[1]"))
        self.assertTrue(self.lua.eval("lineOf(last()).shake:IsPlaying()"))
        self.lua.execute("step(2.7)")
        self.assertFalse(self.lua.eval("lineOf(last()).shake:IsPlaying()"))
        self.assertFalse(self.lua.eval("lineOf(last()).frame:IsShown()"))

    def test_a_fire_spell_in_its_colour_with_its_icon(self):
        text = self.say("cleu('SPELL_DAMAGE', you, mob, 133, 'Fireball', 4, 300, 0, 4)", "Outgoing")
        self.assertEqual(text, "|cffFF4444300|r")
        self.assertEqual(list(self.lua.eval("last().color").values()), [1, 0.27, 0.27])
        icon = self.lua.eval("lineOf(last()).icon")
        self.assertTrue(icon.shown)
        self.assertEqual(icon.texture, "Interface\\Icons\\Spell_Fire_FlameBolt")

    def test_a_physical_spell_keeps_its_kinds_colour(self):
        self.say("cleu('SPELL_DAMAGE', you, mob, 1752, 'Sinister Strike', 1, 90, 0, 1)", "Outgoing")
        self.assertEqual(list(self.lua.eval("last().color").values()), [1, 1, 0])
        self.assertFalse(self.lua.eval("lineOf(last()).icon.shown"))

    def test_a_dot_tick_on_you(self):
        self.assertEqual(self.say("cleu('SPELL_PERIODIC_DAMAGE', mob, you, 172, 'Corruption', 32, 50, 0, 32)",
                                  "Incoming"), RED + "|cff6600CC50|r")

    def test_misses_in_and_out(self):
        for miss, text in (("MISS", "Miss!"), ("DODGE", "Dodge!"), ("PARRY", "Parry!"), ("DEFLECT", "Parry!"),
                           ("BLOCK", "Block!"), ("ABSORB", "Absorb!"), ("IMMUNE", "Immune!"), ("EVADE", "Evade!")):
            self.assertEqual(self.say(f"cleu('SWING_MISSED', mob, you, '{miss}')", "Incoming"), text, miss)
            self.assertEqual(self.say(f"cleu('SWING_MISSED', you, mob, '{miss}')", "Outgoing"), text, miss)
        self.assertEqual(self.say("cleu('SPELL_MISSED', mob, you, 116, 'Frostbolt', 16, 'RESIST')", "Incoming"),
                         "(Frostbolt) Resist!")
        self.assertEqual(self.say("cleu('SPELL_MISSED', you, mob, 116, 'Frostbolt', 16, 'RESIST')", "Outgoing"),
                         "Resist!")
        self.assertEqual(self.say("cleu('SPELL_MISSED', mob, you, 116, 'Frostbolt', 16, 'REFLECT')", "Incoming"),
                         "(Frostbolt) Reflect!")
        self.assertEqual(self.say("cleu('SPELL_MISSED', you, mob, 116, 'Frostbolt', 16, 'DEFLECT')", "Outgoing"),
                         "Parry!")
        self.assertEqual(self.lua.eval("last().fontSize"), 20)

    def test_your_evade_is_large(self):
        self.say("cleu('SWING_MISSED', you, mob, 'EVADE')")
        self.assertEqual(self.lua.eval("last().fontSize"), 22)

    def test_the_partial_trailers(self):
        cases = (("nil, nil, nil, nil, nil, 1", "|cff7D0000 (crushing)|r"),
                 ("nil, nil, nil, nil, 1", "|cffFA0000 (glancing)|r"),
                 ("nil, nil, 30", "|cffFAFA00 (30 absorbed)|r"),
                 ("nil, 25", "|cff7F00FF (25 blocked)|r"),
                 ("20", "|cff81007F (20 resisted)|r"))
        for values, trailer in cases:
            self.assertEqual(self.say(f"cleu('SWING_DAMAGE', mob, you, 100, 0, 1, {values})", "Incoming"),
                             RED + "100" + trailer, values)

    def test_a_hit_fully_absorbed_is_absorb(self):
        self.assertEqual(self.say("cleu('SWING_DAMAGE', mob, you, 0, 0, 1, nil, nil, 100)", "Incoming"), "Absorb!")

    def test_a_heal_with_its_overheal_and_the_healers_class_colour(self):
        self.lua.execute("players['0xPRIEST'] = 'PRIEST'")
        self.assertEqual(self.say("cleu('SPELL_HEAL', priest, you, 2054, 'Heal', 2, 500, 200, 0)", "Incoming"),
                         "+300 (|cffffffffHalfwit|r)|cff00B47F <200>|r")

    def test_your_own_heal_on_you_leaves_your_name_out(self):
        self.assertEqual(self.say("cleu('SPELL_HEAL', you, you, 2054, 'Heal', 2, 500, 0, 0)", "Incoming"), "+500")

    def test_a_hot_tick_that_healed_nothing_is_not_shown(self):
        self.assertEqual(self.say("cleu('SPELL_PERIODIC_HEAL', priest, you, 139, 'Renew', 2, 100, 100, 0)"), "")
        self.assertEqual(self.say("cleu('SPELL_PERIODIC_HEAL', priest, you, 139, 'Renew', 2, 100, 40, 0)", "Incoming"),
                         "+60 (Halfwit)|cff00B47F <40>|r")

    def test_your_crit_heal_pops_at_22(self):
        self.say("cleu('SPELL_HEAL', you, priest, 2054, 'Heal', 2, 500, 0, 0, 1)")
        self.assertEqual(self.lua.eval("texts('Outgoing')"), "+500")
        self.assertEqual(self.lua.eval("last().fontSize"), 22)

    def test_falling(self):
        self.assertEqual(self.say("cleu('ENVIRONMENTAL_DAMAGE', nil, you, 'Falling', 120, 0, 1)", "Incoming"),
                         RED + "120 Falling")

    def test_a_damage_shield_named_and_unnamed(self):
        self.assertEqual(self.say("cleu('DAMAGE_SHIELD', you, mob, 467, 'Thorns', 8, 9, 0, 8)", "Outgoing"),
                         "|cff44FF449|r")
        self.assertEqual(self.say("cleu('DAMAGE_SHIELD', mob, you, 0, nil, 4, 10, 0, 4)", "Incoming"),
                         RED + "|cffFF444410|r")
        self.assertFalse(self.lua.eval("lineOf(last()).icon.shown"))

    def test_others_fights_show_nothing(self):
        self.assertEqual(self.say("cleu('SWING_DAMAGE', priest, mob, 100, 0, 1)"), "")


class Merging(unittest.TestCase):
    def test_three_hits_in_the_window_are_one_line(self):
        lua = load()
        lua.execute("forget() cleu('SWING_DAMAGE', you, mob, 100, 0, 1) "
                    "cleu('SWING_DAMAGE', you, mob, 150, 0, 1, nil, nil, nil, 1) step(0.1) "
                    "cleu('SWING_DAMAGE', you, mob, 100, 0, 1)")
        self.assertEqual(lua.eval("texts()"), "")
        self.assertEqual(lua.eval("liveTimers()"), 1)
        lua.execute("step(0.2)")
        self.assertEqual(lua.eval("texts()"), "350 [3 Hits, 1 Crit]")
        self.assertEqual(lua.eval("last().fontSize"), 20)
        self.assertEqual(lua.eval("liveTimers()"), 0)

    def test_hits_on_two_targets_stay_two_lines(self):
        lua = load()
        flush(lua, "cleu('SWING_DAMAGE', you, mob, 100, 0, 1) cleu('SWING_DAMAGE', you, mob2, 100, 0, 1)")
        self.assertEqual(lua.eval("texts()"), "100|100")

    def test_a_spell_from_two_healers_says_multiple(self):
        lua = load()
        flush(lua, "cleu('SPELL_HEAL', priest, you, 2054, 'Heal', 2, 300, 0, 0) "
                   "cleu('SPELL_HEAL', {'0xP2', 'Tankwife', 0x512}, you, 2054, 'Heal', 2, 300, 0, 0)")
        self.assertEqual(lua.eval("texts()"), "+600 (Multiple) [2 Hits]")

    def test_a_notice_inside_the_window_is_not_held(self):
        lua = load()
        lua.execute("forget() cleu('SWING_DAMAGE', you, mob, 100, 0, 1) "
                    "cleu('SPELL_AURA_APPLIED', priest, you, 1243, 'Power Word: Fortitude', 2, 'BUFF')")
        self.assertEqual(lua.eval("texts()"), "[Power Word: Fortitude]")

    def test_no_timer_at_rest(self):
        lua = load()
        self.assertEqual(lua.eval("liveTimers()"), 0)

    def test_an_error_in_a_line_reaches_the_error_handler_and_the_next_window_works(self):
        lua = load()
        lua.execute("draw = __addon_ns.Draw __addon_ns.Draw = function() error('boom') end "
                    "cleu('SWING_DAMAGE', you, mob, 100, 0, 1) step(0.3)")
        self.assertEqual(lua.eval("#handled"), 1)
        self.assertIn("boom", lua.eval("handled[1]"))
        lua.execute("__addon_ns.Draw = draw")
        flush(lua, "cleu('SWING_DAMAGE', you, mob, 70, 0, 1)")
        self.assertEqual(lua.eval("texts()"), "70")


class Hidden(unittest.TestCase):
    def test_a_hidden_spell_shows_nothing_and_grace_of_air_shows(self):
        lua = load()
        flush(lua, "cleu('SPELL_AURA_APPLIED', nil, you, 8076, 'Strength of Earth', 8, 'BUFF') "
                   "cleu('SPELL_PERIODIC_ENERGIZE', nil, you, 5677, 'Mana Spring', 8, 10, 0) "
                   "cleu('SPELL_PERIODIC_HEAL', nil, you, 5672, 'Healing Stream', 8, 10, 0, 0) "
                   "cleu('SPELL_AURA_APPLIED', nil, you, 8836, 'Grace of Air', 8, 'BUFF')")
        self.assertEqual(lua.eval("texts()"), "[Grace of Air]")

    def test_a_hidden_name_inside_a_units_name_hides_nothing(self):
        lua = load()
        flush(lua, "cleu('SPELL_HEAL', {'0xV', 'Vigor', 0x512}, you, 2054, 'Heal', 2, 100, 0, 0)")
        self.assertEqual(lua.eval("texts()"), "+100 (Vigor)")


class OddData(unittest.TestCase):
    def setUp(self):
        self.lua = load()

    def say(self, code):
        flush(self.lua, code)
        return self.lua.eval("texts()")

    def test_spell_0_with_no_name(self):
        self.assertEqual(self.say("cleu('SPELL_DAMAGE', mob, you, 0, nil, 1, 50, 0, 1)"), RED + "50")

    def test_an_aura_with_no_icon(self):
        self.assertEqual(self.say("cleu('SPELL_AURA_APPLIED', you, you, 2383, 'Find Herbs', 1, 'BUFF')"),
                         "[Find Herbs]")
        self.assertFalse(self.lua.eval("lineOf(last()).icon.shown"))

    def test_an_unknown_healer_and_a_heal_out_of_view(self):
        self.assertEqual(self.say("cleu('SPELL_HEAL', {'0xX', 'Unknown', 0}, you, 2054, 'Heal', 2, 400, 0, 0)"),
                         "+400 (Unknown)")

    def test_a_player_with_no_cache_entry_is_a_plain_name(self):
        self.assertEqual(self.say("cleu('SPELL_HEAL', {'0xNEW', 'Stranger', 0x512}, you, 2054, 'Heal', 2, 10, 0, 0)"),
                         "+10 (Stranger)")

    def test_a_faction_with_no_name(self):
        self.lua.execute("forget() fire('FACTION_STANDING_CHANGED', 9999, 100, 50)")
        self.assertEqual(self.lua.eval("texts()"), "+50 Reputation")


if __name__ == "__main__":
    unittest.main()
