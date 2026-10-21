"""Enemy-frame row features: cast bars, range fading, raid icons and group targets.

The complete AutoBG_Targets.lua runs under Lua 5.1 with the enemy-frame mocks
and a controllable clock. ClassicAPI cast timing, real distances, raid icon
art and the bar animation stay in-game checks.
"""
import unittest

from test_targets_guid_events import GROM, fire, runtime

CLOCK = r'''
clock = 1000
function GetTime() return clock end
'''


def setup(sighting=True):
    lua = runtime(sighting)
    lua.execute(CLOCK)
    return lua


def tick(lua):
    lua.execute('AutoBG_Targets.UpdateRowStatus()')


def animate(lua, seconds=0):
    lua.execute('clock = clock + %s; local c = AutoBG_TargetCast1; c.scripts.OnUpdate(c)' % seconds)


def record_fill(lua, row=1):
    lua.execute('local hb = AutoBG_TargetButton%d.HealthBar; function hb:SetVertexColor(r) self.r = r end' % row)


def fill_red(lua, row=1):
    return lua.eval('AutoBG_TargetButton%d.HealthBar.r' % row)


def cast_shown(lua):
    return bool(lua.eval('AutoBG_TargetCast1.shown'))


class CastBarTests(unittest.TestCase):
    def start_heal(self, lua):
        lua.execute('casts["%s"] = { name = "Flash Heal", icon = "heal", start = 999800, finish = 1001300 }' % GROM)
        fire(lua, "UNIT_CASTEVENT", GROM, "", "START", 10917, 1500)

    def test_enemy_cast_shows_on_its_row(self):
        lua = setup()
        self.start_heal(lua)
        self.assertTrue(cast_shown(lua))
        self.assertEqual(lua.eval('AutoBG_TargetCast1.Text.text'), "Flash Heal")

    def test_interrupt_hides_the_cast(self):
        lua = setup()
        self.start_heal(lua)
        lua.execute('casts["%s"] = nil' % GROM)
        fire(lua, "UNIT_CASTEVENT", GROM, "", "FAIL", 10917, 0)
        self.assertFalse(cast_shown(lua))

    def test_cleared_cast_hides_on_the_next_check(self):
        lua = setup()
        self.start_heal(lua)
        lua.execute('casts["%s"] = nil' % GROM)
        animate(lua, 0.25)
        self.assertFalse(cast_shown(lua))

    def test_finished_cast_hides(self):
        lua = setup()
        self.start_heal(lua)
        animate(lua, 2)
        self.assertFalse(cast_shown(lua))

    def test_event_duration_times_a_cast_classicapi_has_not_cached(self):
        lua = setup()
        fire(lua, "UNIT_CASTEVENT", GROM, "", "START", 10157, 2000)
        self.assertTrue(cast_shown(lua))
        self.assertEqual(lua.eval('AutoBG_TargetCast1.Text.text'), "Arcane Intellect")
        animate(lua, 0.25)  # ClassicAPI still has nothing: keep the event's timing
        self.assertTrue(cast_shown(lua))

    def test_channel_drains_from_full(self):
        lua = setup()
        lua.execute('channels["%s"] = { name = "Arcane Missiles", start = 999000, finish = 1001000 }' % GROM)
        fire(lua, "UNIT_CASTEVENT", GROM, "", "CHANNEL", 10212, 2000)
        animate(lua)
        # Half way through a channel: half of the 93-pixel bar remains.
        self.assertEqual(lua.eval('AutoBG_TargetCast1.barWidth'), 47)

    def test_clicking_the_cast_bar_targets_the_caster(self):
        lua = setup()
        self.start_heal(lua)
        lua.execute('guidNames["%s"] = "Grom"' % GROM)
        lua.execute('targeted = {}; function TargetUnit(u) table.insert(targeted, u) end; function FocusUnit(u) focused = u end')
        lua.execute('local c = AutoBG_TargetCast1; c.scripts.OnClick(c, "LeftButton")')
        self.assertEqual(lua.eval('targeted[1]'), GROM)
        lua.execute('local c = AutoBG_TargetCast1; c.scripts.OnClick(c, "RightButton")')
        self.assertEqual(lua.eval('focused'), GROM)

    def cast_anchor(self, lua):
        lua.execute('local c = AutoBG_TargetCast1; anchor = {}; function c:SetPoint(p, rel, rp) anchor = { p, rel, rp } end')
        lua.execute('AutoBG_Targets:SetupButtonLayout(10)')
        point, rel, _ = lua.eval('anchor[1]'), lua.eval('anchor[2]'), lua.eval('anchor[3]')
        if lua.eval('anchor[2] == AutoBG_TargetButton1'):
            rel = "row"
        elif lua.eval('anchor[2] == AutoBG_TargetButton1.Trinket'):
            rel = "trinket"
        return point, rel

    def test_cast_bar_side_follows_the_setting(self):
        lua = setup()
        lua.execute('AutoBG_Settings.Targets.CastPos = "RIGHT"; AutoBG_Settings.Targets.ShowTrinket[10] = false')
        self.assertEqual(self.cast_anchor(lua), ("LEFT", "row"))
        lua.execute('AutoBG_Settings.Targets.CastPos = "LEFT"')
        self.assertEqual(self.cast_anchor(lua), ("RIGHT", "row"))

    def test_cast_bar_on_the_trinket_side_sits_outside_the_trinket(self):
        lua = setup()
        lua.execute('local o = AutoBG_Settings.Targets; o.CastPos, o.TrinketPos = "RIGHT", "RIGHT"; o.ShowTrinket[10] = true')
        self.assertEqual(self.cast_anchor(lua), ("LEFT", "trinket"))

    def test_cast_bars_switch_off(self):
        lua = setup()
        lua.execute('AutoBG_Settings.Targets.ShowCastBars = false')
        self.start_heal(lua)
        self.assertFalse(cast_shown(lua))


