"""Bagnon follows ClassicAPI for the enchant countdown and the slot rarity, 2026-11-01.

1. The enchant badge on a weapon in your bags used to run a 1 s ticker that read
   the enchant again and rewrote the time text. The client's own Cooldown frame
   now counts it down (countdownForCooldowns CVar 1), so there is no ticker; the
   frame's OnCooldownDone hides the badge when the enchant runs out.
2. The slot border looked a -1 rarity up through GetItemInfo and a link parse;
   C_Item.GetItemQualityByID answers from the item ID.

In game: a poisoned weapon in a bag shows the poison icon with "29m" or seconds
below it, counting down; "3c" replaces the time at 5 charges or fewer.
"""
import unittest
from bgn_env import load

SETUP = r'''
    now, tickers, sweeps = 1000, 0, {}
    function GetTime() return now end
    C_Timer.NewTicker = function() tickers = tickers + 1; return { Cancel = function() end } end
    function CreateFrame(kind, name)
        local w = widget(name)
        function w:CreateTexture() return widget() end
        function w:CreateFontString() return widget() end
        function w:GetFrameLevel() return 1 end
        function w:SetScript(n, fn) self.scripts = self.scripts or {}; self.scripts[n] = fn end
        if kind == "Cooldown" then
            local number = widget()
            function w:GetCountdownFontString() return number end
            function w:SetCooldown(start, duration) self.starts = (self.starts or 0) + 1; self.start, self.duration = start, duration end
            function w:Clear() self.start, self.duration = nil, nil end
            sweeps[#sweeps + 1] = w
        end
        return w
    end
    enchant = { true, 1800000, 0, 77 }
    C_Item.GetItemTempEnchantInfo = function() return enchant[1], enchant[2], enchant[3], enchant[4] end
    C_Item.GetEnchantInfo = function() return { spellID = 5 } end
    C_Spell = { GetSpellTexture = function() return "tex" end }
    BagnonSets.enchantBadges = 1
    parent = widget(nil, 2); parent.parent = widget("Bagnon"); parent.parent.player = "Tester"
    slot = widget("Slot", 3); slot.parent = parent; slot.hasItem = 1; function slot:GetFrameLevel() return 1 end
'''


class EnchantBadge(unittest.TestCase):
    def setUp(self):
        self.lua = load("localization", "utility", "frame", "item")
        self.lua.execute(SETUP)

    def update(self):
        self.lua.execute("BagnonItem_UpdateEnchant(slot)")

    def test_no_ticker_counts_the_time(self):
        self.update()
        self.assertEqual(self.lua.eval("tickers"), 0)
        self.assertEqual(self.lua.eval("sweeps[1].duration"), 1800)
        self.assertTrue(self.lua.eval("slot.enchantOverlay:IsShown()"))

    def test_reading_the_same_enchant_keeps_the_countdown(self):
        self.update()
        self.lua.execute("now = now + 5; enchant[2] = 1795000")
        self.update()
        self.assertEqual(self.lua.eval("sweeps[1].starts"), 1)

    def test_a_new_application_restarts_it(self):
        self.update()
        self.lua.execute("now = now + 5; enchant[2] = 3600000")
        self.update()
        self.assertEqual(self.lua.eval("sweeps[1].starts"), 2)
        self.assertEqual(self.lua.eval("sweeps[1].duration"), 3600)

    def test_few_charges_replace_the_time(self):
        self.lua.execute("enchant[3] = 3")
        self.update()
        self.assertEqual(self.lua.eval("slot.enchantOverlay.duration.text"), "3c")
        self.assertEqual(self.lua.eval("sweeps[1].start"), None)

    def test_enchant_gone_hides_the_badge(self):
        self.update()
        self.lua.execute("enchant = { false, 0, 0, 0 }")
        self.update()
        self.assertFalse(self.lua.eval("slot.enchantOverlay:IsShown()"))
        self.assertEqual(self.lua.eval("sweeps[1].start"), None)

    def test_running_out_hides_the_badge(self):
        self.update()
        self.lua.execute("enchant = { false, 0, 0, 0 }; sweeps[1].scripts.OnCooldownDone()")
        self.assertFalse(self.lua.eval("slot.enchantOverlay:IsShown()"))


class SlotRarity(unittest.TestCase):
    def test_native_minus_one_is_resolved_from_the_item_id(self):
        lua = load("localization", "utility", "frame", "item")
        lua.execute(SETUP)
        lua.execute(r'''
            calls = {}
            slot.border = widget(nil); slot.qualityBorder = widget(nil); slot.normalTexture = widget(nil)
            C_Container.GetContainerItemID = function() return 19019 end
            C_Item.GetItemQualityByID = function(id) count("GetItemQualityByID"); return id == 19019 and 5 or nil end
            BagnonItem_UpdateBorder(slot, -1)
        ''')
        self.assertEqual(lua.eval("slot.qualityBorder.quality"), 5)
        self.assertEqual(lua.eval("calls.GetItemInfo or 0"), 0)

    def test_native_rarity_needs_no_lookup(self):
        lua = load("localization", "utility", "frame", "item")
        lua.execute(SETUP)
        lua.execute(r'''
            calls = {}
            slot.border = widget(nil); slot.qualityBorder = widget(nil); slot.normalTexture = widget(nil)
            C_Item.GetItemQualityByID = function() count("GetItemQualityByID"); return 1 end
            BagnonItem_UpdateBorder(slot, 4)
        ''')
        self.assertEqual(lua.eval("slot.qualityBorder.quality"), 4)
        self.assertEqual(lua.eval("calls.GetItemQualityByID or 0"), 0)


if __name__ == "__main__":
    unittest.main()
