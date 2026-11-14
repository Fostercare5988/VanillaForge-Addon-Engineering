"""Audit 2026-11-14: the arena sweep, the settings window and the retired options.

The complete AutoBG files run under the game's Lua with the suites' widget
stand-ins. Looks, clicks in the client and AddOn Options' own frames stay
in-game checks.
"""
import unittest
from wowlua import LuaRuntime

import addon_loader
from test_targets_guid_events import BASE as TARGETS_BASE, TARGETS

# An arena, your team of two in a raid group, two enemies the UnitXP cycle
# steps through (it selects the next enemy and returns true).
ARENA_WORLD = r'''
ARENA = "Arena"
function AutoBG_IsArenaZone() return true end
function GetBattlefieldStatus() return "none" end
function GetNumBattlefieldScores() return 0 end
raidSize = 2
ENEMIES = { { guid = "0x00000000000000A1", name = "Kael" }, { guid = "0x00000000000000A2", name = "Morg" } }
local function Enemy(u)
    if u == "target" then
        for _, e in ipairs(ENEMIES) do if e.name == target then return e end end
        return nil
    end
    for _, e in ipairs(ENEMIES) do if e.guid == u then return e end end
end
steps, cursor = 0, 0
function UnitXP(unit, verb)
    steps = steps + 1
    cursor = cursor % #ENEMIES + 1
    target = ENEMIES[cursor].name
    return true
end
function ClearTarget() target = nil end
function UnitExists(u) return u == "player" or Enemy(u) ~= nil end
function UnitGUID(u) local e = Enemy(u); return e and e.guid end
function UnitName(u) if u == "player" then return "Tester" end local e = Enemy(u); return e and e.name end
'''


def arena():
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(TARGETS_BASE)
    lua.execute(ARENA_WORLD)
    addon_loader.load(lua, TARGETS, "AutoBG_Targets.lua")
    for event in ("PLAYER_LOGIN", "UPDATE_BATTLEFIELD_STATUS"):
        lua.execute('AutoBG_Targets.scripts.OnEvent(AutoBG_Targets, "%s")' % event)
    return lua


def run_tickers(lua):
    lua.execute('for _, fn in ipairs(tickers) do fn() end')


class ArenaSweep(unittest.TestCase):
    """2026-11-14 /lag on Claude, Sunstrider Court: the sweep (Targets.lua:1030)
    ran 88 times for 597 ms, every second, moving your target through every
    enemy even with the whole team listed."""

    def test_the_sweep_finds_the_team(self):
        lua = arena()
        run_tickers(lua)
        self.assertEqual(lua.eval('AutoBG_Targets.EnemyCount()'), 2)
        self.assertIsNone(lua.eval('target'))          # your empty target is given back

    def test_the_sweep_rests_once_the_whole_team_is_listed(self):
        lua = arena()
        run_tickers(lua)
        lua.execute('steps = 0')
        run_tickers(lua)
        self.assertEqual(lua.eval('steps'), 0)

    def test_the_sweep_goes_on_while_an_enemy_is_missing(self):
        lua = arena()
        lua.execute('ENEMIES[2].hidden = ENEMIES[2]; table.remove(ENEMIES, 2)')   # in stealth
        run_tickers(lua)
        self.assertEqual(lua.eval('AutoBG_Targets.EnemyCount()'), 1)
        lua.execute('steps = 0; table.insert(ENEMIES, { guid = "0x00000000000000A2", name = "Morg" })')
        run_tickers(lua)
        self.assertGreater(lua.eval('steps'), 0)
        self.assertEqual(lua.eval('AutoBG_Targets.EnemyCount()'), 2)


