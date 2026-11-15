"""FostercareTweaks audit, 2026-11-15 (1.21.1 -> 1.22.0): the bugs.

* Inspect borders read the target's gear, whoever was inspected. The party
  menu inspects a member who need not be the target (UnitPopup.lua PARTY menu,
  Blizzard_InspectUI.lua InspectFrame_Show sets InspectFrame.unit), so their
  slots showed the target's qualities or none.
* ClassicAPI's timers swallow a callback's error (API.md C_Timer.After:
  "caught (via lua_pcall) and silently swallowed"): a broken roster rebuild,
  refresh or label never reached !ErrorLog, so the player could not report it.
  Every timer callback is now made with FT.Guarded.

Fails on d1b8c9e.
"""
import os
import re
import unittest
from pathlib import Path

import ft_env

ROOT = Path(os.environ["VANILLAFORGE_ADDON_ROOT"])

# ClassicAPI's timers: an error in a callback goes nowhere (API.md C_Timer.After).
SWALLOWING_TIMERS = r'''
local after, ticker = C_Timer.After, C_Timer.NewTicker
C_Timer.After = function(s, fn) after(s, function(t) pcall(fn, t) end) end
C_Timer.NewTicker = function(s, fn, n) return ticker(s, function(t) pcall(fn, t) end, n) end
'''

ITEMS = r'''
NUM_CONTAINER_FRAMES, MAX_CONTAINER_ITEMS, NUM_BANKGENERIC_SLOTS = 1, 1, 1
function Widget:SetBackdropBorderColor(r, g, b) self.borderColor = { r, g, b } end
-- The kit answers capitalised fields with a function; the module reads these two.
local create = CreateFrame
function CreateFrame(...) local w = create(...); w.FCTweaks_border, w.FostercareTweaks_border = false, false; return w end
quality = { ["item:100"] = 4, ["item:200"] = 2, ["item:300"] = 3 }
gear = { party1 = { [1] = "item:100" }, target = { [1] = "item:200" }, player = {} }
function GetInventoryItemLink(unit, id) return gear[unit] and gear[unit][id] end
function GetInventoryItemQuality() return nil end
function GetContainerItemLink() return nil end
function GetItemQualityColor(q) return q / 10, 0, 0 end
C_Item = { GetItemQualityByID = function(id) return quality["item:" .. id] end }
C_Container = { GetContainerItemInfo = function() return nil end }
function ContainerFrame_OnShow() end
function InspectPaperDollItemSlotButton_Update() end
CharacterFrame = CreateFrame("Frame", "CharacterFrame"); CharacterFrame:Hide()
BankFrame = CreateFrame("Frame", "BankFrame"); BankFrame:Hide()
ContainerFrame1 = CreateFrame("Frame", "ContainerFrame1"); ContainerFrame1:Hide()
CreateFrame("Button", "ContainerFrame1Item1", ContainerFrame1)
CreateFrame("Button", "BankFrameItem1")
for i = 0, 3 do CreateFrame("Button", "CharacterBag" .. i .. "Slot") end
InspectFrame = CreateFrame("Frame", "InspectFrame"); InspectFrame:Hide()
CreateFrame("Button", "InspectHeadSlot", InspectFrame)
CreateFrame("Button", "CharacterHeadSlot", CharacterFrame)
Blizzard_InspectUI = true -- loaded: the module hooks it at once
'''


def items_world():
    lua = ft_env.world([], SWALLOWING_TIMERS + ITEMS)
    ft_env.wowkit.load_files(lua, ROOT, ["mods/item-colors.lua"], "FostercareTweaks")
    return ft_env.start(lua)


class InspectBorders(unittest.TestCase):
    def border(self, lua):
        return lua.eval("InspectHeadSlot.FCTweaks_border.borderColor and InspectHeadSlot.FCTweaks_border.borderColor[1]")

    def test_a_party_member_inspected_from_the_menu_shows_their_gear(self):
        lua = items_world()
        lua.execute('InspectFrame.unit = "party1"; InspectFrame:Show()')
        self.assertAlmostEqual(self.border(lua), 0.4)        # epic, party1's helm

    def test_the_slot_update_redraws_the_inspected_unit(self):
        lua = items_world()
        lua.execute('InspectFrame.unit = "party1"; InspectFrame:Show()')
        lua.execute('gear.party1[1] = "item:300"; InspectPaperDollItemSlotButton_Update(); step(0)')
        self.assertAlmostEqual(self.border(lua), 0.3)

    def test_a_timer_error_reaches_the_error_handler(self):
        lua = items_world()
        lua.execute('CharacterFrame:Show(); function GetInventoryItemQuality() error("quality broke") end')
        lua.execute('fire("GET_ITEM_INFO_RECEIVED", 100, true); step(0)')
        found = [e for e in lua.eval("errors").values() if "quality broke" in e]
        self.assertEqual(len(found), 1)


