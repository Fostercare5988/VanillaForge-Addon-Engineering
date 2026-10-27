"""Event scope (2026-10-27): each module listens only where and to whom it works,
and the stealth alert still works in every battleground.

- The enemy frames register their match events only in a battleground or the
  preview; unit events come only for the tokens an enemy can be on.
- Spy registers its sightings only while its list works: not in a battleground.
- In a battleground the stealth alert comes from the enemy frames, also with the
  frames for that size switched off, and Spy shows it with its list switched off.
- No module takes UNIT_AURA or UNIT_HEALTH for every unit.

Which tokens the engine really fires stays an in-game check.
"""
from pathlib import Path
import os
import re
import unittest
from lupa.lua51 import LuaRuntime

import addon_loader
import test_spy_nearby
import test_spy_stealth_alert
import test_targets_guid_events as tge

ROOT = Path(os.environ["VANILLAFORGE_ADDON_ROOT"])

RECORD_EVENTS = r'''
local _CreateFrame = CreateFrame
function CreateFrame(...)
    local f = _CreateFrame(...)
    f.events = {}
    function f:RegisterEvent(e) self.events[e] = true end
    function f:RegisterUnitEvent(e, ...) self.events[e] = { ... } end
    function f:UnregisterEvent(e) self.events[e] = nil end
    return f
end
'''

BG = r'''
bgName = nil
function GetBattlefieldStatus(i) if i == 1 and bgName then return "active", bgName end return "none" end
notified = {}
AutoBG_Spy = { NotifyStealth = function(_, name, spell, _, _, inBattleground)
    table.insert(notified, name .. " " .. spell .. " " .. tostring(inBattleground)); return true end }
'''


def targets(bg=None):
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(tge.BASE)
    lua.execute(RECORD_EVENTS)
    lua.execute(BG)
    lua.globals().bgName = bg
    addon_loader.load(lua, tge.TARGETS, "AutoBG_Targets.lua")
    lua.execute('AutoBG_Targets.scripts.OnEvent(AutoBG_Targets, "PLAYER_LOGIN")')
    return lua


def enter(lua, bg):
    lua.globals().bgName = bg
    lua.execute('AutoBG_Targets.scripts.OnEvent(AutoBG_Targets, "UPDATE_BATTLEFIELD_STATUS")')


class TargetsEventScopeTests(unittest.TestCase):
    def test_match_events_only_in_a_battleground(self):
        lua = targets()
        enter(lua, None)
        for ev in ("UNIT_CASTEVENT", "BUFF_ADDED_OTHER", "UNIT_HEALTH_GUID", "UNIT_AURA_DELTA", "UNIT_HEALTH"):
            self.assertIsNone(lua.eval('AutoBG_Targets.events.%s' % ev), ev)
        self.assertTrue(lua.eval('AutoBG_Targets.events.UPDATE_BATTLEFIELD_STATUS'))
        enter(lua, "Alterac Valley")
        self.assertTrue(lua.eval('AutoBG_Targets.events.UNIT_CASTEVENT'))
        self.assertTrue(lua.eval('AutoBG_Targets.events.BUFF_ADDED_OTHER'))
        enter(lua, None)
        self.assertIsNone(lua.eval('AutoBG_Targets.events.UNIT_CASTEVENT'))

    def test_unit_events_only_for_enemy_tokens(self):
        lua = targets()
        enter(lua, "Alterac Valley")
        for ev in ("UNIT_AURA_DELTA", "UNIT_HEALTH"):
            units = list(lua.eval('AutoBG_Targets.events.%s' % ev).values())
            self.assertIn("target", units)
            self.assertIn("nameplate40", units)
            self.assertFalse([u for u in units if u.startswith("raid") or u.startswith("party")])

    def test_aura_refresh_alone_is_not_read_again(self):
        """ClassicAPI 1.17.10 UNIT_AURA_DELTA: only updated IDs never change stealth."""
        lua = targets()
        enter(lua, "Warsong Gulch")
        lua.execute('auraReads = 0; C_UnitAuras.GetAuraSlots = function() auraReads = auraReads + 1; return nil, 0 end')
        lua.execute('target = "Grom"')
        lua.execute('AutoBG_Targets.scripts.OnEvent(AutoBG_Targets, "UNIT_AURA_DELTA", "target", '
                    '{ updatedAuraInstanceIDs = { 3 } })')
        self.assertEqual(lua.eval('auraReads'), 0)
        lua.execute('AutoBG_Targets.scripts.OnEvent(AutoBG_Targets, "UNIT_AURA_DELTA", "target", '
                    '{ addedAuraInstanceIDs = { 4 } })')
        self.assertEqual(lua.eval('auraReads'), 1)
        lua.execute('AutoBG_Targets.scripts.OnEvent(AutoBG_Targets, "UNIT_AURA_DELTA", "target", '
                    '{ isFullUpdate = true })')
        self.assertEqual(lua.eval('auraReads'), 2)

    def test_preview_registers_and_ending_it_outside_a_battleground_drops_them(self):
        lua = targets()
        enter(lua, None)
        lua.execute('AutoBG_Targets:EnableConfigMode(10)')
        self.assertTrue(lua.eval('AutoBG_Targets.events.UNIT_CASTEVENT'))
        lua.execute('AutoBG_Targets:DisableConfigMode()')
        self.assertIsNone(lua.eval('AutoBG_Targets.events.UNIT_CASTEVENT'))


