"""Review fixes (2026-11-10, the player's go-ahead on the review's findings, and
the player's note that the settings window had become hard to grasp).

Each test fails on c7ef5cf, the code the review read.
"""
import re
import unittest

from test_audit_2026_10_25 import source
from test_audit_2026_10_26 import ROOT, runtime
from test_settings_2026_10_25 import window
from test_watched_auras_2026_11_02 import watched


class OnlyMineKeepsOthersInTheRow(unittest.TestCase):
    # A watched target debuff was kept out of the target row by name alone, so
    # with "Only mine" another player's debuff of that name showed nowhere.
    def test_the_row_drops_only_your_own(self):
        lua = watched()
        lua.execute('W.Add("Corruption", "target")')                       # Only mine by default
        self.assertTrue(lua.eval('FT.IsAuraHidden("Corruption", "target", nil, "player")'))
        self.assertFalse(lua.eval('FT.IsAuraHidden("Corruption", "target", nil, "party2")'))
        self.assertFalse(lua.eval('FT.IsAuraHidden("Corruption", "target", nil, nil)'))

    def test_anyones_icon_takes_every_cast_from_the_row(self):
        lua = watched()
        lua.execute('W.Add("Corruption", "target"); W.SetMine(1, false)')
        self.assertTrue(lua.eval('FT.IsAuraHidden("Corruption", "target", nil, "party2")'))
        lua.execute('W.SetMine(1, true)')                                  # the switch rebuilds the rule
        self.assertFalse(lua.eval('FT.IsAuraHidden("Corruption", "target", nil, "party2")'))

    def test_the_rows_pass_the_caster(self):
        text = source("mods/unitframes/auras.lua")
        self.assertIn("FT.IsAuraHidden(name, unit, nil, source)", text)
        self.assertIn("FT.IsAuraHidden(d.name, unit, nil, d.sourceUnit)", text)

    def test_no_aura_read_for_a_unit_with_nothing_watched(self):
        lua = watched('reads = 0')
        lua.execute('local get = C_UnitAuras.GetAuraSlots;'
                    ' C_UnitAuras.GetAuraSlots = function(...) reads = reads + 1; return get(...) end')
        lua.execute('W.Add("Envenom", "player"); reads = 0; fire(events, "PLAYER_TARGET_CHANGED")')
        self.assertEqual(lua.eval("reads"), 0)
        lua.execute('fire(events, "UNIT_AURA_DELTA", "player", {})')
        self.assertEqual(lua.eval("reads"), 1)


class CenterTheRightBarsRetired(unittest.TestCase):
    # Custom layouts place the right bar; only characters with custom layouts had it on.
    def test_no_trace_and_the_saved_switch_is_cleared(self):
        for path in ("mods/actionbar-float.lua", "Settings.lua", "Defaults.lua"):
            self.assertNotIn("Center Vertical Actionbar", source(path), path)
        self.assertIn('FostercareTweaks_Config["Center Vertical Actionbar"] = nil', source("Core.lua"))


class OneDefaultPerSetting(unittest.TestCase):
    # A default was written in the module, at each read, in the settings window
    # and in the raid reset button. Now: FT.NUMBERS for numbers, FT:register for switches.
    def lua_files(self):
        return [p for p in ROOT.rglob("*.lua") if p.name not in ("ForgeUI.lua", "ForgeLayout.lua")]

    def test_no_read_passes_a_default(self):
        for path in self.lua_files():
            text = path.read_text("utf-8-sig")
            self.assertIsNone(re.search(r'FT\.GetNumber\("[^"]+",', text), path.name)
            self.assertIsNone(re.search(r'FT\.IsEnabled\("[^"]+",', text), path.name)
            self.assertNotIn("config = {", text, path.name)
        self.assertNotIn("RAID_DEFAULTS", source("Settings.lua"))

    def helpers(self):
        lua = runtime()
        text = source("Helpers.lua")
        lua.execute(text[text.index("-- A switch: its saved value"):text.index("-- One load watcher")])
        return lua

    def test_a_number_is_clamped_and_clearing_it_brings_the_default_back(self):
        lua = self.helpers()
        self.assertEqual(lua.eval('FT.GetNumber("raid_buff_count")'), 4)
        lua.execute('FT.SetOverride("raid_buff_count", 99)')
        self.assertEqual(lua.eval('FT.GetNumber("raid_buff_count")'), 8)
        lua.execute('FT.SetOverride("raid_buff_count", nil)')
        self.assertEqual(lua.eval('FT.GetNumber("raid_buff_count")'), 4)

    def test_a_switch_without_a_saved_value_is_its_modules_default(self):
        lua = self.helpers()
        lua.execute('FT.mods.A, FT.mods.B = { enabled = true }, { enabled = false }')
        self.assertTrue(lua.eval('FT.IsEnabled("A")'))
        self.assertFalse(lua.eval('FT.IsEnabled("B")'))
        self.assertFalse(lua.eval('FT.IsEnabled("No such switch")'))
        lua.execute('FostercareTweaks_Config.B = 1')
        self.assertTrue(lua.eval('FT.IsEnabled("B")'))

    def test_every_switch_in_the_window_has_a_module(self):
        code = "\n".join(p.read_text("utf-8-sig") for p in self.lua_files() if p.name != "Settings.lua")
        titles = re.findall(r'Feature\(\w+, "([^"]+)"', source("Settings.lua"))
        self.assertGreater(len(titles), 30)
        for title in titles:
            self.assertIn('"%s"' % title, code, title)

    def test_raid_reset_clears_instead_of_repeating_the_defaults(self):
        lua = window()
        lua.execute('FostercareTweaks.OpenSettings("raid"); FostercareTweaks.SetOverride("raid_buff_size", 16);'
                    ' FostercareTweaks_Config["Show All Raid Buffs"] = 1;'
                    ' FostercareTweaks_Config.groupframe_dimensions = { width = 90 }; widgets.FTOpt_RaidReset:Click()')
        self.assertIsNone(lua.eval("FostercareTweaks_Config.overwrites.raid_buff_size"))
        self.assertEqual(lua.eval('FostercareTweaks_Config["Show All Raid Buffs"]'), 0)
        self.assertEqual(lua.eval('FostercareTweaks_Config["Show Raid Buffs"]'), 1)
        self.assertIsNone(lua.eval("FostercareTweaks_Config.groupframe_dimensions"))
        self.assertTrue(lua.eval("applied[6]"))


