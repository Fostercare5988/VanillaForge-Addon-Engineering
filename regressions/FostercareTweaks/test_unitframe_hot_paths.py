"""Repeated unit-frame updates with unchanged inputs make no widget writes (P3-1..P3-4).

Widget mocks count every Set*/ClearAllPoints/Show/Hide call. They model only
the getters these functions read; they do not prove native widget semantics.
"""
from pathlib import Path
import os
import unittest
from lupa.lua51 import LuaRuntime

ROOT = Path(os.environ["VANILLAFORGE_ADDON_ROOT"])
RAID = (ROOT / "mods/unitframes/raid.lua").read_text("utf-8-sig")
CORE = (ROOT / "mods/unitframes/core.lua").read_text("utf-8-sig")
AURAS = (ROOT / "mods/unitframes/auras.lua").read_text("utf-8-sig")

WIDGETS = r'''
writes = 0
local Widget = {}
local function Write() writes = writes + 1 end
function Widget:GetWidth() return self.width or 0 end
function Widget:GetHeight() return self.height or 0 end
function Widget:IsShown() return self.shown end
function Widget:GetText() return self.text end
function Widget:GetFont() return "Fonts\\FRIZQT__.TTF", self.fontSize or 12, "" end
function Widget:GetStringWidth() return string.len(tostring(self.text or "")) * (self.fontSize or 12) * 0.5 end
function Widget:SetText(t) Write(); if t ~= nil then t = tostring(t) end; self.text = t end
function Widget:SetFont(_, size) Write(); self.fontSize = size end
function Widget:SetWidth(w) Write(); self.width = w end
function Widget:SetHeight(h) Write(); self.height = h end
function Widget:Show() Write(); self.shown = true end
function Widget:Hide() Write(); self.shown = false end
setmetatable(Widget, { __index = function(_, name)
    if string.find(name, "^%u") then return function() Write() end end
end })
function W(props) return setmetatable(props or {}, { __index = Widget }) end
'''


def slice(source, start, end, fallback=None):
    i = source.find(start)
    if i < 0 and fallback:
        i = source.index(fallback)
    return source[i:source.index(end, i)]


def raid_runtime():
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(WIDGETS)
    lua.execute(r'''
        FT = { GetRaidMarkSettings = function() return 14, "portrait" end,
               NormalizeClass = function(c) return c end,
               Abbreviate = function(n) return n end }
        layouts = 0
        UF = { ClassColors = { MAGE = { r = 0.4, g = 0.8, b = 0.9 } } }
        function UF.SetFontSize(text, size)
            local _, current = text:GetFont()
            if current ~= size then text:SetFont("x", size) end
        end
        function UF.GetUnitHealthValues() return 3000, 4000 end
        function UF:GetRaidHealthFormat() return "deficit" end
        function UnitClass() return "Mage", "MAGE" end
        function UnitName() return "Jaina" end
        function UnitIsConnected() return true end
        function UnitIsDeadOrGhost() return false end
        function UnitIsGhost() return false end
        local bar = { SetMinMaxValues = function() end, SetValue = function() end,
                      SetStatusBarColor = function() end }
        btn = W({ unit = "raid1", shown = true, index = 1, auraStripHeight = 0,
                  healthBar = W({ width = 62, height = 28 }),
                  nameText = W(), healthText = W(),
                  raidIcon = W({ shown = false }), leaderIcon = W({ shown = false }) })
        for k, v in pairs(bar) do btn.healthBar[k] = v end
    ''')
    lua.execute(slice(RAID, 'local function LayoutRaidText', 'UF.LayoutRaidText = LayoutRaidText') + r'''
        UF.LayoutRaidText = function(...) layouts = layouts + 1; return LayoutRaidText(...) end
        RaidText = LayoutRaidText
    ''')
    lua.execute(slice(RAID, 'local function UpdateButtonHealth', 'local function UpdateButtonPower')
                + '\nHealth = UpdateButtonHealth')
    return lua


