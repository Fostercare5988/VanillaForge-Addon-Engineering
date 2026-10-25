"""FostercareTweaks, notes from play up to 2026-10-25.

- A dead player target showed "0" under the native "Dead" label, and "0" mana.
  Health reaches 0 before UnitIsDead turns true.
- Raid frames showed "Unknown" for players the client had not loaded yet.
- Raid frames did not target on click: they now use ClassicAPI unit attributes.
- Solo, the mark keys did nothing: they now set NamPower local marks.
Clicking, menus and local marks stay in-game checks.
"""
from pathlib import Path
import os
import unittest
from lupa.lua51 import LuaRuntime

ROOT = Path(os.environ["VANILLAFORGE_ADDON_ROOT"])


def source(name):
    return (ROOT / name).read_text("utf-8-sig")


def between(text, start, end):
    return text[text.index(start):text.index(end)]


BASE = r'''
hooks = {}
FT = { overwrites = {} }
FostercareTweaks = FT
function FT:register(m) self.module = m; return m end
function FT.hooksecurefunc(name, f) hooks[name] = f end
function FT.Abbreviate(v) return tostring(v) end
function FT.GetUnitHealthValues(u) return UnitHealth(u), UnitHealthMax(u) end
STANDARD_TEXT_FONT, UNKNOWNOBJECT = "font", "Unknown"
floor = math.floor
local function text()
    return { shown = true, text = "",
        Show = function(s) s.shown = true end, Hide = function(s) s.shown = false end,
        SetText = function(s, t) s.text = t end, GetText = function(s) return s.text end,
        SetPoint = function() end, SetFontObject = function() end, SetFont = function() end,
        SetHeight = function() end, SetJustifyH = function() end, SetAlpha = function() end }
end
local function bar(name, unit, value, max)
    return { name = name, unit = unit, value = value, max = max, TextString = text(),
        GetName = function(s) return s.name end, Show = function() end,
        GetMinMaxValues = function(s) return 0, s.max end, GetValue = function(s) return s.value end }
end
health = { target = 0 }
function UnitHealth(u) return health[u] or 100 end
function UnitHealthMax() return 100 end
dead = false
function UnitIsDeadOrGhost() return dead end
function CreateFrame() return { SetAllPoints = function() end, CreateFontString = function() return text() end } end
TargetFrame = {}
TargetFrameHealthBar = bar("TargetFrameHealthBar", "target", 0, 100)
TargetFrameManaBar = bar("TargetFrameManaBar", "target", 0, 3000)
PlayerFrameHealthBar = bar("PlayerFrameHealthBar", "player", 100, 100)
PlayerFrameManaBar = bar("PlayerFrameManaBar", "player", 100, 100)
PetFrameHealthBar = bar("PetFrameHealthBar", "pet", 100, 100)
PetFrameManaBar = bar("PetFrameManaBar", "pet", 100, 100)
'''


