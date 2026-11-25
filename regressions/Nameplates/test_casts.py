"""Cast bars and enemy cooldowns (spec 4.6, tests 10 and 11). Nameplates 1.0,
written new 2026-11-22. Cast times are GetTime() milliseconds (### C_Spell.UnitCastingInfo).
"""
import unittest
from np_env import load, ENEMY_ROGUE, ENEMY_NPC, FRIEND

P = "__addon_ns.byToken.nameplate1"
BAR = P + ".cast"
CDS = P + ".cds.icons"


def shown(lua, expr):
    return bool(lua.eval(f"({expr}):IsShown()"))


def casting(lua, kind="cast", start=100000, end=102500, locked="false"):
    lua.execute(f"units.nameplate1.{kind} = {{ name = 'Fireball', icon = 'fb', from = {start}, to = {end},"
                f" locked = {locked} }}")


class Casts(unittest.TestCase):
    def setUp(self):
        self.lua = load()
        self.lua.execute(f"show('nameplate1', {ENEMY_NPC})")

    def test_a_cast_fills_itself_and_stops(self):
        lua = self.lua
        casting(lua)
        lua.execute("fire('UNIT_SPELLCAST_START', 'nameplate1')")
        self.assertTrue(shown(lua, BAR))
        self.assertEqual((lua.eval(f"{BAR}.timer.from"), lua.eval(f"{BAR}.timer.to")), (100, 102.5))
        self.assertEqual(lua.eval(f"{BAR}.direction"), 0)
        self.assertEqual(lua.eval(f"{BAR}.barColor"), "1,0.8,0")
        for stop in ("UNIT_SPELLCAST_STOP", "UNIT_SPELLCAST_INTERRUPTED"):
            lua.execute(f"fire('UNIT_SPELLCAST_START', 'nameplate1'); fire('{stop}', 'nameplate1')")
            self.assertFalse(shown(lua, BAR), stop)
        self.assertEqual(lua.eval("liveTimers()"), 0)

    def test_a_channel_runs_the_other_way(self):
        lua = self.lua
        casting(lua, "channel")
        lua.execute("fire('UNIT_SPELLCAST_CHANNEL_START', 'nameplate1')")
        self.assertEqual(lua.eval(f"{BAR}.direction"), 1)
        lua.execute("fire('UNIT_SPELLCAST_CHANNEL_STOP', 'nameplate1')")
        self.assertFalse(shown(lua, BAR))

    def test_a_cast_seen_mid_way_has_no_times_and_no_bar(self):
        lua = self.lua
        lua.execute("units.nameplate1.channel = { name = 'Drain', icon = 'x' }; fire('UNIT_SPELLCAST_CHANNEL_START', 'nameplate1')")
        self.assertFalse(shown(lua, BAR))

    def test_a_lost_stop_hides_at_the_end_by_one_timer(self):
        lua = self.lua
        casting(lua)
        lua.execute(f"show('nameplate2', {ENEMY_NPC}); units.nameplate2.cast = {{ name = 'Heal', icon = 'h',"
                    " from = 100000, to = 101000 }; fire('UNIT_SPELLCAST_START', 'nameplate1');"
                    " fire('UNIT_SPELLCAST_START', 'nameplate2')")
        self.assertEqual(lua.eval("liveTimers()"), 1)
        lua.execute("units.nameplate1.cast = nil; units.nameplate2.cast = nil; step(1.6)")
        self.assertFalse(shown(lua, "__addon_ns.byToken.nameplate2.cast"))
        self.assertTrue(shown(lua, BAR))
        lua.execute("step(1.5)")
        self.assertFalse(shown(lua, BAR))
        self.assertEqual(lua.eval("liveTimers()"), 0)

    def test_grey_when_locked_gold_when_it_opens_on_your_target(self):
        lua = self.lua
        casting(lua, locked="true")
        lua.execute("target('nameplate1'); fire('UNIT_SPELLCAST_START', 'nameplate1')")
        self.assertEqual(lua.eval(f"{BAR}.barColor"), "0.6,0.6,0.6")
        lua.execute("fire('UNIT_SPELLCAST_INTERRUPTIBLE', 'target')")
        for part in ("barColor", "edge.edgeColor", "box.edgeColor"):  # the borders with the bar
            self.assertEqual(lua.eval(f"{BAR}.{part}"), "1,0.8,0", part)
        lua.execute("fire('UNIT_SPELLCAST_NOT_INTERRUPTIBLE', 'target')")
        self.assertEqual(lua.eval(f"{BAR}.barColor"), "0.6,0.6,0.6")

    def test_the_plate_leaving_hides_its_bar(self):
        lua = self.lua
        casting(lua)
        lua.execute("fire('UNIT_SPELLCAST_START', 'nameplate1'); bar = __addon_ns.byToken.nameplate1.cast;"
                    " hide('nameplate1')")
        self.assertFalse(lua.eval("bar:IsShown()"))
        self.assertEqual(lua.eval("liveTimers()"), 0)

    def test_switched_off_no_bar_and_no_events(self):
        lua = self.lua
        lua.execute("settingsWindow.use('Nameplates_casts', false)")
        listening = lua.eval("listening()")
        for e in ("UNIT_SPELLCAST_START", "UNIT_SPELLCAST_STOP", "UNIT_SPELLCAST_INTERRUPTIBLE"):
            self.assertNotIn(e + ",", listening + ",")