CHAT = r'''
    NUM_CHAT_WINDOWS = 1
    lines = {}
    function date(f) return (string.gsub(f, "%%H:%%M:%%S", "12:34:56")) end
    function FT.IsCombatChatFrame() return false end
    ChatFrame1 = { AddMessage = function(_, text) lines[#lines + 1] = text end }
    passed = {}
    function SetItemRef(link) passed[#passed + 1] = link end
'''


class SwitchesApplyAtOnce(unittest.TestCase):
    LIVE = (("AutoStance", "Auto Stance"), ("MiniMapClock", "MiniMap Clock"), ("ChatTimestamps", "Chat Timestamps"),
            ("ChatClassColors", "Chat Class Colors"), ("BlueShamanClassColors", "Blue Shaman Class Colors"),
            ("HideGryphons", "Hide Gryphons"), ("ReagentCounter", "Reagent Counter"))

    def test_seven_switches_no_longer_ask_for_a_reload(self):
        lua = window()
        lua.execute('FostercareTweaks.OpenSettings("general")')
        for widget, title in self.LIVE:
            lua.execute('widgets.FTOpt_%s:Click()' % widget)
            self.assertEqual(lua.eval('calls["%s"]' % title), 1, title)
        self.assertFalse(lua.eval("widgets.FTOptReload1.shown"))

    def test_each_of_them_has_apply(self):
        code = "\n".join(source("mods/" + name) for name in ("gameplay.lua", "minimap-tweaks.lua", "chat-tweaks.lua",
                         "blue-shaman.lua", "actionbar-float.lua", "actionbar-reagents.lua"))
        self.assertEqual(code.count("module.apply = function(self, "), 8)       # the seven, and the stance bar

    def chat(self):
        lua = runtime()
        lua.execute(CHAT)
        lua.execute(source("mods/chat-tweaks.lua"))
        return lua

    def test_timestamps_start_and_stop(self):
        lua = self.chat()
        lua.execute('local m = FT.mods["Chat Timestamps"]; m:apply(false); ChatFrame1:AddMessage("a");'
                    ' m:apply(true); ChatFrame1:AddMessage("b"); m:apply(false); ChatFrame1:AddMessage("c")')
        self.assertEqual(lua.eval("lines[1]"), "a")
        self.assertIn("12:34:56", lua.eval("lines[2]"))
        self.assertEqual(lua.eval("lines[3]"), "c")

    def test_blue_shamans_go_back_to_the_games_color(self):
        lua = runtime()
        lua.execute('RAID_CLASS_COLORS = { SHAMAN = { r = 0.96, g = 0.55, b = 0.73, colorStr = "fff58cba" } }')
        lua.execute(source("mods/blue-shaman.lua"))
        lua.execute('FT.mods["Blue Shaman Class Colors"].enable()')
        self.assertEqual(lua.eval("RAID_CLASS_COLORS.SHAMAN.b"), 1)
        lua.execute('FT.mods["Blue Shaman Class Colors"]:apply(false)')
        self.assertEqual(lua.eval("RAID_CLASS_COLORS.SHAMAN.colorStr"), "fff58cba")

    def test_quest_links_are_the_games(self):
        # ClassicAPI's SetHyperlink shows a quest's title and objectives; ours showed the title and an ID.
        lua = self.chat()
        lua.execute('FT.mods["Chat Hyperlinks"].enable();'
                    ' SetItemRef("quest:783:10", "|Hquest:783:10|h[A Threat Within]|h", "LeftButton")')
        self.assertEqual(lua.eval("passed[1]"), "quest:783:10")
        self.assertNotIn("Quest ID", source("mods/chat-tweaks.lua"))


