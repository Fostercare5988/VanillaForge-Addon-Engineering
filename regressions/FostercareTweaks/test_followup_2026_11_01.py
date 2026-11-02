"""FostercareTweaks follow-up to the 2026-11-01 audit (the player's decisions).

- Energy and mana ticks: the line waited for a first observed gain, so at full
  energy or mana (after login, a reload, a shapeshift or a respawn) it never
  showed until the player spent some. It now runs at once on a two-second
  cycle; the first gain sets the phase, and the edge flashes only then.
- WorldMap Window retired for the client's own windowed map; a character that
  used it keeps a window (WORLDMAP_WINDOWED).
- Settings: one Ctrl+Shift hint on General and Unit Frames (action bars move
  with Move bars), Minimap size under Minimap, clearer labels and tooltips,
  "Reset all positions" names everything it resets.
- Raid frames wrote bar range and colour on every health and power event, and
  the party roster rebuilt every member on each change; player and target
  auras rewrote icon, count, border, colour and alpha on every update.
- Chat Class Colors built four patterns per player link per line; Chat History
  copied every line through an AddMessage wrapper. The frames keep their lines
  (ClassicAPI GetMessageInfo / BackFillMessage), read once at logout.

Each test fails on e846905 unless marked as a control. Widget mocks count
calls; they prove our writes, not the engine's drawing.
"""
import unittest
from lupa.lua51 import LuaRuntime

from test_audit_2026_10_26 import runtime, source
from test_audit_2026_11_01 import core
from test_unitframe_hot_paths import AURAS, RAID, WIDGETS, raid_runtime, slice


class TickRunsBeforeTheFirstGain(unittest.TestCase):
    def start(self, power_type=3, value=100):
        lua = self.lua = runtime()
        lua.execute(r'''
            now, mana, powerType = 100, %d, %d
            function GetTime() return now end
            function UnitMana() return mana end
            function UnitPowerType() return powerType end
            C_Timer.After = function(_, fn) fn() end
            PlayerFrameManaBar.IsVisible = function() return true end
            PlayerFrameManaBar.GetEffectiveScale = function() return 1 end
            textures = {}
            function PlayerFrameManaBar:CreateTexture()
                local t = Widget()
                t.alpha = 0
                t.SetAlpha = function(self, a) self.alpha = a end
                textures[#textures + 1] = t
                return t
            end
        ''' % (value, power_type))
        lua.execute(source("mods/unitframe-energytick.lua"))
        lua.execute('FT.mods["Show Energy Ticks"]:enable()')
        return lua

    def render(self, at):
        self.lua.execute('now = %s; FCTweaksEnergyTick.scripts.OnUpdate()' % at)
        return self.lua.eval('textures[1].alpha')          # the edge pulse

    def test_full_energy_runs_at_login(self):
        lua = self.start()
        self.assertTrue(lua.eval('FCTweaksEnergyTick.scripts.OnUpdate ~= nil'))

    def test_full_mana_runs_at_login(self):
        lua = self.start(power_type=0)
        self.assertTrue(lua.eval('FCTweaksEnergyTick.scripts.OnUpdate ~= nil'))

    def test_no_flash_until_a_gain_sets_the_phase(self):
        lua = self.start(value=80)
        self.assertEqual(self.render(100.1), 0)             # guessed cycle: no beat
        lua.execute('now = 101; mana = 100; fire(FCTweaksEnergyTick, "UNIT_POWER_UPDATE", "player")')
        self.assertGreater(self.render(101.1), 0)           # the gain set the phase

    def test_the_first_gain_sets_the_phase_off_the_guess(self):
        # Control: a gain half way through the guessed cycle is still the
        # first real tick, not an off-phase gain to reject.
        lua = self.start(value=80)
        lua.execute('now = 101; mana = 100; fire(FCTweaksEnergyTick, "UNIT_POWER_UPDATE", "player")')
        self.assertEqual(lua.eval('FCTweaksEnergyTick.start'), 101)