class TimerCallbacksAreGuarded(unittest.TestCase):
    CALL = re.compile(r"C_Timer\.(?:After|NewTicker|NewTimer)\(([^,]+),\s*(FT\.Guarded\(|[A-Za-z_][\w.]*)")

    def test_guarded_reports_and_returns(self):
        lua = ft_env.world([], SWALLOWING_TIMERS)
        lua.execute('C_Timer.After(0, FT.Guarded(function() error("late") end)); step(0)')
        self.assertEqual(len(lua.eval("errors")), 1)

    def test_no_timer_takes_an_unguarded_callback(self):
        files = [p for p in ROOT.rglob("*.lua") if "ForgeUI" not in p.name and "ForgeLayout" not in p.name]
        checked = 0
        for path in files:
            text = path.read_text("utf-8-sig")
            for match in self.CALL.finditer(text):
                name = match.group(2)
                checked += 1
                if name == "FT.Guarded(":
                    continue
                short = name.split(".")[-1]
                guarded = re.search(r"\b%s\s*=\s*FT\.Guarded\(" % re.escape(short), text)
                self.assertIsNotNone(guarded, "%s: %s" % (path.name, name))
        self.assertGreater(checked, 10)


class EventsReadTheEngineGlobals(unittest.TestCase):
    """The old wrapper guessed the dispatch by the first argument's type; the
    engine sets `event` and `arg1`... for every handler either way (API.md,
    SetModernScriptArgs), so they are read directly. Class tokens come as
    tokens from every source, so NormalizeClass went too."""

    def test_a_handler_gets_the_event_and_its_arguments(self):
        lua = ft_env.world()
        lua.execute('''f = CreateFrame("Frame"); f:RegisterEvent("UNIT_HEALTH")
            FT.SetEventHandler(f, function(frame, ev, unit, a2) got = { frame == f, ev, unit, a2 } end)
            fire("UNIT_HEALTH", "raid3", 7)''')
        self.assertEqual(list(lua.eval("got").values()), [True, "UNIT_HEALTH", "raid3", 7])

    def test_the_guessing_helpers_are_gone(self):
        for path in ROOT.rglob("*.lua"):
            text = path.read_text("utf-8-sig")
            for gone in ("EventArgs", "NormalizeClass"):
                self.assertNotIn(gone, text, path.name)


CHAT = r'''
NUM_CHAT_WINDOWS = 1
ChatFrame1 = CreateFrame("ScrollingMessageFrame", "ChatFrame1")
stockWheel = function() end
ChatFrame1:SetScript("OnMouseWheel", stockWheel)  -- ChatFrame.xml; ChatFrame_OnLoad enables the wheel
ChatFrameEditBox = CreateFrame("EditBox", "ChatFrameEditBox")
function ChatFrameEditBox:SetAltArrowKeyMode(on) self.altArrows = on end
function SetItemRef() end
'''


class ChatLeavesTheWheelToTheGame(unittest.TestCase):
    """The client's chat windows scroll with the wheel (ChatFrame.lua: Shift to
    the top or bottom, Alt four lines); Chat Tweaks replaced that handler with
    one that dropped Alt, and needed a reload to switch."""

    def world(self):
        lua = ft_env.world(["mods/chat-tweaks.lua"], CHAT)
        return ft_env.start(lua)

    def test_the_stock_wheel_stays(self):
        lua = self.world()
        self.assertTrue(lua.eval("ChatFrame1.scripts.OnMouseWheel == stockWheel"))

    def test_the_arrow_keys_switch_live(self):
        lua = self.world()
        self.assertFalse(lua.eval("ChatFrameEditBox.altArrows"))
        lua.execute('FT.mods["Chat Tweaks"]:apply(false)')
        self.assertTrue(lua.eval("ChatFrameEditBox.altArrows"))


class BorderlessCastbarsLive(unittest.TestCase):
    def test_off_puts_the_stock_art_back(self):
        lua = ft_env.world([], r'''
            CastingBarFrame = CreateFrame("StatusBar", "CastingBarFrame")
            CastingBarBorder, CastingBarFlash = CreateFrame("Texture"), CreateFrame("Texture")
            function CastingBarBorder:SetTexture(t) self.tex = t or "none" end
            CastingBarFlash.SetTexture = CastingBarBorder.SetTexture
            function UIParent_ManageFramePositions() end''')
        lua.execute("function FT.RestoreFramePosition() end; function FT.RegisterFrameMover() end")
        ft_env.wowkit.load_files(lua, ROOT, ["mods/player-castbar.lua"], "FostercareTweaks")
        lua.execute('FostercareTweaks_Config = { ["Borderless Castbars"] = 1 }')
        ft_env.start(lua)
        self.assertEqual(lua.eval("CastingBarBorder.tex"), "none")
        lua.execute('FT.mods["Borderless Castbars"]:apply(false)')
        self.assertEqual(lua.eval("CastingBarBorder.tex"), "Interface\\CastingBar\\UI-CastingBar-Border")
        self.assertEqual(lua.eval("CastingBarFlash.tex"), "Interface\\CastingBar\\UI-CastingBar-Flash")


if __name__ == "__main__":
    unittest.main()