class RetiredSwitches(unittest.TestCase):
    """2026-11-14: switches every character left on, with no reason to be off,
    are always on; their saved keys are cleared by the sweeps (KP-64)."""

    def test_enemy_rows_always_dim_in_stealth_show_their_text_and_raid_icons(self):
        import test_targets_guid_events as tg
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute(TARGETS_BASE)
        lua.execute('AutoBG_Settings = { Targets = { DimStealthed = { [10] = false }, '
                    'ButtonShowHealthText = { [10] = false }, ShowRaidIcons = false } }')
        addon_loader.load(lua, TARGETS, "AutoBG_Targets.lua")
        for event in ("PLAYER_LOGIN", "UPDATE_BATTLEFIELD_STATUS"):
            lua.execute('AutoBG_Targets.scripts.OnEvent(AutoBG_Targets, "%s")' % event)
        lua.execute('target = "Grom"; AutoBG_Targets.scripts.OnEvent(AutoBG_Targets, "PLAYER_TARGET_CHANGED"); target = nil')
        for key in ("DimStealthed", "ButtonShowHealthText", "ShowRaidIcons"):
            self.assertIsNone(lua.eval('AutoBG_Settings.Targets.%s' % key), key)
        self.assertEqual(tg.row_text(lua), "100%")
        lua.execute('raidIcons["%s"] = 8; AutoBG_Targets.UpdateRowStatus()' % tg.GROM)
        self.assertTrue(lua.eval('AutoBG_TargetButton1.RaidIcon.shown'))
        tg.fire(lua, "BUFF_ADDED_OTHER", tg.GROM, 1, 1787, 1, 60, 5, 0)
        self.assertEqual(lua.eval('AutoBG_TargetButton1.alpha'), 0.75)

    def test_a_stealth_heard_from_an_enemy_you_cannot_see_never_warns(self):
        import test_spy_stealth_alert as ts
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute(ts.BASE)
        lua.execute(ts.STEALTH.replace("StealthProximityOnly = true", "StealthProximityOnly = false"))
        addon_loader.load(lua, ts.SPY, "AutoBG_Spy.lua")
        lua.execute('AutoBG_SpyEventFrame.scripts.OnEvent(AutoBG_SpyEventFrame, "PLAYER_LOGIN")')
        lua.execute('stealthed["%s"] = "Stealth"; visible = false' % ts.ROGUE)
        ts.dispatch(lua, "UNIT_CASTEVENT", ts.ROGUE, "", "CAST", 1787, 0)
        self.assertFalse(lua.eval('AutoBG_SpyAlertWindow ~= nil and AutoBG_SpyAlertWindow.shown'))
        self.assertIsNone(lua.eval('AutoBG_Settings.Spy.StealthProximityOnly'))


class Looks(unittest.TestCase):
    def test_the_preview_reads_like_a_match(self):
        import test_targets_guid_events as tg
        lua = tg.runtime()
        lua.execute('AutoBG_Targets:EnableConfigMode(10)')
        names = [lua.eval('AutoBG_TargetButton%d.targetName' % i) for i in range(1, 11)]
        self.assertFalse([n for n in names if n.startswith("Target")])
        self.assertEqual(len(set(names)), 10)


COOLDOWNS = r'''
local Widget = getmetatable(UIParent).__index
function Widget:SetCooldown(start, duration) self.cd = { start, duration } end
function Widget:Clear() self.cd = nil end
function Widget:SetHideCountdownNumbers(on) self.hideNumbers = on end
'''


def trinket_world():
    import test_targets_guid_events as tg
    from clock_mock import CLOCK
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(TARGETS_BASE)
    lua.execute(CLOCK)
    lua.execute(COOLDOWNS)
    addon_loader.load(lua, TARGETS, "AutoBG_Targets.lua")
    for event in ("PLAYER_LOGIN", "UPDATE_BATTLEFIELD_STATUS"):
        lua.execute('AutoBG_Targets.scripts.OnEvent(AutoBG_Targets, "%s")' % event)
    lua.execute('target = "Grom"; AutoBG_Targets.scripts.OnEvent(AutoBG_Targets, "PLAYER_TARGET_CHANGED"); target = nil')
    return lua, tg


def trinket_text(lua, now):
    lua.execute('NOW = %s; __frame()' % now)
    return lua.eval('AutoBG_TargetButton1.Trinket.Text.text')