class WorldMapWindowRetired(unittest.TestCase):
    def initialize(self, saved, windowed):
        lua = core()
        lua.execute('''
            minimized = 0
            WORLDMAP_WINDOWED = %d
            function WorldMapFrame_Minimize() minimized = minimized + 1 end
            FostercareTweaks_Config["WorldMap Window"] = %s
            FostercareTweaks:Initialize()
        ''' % (windowed, saved))
        return lua

    def test_a_character_that_used_it_keeps_a_window(self):
        lua = self.initialize("1", 0)
        self.assertEqual(lua.eval("WORLDMAP_WINDOWED"), 1)
        self.assertEqual(lua.eval("minimized"), 1)
        self.assertIsNone(lua.eval('FostercareTweaks_Config["WorldMap Window"]'))

    def test_others_keep_the_full_screen_map(self):
        lua = self.initialize("0", 0)
        self.assertEqual(lua.eval("WORLDMAP_WINDOWED"), 0)
        self.assertEqual(lua.eval("minimized"), 0)
        self.assertIsNone(lua.eval('FostercareTweaks_Config["WorldMap Window"]'))

    def test_the_client_owns_the_map_window(self):
        code = source("mods/worldmap-window.lua")
        for gone in ('"WorldMap Window"', "ToggleWorldMap", "UIPanelWindows", "SetScale(0.85)"):
            self.assertNotIn(gone, code)
        self.assertIn('title = "WorldMap Coordinates"', code)  # control: the rest stays
        self.assertIn('title = "WorldMap Class Colors"', code)
        self.assertNotIn('"WorldMap Window"', source("Settings.lua"))


class WorldMapWindowSize(unittest.TestCase):
    """The client's windowed map draws at a fixed 0.7; its size is a setting."""

    def setUp(self):
        lua = self.lua = runtime()
        lua.execute(r'''
            hooks, scripts, ctrl = {}, {}, false
            hooksecurefunc = function(name, fn) hooks[name] = fn end
            FT.HookScript = function(frame, script, fn) scripts[script] = fn end
            FT.HookAddonOrVariable = NOOP
            saved = {}
            function FT.GetNumber(key, default, lo, hi)
                local v = saved[key] or default
                return math.max(lo, math.min(hi, v))
            end
            function FT.SetOverride(key, value) saved[key] = value end
            function IsControlKeyDown() return ctrl end
            WORLDMAP_WINDOWED = 1
            WorldMapFrame = Widget({ scale = 1 })
            function WorldMapFrame:GetScale() return self.scale end
            function WorldMapFrame:SetScale(s) self.scale = s end
            function WorldMapFrame:GetCenter() return 500 / self.scale, 400 / self.scale end
            function WorldMapFrame:SetPoint(_, _, _, x, y) self.x, self.y = x, y end
            C_Map = { GetMapAreaIDs = function() return {} end, GetMapChildrenInfo = function() return {} end,
                      GetFallbackWorldMapID = NOOP }
        ''')
        code = source("mods/worldmap-window.lua")
        lua.execute(code)
        lua.execute('FT.mods["WorldMap Window Size"].enable()')

    def wheel(self, delta):
        self.lua.execute('scripts.OnMouseWheel(WorldMapFrame, %d)' % delta)

    def test_ctrl_wheel_sizes_the_window_and_saves_it(self):
        self.lua.execute("ctrl = true")
        self.wheel(1); self.wheel(1)
        self.assertAlmostEqual(self.lua.eval("WorldMapFrame.scale"), 1.1)
        self.assertAlmostEqual(self.lua.eval("saved.worldmap_scale"), 1.1)
        # The centre stays put: 500 px on screen at any scale.
        self.assertAlmostEqual(self.lua.eval("WorldMapFrame.x * WorldMapFrame.scale"), 500)

    def test_the_wheel_without_ctrl_or_full_screen_does_nothing(self):
        self.wheel(1)
        self.lua.execute("ctrl = true; WORLDMAP_WINDOWED = 0")
        self.wheel(1)
        self.assertEqual(self.lua.eval("WorldMapFrame.scale"), 1)

    def test_size_follows_minimize_and_maximize(self):
        self.lua.execute("saved.worldmap_scale = 1.4; hooks.WorldMapFrame_Minimize()")
        self.assertAlmostEqual(self.lua.eval("WorldMapFrame.scale"), 1.4)
        self.lua.execute("WORLDMAP_WINDOWED = 0; hooks.WorldMapFrame_Maximize()")
        self.assertEqual(self.lua.eval("WorldMapFrame.scale"), 1)  # full screen is never scaled

    def test_size_has_a_slider(self):
        self.assertRegex(source("Settings.lua"), r'Slider\(general, "worldmap_scale", 1, 0\.6, 2,')


