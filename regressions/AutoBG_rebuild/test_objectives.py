"""Objective bars, the game start, the spirit wave, the Arathi Basin estimate and
your side on mixed teams (spec 4.4 tests 5-8). AutoBG 1.0, written new 2026-11-22."""
import unittest
from abg_env import load

CLAUDES_TICKS = "AutoBGDB = { queueOnLogin = false, ticks = { [1] = { gain = 10, every = 12, n = 1 }, [2] = { gain = 10, every = 9, n = 1 }, [3] = { gain = 10, every = 5, n = 1 }, [4] = { gain = 10, every = 3, n = 1 } } }"


def labels(lua, frame):
    return lua.eval(f'''(function()
        local out = {{}}
        for _, r in ipairs({frame}.rows) do if r:IsShown() then out[#out + 1] = r.label.text end end
        return table.concat(out, '|')
    end)()''')


class Bars(unittest.TestCase):
    def test_a_claim_runs_60_seconds_in_its_sides_colour_and_a_capture_ends_it(self):
        lua = load()
        lua.execute("enter('Arathi Basin'); line('Grom claims the Stables! If left unchallenged, the Horde will control it in 1 minute!', 'CHAT_MSG_BG_SYSTEM_HORDE')")
        self.assertEqual(labels(lua, "AutoBG_NodeFrame"), "Stables")
        r = "AutoBG_NodeFrame.rows[1]"
        self.assertEqual(lua.eval(f"clock({r}.clock)"), "1:00")
        self.assertIn("Stables_Horde", lua.eval(f"{r}.icon.texture"))
        lua.execute("step(39.5)")
        self.assertEqual(lua.eval(f"clock({r}.clock)"), "21")
        lua.execute("step(12)")
        self.assertEqual(lua.eval(f"clock({r}.clock)"), "|cffffd1009|r")
        lua.execute("line('The Horde has taken the Stables!', 'CHAT_MSG_BG_SYSTEM_HORDE')")
        self.assertFalse(lua.eval("AutoBG_NodeFrame:IsShown()"))

    def test_ctrl_click_announces(self):
        lua = load()
        lua.execute("enter('Arathi Basin'); line('Grom has assaulted the Blacksmith!', 'CHAT_MSG_BG_SYSTEM_HORDE'); step(9)")
        lua.execute("ctrl = true; run(AutoBG_NodeFrame.rows[1], 'OnClick', 'LeftButton')")
        self.assertTrue(lua.eval("said('^say:BATTLEGROUND:Blacksmith %(Horde%) captured in 51$')"))

    def test_the_close_warning_starts_nothing_and_a_start_line_counts(self):
        lua = load()
        lua.execute("enter('Warsong Gulch'); line('Not enough players. This game will close in 30 seconds.')")
        self.assertFalse(lua.eval("AutoBG_StartTimerFrame:IsShown()"))
        lua.execute("line('The battle for Warsong Gulch begins in 1 minute.')")
        self.assertEqual(lua.eval("clock(AutoBG_StartTimerFrame.rows[1].clock)"), "1:00")
        lua.execute("line('The battle for Warsong Gulch has begun!')")
        self.assertFalse(lua.eval("AutoBG_StartTimerFrame:IsShown()"))

    def test_an_alterac_mine_only_from_has_taken_and_short_names_only_in_arathi(self):
        lua = load()
        lua.execute("enter('Alterac Valley'); line('The Irondeep Mine is under attack!')")
        self.assertEqual(labels(lua, "AutoBG_AVNodeFrame"), "")
        lua.execute("line('The Horde has taken the Irondeep Mine! Its supplies will now be used for reinforcements!', 'CHAT_MSG_MONSTER_YELL')")
        lua.execute("line('Grom claims the Snowfall Graveyard! If left unchallenged, the Horde will control it!')")
        self.assertEqual(labels(lua, "AutoBG_AVNodeFrame"), "Irondeep Mine|Snowfall Graveyard")
        self.assertEqual(lua.eval("clock(AutoBG_AVNodeFrame.rows[1].clock)"), "5:00")
        lua.execute("line('Grom claims the mine!')")
        self.assertEqual(labels(lua, "AutoBG_NodeFrame"), "")

    def test_a_warsong_flag_comes_back_in_23_seconds(self):
        lua = load()
        lua.execute("enter('Warsong Gulch'); line('Grom captured the Alliance flag!', 'CHAT_MSG_BG_SYSTEM_HORDE')")
        self.assertEqual(labels(lua, "AutoBG_WSGFlagFrame"), "Alliance flag")
        self.assertEqual(lua.eval("clock(AutoBG_WSGFlagFrame.rows[1].clock)"), "23")

    def test_a_group_wakes_once_at_its_soonest_end_and_nothing_runs_between(self):
        lua = load()
        lua.execute("enter('Arathi Basin'); healerTime = 0")
        lua.execute("line('A claims the Farm! the Horde'); step(10); line('B claims the Stables! the Horde'); step()")
        live = lua.eval("liveTimers()")
        lua.execute("step(49.9)")
        self.assertEqual(labels(lua, "AutoBG_NodeFrame"), "Farm|Stables")
        lua.execute("step(0.2)")
        self.assertEqual(labels(lua, "AutoBG_NodeFrame"), "Stables")
        self.assertEqual(lua.eval("liveTimers()"), live)
        self.assertEqual(lua.eval("onUpdates()"), 0)


