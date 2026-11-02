"""FostercareTweaks audit, 2026-11-01 (passes 1-5, .private/audit-FostercareTweaks-2026-11-01.md).

- DLLs are checked as loaded, never by version (VANILLAFORGE.md section 7):
  Core.lua refused SuperWoW below "2.2" and the energy ticks skipped NamPower's
  SPELL_ENERGIZE_ON_SELF without a version function; the TOC and README named
  versions.
- A module that fails to start reached only the chat frame (pcall); it now
  reaches the error handler (!ErrorLog) with its stack, and the rest start.
- Class colors repainted the player, target, party and three health bars on
  every target and party change; native health bars are always green and the
  target and party hooks already follow those changes.
- Blizzard Aura Controls and the timestamp style had no control in the window.
- Hot paths: every player or target aura update built a table; every bag
  update built one per slot; every chat line ran six CLINK patterns; every
  power change rewrote the energy tick's widgets.
- Polling: Equip Compare watched the tooltip every 0.1 s while Shift was held
  (OnTooltipSetItem reports every item); the clock woke every second.
- Reduced Actionbar moved the bottom bars on every frame-position pass even
  while custom layouts own them (ActionBars.lua moved them straight back).

Each test fails on 9d2429e..ba4d058 code unless marked as a control. Widget
mocks count calls; they prove our writes, not the engine's drawing.
"""
from pathlib import Path
import os
import re
import unittest
from lupa.lua51 import LuaRuntime

from test_audit_2026_10_26 import runtime, source
from test_unitframe_hot_paths import slice

ROOT = Path(os.environ["VANILLAFORGE_ADDON_ROOT"])

CORE_PRELUDE = r'''
    CLASSIC_API_VERSION, SUPERWOW_VERSION = 11811, "%s"
    handled = {}
    function geterrorhandler() return function(e) handled[#handled + 1] = e; return e end end
    function SetCVar() end
    function CreateFrame() return { RegisterEvent = function() end, SetScript = function() end } end
    SlashCmdList = {}
    function GetScreenWidth() return 1920 end
    function GetScreenHeight() return 1080 end
    FostercareTweaks_Config = { overwrites = {} }
'''


def core(version="2.2"):
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(CORE_PRELUDE % version)
    lua.execute(source("Core.lua") + "\nif FostercareTweaks then FostercareTweaks.ActionBars = { Initialize = function() end } end")
    return lua


class DllsCheckedAsLoaded(unittest.TestCase):
    def test_any_superwow_version_loads(self):
        # UPSTREAM_VERSIONS.json holds the minimum; the addon only checks it is there.
        self.assertIsNotNone(core("1.5").eval("FostercareTweaks"))

    def test_missing_superwow_still_stops_the_addon(self):
        # Control: passes on the old code too.
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute((CORE_PRELUDE % "x").replace('SUPERWOW_VERSION = 11811, "x"', 'SUPERWOW_VERSION = 11811, nil'))
        lua.execute(source("Core.lua") + "\nif FostercareTweaks then FostercareTweaks.ActionBars = { Initialize = function() end } end")
        self.assertIsNone(lua.eval("FostercareTweaks"))

    def test_toc_and_readme_name_no_dll_version(self):
        for name in ("FostercareTweaks.toc", "README.md"):
            text = source(name)
            self.assertIsNone(re.search(r"(SuperWoW|NamPower|UnitXP SP3)\**\s+v?\d", text), name)

    def test_energy_ticks_hear_nampower_without_a_version_check(self):
        lua = runtime()
        lua.execute(source("mods/unitframe-energytick.lua"))
        lua.execute('PlayerFrameManaBar.GetEffectiveScale = function() return 1 end')
        lua.execute('FT.mods["Show Energy Ticks"]:enable()')
        self.assertTrue(lua.eval('FCTweaksEnergyTick.events.SPELL_ENERGIZE_ON_SELF'))
        self.assertNotIn("GetNampowerVersion", source("mods/unitframe-energytick.lua"))


class ModuleErrorsReachTheErrorHandler(unittest.TestCase):
    def test_a_failing_module_is_reported_and_the_rest_start(self):
        lua = core()
        lua.execute('''
            started = false
            FostercareTweaks:register({ title = "Broken", enabled = true, enable = function() error("boom") end })
            FostercareTweaks:register({ title = "Fine", enabled = true, enable = function(self) started = self.title end })
            FostercareTweaks:Initialize()
        ''')
        self.assertEqual(lua.eval("#handled"), 1)
        self.assertIn("boom", lua.eval("handled[1]"))
        self.assertEqual(lua.eval("started"), "Fine")


