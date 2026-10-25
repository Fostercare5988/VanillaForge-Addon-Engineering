"""Player AFK and Deserter state come from ClassicAPI lookups (audit 2026-10-19b, P3-2, P3-3).

The complete AutoBG.lua file runs under Lua 5.1 with generic widget mocks.
Native aura timing and the AFK flag remain in-game checks.
"""
from pathlib import Path
import os
import unittest
from lupa.lua51 import LuaRuntime

ROOT = Path(os.environ["VANILLAFORGE_ADDON_ROOT"])
CORE = (ROOT / "AutoBG.lua").read_text("utf-8-sig")

BASE = r'''
function table.wipe(t) for k in pairs(t) do t[k] = nil end return t end
CLASSIC_API_VERSION, SUPERWOW_VERSION = 11707, "2.2"
flashes = 0; function FlashClientIcon() flashes = flashes + 1 end
function IsInRaid() return nil end; function IsInGroup() return nil end
local Widget = {}
setmetatable(Widget, { __index = function(_, name)
    if string.find(name, "^%u") then return function() end end
end })
function Widget:SetScript(kind, fn) self.scripts = self.scripts or {}; self.scripts[kind] = fn end
function Widget:GetScript(kind) return self.scripts and self.scripts[kind] end
function CreateFrame(_, name) local f = setmetatable({ name = name }, { __index = Widget }); if name then _G[name] = f end; return f end
UIParent = CreateFrame("Frame", "UIParent")
messages = {}
DEFAULT_CHAT_FRAME = { AddMessage = function(_, msg) table.insert(messages, msg) end }
function hooksecurefunc() end
local handle = { Cancel = function() end }
C_Timer = { After = function() end, NewTimer = function() return handle end, NewTicker = function() return handle end }
SlashCmdList = {}
MAX_BATTLEFIELD_QUEUES = 3
function GetBattlefieldStatus() return "none" end
function GetTime() return 1000 end
function GetRealZoneText() return "Orgrimmar" end
function IsInInstance() return nil, "none" end
function UnitExists() return 1 end
function UnitIsDeadOrGhost() return nil end
function GetBattlefieldWinner() return nil end
function PlaySound() end
afk = false
function UnitIsAFK() return afk end
-- Ten harmful auras; the tenth is Deserter.
lookups = { index = 0, name = 0, id = 0 }
local deserter = { name = "Deserter", spellId = 26013, expirationTime = 1300 }
C_UnitAuras = {
    GetAuraDataByIndex = function(_, i)
        lookups.index = lookups.index + 1
        if i < 10 then return { name = "Aura" .. i, spellId = i } elseif i == 10 then return deserter end
    end,
    GetAuraDataBySpellName = function(_, name)
        lookups.name = lookups.name + 1
        if name == "Deserter" then return deserter end
    end,
    GetPlayerAuraBySpellID = function(id)
        lookups.id = lookups.id + 1
        if id == 26013 then return deserter end
    end,
}
'''


def runtime():
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(BASE)
    lua.execute(CORE)
    lua.execute('AutoBGFrame.scripts.OnEvent(AutoBGFrame, "ADDON_LOADED", "AutoBG")')
    return lua


def fire(lua, event, arg=None):
    value = 'nil' if arg is None else repr(arg)
    lua.execute('AutoBGFrame.scripts.OnEvent(AutoBGFrame, "%s", %s)' % (event, value))


class PlayerStateTests(unittest.TestCase):
    def test_afk_follows_the_unit_flag_not_chat_text(self):
        lua = runtime()
        fire(lua, "CHAT_MSG_SYSTEM", "You are now AFK: Away from Keyboard")
        self.assertFalse(lua.eval('AutoBG_IsPlayerAFK()'))
        lua.execute('afk = true')
        self.assertTrue(lua.eval('AutoBG_IsPlayerAFK()'))

    def test_one_aura_change_needs_no_per_aura_scan(self):
        lua = runtime()
        lua.execute('lookups = { index = 0, name = 0, id = 0 }')
        # The client raises both events for one change to the player's auras.
        fire(lua, "UNIT_AURA", "player")
        fire(lua, "PLAYER_AURAS_CHANGED")
        self.assertEqual(lua.eval('lookups.index'), 0)
        self.assertLessEqual(lua.eval('lookups.name + lookups.id'), 1)

    def test_deserter_is_still_found_with_its_remaining_time(self):
        lua = runtime()
        has, remaining = lua.eval('AutoBG_HasDeserter()')
        self.assertTrue(has)
        self.assertEqual(remaining, 300)


if __name__ == '__main__':
    unittest.main()