class AurasOnOnePage(unittest.TestCase):
    # The player's note: "the menu is becoming very hard to grasp. All the auras
    # and buffs are very scattered." Every list of buffs and debuffs is on the
    # Auras page, a heading per place on screen; watched auras have their own page.
    AURAS = ("ShowPlayerBuffs", "ShowPlayerDebuffs", "ShowTargetBuffs", "ShowTargetDebuffs", "uf_buff_size",
             "uf_debuff_size", "ShowStandardBuffs", "ShowStandardDebuffs", "ShowWeaponEnchants", "ShowBuffBorders",
             "ShowDebuffBorders", "ShowWeaponEnchantBorders", "ShowRaidBuffs", "ShowAllRaidBuffs", "raid_buff_count",
             "raid_buff_size", "ShowRaidDebuffBadges", "raid_debuff_count", "raid_debuff_size", "raid_aura_spacing")

    def test_every_aura_control_is_on_the_auras_page(self):
        lua = window()
        lua.execute('FostercareTweaks.OpenSettings("auras")')
        for name in self.AURAS:
            self.assertTrue(lua.eval("widgets.FTOpt_%s.pt[2] == FTOptPage3" % name), name)

    def test_watched_auras_have_their_own_page(self):
        lua = window()
        lua.execute('FostercareTweaks.OpenSettings("watched")')
        self.assertTrue(lua.eval("widgets.FTOpt_WatchName.pt[2] == FTOptPage4"))
        self.assertTrue(lua.eval("FTOptPage4:IsShown()"))
        self.assertIn('watched = "watched"', source("Core.lua"))                  # /ft watched

    def test_the_test_grid_is_on_both_pages_that_shape_it(self):
        lua = window()
        lua.execute('FostercareTweaks.OpenSettings("auras"); widgets.FTOpt_RaidTestAuras:Click()')
        self.assertTrue(lua.eval("raidTest"))
        lua.execute('widgets.FTOpt_RaidTest:Click()')
        self.assertFalse(lua.eval("raidTest"))

    def test_raid_icons_dim_without_the_raid_frames(self):
        lua = window()
        lua.execute('groupEnabled = false; FostercareTweaks.OpenSettings("auras")')
        self.assertFalse(lua.eval("widgets.FTOpt_ShowRaidBuffs.enabled"))
        self.assertTrue(lua.eval("widgets.FTOpt_ShowPlayerBuffs.enabled"))

    def test_no_footer_button_covers_another(self):
        lua = window()
        lua.execute('FostercareTweaks.OpenSettings("general"); widgets.FTOpt_MiniMapSquare:Click();'
                    ' FostercareTweaks.OpenSettings("raid")')
        spans = sorted((lua.eval("widgets.%s.pt[4]" % name), lua.eval("widgets.%s.width" % name))
                       for name in ("FTOpt_RaidTest", "FTOpt_RaidReset", "FTOptReload5"))
        for (x, width), (following, _) in zip(spans, spans[1:]):
            self.assertLessEqual(x + width, following)


class StockFramesNeedNoChecks(unittest.TestCase):
    def test_the_short_bar_asks_for_no_frame_that_always_exists(self):
        text = source("mods/reduced-actionbar.lua")
        self.assertIsNone(re.search(r"if \w+ and \w+ then", text))
        self.assertNotIn("if not frame then return end", text)


class RaidButtonsAreSizedInOnePlace(unittest.TestCase):
    def test_creation_and_a_size_change_share_one_function(self):
        text = source("mods/unitframes/raid.lua")
        self.assertEqual(text.count("math.floor(height * 0.12)"), 1)
        self.assertNotIn("math.floor(btnH * 0.12)", text)
        self.assertEqual(text.count("SizeButton(btn, "), 3)                 # itself, creation, a size change

    def test_the_test_grid_follows_the_health_text_setting(self):
        # It wrote "-1.5k" whatever the setting, and after any change "Dead" became a number.
        text = source("mods/unitframes/raid.lua")
        self.assertNotIn('SetText("-1.5k")', text)
        self.assertEqual(text.count("MockHealth(btn, fmt)"), 3)             # itself, the toggle, a settings change


if __name__ == "__main__":
    unittest.main()