class ClassColorsFollowTheHooks(unittest.TestCase):
    def setUp(self):
        self.lua = runtime()
        self.lua.execute(r'''
            healthWrites = 0
            local function Bar() local b = Widget(); b.SetStatusBarColor = function() healthWrites = healthWrites + 1 end; return b end
            PlayerFrameHealthBar, TargetFrameHealthBar = Bar(), Bar()
            PartyMemberFrame1HealthBar = Bar()
            TargetFrameNameBackground = Widget()
            MAX_PARTY_MEMBERS = 4
            RAID_CLASS_COLORS = {}
            function UnitClass() return "Rogue", "ROGUE" end
            function UnitIsPlayer() return true end
            function FT.NormalizeClass(c) return c end
            TargetFrame_CheckFaction, TargetFrame_Update, PlayerFrame_Update, PartyMemberFrame_UpdateMember = NOOP, NOOP, NOOP, NOOP
            FT.UnitFrames = { ClassColors = { ROGUE = { r = 1, g = 0.96, b = 0.41 } } }
        ''')
        self.lua.execute(source("mods/unitframes-classcolor.lua"))
        self.lua.execute('FT.mods["Unit Frame Class Colors"]:enable()')

    def test_target_and_party_changes_are_left_to_the_hooks(self):
        for event in ("PLAYER_TARGET_CHANGED", "PARTY_MEMBERS_CHANGED"):
            self.assertFalse(self.lua.eval('''(function(ev)
                for _, f in ipairs(frames) do if fire(f, ev) then return true end end
                return false end)("%s")''' % event), event)

    def test_health_bars_keep_the_native_color(self):
        self.lua.execute('for _, f in ipairs(frames) do fire(f, "PLAYER_ENTERING_WORLD") end')
        self.assertEqual(self.lua.eval("healthWrites"), 0)


class SwitchesWithoutAControl(unittest.TestCase):
    def test_blizzard_aura_controls_is_always_on(self):
        self.assertRegex(source("mods/standard-player-auras.lua"),
                         r'title = "Blizzard Aura Controls"[^}]*always = true')
        self.assertNotIn("Blizzard Aura Controls", source("Settings.lua"))

    def chat(self):
        lua = runtime()
        lua.execute(r'''
            NUM_CHAT_WINDOWS = 1
            lines = {}
            gsubs = 0
            function gsub(...) gsubs = gsubs + 1; return string.gsub(...) end
            function date(f) return (string.gsub(f, "%%H:%%M:%%S", "12:34:56")) end
            function FT.IsCombatChatFrame() return false end
            -- A plain table: the generic Widget answers every capitalised field.
            ChatFrame1 = { AddMessage = function(_, text) lines[#lines + 1] = text end }
        ''')
        lua.execute(source("mods/chat-tweaks.lua"))
        return lua

    def test_timestamps_keep_their_look_and_lose_the_hidden_style(self):
        lua = self.chat()
        lua.execute('FT.mods["Chat Timestamps"]:enable(); ChatFrame1:AddMessage("hello")')
        self.assertEqual(lua.eval("lines[1]"), "|cffcccccc[12:34:56]|r hello")   # control: the old look
        self.assertIsNone(lua.eval('FT.mods["Chat Timestamps"].config'))

    def test_a_line_without_clink_skips_the_clink_patterns(self):
        lua = self.chat()
        lua.execute('FT.mods["Chat Hyperlinks"]:enable(); ChatFrame1:AddMessage("hello there")')
        self.assertEqual(lua.eval("lines[1]"), "hello there")
        self.assertEqual(lua.eval("gsubs"), 0)

    def test_a_clink_still_becomes_an_item_link(self):
        # Control.
        lua = self.chat()
        lua.execute('FT.mods["Chat Hyperlinks"]:enable(); ChatFrame1:AddMessage("{CLINK:ff1eff00:2589:0:0:0:Linen Cloth}")')
        self.assertEqual(lua.eval("lines[1]"), "|cff1eff00|Hitem:2589:0:0:0|h[Linen Cloth]|h|r")