class EnemyTrinketSweep(unittest.TestCase):
    """2026-11-14, asked for by the player: enemy trinkets count down like
    GearRack's (a native cooldown sweep), with AutoBG's timer clock."""

    def use(self, lua, tg, now):
        lua.execute('NOW = %s' % now)
        tg.fire(lua, "BUFF_ADDED_OTHER", tg.GROM, 1, 23276, 1, 60, 5, 0)

    def test_a_used_trinket_sweeps_and_counts_like_the_timers(self):
        lua, tg = trinket_world()
        self.use(lua, tg, 1000)
        cd = 'AutoBG_TargetTrinketCD1'
        self.assertEqual((lua.eval(cd + '.cd[1]'), lua.eval(cd + '.cd[2]')), (1000, 180))
        self.assertTrue(lua.eval(cd + '.hideNumbers'))        # the player's CVar decides those
        self.assertEqual(trinket_text(lua, 1000), "3:00")
        self.assertEqual(trinket_text(lua, 1142), "38")

    def test_the_half_second_pass_leaves_a_counting_trinket_alone(self):
        lua, tg = trinket_world()
        self.use(lua, tg, 1000)
        lua.execute('NOW = 1010; AutoBG_TargetButton1.Trinket.Text:SetText("engine")')
        run_tickers(lua)
        self.assertEqual(lua.eval('AutoBG_TargetButton1.Trinket.Text.text'), "engine")

    def test_the_trinket_is_ready_again_when_the_sweep_ends(self):
        lua, tg = trinket_world()
        self.use(lua, tg, 1000)
        lua.execute('NOW = 1180; local cd = AutoBG_TargetTrinketCD1; cd.scripts.OnCooldownDone(cd)')
        self.assertIsNone(lua.eval('AutoBG_TargetTrinketCD1.cd'))
        self.assertEqual(lua.eval('AutoBG_TargetButton1.Trinket.Text.text'), "")
        self.use(lua, tg, 1181)
        self.assertEqual(lua.eval('AutoBG_TargetTrinketCD1.cd[1]'), 1181)


PLACES = r'''
local Widget = getmetatable(UIParent).__index
function Widget:SetPoint(...) self.pt = { ... } end
function Widget:ClearAllPoints() self.pt = nil end
function Widget:SetParent(p) self.parent = p end
function Widget:SetWidth(w) self.width = w end
function Widget:GetWidth() return self.width end
function Widget:SetAlpha(a) self.alpha = a end
function Widget:EnableMouse(on) self.mouse = on end
function Widget:Enable() self.enabled = true end
function Widget:Disable() self.enabled = false end
function Widget:SetChecked(v) self.checked = v and true or nil end
function Widget:GetChecked() return self.checked end
-- The named controls placed on a page: { name, x, y }.
function Spots(page)
    local t = {}
    for name, w in pairs(_G) do
        if type(name) == "string" and string.find(name, "^AutoBG_") and type(w) == "table"
            and w.pt and w.pt[2] == page and w.shown ~= false then
            t[#t + 1] = { name, w.pt[4], w.pt[5] }
        end
    end
    return t
end
'''

# Controls that share their line on purpose: a battleground's teams button, the
# sound's Play, the second queue button.
SHARES_A_LINE = ("AutoBG_Opt_QueueModeWSG", "AutoBG_Opt_QueueModeAB", "AutoBG_BtnTestSound", "AutoBG_BtnCancelAll")


def window():
    import test_options_preview as op
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(op.BASE)
    lua.execute(PLACES)
    lua.execute('AutoBG_Targets.activeBG = true')
    addon_loader.load(lua, op.OPTIONS, "AutoBG_Options.lua")
    return lua


