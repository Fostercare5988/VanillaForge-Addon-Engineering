"""Every Auto-Queue choice must reach a native OctoWoW queue type (audit 2026-10-19b, P2-1).

Blood Ring had no OctoWoW queue type and was removed on 2026-10-20.

OctoWoW's FrameXML Minimap.lua defines JoinBattlegroundQueue(bgType) and offers
the types "Warsong", "Arathi", "ThornGorge" and "Alterac". The complete
AutoBG.lua file runs under Lua 5.1 with generic widget mocks; the server's
handling of the queue message remains an in-game check.
"""
from pathlib import Path
import os
import re
import unittest
from lupa.lua51 import LuaRuntime

ROOT = Path(os.environ["VANILLAFORGE_ADDON_ROOT"])
CORE = (ROOT / "AutoBG.lua").read_text("utf-8-sig")
FRAMEXML = Path(__file__).resolve().parents[2] / ".private" / "framexml" / "Interface" / "FrameXML"
NATIVE_TYPES = {"Warsong", "Arathi", "ThornGorge", "Alterac"}

BASE = r'''
function table.wipe(t) for k in pairs(t) do t[k] = nil end return t end
CLASSIC_API_VERSION, SUPERWOW_VERSION = 11707, "2.2"
local Widget = {}
setmetatable(Widget, { __index = function(_, name)
    if string.find(name, "^%u") then return function() end end
end })
function Widget:SetScript(kind, fn) self.scripts = self.scripts or {}; self.scripts[kind] = fn end
function Widget:GetScript(kind) return self.scripts and self.scripts[kind] end
function CreateFrame(_, name) local f = setmetatable({ name = name }, { __index = Widget }); if name then _G[name] = f end; return f end
UIParent = CreateFrame("Frame", "UIParent")
DEFAULT_CHAT_FRAME = { AddMessage = function() end }
function hooksecurefunc() end
local handle = { Cancel = function() end }
C_Timer = { After = function() end, NewTimer = function() return handle end, NewTicker = function() return handle end }
C_UnitAuras = { GetAuraDataByIndex = function() return nil end,
                GetAuraDataBySpellName = function() return nil end,
                GetPlayerAuraBySpellID = function() return nil end }
SlashCmdList = {}
MAX_BATTLEFIELD_QUEUES = 3
function GetBattlefieldStatus() return "none" end
function GetTime() return 1000 end
function GetRealZoneText() return "Orgrimmar" end
function IsInInstance() return nil, "none" end
function UnitIsAFK() return nil end
function UnitExists() return 1 end
function UnitIsDeadOrGhost() return nil end
function PlaySound() end
queued = {}
function JoinBattlegroundQueue(bgType) table.insert(queued, bgType) end
'''


class QueueTypeTests(unittest.TestCase):
    def test_every_selectable_battleground_reaches_a_native_queue_type(self):
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute(BASE)
        lua.execute(CORE)
        lua.execute('AutoBGFrame.scripts.OnEvent(AutoBGFrame, "ADDON_LOADED", "AutoBG")')
        lua.execute('''
            for _, key in ipairs({ "AutoQueue_WSG", "AutoQueue_AB", "AutoQueue_AV", "AutoQueue_BR" }) do
                AutoBG_Settings[key] = true
            end
            unreached = {}
            for _, bg in ipairs(AutoBG_GetSelectedBGs()) do
                local before = #queued
                AutoBG_TriggerBattlegroundFinder(bg)
                if #queued == before then table.insert(unreached, bg) end
            end
        ''')
        unreached = list(lua.eval('unreached').values())
        self.assertEqual(unreached, [], "these choices never reach JoinBattlegroundQueue")
        self.assertTrue(set(lua.eval('queued').values()) <= NATIVE_TYPES)

    def test_old_blood_ring_setting_is_cleared_on_load(self):
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute(BASE)
        lua.execute('AutoBG_Settings = { AutoQueue_BR = true }')
        lua.execute(CORE)
        lua.execute('AutoBGFrame.scripts.OnEvent(AutoBGFrame, "ADDON_LOADED", "AutoBG")')
        self.assertIsNone(lua.eval('AutoBG_Settings.AutoQueue_BR'))

    def test_framexml_queue_types(self):
        source = FRAMEXML / "Minimap.lua"
        if not source.exists():
            self.skipTest("run tools/extract_framexml.py --file Interface\\FrameXML\\Minimap.lua")
        text = source.read_text("latin-1")
        self.assertIn("function JoinBattlegroundQueue(bgType)", text)
        found = set(re.findall(r'info\.func = JoinBattlegroundQueue\s+info\.arg1 = "(\w+)"', text))
        self.assertEqual(found, NATIVE_TYPES)


if __name__ == '__main__':
    unittest.main()