class DeadTargetNumbers(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute(BASE)
        self.lua.execute(source("mods/health-numbers.lua"))
        self.lua.execute('FT.module:enable()')

    def test_zero_health_hides_both_numbers_before_dead_flag(self):
        self.lua.execute('''
            TargetFrameManaBar.TextString.text = "0"
            hooks.TextStatusBar_UpdateTextString(TargetFrameHealthBar)
            hooks.TargetFrame_CheckDead()
        ''')
        self.assertFalse(self.lua.eval('TargetFrameHealthBar.TextString.shown'))
        self.assertFalse(self.lua.eval('TargetFrameManaBar.TextString.shown'))

    def test_living_target_keeps_numbers(self):
        self.lua.execute('''
            health.target = 40; TargetFrameHealthBar.value = 40; TargetFrameManaBar.value = 900
            hooks.TargetFrame_CheckDead()
        ''')
        self.assertTrue(self.lua.eval('TargetFrameHealthBar.TextString.shown'))
        self.assertEqual(self.lua.eval('TargetFrameHealthBar.TextString.text'), "40%")
        self.assertTrue(self.lua.eval('TargetFrameManaBar.TextString.shown'))


RAID = source("mods/unitframes/raid.lua")


class RaidNames(unittest.TestCase):
    def name_for(self, roster, unit_name):
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute(BASE)
        lua.execute('''
            UF = { ClassColors = {} }
            function UF.GetUnitHealthValues() return 100, 100 end
            function FT.NormalizeClass() end
            function UnitClass() end
            function UnitName() return %s end
            function UnitIsConnected() return 1 end
            function UnitIsGhost() end
            local function sb() return { SetMinMaxValues = function() end, SetValue = function() end,
                SetStatusBarColor = function() end } end
            btn = { unit = "raid3", rosterName = %s, IsShown = function() return true end,
                healthBar = sb(), nameText = { GetText = function(s) return s.t end, SetText = function(s, t) s.t = t end },
                healthText = { GetText = function() end, SetText = function() end } }
        ''' % (unit_name, roster))
        lua.execute(between(RAID, "local function UpdateButtonHealth", "local function UpdateButtonPower")
                    + "\nUpdateButtonHealth(btn)")
        return lua.eval('btn.nameText.t')

    def test_roster_name_beats_unknown(self):
        self.assertEqual(self.name_for('"Parting"', '"Unknown"'), "Parting")

    def test_party_member_falls_back_to_unit_name(self):
        self.assertEqual(self.name_for('nil', '"Parting"'), "Parting")


class RaidClicks(unittest.TestCase):
    def test_buttons_click_through_unit_attributes(self):
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute('btn = { attr = {}, SetAttribute = function(s, k, v) s.attr[k] = v end,'
                    ' GetAttribute = function(s, k) return s.attr[k] end }')
        lua.execute(between(RAID, "local function SetUnit", "local function CreateRaidButton")
                    + '\nSetUnit(btn, "raid7"); first = btn.attr.unit; SetUnit(btn, nil)')
        self.assertEqual(lua.eval('first'), "raid7")
        self.assertIsNone(lua.eval('btn.attr.unit'))
        create = between(RAID, "local function CreateRaidButton", "-- Health Bar")
        self.assertIn('SetAttribute("type1", "target")', create)
        self.assertIn('SetAttribute("type2", "menu")', create)
        self.assertNotIn('SetScript("OnClick"', create)


class SoloMarks(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute(BASE)
        self.lua.execute('''
            raid, party, marks, sent, native = 0, 0, {}, {}, {}
            function GetNumRaidMembers() return raid end
            function GetNumPartyMembers() return party end
            function UnitGUID() return "0xF1" end
            function GetRaidTargets() return marks end
            function SetLocalRaidTargetIndex(u, i) table.insert(sent, i); marks[i] = i > 0 and "0xF1" or nil end
            function SetRaidTargetIcon(u, i) table.insert(native, i) end
            function FT.GetNumber(_, d) return d end
            function FT.GetOverride() end
            function FT:RefreshRaidMarks() end
            function CreateFrame() return { RegisterEvent = function() end } end
            function FT.SetEventHandler() end
        ''')
        self.lua.execute(source("mods/raid-target-marks.lua"))
        self.lua.execute('FT.module:enable()')

    def test_solo_key_toggles_a_local_mark(self):
        self.lua.execute('SetRaidTargetIcon("target", 8); SetRaidTargetIcon("target", 8)')
        self.assertEqual(list(self.lua.eval('sent').values()), [8, 0])
        self.assertEqual(len(self.lua.eval('native')), 0)

    def test_grouped_key_uses_the_server_mark(self):
        self.lua.execute('party = 1; SetRaidTargetIcon("target", 8)')
        self.assertEqual(list(self.lua.eval('native').values()), [8])
        self.assertEqual(len(self.lua.eval('sent')), 0)


if __name__ == "__main__":
    unittest.main()