class BattlegroundStealthTests(unittest.TestCase):
    def stealth_alert(self, bg, frames_on):
        lua = targets()
        lua.execute('AutoBG_Settings.Targets.EnableBracket = { [10] = %s, [15] = %s, [40] = %s }'
                    % ((("true" if frames_on else "false"),) * 3))
        enter(lua, bg)
        # Never targeted: the name comes from the GUID, as for any loaded enemy.
        lua.execute('guidNames["%s"] = "Grom"' % tge.GROM)
        tge.fire(lua, "BUFF_ADDED_OTHER", tge.GROM, 1, 1787, 1, 60, 5, 0)
        return list(lua.eval('notified').values())

    def test_stealth_alerts_in_every_battleground_with_frames_on_or_off(self):
        for bg in ("Warsong Gulch", "Arathi Basin", "Alterac Valley", "Thorn Gorge"):
            for frames_on in (True, False):
                self.assertEqual(self.stealth_alert(bg, frames_on), ["Grom Stealth true"], (bg, frames_on))

    def test_spy_shows_the_battleground_alert_with_its_list_off(self):
        lua = test_spy_stealth_alert.runtime()
        lua.execute('AutoBG_Settings.Spy.Enabled = false; AutoBG_Settings.Spy.SoundAlert = false')
        lua.execute('AutoBG_Targets.activeBG = true; AutoBG_Spy:OnBattlegroundChanged(true)')
        rogue = test_spy_stealth_alert.ROGUE
        lua.execute('stealthed["%s"] = "Stealth"' % rogue)
        lua.execute('AutoBG_Spy:NotifyStealth("Sneaky", "Stealth", "ROGUE", "%s", true, "%s")' % (rogue, rogue))
        self.assertTrue(lua.eval('AutoBG_SpyAlertWindow.shown'))
        self.assertEqual(lua.eval('AutoBG_SpyAlertWindow.Name.text'), "Sneaky")
        self.assertEqual(lua.eval('sounds[1]'), "RaidWarning")


class SpyEventScopeTests(unittest.TestCase):
    def spy(self):
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute(test_spy_nearby.BASE)
        lua.execute(RECORD_EVENTS)
        addon_loader.load(lua, test_spy_nearby.SPY, "AutoBG_Spy.lua")
        lua.execute('AutoBG_SpyEventFrame.scripts.OnEvent(AutoBG_SpyEventFrame, "PLAYER_LOGIN")')
        return lua

    def test_sightings_are_off_in_a_battleground_and_back_after(self):
        lua = self.spy()
        self.assertTrue(lua.eval('AutoBG_SpyEventFrame.events.UNIT_CASTEVENT'))
        lua.execute('AutoBG_Targets.activeBG = true; AutoBG_Spy:OnBattlegroundChanged(true)')
        for ev in ("UNIT_CASTEVENT", "BUFF_ADDED_OTHER", "UNIT_AURA_DELTA", "NAME_PLATE_UNIT_ADDED"):
            self.assertIsNone(lua.eval('AutoBG_SpyEventFrame.events.%s' % ev), ev)
        self.assertTrue(lua.eval('AutoBG_SpyEventFrame.events.PLAYER_ENTERING_WORLD'))
        lua.execute('AutoBG_Targets.activeBG = false; AutoBG_Spy:OnBattlegroundChanged(false)')
        self.assertTrue(lua.eval('AutoBG_SpyEventFrame.events.UNIT_CASTEVENT'))

    def test_spy_aura_events_only_for_enemy_tokens(self):
        lua = self.spy()
        units = list(lua.eval('AutoBG_SpyEventFrame.events.UNIT_AURA_DELTA').values())
        self.assertIn("mouseover", units)
        self.assertFalse([u for u in units if u.startswith("raid") or u.startswith("party")])


class NoUnfilteredUnitEventsTests(unittest.TestCase):
    def test_no_module_takes_aura_or_health_for_every_unit(self):
        found = []
        for path in ROOT.glob("*.lua"):
            text = path.read_text("utf-8-sig")
            for m in re.finditer(r'RegisterEvent\("(UNIT_AURA|UNIT_HEALTH)"\)', text):
                found.append("%s %s" % (path.name, m.group(1)))
        self.assertEqual(found, [])


if __name__ == '__main__':
    unittest.main()
