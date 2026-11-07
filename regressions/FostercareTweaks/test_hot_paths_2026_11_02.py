"""FostercareTweaks audit, second pass of 2026-11-02 (1.15.0 -> 1.16.0): hot paths.

- Watched auras built each icon's key with gsub on every aura change.
- Raid aura candidates dropped their tables whenever a member lost an aura.
- The debuff rows re-anchored every icon on every update, a layout left from
  the retired larger armor debuffs.
- Every Shift, Ctrl or Alt press touched every frame mover.
- The player's power text was formatted again on each update.
- Chat lines with a dot or a colon ran the URL patterns.
- Event paths made a new timer callback per event; tooltip events a table.
- Comments named DLL versions (VANILLAFORGE.md section 7).

Every test fails on 1.15.0 (a798dc8). The look of the rows stays an in-game check.
"""
import re
import unittest
from pathlib import Path

from wowlua import LuaRuntime

from test_audit_2026_10_25 import BASE as HEALTH_BASE
from test_audit_2026_10_26 import ROOT, runtime
from test_aura_delta_2026_10_27 import AURAS, RAID, between, source
from test_minimap_movers_2026_11_01 import SETUP as MOVERS
from test_watched_auras_2026_11_02 import watched

WIDGET = r'''
local W = {}
W.__index = function(t, k) return rawget(W, k) or (string.find(k, "^%u") and function() end) or nil end
function W:Show() self.shown = true end
function W:Hide() self.shown = false end
function W:IsShown() return self.shown end
function W:SetTexture(t) self.texture = t end
function W:SetText(t) self.text = t end
function W:GetID() return self.id end
function W:SetWidth(w) self.width = w end
function W:SetHeight(h) self.height = h end
function W:GetWidth() return self.width or 20 end
function W:ClearAllPoints() clears = (clears or 0) + 1 end
function Widget(t) return setmetatable(t or {}, W) end
'''


class WatchedKeysAreBuiltOnce(unittest.TestCase):
    def test_an_aura_change_builds_no_key(self):
        lua = watched()
        lua.execute(r'''
            W.Add("Envenom", "player"); W.Add("Rupture", "target")
            local gsub, n = string.gsub, 0
            string.gsub = function(...) n = n + 1; return gsub(...) end
            W.Update("player"); W.Update("target")
            string.gsub = gsub
            gsubs = n
        ''')
        self.assertEqual(lua.eval("gsubs"), 0)


class RaidAuraCandidatesAreKept(unittest.TestCase):
    def test_a_lost_aura_keeps_its_table_for_the_next(self):
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute(r'''
            n = 3
            C_UnitAuras = {
                GetAuraSlots = function(unit, f, max, tok, buf) for i = 1, n do buf[i] = i end return nil, n end,
                UnitAuraBySlot = function(unit, slot) return "A" .. slot, "icon", 1, nil, 0, 0, nil, nil, nil, slot end,
            }
            function UnitIsUnit() return false end
            btn = { unit = "raid1", buffCandidates = {}, buffSlots = {}, buffPool = {} }
        ''')
        lua.execute(between(RAID, "local HOT_NAMES", "function UF:GetRaidBuffSettings")
                    + between(RAID, "local function AuraPriority", "local function LayoutRaidText")
                    + "\n_G.ReadRaidAuras = ReadRaidAuras")
        lua.execute(r'''
            ReadRaidAuras(btn, "buff", true)
            local before = {}
            for _, a in ipairs(btn.buffCandidates) do before[a] = true end
            n = 1; ReadRaidAuras(btn, "buff", true)
            n = 3; ReadRaidAuras(btn, "buff", true)
            kept = 0
            for _, a in ipairs(btn.buffCandidates) do if before[a] then kept = kept + 1 end end
        ''')
        self.assertEqual(lua.eval("#btn.buffCandidates"), 3)
        self.assertEqual(lua.eval("kept"), 3)


class DebuffRowsKeepTheirAnchors(unittest.TestCase):
    def test_an_update_moves_no_icon(self):
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute(WIDGET + r'''
            FostercareTweaks_Config = { unitframe_positions = {} }
            FT = {}
            Auras = {}
            local function Btn(on) return Widget({ isOccupied = on, border = Widget() }) end
            parent = Widget()
            container = Widget({ options = { perRow = 8, spacing = 3 }, debuffFrame = Widget(),
                debuffButtons = { Btn(true), Btn(true), Btn(false) }, debuffSize = 20 })
            function container:GetParent() return parent end
        ''')
        lua.execute(between(AURAS, "local function HasSavedPosition", "function Auras:AttachToTargetFrame"))
        lua.execute("Auras:LayoutContainer(container); clears = 0; Auras:LayoutContainer(container)")
        self.assertEqual(lua.eval("clears"), 0)
        self.assertEqual(lua.eval("container.debuffFrame.width"), 43)      # two icons and a gap
        self.assertEqual(lua.eval("container.debuffFrame.height"), 20)