SPELLS = "spells[1] = { name = 'Blind', icon = 'blind', cd = 300000 };" \
         " spells[2] = { name = 'Kick', icon = 'kick', cd = 10000 };" \
         " spells[3] = { name = 'Strike', icon = 'ss', cd = 0 };" \
         " spells[4] = { name = 'Bolt', icon = 'b', cd = 1500 };" \
         " for i = 10, 15 do spells[i] = { name = 'S' .. i, icon = 'i' .. i, cd = 60000 } end"


def cds(lua):
    return [lua.eval(f"{CDS}[{i}].info.icon") if lua.eval(f"{CDS}[{i}]:IsShown()") else None for i in range(1, 6)]


def used(lua, spell, token="nameplate1"):
    lua.execute(f"fire('UNIT_SPELLCAST_SUCCEEDED', '{token}', 'Cast-1', {spell})")


class Cooldowns(unittest.TestCase):
    def setUp(self):
        self.lua = load(setup=SPELLS)
        self.lua.execute(f"show('nameplate1', {ENEMY_ROGUE}); show('nameplate2', {ENEMY_NPC}); show('nameplate3', {FRIEND})")

    def test_an_enemy_players_long_cooldown_shows_with_a_tilde(self):
        lua = self.lua
        used(lua, 1)
        self.assertEqual(cds(lua), ["blind", None, None, None, None])
        self.assertEqual(lua.eval(f"{CDS}[1].cd.cdDuration"), 300)
        self.assertEqual(lua.eval(f"{CDS}[1].cd.formatter.breakpoints[1].format"), "~%d")

    def test_short_or_none_and_npcs_and_friends_show_nothing(self):
        lua = self.lua
        used(lua, 3); used(lua, 4); used(lua, 99)
        used(lua, 1, "nameplate2"); used(lua, 1, "nameplate3")
        self.assertEqual(cds(lua), [None] * 5)
        for t in ("nameplate2", "nameplate3"):
            self.assertFalse(lua.eval(f"__addon_ns.byToken.{t}.cds.icons[1]:IsShown()"))

    def test_a_later_use_of_the_same_spell_replaces_it(self):
        lua = self.lua
        used(lua, 2); used(lua, 1)
        lua.execute("now = now + 1")
        used(lua, 2)
        self.assertEqual(cds(lua), ["kick", "blind", None, None, None])
        self.assertEqual(lua.eval(f"{CDS}[1].cd.cdStart"), lua.eval("now"))

    def test_newest_first_five_at_most(self):
        lua = self.lua
        for i in range(10, 16):
            used(lua, i)
        self.assertEqual(cds(lua), ["i15", "i14", "i13", "i12", "i11"])

    def test_it_leaves_at_its_end(self):
        lua = self.lua
        used(lua, 2); used(lua, 1)
        lua.execute(f"now = now + 11; local cd = {CDS}[2].cd; cd:GetScript('OnCooldownDone')(cd)")
        self.assertEqual(cds(lua), ["blind", None, None, None, None])

    def test_the_plate_coming_back_shows_them_and_a_loading_screen_clears_all(self):
        lua = self.lua
        used(lua, 1)
        lua.execute("guid = units.nameplate1.guid; hide('nameplate1');"
                    f" d = {ENEMY_ROGUE}; d.guid = guid; show('nameplate7', d)")
        self.assertEqual(lua.eval("__addon_ns.byToken.nameplate7.cds.icons[1].info.icon"), "blind")
        lua.execute("fire('PLAYER_ENTERING_WORLD')")
        self.assertFalse(lua.eval("__addon_ns.byToken.nameplate7.cds.icons[1]:IsShown()"))

    def test_a_channel_counts_once_by_its_succeeded(self):
        lua = self.lua
        lua.execute("fire('UNIT_SPELLCAST_CHANNEL_START', 'nameplate1', 'Cast-2', 1)")
        self.assertEqual(cds(lua), [None] * 5)
        used(lua, 1)
        self.assertEqual(cds(lua), ["blind", None, None, None, None])

    def test_cooldowns_alone_listen_to_no_cast_bar_event(self):
        lua = self.lua
        lua.execute("settingsWindow.use('Nameplates_casts', false)")
        listening = lua.eval("listening()") + ","
        self.assertIn("UNIT_SPELLCAST_SUCCEEDED,", listening)
        self.assertNotIn("UNIT_SPELLCAST_CHANNEL_START,", listening)


if __name__ == "__main__":
    unittest.main()