class HotPathsBuildNoTables(unittest.TestCase):
    def test_aura_layout_builds_nothing_per_update(self):
        lua = LuaRuntime(unpack_returned_tuples=True)
        # Fixed methods: a mock that made a closure per call would hide the result.
        lua.execute(r'''
            local M = {}
            M.__index = M
            function M:ClearAllPoints() end
            function M:SetPoint() end
            function M:SetWidth(w) self.width = w end
            function M:SetHeight(h) self.height = h end
            function M:GetWidth() return self.width or 0 end
            function M:IsShown() return self.shown end
            function W(p) return setmetatable(p or {}, M) end
            FT = {}; FostercareTweaks_Config = { unitframe_positions = {} }; Auras = {}
        ''')
        auras = source("mods/unitframes/auras.lua")
        lua.execute(slice(auras, "local function HasSavedPosition", "function Auras:AttachToTargetFrame"))
        lua.execute(r'''
            local parent = W({ width = 100 })
            container = W({ unit = "player", buffSize = 20, debuffSize = 20,
                options = { spacing = 3, perRow = 8, buffAnchor = "BOTTOM", debuffAnchor = "BOTTOM",
                            standard = true, moveKey = "standard_player" },
                buffFrame = W(), debuffFrame = W(), buffButtons = {}, debuffButtons = {} })
            container.GetParent = function() return parent end
            for i = 1, 8 do
                container.buffButtons[i] = W({ isOccupied = i < 4, width = 20, border = W() })
                container.debuffButtons[i] = W({ isOccupied = i < 3, width = 20, border = W() })
            end
            function measure(n)
                Auras:LayoutContainer(container)
                collectgarbage("collect"); collectgarbage("stop")
                local before = collectgarbage("count")
                for _ = 1, n do Auras:LayoutContainer(container) end
                local grown = collectgarbage("count") - before
                collectgarbage("restart")
                return grown
            end
        ''')
        self.assertLess(lua.eval("measure(500)"), 1.0)   # KB for 500 layouts

    def test_bag_borders_reuse_one_table(self):
        lua = runtime()
        lua.execute(r'''
            bufs = {}
            C_Container = { GetContainerItemInfo = function(bag, slot, buf)
                bufs[#bufs + 1] = buf or false
                if buf then buf.quality = 2 end
                return buf or { quality = 2 }
            end }
            C_Item = { GetItemQualityByID = function() end }
            MAX_CONTAINER_ITEMS, NUM_CONTAINER_FRAMES, NUM_BANKGENERIC_SLOTS = 3, 12, 24
            function GetItemQualityColor() return 1, 1, 1 end
            function GetInventoryItemQuality() end
            function GetInventoryItemLink() end
            function FT.AddBorder() return Widget() end
            function FT.HookAddonOrVariable() end
            CharacterFrame, BankFrame = Widget(), Widget()
            ContainerFrame1 = Widget({ name = "ContainerFrame1", shown = true })
            -- Plain tables: the generic Widget answers FCTweaks_border too.
            for i = 1, 3 do
                _G["ContainerFrame1Item" .. i] = { IsShown = function() return true end, GetID = function() return i end }
            end
        ''')
        lua.execute(source("mods/item-colors.lua"))
        lua.execute('FT.mods["Item Rarity Borders"].enable()')
        lua.execute('for _, f in ipairs(frames) do fire(f, "BAG_UPDATE_DELAYED") end')
        self.assertGreaterEqual(lua.eval("#bufs"), 3)
        self.assertTrue(lua.eval("bufs[1] ~= false and bufs[1] == bufs[#bufs]"))


class EnergyTickWritesOnlyOnChange(unittest.TestCase):
    def setUp(self):
        lua = self.lua = runtime()
        lua.execute(r'''
            writes = 0
            mana = 50
            function UnitMana() return mana end
            C_Timer.After = function(_, fn) fn() end
            PlayerFrameManaBar.IsVisible = function() return true end
            PlayerFrameManaBar.GetEffectiveScale = function() return 1 end
            function PlayerFrameManaBar:CreateTexture()
                local t = Widget()
                t.SetWidth = function() writes = writes + 1 end
                return t
            end
        ''')
        lua.execute(source("mods/unitframe-energytick.lua"))
        lua.execute('FT.mods["Show Energy Ticks"]:enable()')

    def power(self, value):
        self.lua.execute('mana = %d; fire(FCTweaksEnergyTick, "UNIT_POWER_UPDATE", "player")' % value)

    def test_power_changes_do_not_rewrite_the_layout(self):
        self.power(70)                      # a 20-energy tick starts the clock
        self.assertTrue(self.lua.eval("FCTweaksEnergyTick.scripts.OnUpdate ~= nil"))
        first = self.lua.eval("writes")
        self.assertGreater(first, 0)
        self.power(30)                      # an ability spends energy
        self.power(50)
        self.assertEqual(self.lua.eval("writes"), first)

    def test_glow_returns_after_the_tick_hides(self):
        # Control for the cached layout: hiding and showing again lays out again.
        self.power(70)
        first = self.lua.eval("writes")
        self.lua.execute('function UnitPowerType() return 1 end; fire(FCTweaksEnergyTick, "UNIT_POWER_UPDATE", "player")')
        self.lua.execute('function UnitPowerType() return 3 end; fire(FCTweaksEnergyTick, "UNIT_DISPLAYPOWER", "player")')
        self.power(90)
        self.assertGreater(self.lua.eval("writes"), first)