class SettingsWording(unittest.TestCase):
    MOVE = "Hold Ctrl+Shift to move frames, aura areas, the raid frames and minimap pieces. Action bars: Move bars."

    def test_one_move_hint_on_general_and_unit_frames(self):
        code = source("Settings.lua")
        self.assertIn('local MOVE_HINT = "%s"' % self.MOVE, code)
        self.assertIn("Hint(general, R, MOVE_HINT", code)
        self.assertIn("Hint(unit, L, MOVE_HINT", code)
        self.assertNotIn("raid frames and action bars", code)

    def test_minimap_size_sits_under_minimap(self):
        code = source("Settings.lua")
        self.assertRegex(code, r'Slider\(general, "minimap_scale"[^\n]*, L, ')
        self.assertLess(code.index('Heading(general, L, "Minimap")'), code.index('"minimap_scale"'))

    def test_labels_and_tooltips(self):
        code = source("Settings.lua")
        self.assertIn('"Dismount to attack, fly, talk"', code)
        self.assertNotIn("Spells do this in ClassicAPI", code)
        self.assertNotIn('"Target buffs", nil', code)
        self.assertNotIn('"Target debuffs", nil', code)
        self.assertIn('"Reset all positions"', code)
        self.assertIn("the minimap pieces back in place", code)
        clock = source("mods/minimap-tweaks.lua")
        self.assertIn('"Local time"', clock)
        self.assertIn('"Server time"', clock)


RAID_HEALTH_START = "-- Range and colour change rarely"


class RaidBarsWriteOnlyOnChange(unittest.TestCase):
    def setUp(self):
        lua = self.lua = raid_runtime()
        # The harness bar ignores these; count them here.
        lua.execute(r'''
            ranges, colors = 0, 0
            for _, bar in ipairs({ btn.healthBar }) do
                bar.SetMinMaxValues = function() ranges = ranges + 1 end
                bar.SetStatusBarColor = function() colors = colors + 1 end
            end
            btn.powerBar = { SetValue = function() end,
                SetMinMaxValues = function() ranges = ranges + 1 end,
                SetStatusBarColor = function() colors = colors + 1 end }
            UF.PowerColors = { [0] = { r = 0, g = 0, b = 1 } }
            function UnitMana() return 50 end
            function UnitManaMax() return 100 end
            function UnitPowerType() return 0 end
        ''')
        lua.execute(slice(RAID, RAID_HEALTH_START, "-- Healing and protective buffs", "local function UpdateButtonHealth")
                    + "\nHealth, Power = UpdateButtonHealth, UpdateButtonPower")

    def test_health_events_keep_range_and_colour(self):
        self.lua.execute("Health(btn); ranges, colors = 0, 0; Health(btn); Health(btn)")
        self.assertEqual(self.lua.eval("ranges + colors"), 0)

    def test_power_events_keep_range_and_colour(self):
        self.lua.execute("Power(btn); ranges, colors = 0, 0; Power(btn); Power(btn)")
        self.assertEqual(self.lua.eval("ranges + colors"), 0)

    def test_a_new_maximum_is_written(self):
        # Control.
        self.lua.execute("Health(btn); ranges = 0; FT.GetUnitHealthValues = function() return 3000, 5000 end; Health(btn)")
        self.assertEqual(self.lua.eval("ranges"), 1)


