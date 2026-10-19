"""Spy Nearby list stability (follows Spy-superwow's Active/Inactive model).

The complete AutoBG_Spy.lua file runs under Lua 5.1 with generic widget mocks and
a manual clock. Real unit visibility, nameplate events and window drawing remain
in-game checks.
"""
from pathlib import Path
import os
import unittest
from lupa.lua51 import LuaRuntime

ROOT = Path(os.environ["VANILLAFORGE_ADDON_ROOT"])
SPY = (ROOT / "AutoBG_Spy.lua").read_text("utf-8-sig")

BASE = r'''
function table.wipe(t) for k in pairs(t) do t[k] = nil end return t end
CLASSIC_API_VERSION, SUPERWOW_VERSION = 11600, "2.2"
local Widget = {}
setmetatable(Widget, { __index = function(_, name)
    if string.find(name, "^%u") then return function() end end
end })
function Widget:SetText(text) self.text = text end
function Widget:GetText() return self.text end
function Widget:SetScript(kind, fn) self.scripts = self.scripts or {}; self.scripts[kind] = fn end
function Widget:IsShown() return self.shown end
function Widget:Show() self.shown = true end
function Widget:Hide() self.shown = false end
function Widget:SetAlpha(a) self.alpha = a end
function Widget:SetWidth(w) self.width = w end
function Widget:GetWidth() return self.width or 0 end
function Widget:SetHeight(h) self.height = h end
function Widget:GetHeight() return self.height or 0 end
function Widget:CreateTexture() return setmetatable({}, { __index = Widget }) end
function Widget:CreateFontString() return setmetatable({}, { __index = Widget }) end
function CreateFrame(_, name) local f = setmetatable({ name = name }, { __index = Widget }); if name then _G[name] = f end; return f end
UIParent = CreateFrame("Frame", "UIParent")
GameTooltip = CreateFrame("Frame", "GameTooltip")
now, tickers, deferred = 1000, {}, {}
function GetTime() return now end
C_Timer = { After = function() end,
            NewTimer = function(_, fn) table.insert(deferred, fn); return { Cancel = function() for i, f in ipairs(deferred) do if f == fn then table.remove(deferred, i) end end end } end,
            NewTicker = function(_, fn) table.insert(tickers, fn); return { Cancel = function() for i, f in ipairs(tickers) do if f == fn then table.remove(tickers, i) end end end } end }
visible, plates, names = true, {}, { ["0x0000000000000001"] = "Grom" }
function UnitExists(u)
    if string.find(u or "", "^nameplate") then return plates[u] ~= nil end
    return u ~= nil
end
function UnitIsVisible() return visible end
function UnitIsPlayer() return 1 end
deadUnits = {}
function UnitIsDead(u) return deadUnits[u] end
function UnitIsGhost() return nil end
function UnitClass() return "Warrior", "WARRIOR" end
function UnitLevel() return 60 end
function UnitHealth() return 100 end
function UnitHealthMax() return 100 end
function UnitName(u)
    if u == "player" then return "Tester" end
    if plates[u] then return plates[u].name end
    return names[u]
end
function UnitGUID(u)
    if u == "player" then return "0x00000000000000AA" end
    if plates[u] then return plates[u].guid end
    if names[u] then return u end
end
function UnitFactionGroup() return "Alliance" end
function UnitIsFriend() return nil end
function UnitCanAttack() return 1 end
function UnitIsUnit() return nil end
function UnitRace() return "Orc" end
function GetNumRaidMembers() return 0 end
function GetNumPartyMembers() return 0 end
function PlaySound() end
AutoBG_Targets = {
    activeBG = false,
    ResolveClassToken = function(c) return string.upper(c) end,
    GetClassColor = function() return { r = 1, g = 1, b = 1 } end,
    CheckUnitStealth = function() return false end,
    CheckIsStealthSpell = function(id) if id == 1787 then return true, "Stealth", "tex", 0 end return false end,
    CheckIsStealthName = function() return false end,
}
AutoBG_Settings = { Spy = { Enabled = true, SoundAlert = false, StealthAlert = false, Timeout = 30, MaxRows = 5 } }
'''


def runtime():
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(BASE)
    lua.execute(SPY)
    lua.execute('AutoBG_SpyEventFrame.scripts.OnEvent(AutoBG_SpyEventFrame, "PLAYER_LOGIN")')
    lua.execute('AutoBG_Spy:RecordEnemy("Grom", "WARRIOR", 60, "0x0000000000000001", 100, nil, nil, "Orc")')
    lua.execute('AutoBG_Spy:RenderRows()')
    return lua