class NoPolling(unittest.TestCase):
    def test_equip_compare_has_no_tooltip_watch(self):
        lua = runtime()
        lua.execute(r'''
            tickers = 0
            C_Timer = { After = function(_, fn) fn() end, NewTicker = function() tickers = tickers + 1; return { Cancel = NOOP } end }
            compared = {}
            hooks = {}
            function FT.HookScript(frame, script, fn) hooks[frame] = hooks[frame] or {}; hooks[frame][script] = fn end
            function FT.HookAddonOrVariable() end
            shift = false
            function IsLeftShiftKeyDown() return shift end
            function IsRightShiftKeyDown() return false end
            function IsShiftKeyDown() return shift end
            function MouseIsOver() return false end
            function GameTooltip_ShowCompareItem(t) compared[#compared + 1] = t.item end
            local function Tip(name) local t = Widget({ name = name }); t.GetItem = function(self) return self.item, self.item end; return t end
            GameTooltip, ItemRefTooltip = Tip("GameTooltip"), Tip("ItemRefTooltip")
            ShoppingTooltip1, ShoppingTooltip2 = Widget(), Widget()
            function setItem(link) GameTooltip.item = link; GameTooltip.shown = true; hooks[GameTooltip].OnTooltipSetItem(GameTooltip) end
        ''')
        lua.execute(source("mods/equip-compare.lua"))
        lua.execute('FT.mods["Equip Compare"].enable()')
        lua.execute('setItem("item:1"); shift = true; fire(FCTweaksEquipCompareModFrame, "MODIFIER_STATE_CHANGED", "LSHIFT", 1)')
        lua.execute('setItem("item:2")')                       # a new item under the cursor, Shift held
        self.assertEqual(list(lua.eval("compared").values()), ["item:1", "item:2"])
        self.assertEqual(lua.eval("tickers"), 0)

    def test_clock_wakes_at_the_next_minute(self):
        lua = runtime()
        lua.execute(r'''
            delays, tickers = {}, 0
            C_Timer = { After = function(d) delays[#delays + 1] = d end, NewTicker = function() tickers = tickers + 1 end }
            function date(f) if f == "%S" then return "15" end return "12:34" end
            Minimap = Widget(); MinimapCluster = Widget(); MinimapZoneText = Widget()
            function Minimap:GetScale() return 1 end
        ''')
        lua.execute(source("mods/minimap-tweaks.lua"))
        lua.execute('FT.mods["MiniMap Clock"].enable()')
        self.assertEqual(lua.eval("tickers"), 0)
        self.assertIn(46, list(lua.eval("delays").values()))


class ReducedBarLeavesLayoutsAlone(unittest.TestCase):
    def test_bottom_bars_are_not_moved_while_layouts_own_them(self):
        lua = runtime()
        lua.execute(r'''
            hooked = {}
            hooksecurefunc = function(name, fn) hooked[name] = fn end
            moves = 0
            MultiBarBottomLeft = Widget({ ClearAllPoints = function() moves = moves + 1 end })
            MultiBarBottomRight, MainMenuBar, MainMenuExpBar, ReputationWatchBar = Widget(), Widget(), Widget(), Widget()
            MainMenuBarArtFrame, ActionButton1 = Widget(), Widget()
            ReputationWatchBarTexture0, ReputationWatchBarTexture1 = Widget(), Widget()
            FT.ActionBars = { enabled = true }
        ''')
        lua.execute(source("mods/reduced-actionbar.lua"))
        lua.execute('FT.mods["Reduced Actionbar Size"].enable(); hooked.UIParent_ManageFramePositions()')
        self.assertEqual(lua.eval("moves"), 0)
        lua.execute('FT.ActionBars.enabled = false; hooked.UIParent_ManageFramePositions()')
        self.assertEqual(lua.eval("moves"), 1)              # control: without layouts it still places them


if __name__ == "__main__":
    unittest.main()