class RowStatusTests(unittest.TestCase):
    def test_far_enemy_greys_its_health_bar_and_regains_color_when_close(self):
        # The row stays fully visible; only the bar fill darkens a little.
        lua = setup()
        record_fill(lua)
        lua.execute('yards["%s"] = 20' % GROM)
        tick(lua)
        near = fill_red(lua)
        lua.execute('yards["%s"] = 55' % GROM)
        tick(lua)
        self.assertEqual(lua.eval('AutoBG_TargetButton1.alpha'), 1.0)
        self.assertLess(fill_red(lua), near - 0.15)
        lua.execute('yards["%s"] = 20' % GROM)
        tick(lua)
        self.assertEqual(fill_red(lua), near)

    def test_enemy_not_seen_yet_stays_bright(self):
        lua = setup(sighting=False)
        tick(lua)
        self.assertEqual(lua.eval('AutoBG_TargetButton1.alpha'), 1.0)

    def test_fading_can_be_turned_off(self):
        lua = setup()
        lua.execute('AutoBG_Settings.Targets.FadeOutOfRange = false; yards["%s"] = 55' % GROM)
        tick(lua)
        self.assertEqual(lua.eval('AutoBG_TargetButton1.alpha'), 1.0)

    def test_raid_icon_follows_the_mark(self):
        lua = setup()
        lua.execute('raidIcons["%s"] = 8' % GROM)
        fire(lua, "RAID_TARGET_UPDATE", 0)
        self.assertTrue(lua.eval('AutoBG_TargetButton1.RaidIcon.shown'))
        self.assertEqual(lua.eval('AutoBG_TargetButton1.RaidIcon.raidIndex'), 8)
        lua.execute('raidIcons["%s"] = nil' % GROM)
        fire(lua, "RAID_TARGET_UPDATE", 0)
        self.assertFalse(lua.eval('AutoBG_TargetButton1.RaidIcon.shown'))

    def test_counts_group_members_on_each_enemy(self):
        lua = setup()
        lua.execute('raidSize = 3; raidTargets["raid1target"] = "%s"; raidTargets["raid3target"] = "%s"' % (GROM, GROM))
        tick(lua)
        self.assertEqual(lua.eval('AutoBG_TargetButton1.TargetCount.text'), "2")
        lua.execute('raidTargets = {}')
        tick(lua)
        self.assertEqual(lua.eval('AutoBG_TargetButton1.TargetCount.text'), "")

    def test_preview_shows_every_feature(self):
        lua = setup()
        lua.execute('AutoBG_Targets:EnableConfigMode(10)')
        self.assertTrue(lua.eval('AutoBG_TargetButton1.RaidIcon.shown'))
        self.assertEqual(lua.eval('AutoBG_TargetButton1.TargetCount.text'), "3")
        self.assertEqual(lua.eval('AutoBG_TargetButton6.alpha'), 1.0)
        self.assertTrue(lua.eval('AutoBG_TargetButton6.fillFar'))
        self.assertTrue(lua.eval('AutoBG_TargetCast2.shown'))
        self.assertEqual(lua.eval('AutoBG_TargetCast2.Text.text'), "Flash Heal")
        lua.execute('AutoBG_Targets:DisableConfigMode()')
        self.assertFalse(lua.eval('AutoBG_TargetCast2.shown'))


if __name__ == "__main__":
    unittest.main()