FLUSH = 'local d = deferred; deferred = {}; for _, fn in ipairs(d) do fn() end'


def advance(lua, seconds):
    for _ in range(seconds):
        lua.execute('now = now + 1; for _, fn in ipairs(tickers) do fn() end; ' + FLUSH)


def fire(lua, *args):
    values = ", ".join(repr(a) if isinstance(a, str) else str(a) for a in args)
    lua.execute('AutoBG_SpyEventFrame.scripts.OnEvent(AutoBG_SpyEventFrame, %s); %s' % (values, FLUSH))


class SpyNearbyTests(unittest.TestCase):
    def test_visible_enemy_stays_listed_without_new_events(self):
        lua = runtime()
        advance(lua, 45)  # longer than the 30 s removal timeout
        self.assertTrue(lua.eval('AutoBG_SpyRow1.shown'))
        self.assertEqual(lua.eval('AutoBG_SpyRow1.targetName'), "Grom")
        self.assertNotEqual(lua.eval('AutoBG_SpyRow1.alpha'), 0.45)

    def test_unseen_enemy_dims_before_removal(self):
        lua = runtime()
        lua.execute('visible = false')
        advance(lua, 8)
        self.assertTrue(lua.eval('AutoBG_SpyRow1.shown'))
        self.assertEqual(lua.eval('AutoBG_SpyRow1.alpha'), 0.45)
        lua.execute('visible = true')
        advance(lua, 1)
        self.assertEqual(lua.eval('AutoBG_SpyRow1.alpha'), 1)

    def test_unseen_enemy_is_removed_after_timeout(self):
        lua = runtime()
        lua.execute('visible = false')
        advance(lua, 32)
        self.assertFalse(lua.eval('AutoBG_SpyRow1.shown'))

    def test_nameplate_scan_lists_a_standing_enemy(self):
        lua = runtime()
        lua.execute('plates.nameplate3 = { guid = "0x0000000000000002", name = "Thrall" }')
        advance(lua, 1)
        self.assertEqual(lua.eval('AutoBG_SpyRow1.targetName'), "Thrall")
        self.assertEqual(lua.eval('AutoBG_SpyRow2.targetName'), "Grom")

    def test_nampower_buff_events_set_and_clear_stealth(self):
        lua = runtime()
        fire(lua, "BUFF_ADDED_OTHER", "0x0000000000000001", 1, 1787, 1, 60, 5, 0)
        self.assertTrue(lua.eval('AutoBG_SpyRow1.targetStealth'))
        fire(lua, "BUFF_REMOVED_OTHER", "0x0000000000000001", 1, 1787, 0, 60, 5, 1)
        self.assertFalse(lua.eval('AutoBG_SpyRow1.targetStealth'))

    def test_unit_died_dims_at_once_and_a_visible_corpse_stays_dim(self):
        lua = runtime()
        lua.execute('deadUnits["0x0000000000000001"] = true')
        fire(lua, "UNIT_DIED", "0x0000000000000001")
        self.assertEqual(lua.eval('AutoBG_SpyRow1.alpha'), 0.45)
        self.assertTrue(lua.eval('AutoBG_SpyRow1.targetDead'))
        advance(lua, 3)
        self.assertEqual(lua.eval('AutoBG_SpyRow1.alpha'), 0.45)
        advance(lua, 30)
        self.assertFalse(lua.eval('AutoBG_SpyRow1.shown'))

    def test_resurrected_enemy_becomes_active_again(self):
        lua = runtime()
        lua.execute('deadUnits["0x0000000000000001"] = true')
        fire(lua, "UNIT_DIED", "0x0000000000000001")
        lua.execute('deadUnits["0x0000000000000001"] = nil')
        advance(lua, 1)
        self.assertEqual(lua.eval('AutoBG_SpyRow1.alpha'), 1)
        self.assertFalse(lua.eval('AutoBG_SpyRow1.targetDead'))

    def test_window_width_does_not_change_when_list_empties(self):
        lua = runtime()
        width = lua.eval('AutoBG_SpyFrame.width')
        lua.execute('AutoBG_Spy:ClearHistory()')
        self.assertEqual(lua.eval('AutoBG_SpyFrame.width'), width)


if __name__ == '__main__':
    unittest.main()
