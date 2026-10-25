"""WSG flag carrier health text: real values when the client has them.

The complete AutoBG_FC.lua file runs under Lua 5.1 with generic widget mocks.
Which units OctoWoW sends real health for remains an in-game check.
"""
from pathlib import Path
import os
import unittest
from lupa.lua51 import LuaRuntime

ROOT = Path(os.environ["VANILLAFORGE_ADDON_ROOT"])
FC = (ROOT / "AutoBG_FC.lua").read_text("utf-8-sig")

BASE = r'''
CLASSIC_API_VERSION, SUPERWOW_VERSION = 11600, "2.2"
local Widget = {}
setmetatable(Widget, { __index = function(_, name)
    if string.find(name, "^%u") then return function() end end
end })
function Widget:SetText(text) self.text = text end
function Widget:SetBackdrop(t) self.backdrop = t end
function Widget:SetScript(kind, fn) self.scripts = self.scripts or {}; self.scripts[kind] = fn end
function Widget:IsShown() return self.shown end
function Widget:Show() self.shown = true end
function Widget:Hide() self.shown = false end
function Widget:CreateTexture() return setmetatable({}, { __index = Widget }) end
function Widget:CreateFontString() return setmetatable({}, { __index = Widget }) end
function CreateFrame(_, name) local f = setmetatable({ name = name }, { __index = Widget }); if name then _G[name] = f end; return f end
UIParent = CreateFrame("Frame", "UIParent")
local handle = { Cancel = function() end }
C_Timer = { NewTicker = function() return handle end }
auraScans = 0
C_UnitAuras = { GetAuraSlots = function() auraScans = auraScans + 1; return nil, 0 end }
function SpellInfo(id) if id == 46392 then return "Focused Assault" end return "Other" end
function GetRealZoneText() return "Warsong Gulch" end
function UnitTokenFromName(name) if name == "Grom" then return "raid3" end end
function UnitExists(u) return u == "raid3" end
function UnitIsPlayer(u) return u == "raid3" end
function UnitName(u) if u == "raid3" then return "Grom" end end
function UnitGUID(u) if u == "raid3" then return "0x00000000000000C3" end end
function UnitDistanceSquared() return 0, false end
hp, maxHp = 3690, 4500
function UnitHealth() return hp end
function UnitHealthMax() return maxHp end
AutoBG_Settings = { FCFrame = true }
'''


def runtime(health, maximum):
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(BASE + 'hp, maxHp = %d, %d' % (health, maximum))
    lua.execute(FC)
    lua.execute('local f = AutoBG_FCEventFrame; f.scripts.OnEvent(f, "CHAT_MSG_BG_SYSTEM_HORDE", "The Horde flag was picked up by Grom!")')
    lua.execute('AutoBG_FC_UpdateVisibility()')
    return lua


class CarrierHealthTests(unittest.TestCase):
    def test_carrier_frames_have_tooltips_backdrop_border(self):
        lua = runtime(3690, 4500)
        self.assertEqual(lua.eval('AutoBG_AllianceFC.backdrop.edgeFile'), "Interface\\Tooltips\\UI-Tooltip-Border")
        self.assertEqual(lua.eval('AutoBG_HordeFC.backdrop.edgeFile'), "Interface\\Tooltips\\UI-Tooltip-Border")

    def test_real_health_is_shown_when_available(self):
        lua = runtime(3690, 4500)
        self.assertEqual(lua.eval('AutoBG_AllianceFC.hpText.text'), "3690 / 4500")

    def test_nampower_fields_are_preferred_over_unithealth(self):
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute(BASE + r'''
            hp, maxHp = 82, 100
            function GetUnitField(unit, field)
                if unit ~= "raid3" then return nil end
                if field == "health" then return 3690 elseif field == "maxHealth" then return 4500 end
                error("invalid field " .. field)
            end
        ''')
        lua.execute(FC)
        lua.execute('local f = AutoBG_FCEventFrame; f.scripts.OnEvent(f, "CHAT_MSG_BG_SYSTEM_HORDE", "The Horde flag was picked up by Grom!")')
        lua.execute('AutoBG_FC_UpdateVisibility()')
        self.assertEqual(lua.eval('AutoBG_AllianceFC.hpText.text'), "3690 / 4500")

    def test_assault_stacks_follow_nampower_debuff_events(self):
        lua = runtime(3690, 4500)
        stacks = 'AutoBG_AllianceFC.debuffText.text'
        debuff = ('arg1, arg3, arg4, arg7 = "0x00000000000000C3", 46392, %d, %d; '
                  'local f = AutoBG_FCEventFrame; f.scripts.OnEvent(f, "%s")')
        lua.execute(debuff % (2, 0, "DEBUFF_ADDED_OTHER"))
        self.assertEqual(lua.eval(stacks), "|cFFFF2020[2]|r")
        lua.execute(debuff % (0, 1, "DEBUFF_REMOVED_OTHER"))
        self.assertEqual(lua.eval(stacks), "")

    def test_auras_are_read_once_per_carrier_not_every_tick(self):
        lua = runtime(3690, 4500)
        lua.execute('for i = 1, 5 do AutoBG_FC_UpdateVisibility() end')
        self.assertEqual(lua.eval('auraScans'), 1)

    def test_live_carrier_returns_after_timer_test_mode(self):
        lua = runtime(3690, 4500)
        lua.execute('AutoBG_Settings.TestAllTimers = true; AutoBG_FC_UpdateVisibility()')
        self.assertIn("Alliance Druid", lua.eval('AutoBG_AllianceFC.nameText.text'))
        lua.execute('AutoBG_Settings.TestAllTimers = false; AutoBG_FC_UpdateVisibility()')
        self.assertEqual(lua.eval('AutoBG_AllianceFC.nameText.text'), "Grom")
        self.assertEqual(lua.eval('AutoBG_AllianceFC.hpText.text'), "3690 / 4500")

    def test_percentage_health_stays_a_percent(self):
        lua = runtime(82, 100)
        self.assertEqual(lua.eval('AutoBG_AllianceFC.hpText.text'), "82%")


if __name__ == '__main__':
    unittest.main()