class PartyRosterRebuildsOnlyChanges(unittest.TestCase):
    def setUp(self):
        lua = self.lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute(WIDGETS)
        lua.execute(r'''
            raidFrame, testMode = W(), false
            unitToButton, groupCounters = {}, {}
            function wipe(t) for k in pairs(t) do t[k] = nil end end
            groups = {}
            for g = 1, 8 do
                local group = W({ title = W(), buttons = {} })
                for m = 1, 5 do group.buttons[m] = W({ buffBadges = {}, debuffBadges = {} }) end
                groups[g] = group
            end
            RAID_UNITS = {}
            function GetNumRaidMembers() return 0 end
            function GetNumPartyMembers() return 2 end
            function UnitIsPartyLeader() return false end
            names = { player = "Me", party1 = "Ann", party2 = "Bob" }
            function UnitName(u) return names[u] end
            function UnitIsConnected() return 1 end
            function SetUnit(b, unit) b.unit = unit end
            rebuilt = 0
            function UpdateButtonAll() rebuilt = rebuilt + 1 end
            function LayoutRaidGroups() end
            FT = { NormalizeClass = function(c) return c end }
            UF = { Auras = { ResetAuraButton = function() end } }
            function UF:GetGroupDimensions() return { enabled = true } end
        ''')
        lua.execute(slice(RAID, "-- Unit events keep a member current. A roster", "-- Roster events come in bursts",
                          "-- force: rebuild every button"))

    def test_an_unchanged_party_rebuilds_nothing(self):
        self.lua.execute("UF:UpdateGroupRoster(); rebuilt = 0; UF:UpdateGroupRoster()")
        self.assertEqual(self.lua.eval("rebuilt"), 0)

    def test_a_new_member_rebuilds_one_button(self):
        self.lua.execute('UF:UpdateGroupRoster(); rebuilt = 0; names.party2 = "Cid"; UF:UpdateGroupRoster()')
        self.assertEqual(self.lua.eval("rebuilt"), 1)
        self.assertTrue(self.lua.eval("unitToButton.party2 == groups[1].buttons[3]"))


class AuraButtonsWriteOnlyOnChange(unittest.TestCase):
    def setUp(self):
        lua = self.lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute(WIDGETS)
        lua.execute(r'''
            UF = { DispelColors = { None = { r = 0.8, g = 0, b = 0 }, Magic = { r = 0.2, g = 0.6, b = 1 } } }
            Auras = {}
            FostercareTweaks_Config = { ["Show Debuff Borders"] = 1 }
            btn = W({ isDebuff = true, border = W(), icon = W(), countText = W() })
        ''')
        lua.execute(slice(AURAS, "function Auras.StyleBorder", "function Auras:RefreshBorders"))

    def test_an_unchanged_debuff_border_writes_nothing(self):
        self.lua.execute('Auras.StyleBorder(btn, "Magic"); writes = 0; Auras.StyleBorder(btn, "Magic")')
        self.assertEqual(self.lua.eval("writes"), 0)

    def test_border_follows_dispel_type_and_setting(self):
        # Control.
        lua = self.lua
        lua.execute('Auras.StyleBorder(btn, "Magic"); writes = 0; Auras.StyleBorder(btn, nil)')
        self.assertGreater(lua.eval("writes"), 0)
        lua.execute('FostercareTweaks_Config["Show Debuff Borders"] = 0; Auras.StyleBorder(btn, nil)')
        self.assertFalse(lua.eval("btn.border.shown"))

    def test_icon_and_count_write_only_on_change(self):
        code = source("mods/unitframes/auras.lua")
        self.assertIn("local function SetIcon", code)
        lua = self.lua
        lua.execute(slice(AURAS, "-- Every aura update rewrites its buttons", "function Auras:UpdateContainer")
                    + "\n_G.SetIcon, _G.SetCount = SetIcon, SetCount")
        lua.execute('SetIcon(btn, "a"); SetCount(btn, 3); writes = 0; SetIcon(btn, "a"); SetCount(btn, 3); SetCount(btn, 1); SetCount(btn, nil)')
        self.assertEqual(lua.eval("writes"), 2)                 # 3 -> none: text and hide, once
        self.assertNotIn("btn:SetAlpha(1.0)", code)              # nothing else ever changes these
        self.assertNotIn("btn.icon:SetVertexColor(1, 1, 1, 1)\n                        btn:SetAlpha", code)