class SettingsInAddOnOptions(unittest.TestCase):
    def test_every_page_is_a_category_under_autobg(self):
        lua = window()
        self.assertEqual(lua.eval('categories[1].name'), "AutoBG")
        names = [lua.eval('categories[%d].name' % i) for i in range(2, 7)]
        self.assertEqual(names, ["General", "Timers", "Enemy frames", "Spy", "Arena"])
        self.assertTrue(all(lua.eval('categories[%d].parent' % i) == "AutoBG" for i in range(2, 7)))

    def test_a_category_borrows_its_page_and_gives_it_back(self):
        lua = window()
        lua.execute('AutoBG_OpenOptions("general")')
        lua.execute('host = categories[2]; host.shown = false; host:Show()')
        self.assertTrue(lua.eval('AutoBG_OptionsPage1.parent == host.holder'))
        self.assertEqual(lua.eval('AutoBG_Opt_AutoAccept.pt[4]'), 28)          # one column
        lua.execute('host.scripts.OnHide(host)')
        self.assertTrue(lua.eval('AutoBG_OptionsPage1.parent == AutoBG_OptionsPanel'))
        lua.execute('AutoBG_OptionsPanel.shown = false; AutoBG_OpenOptions("general")')
        self.assertTrue(lua.eval('AutoBG_OptionsPage1.shown'))
        self.assertEqual(lua.eval('AutoBG_Opt_AutoAccept.pt[4]'), 264)         # two columns again

    def test_in_addon_options_every_page_is_one_column(self):
        lua = window()
        for index in range(1, 6):
            lua.execute('host = categories[%d]; host.shown = false; host:Show()' % (index + 1))
            spots = lua.eval('Spots(AutoBG_OptionsPage%d)' % index)
            seen = {}
            for i in range(1, len(spots) + 1):
                name, x, y = spots[i][1], spots[i][2], spots[i][3]
                if name in SHARES_A_LINE:
                    continue
                self.assertLess(x, 120, "page %d: %s at x=%s" % (index, name, x))
                self.assertNotIn(round(y), seen, "page %d: %s shares a line with %s" % (index, name, seen.get(round(y))))
                seen[round(y)] = name
            self.assertGreater(len(seen), 4, index)
            lua.execute('host.scripts.OnHide(host)')

    def test_the_window_closes_addon_options(self):
        lua = window()
        lua.execute('InterfaceOptionsFrame.shown = true; AutoBG_OpenOptions("spy")')
        self.assertFalse(lua.eval('InterfaceOptionsFrame:IsShown()'))
        self.assertTrue(lua.eval('AutoBG_OptionsPanel:IsShown()'))


class SettingsThatDoNothingDim(unittest.TestCase):
    """2026-11-14, Claude's saved settings: an enter delay of 78 s with
    Accept queue pops off, and team rows picked for battlegrounds not queued."""

    def test_the_enter_delay_dims_while_entering_is_off(self):
        lua = window()
        lua.execute('AutoBG_Settings.AutoAccept = false; AutoBG_OpenOptions("general")')
        self.assertEqual(lua.eval('AutoBG_Opt_AcceptDelay.alpha'), 0.4)
        lua.execute('local w = AutoBG_Opt_AutoAccept; w:SetChecked(true); w.scripts.OnClick(w)')
        self.assertTrue(lua.eval('AutoBG_Settings.AutoAccept'))
        self.assertEqual(lua.eval('AutoBG_Opt_AcceptDelay.alpha'), 1)

    def test_a_teams_button_dims_while_its_battleground_is_not_queued(self):
        lua = window()
        lua.execute('AutoBG_Settings.AutoQueue_WSG = false; AutoBG_Settings.AutoQueue_AB = true; '
                    'AutoBG_Settings.QueueMode_WSG = "fa"; AutoBG_OpenOptions("general")')
        self.assertFalse(lua.eval('AutoBG_Opt_QueueModeWSG.enabled'))
        self.assertTrue(lua.eval('AutoBG_Opt_QueueModeAB.enabled'))
        self.assertEqual(lua.eval('AutoBG_Opt_QueueModeWSG.text'), "Any")

    def test_the_arena_type_dims_while_no_arena_is_queued(self):
        lua = window()
        lua.execute('AutoBG_Settings.AutoQueue_Arena = false; AutoBG_OpenOptions("general")')
        self.assertFalse(lua.eval('AutoBG_Opt_ArenaType1.enabled'))
        lua.execute('local w = AutoBG_Opt_QueueArena; w:SetChecked(true); w.scripts.OnClick(w)')
        self.assertTrue(lua.eval('AutoBG_Opt_ArenaType1.enabled'))


if __name__ == "__main__":
    unittest.main()
