"""AutoBG.lua queue, notification and scoreboard regressions (P1-1, P2-1, P2-2).

The complete AutoBG.lua file runs under Lua 5.1 with generic widget mocks.
Native AcceptBattlefieldPort flag handling, taskbar flashing and scoreboard
drawing remain in-game checks.
"""
from pathlib import Path
import os
import re
import unittest
from lupa.lua51 import LuaRuntime

ROOT = Path(os.environ["VANILLAFORGE_ADDON_ROOT"])
CORE = (ROOT / "AutoBG.lua").read_text("utf-8-sig")
FRAMEXML = Path(__file__).resolve().parents[2] / ".private" / "framexml" / "Interface" / "FrameXML"

BASE = r'''
function table.wipe(t) for k in pairs(t) do t[k] = nil end return t end
CLASSIC_API_VERSION, SUPERWOW_VERSION = 11707, "2.2"
flashes = 0; function FlashClientIcon() flashes = flashes + 1 end
function IsInRaid() return nil end; function IsInGroup() return nil end
local Widget = {}
setmetatable(Widget, { __index = function(_, name)
    if string.find(name, "^%u") then return function() end end
end })
function Widget:SetText(text) self.text = text end
function Widget:GetText() return self.text end
function Widget:SetScript(kind, fn) self.scripts = self.scripts or {}; self.scripts[kind] = fn end
function Widget:GetScript(kind) return self.scripts and self.scripts[kind] end
function Widget:IsShown() return self.shown end
function Widget:Show() self.shown = true end
function Widget:Hide() self.shown = false end
function CreateFrame(_, name) local f = setmetatable({ name = name }, { __index = Widget }); if name then _G[name] = f end; return f end
function NewWidget(name) return CreateFrame("Frame", name) end
UIParent = CreateFrame("Frame", "UIParent")
messages, ports, hooks = {}, {}, {}
DEFAULT_CHAT_FRAME = { AddMessage = function(_, msg) table.insert(messages, msg) end }
function hooksecurefunc(name, fn) hooks[name] = fn end
local timerObject = { Cancel = function() end }
C_Timer = { After = function() end,
            NewTimer = function() return timerObject end,
            NewTicker = function() return timerObject end }
C_UnitAuras = { GetAuraDataByIndex = function() return nil end }
SlashCmdList = {}
MAX_BATTLEFIELD_QUEUES = 3
statuses = {}
function GetBattlefieldStatus(i) local s = statuses[i]; if s then return s[1], s[2] end; return "none" end
function AcceptBattlefieldPort(id, accept) table.insert(ports, { id = id, accept = accept }) end
function GetTime() return 1000 end
function GetRealZoneText() return "Orgrimmar" end
function IsInInstance() return nil, "none" end
function UnitIsAFK() return nil end
function UnitExists() return 1 end
function UnitIsDeadOrGhost() return nil end
function UnitName() return "Tester" end
function GetBattlefieldWinner() return nil end
function GetNumBattlefieldScores() return 0 end
function GetBattlefieldScore() return nil end
function PlaySound() end
function StaticPopup_Hide() end
'''


def runtime(extra=""):
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(BASE + extra)
    lua.execute(CORE)
    lua.execute('AutoBGFrame.scripts.OnEvent(AutoBGFrame, "ADDON_LOADED", "AutoBG")')
    return lua


class CancelQueueTests(unittest.TestCase):
    """P1-1: Blizzard leaves a queue with AcceptBattlefieldPort(i, nil)."""

    def test_cancel_declines_with_nil_flag_like_framexml(self):
        lua = runtime()
        lua.execute('statuses[1] = { "queued", "Warsong Gulch" }; AutoBG_CancelAllQueues()')
        self.assertEqual(lua.eval('#ports'), 1)
        # 0 is true in Lua; any native that reads the flag as a boolean would accept.
        self.assertTrue(lua.eval('ports[1].accept == nil or ports[1].accept == false'),
                        "cancel passed a truthy flag: %r" % lua.eval('ports[1].accept'))

    def test_framexml_leave_queue_passes_nil(self):
        source = FRAMEXML / "BattlefieldFrame.lua"
        if not source.exists():
            self.skipTest("run tools/extract_framexml.py --file Interface\\FrameXML\\BattlefieldFrame.lua")
        text = source.read_text("latin-1")
        block = re.search(r"info\.text = LEAVE_QUEUE;(.*?)UIDropDownMenu_AddButton", text, re.S)
        self.assertIsNotNone(block)
        self.assertIn("AcceptBattlefieldPort", block.group(1))
        self.assertIn("info.arg2 = nil", block.group(1))


class TaskbarFlashTests(unittest.TestCase):
    """ClassicAPI 1.17.7 FlashClientIcon flashes the taskbar on a queue pop."""

    def pop(self, lua):
        lua.execute('statuses[1] = { "confirm", "Warsong Gulch" }')
        lua.execute('AutoBGFrame.scripts.OnEvent(AutoBGFrame, "UPDATE_BATTLEFIELD_STATUS")')

    def test_queue_pop_flashes_the_taskbar(self):
        lua = runtime('')
        self.pop(lua)
        self.assertEqual(lua.eval('flashes'), 1)

    def test_flash_respects_setting_off(self):
        lua = runtime('')
        lua.execute('AutoBG_Settings.FlashTaskbar = false')
        self.pop(lua)
        self.assertEqual(lua.eval('flashes'), 0)


class ScoreboardColorTests(unittest.TestCase):
    """P2-1: the scoreboard name FontString is WorldStateScoreButton<i>NameButtonName."""

    def test_class_color_reaches_framexml_name_fontstring(self):
        lua = runtime(r'''
            MAX_WORLDSTATE_SCORE_BUTTONS = 22
            nameText = NewWidget("WorldStateScoreButton1NameButtonName")
            function GetNumBattlefieldScores() return 1 end
            function GetBattlefieldScore(i)
                if i == 1 then return "Grom", 1, 1, 1, 1, 0, 0, "Orc", "Warrior" end
            end
        ''')
        lua.execute('hooks.WorldStateScoreFrame_Update()')
        self.assertEqual(lua.eval('nameText.text'), "|cffc79c6eGrom|r")

    def test_framexml_defines_that_fontstring(self):
        source = FRAMEXML / "WorldStateFrame.xml"
        if not source.exists():
            self.skipTest("run tools/extract_framexml.py --file Interface\\FrameXML\\WorldStateFrame.xml")
        text = source.read_text("latin-1")
        template = re.search(r'<Frame name="WorldStateScoreTemplate".*?</Frame>\s*</Ui>|<Frame name="WorldStateScoreTemplate".*', text, re.S).group(0)
        self.assertRegex(template, r'<Frame name="\$parentNameButton"[\s\S]*?<FontString name="\$parentName"')
        self.assertNotIn('name="$parentNameText"', template)


if __name__ == '__main__':
    unittest.main()