class RaidHotPathTests(unittest.TestCase):
    def test_repeated_raid_text_layout_writes_nothing(self):
        lua = raid_runtime()
        lua.execute('RaidText(btn, 0); writes = 0; RaidText(btn, 0)')
        self.assertEqual(lua.eval('writes'), 0)

    def test_unchanged_health_update_writes_nothing(self):
        lua = raid_runtime()
        lua.execute('RaidText(btn, 0); Health(btn); writes = 0; layouts = 0; Health(btn)')
        self.assertEqual(lua.eval('writes'), 0)

    def test_health_change_only_replaces_health_text(self):
        lua = raid_runtime()
        lua.execute('''RaidText(btn, 0); Health(btn); writes = 0
            UF.GetUnitHealthValues = function() return 2000, 4000 end; Health(btn)''')
        self.assertEqual(lua.eval('writes'), 1)
        self.assertEqual(lua.eval('btn.healthText.text'), "-2000")

    def test_unchanged_raid_badge_keeps_geometry(self):
        lua = raid_runtime()
        lua.execute(r'''
            UF.Auras = { UpdateAuraTiming = function() end, StyleBorder = function() end }
            function UF:IsDebuffSpin() return true end
            function UF:IsDebuffText() return true end
            function UF:IsBuffSpin() return true end
            function UF:IsBuffText() return true end
            function UF:IsColorDebuffsByDispel() return true end
            function UnitGUID() return "0x1" end
            function GetTime() return 1 end
        ''')
        lua.execute(slice(RAID, 'local function ShowRaidAura', '-- Mark/leader changes')
                    + '\nShowAura = ShowRaidAura')
        lua.execute(r'''
            badge = W({ border = W(), countText = W(), durationText = W(), cooldown = W(), icon = W() })
            aura = { index = 1, icon = "i", stacks = 1, id = 139 }
            ShowAura(btn, badge, aura, 10, 2, 20)
            geometry = 0
            local base = getmetatable(badge).__index
            for _, w in ipairs({ badge, badge.border, badge.countText, badge.durationText, badge.cooldown }) do
                setmetatable(w, { __index = function(_, k)
                    if k == "SetPoint" or k == "ClearAllPoints" or k == "SetWidth" or k == "SetHeight"
                        or k == "SetScale" or k == "SetFont" then
                        return function() geometry = geometry + 1 end
                    end
                    return base[k]
                end })
            end
            ShowAura(btn, badge, aura, 10, 2, 20)
        ''')
        self.assertEqual(lua.eval('geometry'), 0)


def core_runtime():
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(WIDGETS)
    lua.execute('UF = {}\n' + slice(CORE, 'function UF.SetFontSize', 'function UF:ApplyDimensions()'))
    lua.execute(r'''
        function UF:GetFontNameSize() return 12 end
        function UF:GetFontHealthSize() return 11 end
        function UF:GetFontLevelSize() return 11 end
        function UF:GetFontPowerSize() return 11 end
    ''')
    lua.execute(slice(CORE, 'local function FitText', 'function UF:IsImprovedStandardAuras()'))
    lua.execute(r'''
        local hb = W({ width = 150, height = 30, nameText = W({ text = "Jaina" }), healthText = W({ text = "3000 / 4000" }) })
        local pb = W({ width = 150, height = 10, powerText = W({ text = "800" }), leftText = W({ text = "" }) })
        badgeText = W({ text = "60", fontSize = 11 })
        frame = { healthBar = hb, powerBar = pb, portrait = W({ width = 40 }), portraitSide = "left",
                  levelBadge = W({ text = badgeText, height = 15 }) }
    ''')
    return lua


class ModernFrameHotPathTests(unittest.TestCase):
    def test_repeated_text_layout_writes_nothing(self):
        lua = core_runtime()
        lua.execute('UF:LayoutText(frame); writes = 0; UF:LayoutText(frame)')
        self.assertEqual(lua.eval('writes'), 0)

    def test_changed_health_text_is_refitted(self):
        lua = core_runtime()
        lua.execute(r'''UF:LayoutText(frame)
            frame.healthBar.healthText.text = "123456789012 / 123456789012"
            UF:LayoutText(frame)''')
        self.assertLess(lua.eval('frame.healthBar.healthText.fontSize'), 11)

    def test_externally_reset_font_is_refitted(self):
        lua = core_runtime()
        lua.execute(r'''frame.healthBar.healthText.text = "123456789012 / 123456789012"
            UF:LayoutText(frame)
            frame.healthBar.healthText.fontSize = 11
            UF:LayoutText(frame)''')
        self.assertLess(lua.eval('frame.healthBar.healthText.fontSize'), 11)


class PlayerAuraCoalescingTests(unittest.TestCase):
    def test_one_change_reported_twice_rescans_once(self):
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute(r'''
            scans, timers = 0, {}
            Auras = { UpdateBlizzPlayerAuras = function() scans = scans + 1 end,
                      UpdateBlizzTargetAuras = function() end }
            auraEventFrame = { RegisterEvent = function() end }
            FT = { SetEventHandler = function(_, fn) handler = fn end }
            C_Timer = { After = function(_, fn) table.insert(timers, fn) end }
            function UnitIsUnit(a, b) return a == b end
        ''')
        lua.execute(slice(AURAS, '-- UNIT_AURA(player) and PLAYER_AURAS_CHANGED',
                          'FT.SetEventHandler(auraEventFrame',
                          'auraEventFrame:RegisterEvent("PLAYER_AURAS_CHANGED")')
                    + AURAS[AURAS.index('FT.SetEventHandler(auraEventFrame'):])
        lua.execute(r'''
            handler(nil, "UNIT_AURA", "player")
            handler(nil, "PLAYER_AURAS_CHANGED")
            for _, fn in ipairs(timers) do fn() end
        ''')
        self.assertEqual(lua.eval('scans'), 1)


if __name__ == '__main__':
    unittest.main()