class MoversWaitForCtrlShift(unittest.TestCase):
    def test_other_modifier_keys_touch_no_mover(self):
        lua = runtime()
        lua.execute(MOVERS)
        lua.execute(source("mods/move-unitframes.lua"))
        lua.execute(r'''
            icon = Widget({ shown = true })
            FT.RegisterFrameMover(icon, "watch_player_Envenom", "Envenom")
            local mover = icon.fctMover
            hides = 0
            local hide = mover.Hide
            mover.Hide = function(self) hides = hides + 1; return hide(self) end
            FT.UpdateFrameMovers(); FT.UpdateFrameMovers()
        ''')
        self.assertEqual(lua.eval("hides"), 0)
        self.assertFalse(lua.eval("icon.fctMover:IsShown()"))
        lua.execute("keys = true; FT.UpdateFrameMovers()")
        self.assertTrue(lua.eval("icon.fctMover:IsShown()"))
        lua.execute("keys = false; FT.UpdateFrameMovers()")
        self.assertFalse(lua.eval("icon.fctMover:IsShown()"))

    def test_a_mover_made_while_keys_are_up_starts_hidden(self):
        lua = runtime()
        lua.execute(MOVERS)
        lua.execute(source("mods/move-unitframes.lua"))
        lua.execute('FT.UpdateFrameMovers(); icon = Widget({ shown = true }); FT.RegisterFrameMover(icon, "k", "K")')
        self.assertFalse(lua.eval("icon.fctMover:IsShown()"))


class PowerTextIsFormattedOnce(unittest.TestCase):
    def test_the_same_value_is_not_formatted_again(self):
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute(HEALTH_BASE + "abbrevs = 0; function AbbreviateNumbers(v) abbrevs = abbrevs + 1; return tostring(v) end")
        lua.execute(source("mods/health-numbers.lua"))
        lua.execute(r'''
            FT.module:enable()
            hooks.TextStatusBar_UpdateTextString(PlayerFrameManaBar)
            PlayerFrameManaBar.TextString.text = "100 / 100"          -- the game's own redraw
            hooks.TextStatusBar_UpdateTextString(PlayerFrameManaBar)
        ''')
        self.assertEqual(lua.eval("PlayerFrameManaBar.TextString.text"), "100")
        self.assertEqual(lua.eval("abbrevs"), 1)


class ChatLinesWithoutLinks(unittest.TestCase):
    def chat(self):
        lua = runtime()
        lua.execute(r'''
            NUM_CHAT_WINDOWS = 1
            lines = {}
            function FT.IsCombatChatFrame() return false end
            ChatFrame1 = { AddMessage = function(_, text) lines[#lines + 1] = text end }
        ''')
        lua.execute(source("mods/chat-tweaks.lua"))
        lua.execute('FT.mods["Chat Hyperlinks"]:enable()')
        return lua

    def test_a_channel_line_runs_no_url_pattern(self):
        lua = self.chat()
        lua.execute(r'''
            local gsub, n = string.gsub, 0
            string.gsub = function(...) n = n + 1; return gsub(...) end
            ChatFrame1:AddMessage("[1. General] [Bob]: see you at 5. ok")
            string.gsub = gsub
            calls = n
        ''')
        self.assertEqual(lua.eval("lines[1]"), "[1. General] [Bob]: see you at 5. ok")
        self.assertEqual(lua.eval("calls"), 0)

    def test_links_still_become_copyable(self):
        lua = self.chat()
        lua.execute('ChatFrame1:AddMessage("[Bob]: www.example.com or http://x and a@b.de")')
        line = lua.eval("lines[1]")
        for link in ("|Hurl:www.example.com|h", "|Hurl:http://x|h", "|Hurl:a@b.de|h"):
            self.assertIn(link, line)


class OneCallbackPerTimer(unittest.TestCase):
    # A C_Timer.After with a new function on each event is garbage on that path.
    def test_event_paths_reuse_their_timer_callback(self):
        for name in ("mods/unitframe-energytick.lua", "mods/target-castbar.lua", "mods/equip-compare.lua",
                     "mods/item-colors.lua", "mods/standard-player-auras.lua"):
            self.assertIsNone(re.search(r"C_Timer\.After\([^\n]*function\(", source(name)), name)

    def test_tooltip_events_build_no_table(self):
        src = source("mods/vendor-values.lua")
        handler = src[src.index("GET_ITEM_INFO_RECEIVED"):src.index("hooksecurefunc(ItemRefTooltip")]
        self.assertNotIn("{", handler)
        self.assertNotIn('.. ":" ..', src)


class NoVersionsInTheCode(unittest.TestCase):
    def test_comments_name_no_dll_version(self):
        for path in sorted(Path(ROOT).rglob("*.lua")):
            text = path.read_text("utf-8-sig")
            self.assertIsNone(re.search(r"(ClassicAPI|SuperWoW|NamPower)[^\n]{0,12}\d+\.\d+", text), path.name)


if __name__ == "__main__":
    unittest.main()