class ChatLinesCostLess(unittest.TestCase):
    def test_class_colours_build_no_pattern_per_name(self):
        lua = runtime()
        lua.execute(r'''
            NUM_CHAT_WINDOWS = 1
            lines = {}
            function FT.IsCombatChatFrame() return false end
            function FT.GetPlayerClass(name) return name == "Jaina" and "MAGE" or nil end
            FT.rgbhex = function() return "|cff3fc7eb" end
            RAID_CLASS_COLORS = { MAGE = {} }
            ChatFrame1 = { AddMessage = function(_, text) lines[#lines + 1] = text end }
        ''')
        lua.execute(source("mods/chat-tweaks.lua"))
        lua.execute(r'''
            FT.mods["Chat Class Colors"]:enable()
            local gsub, n = string.gsub, 0
            string.gsub = function(...) n = n + 1; return gsub(...) end
            ChatFrame1:AddMessage("|Hplayer:Jaina:12|h[Jaina]|h: hi")
            string.gsub = gsub
            calls = n
            ChatFrame1:AddMessage("|Hplayer:Thrall|h[Thrall]|h waves.")
            ChatFrame1:AddMessage("no links here")
        ''')
        self.assertEqual(lua.eval("lines[1]"), "|r[|cff3fc7eb|Hplayer:Jaina:12|h|cff3fc7ebJaina|h|r]|r: hi")
        self.assertEqual(lua.eval("lines[2]"), "|r[|cffaaaaaa|Hplayer:Thrall|h|cffaaaaaaThrall|h|r]|r waves.")
        self.assertEqual(lua.eval("lines[3]"), "no links here")
        self.assertLessEqual(lua.eval("calls"), 2)

    def history(self):
        lua = runtime()
        lua.execute(r'''
            NUM_CHAT_WINDOWS = 1
            function FT.IsCombatChatFrame() return false end
            FT.rgbhex = function() return "|cff999999" end
            function GetRealmName() return "R" end
            function UnitName() return "P" end
            FostercareTweaks_Cache = { chathistory = { R = { P = { [1] = { "|cff999999newer", "|cff999999older" } } } } }
            msgs = { { "login line", 1, 1, 0 } }
            ChatFrame1 = {}
            function ChatFrame1:AddMessage(text, r, g, b, mark) msgs[#msgs + 1] = { text, r, g, b, mark } end
            function ChatFrame1:BackFillMessage(text, r, g, b, mark) table.insert(msgs, 1, { text, r, g, b, mark }) end
            function ChatFrame1:GetNumMessages() return #msgs end
            function ChatFrame1:GetMessageInfo(i) local m = msgs[i]; if m then return m[1], m[2], m[3], m[4], m[5] end end
            plain = ChatFrame1.AddMessage
        ''')
        lua.execute(source("mods/chat-tweaks.lua"))
        lua.execute('FT.mods["Chat History"]:enable()')
        return lua

    def test_history_goes_behind_new_lines_without_a_wrapper(self):
        lua = self.history()
        self.assertTrue(lua.eval("ChatFrame1.AddMessage == plain"))
        self.assertEqual(lua.eval("msgs[1][1]"), "|cff999999older")
        self.assertEqual(lua.eval("msgs[2][1]"), "|cff999999newer")
        self.assertEqual(lua.eval("msgs[3][1]"), "login line")

    def test_logout_saves_the_frame_newest_first(self):
        lua = self.history()
        lua.execute('ChatFrame1:AddMessage("hi |rthere", 1, 1, 1, 7)')
        lua.execute('for _, f in ipairs(frames) do fire(f, "PLAYER_LOGOUT") end')
        saved = lua.eval("FostercareTweaks_Cache.chathistory.R.P[1]")
        self.assertEqual(list(saved.values()), [
            "|cff999999hi |r|cff999999there",                   # dimmed once
            "|cff999999login line",
            "|cff999999newer",                                   # restored lines stay as they were
            "|cff999999older",
        ])


if __name__ == "__main__":
    unittest.main()