class Wave(unittest.TestCase):
    def test_a_guess_until_a_wave_is_seen_then_synced(self):
        lua = load()
        lua.execute("enter('Warsong Gulch')")
        r = "AutoBG_RespawnFrame.rows[1]"
        self.assertEqual(lua.eval(f"clock({r}.clock)"), "~30")
        lua.execute("healerTime = 12; fire('AREA_SPIRIT_HEALER_IN_RANGE')")
        self.assertEqual(lua.eval(f"clock({r}.clock)"), "12")
        lua.execute("step(12.5)")
        self.assertEqual(lua.eval(f"clock({r}.clock)"), "30")

    def test_your_unghost_and_a_raid_ghost_turning_alive_sync_it(self):
        lua = load()
        lua.execute("enter('Arathi Basin'); step(7); fire('PLAYER_UNGHOST')")
        self.assertEqual(lua.eval("clock(AutoBG_RespawnFrame.rows[1].clock)"), "30")
        lua.execute("unit('0x0000000000000077', { name = 'Mate', player = true, inGroup = true, ghost = true }); tokens.raid3 = '0x0000000000000077'")
        lua.execute("step(10); fire('PLAYER_FLAGS_CHANGED', 'raid3'); units['0x0000000000000077'].ghost = nil; fire('UNIT_HEALTH', 'raid3')")
        self.assertEqual(lua.eval("clock(AutoBG_RespawnFrame.rows[1].clock)"), "30")

    def test_never_in_an_arena(self):
        lua = load()
        lua.execute("enter('Lordaeron Arena', true)")
        self.assertFalse(lua.eval("AutoBG_RespawnFrame:IsShown()"))
        self.assertFalse(lua.eval("receives(AutoBG_RespawnFrame, 'AREA_SPIRIT_HEALER_IN_RANGE')"))


class Estimate(unittest.TestCase):
    def states(self, lua, a, ab, h, hb):
        lua.execute(f"worldStates = {{ 'Bases: {ab}  Resources: {a}/2000', 'Bases: {hb}  Resources: {h}/2000' }}; fire('UPDATE_WORLD_STATES'); step()")

    def test_the_verdict_finals_and_bases_from_learned_ticks(self):
        lua = load(CLAUDES_TICKS)
        lua.execute("enter('Arathi Basin')")
        self.states(lua, 1000, 2, 1000, 3)
        est = "AutoBG_ABProjectionFrame"
        self.assertTrue(lua.eval(f"{est}:IsShown()"))
        # Horde (you) at 3 bases, 2 per s, needs 500 s; the Alliance at 2 bases makes 555 by then.
        self.assertEqual(lua.eval(f"clock({est}.verdict)"), "|cff59ff72Win|r 8:20")
        self.assertEqual(lua.eval(f"{est}.info.text"), "2000 : 1550   Hold 3 bases")
        lua.execute(f"ctrl = true; run({est}, 'OnClick')")
        self.assertTrue(lua.eval("said('^say:BATTLEGROUND:Arathi Basin: Win in 8:20, 2000 to 1550. Hold 3 bases.$')"))

    def test_a_base_count_not_seen_is_a_guess(self):
        lua = load(CLAUDES_TICKS)
        lua.execute("enter('Arathi Basin')")
        self.states(lua, 100, 0, 1500, 5)
        self.assertEqual(lua.eval("clock(AutoBG_ABProjectionFrame.verdict)"), "|cff59ff72Win|r ~17")

    def test_an_assault_under_way_counts_and_a_late_tick_moves_the_average(self):
        lua = load(CLAUDES_TICKS)
        lua.execute("enter('Arathi Basin')")
        self.states(lua, 1000, 3, 1000, 2)
        lua.execute("step(5)")
        self.states(lua, 1010, 3, 1000, 2)
        lua.execute("step(6)")
        self.states(lua, 1020, 3, 1000, 2)
        self.assertEqual(lua.eval("AutoBGDB.ticks[3].every"), 5.33)
        self.assertEqual(lua.eval("AutoBGDB.ticks[3].n"), 3)

    def test_a_new_base_count_is_learned(self):
        lua = load("AutoBGDB = { queueOnLogin = false }")
        lua.execute("enter('Arathi Basin')")
        self.states(lua, 500, 4, 0, 0)
        lua.execute("step(3)")
        self.states(lua, 510, 4, 0, 0)
        lua.execute("step(3)")
        self.states(lua, 520, 4, 0, 0)
        self.assertEqual(lua.eval("AutoBGDB.ticks[4].gain"), 10)
        self.assertEqual(lua.eval("AutoBGDB.ticks[4].every"), 3)


class Side(unittest.TestCase):
    def test_a_group_member_carrying_the_horde_flag_makes_you_alliance_until_a_loading_screen(self):
        lua = load()
        lua.execute("enter('Warsong Gulch'); unit('0x0000000000000050', { name = 'Mate', player = true, inGroup = true, faction = 'Horde' })")
        self.assertEqual(lua.eval("__addon_ns.MySide()"), "Horde")
        lua.execute("line('The Horde flag was picked up by Mate!', 'CHAT_MSG_BG_SYSTEM_ALLIANCE')")
        self.assertEqual(lua.eval("__addon_ns.MySide()"), "Alliance")
        lua.execute("enter(nil)")
        self.assertEqual(lua.eval("__addon_ns.MySide()"), "Horde")

    def test_an_enemy_claiming_a_base_settles_it_too(self):
        lua = load()
        lua.execute("enter('Arathi Basin'); enemy('0x0000000000000060', { name = 'Foe', faction = 'Horde' })")
        lua.execute("line('Foe claims the Farm! If left unchallenged, the Horde will control it in 1 minute!')")
        self.assertEqual(lua.eval("__addon_ns.MySide()"), "Alliance")


if __name__ == "__main__":
    unittest.main()
