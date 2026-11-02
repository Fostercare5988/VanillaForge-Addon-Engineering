"""Auras show in one place; weapons show their poison, 2026-11-02 (the player's notes).

"When I do Evasion and Sprint, I see it 3 places each": a watched aura leaves
that unit's lists (Blizzard's buffs at the top right, the player and target
rows) and a hidden one leaves them all. The Weapon enchants area draws the
poison, oil or imbue over each weapon's icon: the poison item's icon from the
bags, else the enchant's proc spell. Every test fails on the 1.9.2 commit.
Real aura names, the enchant names on OctoWoW and the drawn icons stay in-game
checks.
"""
import unittest

from lupa.lua51 import LuaRuntime

from test_aura_delta_2026_10_27 import AURAS, between, rows, source
from test_watched_auras_2026_11_02 import watched

STANDARD = source("mods/standard-player-auras.lua")

WIDGETS = r'''
local W = {}
W.__index = function(t, k) return rawget(W, k) or (string.find(k, "^%u") and function() end) or nil end
function W:Show() self.shown = true end
function W:Hide() self.shown = false end
function W:IsShown() return self.shown end
function W:SetTexture(t) self.texture = t end
function W:GetID() return self.id end
function W:GetName() return self.name end
function W:CreateTexture() return setmetatable({}, W) end
function W:SetPoint(...) self.point = { ... } end
function Widget(t) return setmetatable(t or {}, W) end
C_Timer = { After = function(_, fn) fn() end }
function GetTime() return now or 0 end
'''


class OnePlace(unittest.TestCase):
    def test_a_watched_aura_leaves_that_units_lists_and_a_hidden_one_all(self):
        lua = watched()
        lua.execute('W.Add("Evasion", "player"); W.Add("Expose Armor", "target"); W.Add("Honorless Target", "hidden")')
        hidden = lambda name, unit: lua.eval('FT.IsAuraHidden("%s", "%s")' % (name, unit))
        self.assertTrue(hidden("Evasion", "player"))
        self.assertFalse(hidden("Evasion", "target"))
        self.assertTrue(hidden("Expose Armor", "target"))
        self.assertFalse(hidden("Expose Armor", "player"))
        self.assertTrue(hidden("Honorless Target", "player") and hidden("Honorless Target", "target"))
        self.assertIsNone(lua.eval("FCTweaksWatch_watch_hidden_HonorlessTarget"))   # no icon
        self.assertEqual(lua.eval("lists"), 3)                                      # the lists redrawn
        lua.execute("W.Remove(1)")
        self.assertFalse(hidden("Evasion", "player"))

    def test_the_rows_skip_hidden_auras(self):
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute(WIDGETS + r'''
            FT = { IsAuraHidden = function(name, unit) return name == "Evasion" and unit == "player" end }
            UF = { IsShowPlayerBuffs = function() return true end, IsShowPlayerDebuffs = function() return true end }
            Auras = { StyleBorder = function() end, LayoutContainer = function() end, ResetContainer = function() end }
            function UnitExists() return true end
            function UnitGUID() return "0xme" end
            function UpdateAuraTiming() end
            function ResetAuraButton(btn) btn.isOccupied = false; btn.shown = false end
            list = { "Evasion", "Sprint" }
            C_UnitAuras = {
                GetAuraSlots = function(unit, filter, max, token, buf) if filter ~= "HELPFUL" then return nil, 0 end
                    buf[1], buf[2] = 1, 2; return nil, 2 end,
                UnitAuraBySlot = function(unit, slot) return list[slot], "icon" .. slot, 1 end,
            }
            function Btn() return Widget({ icon = Widget(), countText = Widget() }) end
            container = Widget({ unit = "player", buffFrame = Widget(), debuffFrame = Widget(),
                buffButtons = { Btn(), Btn() }, debuffButtons = {}, buffSlots = {}, debuffSlots = {} })
        ''')
        lua.execute(between(AURAS, "local function SetCount", "local function HasSavedPosition")
                    + "\nAuras:UpdateContainer(container)")
        self.assertEqual(lua.eval("container.buffButtons[1].auraIndex"), 2)       # Sprint takes the first button
        self.assertFalse(lua.eval("container.buffButtons[2].isOccupied"))

    def test_a_hidden_auras_refresh_reads_no_row(self):
        lua = rows()
        lua.execute('auras[8].name = "Evasion"; FT.IsAuraHidden = function(name) return name == "Evasion" end')
        lua.execute('handler(nil, "UNIT_AURA_DELTA", "player", { updatedAuraInstanceIDs = { 8 } })')
        self.assertEqual(lua.eval("reads.player"), 0)

    def test_blizzards_buffs_hide_it_and_close_up(self):
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute(WIDGETS + r'''
            SHOW_BUFF_DURATIONS = "0"
            names = { [0] = 2983, [1] = 5277, [2] = 1784 }          -- Sprint, Evasion, Stealth
            spells = { [2983] = "Sprint", [5277] = "Evasion", [1784] = "Stealth" }
            function GetPlayerBuffID(index) return names[index] end
            function GetSpellInfo(id) return spells[id] end
            FT = { IsAuraHidden = function(name) return name == "Evasion" end }
            frame = Widget()
            buttons = {}
            for i = 0, 2 do buttons[i + 1] = Widget({ buffIndex = i, shown = true }) end
            areas = { { frame = frame, buttons = buttons }, { frame = frame, buttons = {} }, { frame = frame, buttons = {} } }
        ''')
        lua.execute(between(STANDARD, "local function AnchorButtons()", "function FT.ApplyStandardAuraSettings")
                    + "\nfor _, b in ipairs(buttons) do HideIfElsewhere(b) end")
        self.assertTrue(lua.eval("buttons[1].shown"))
        self.assertFalse(lua.eval("buttons[2].shown"))
        self.assertEqual(lua.eval("buttons[3].point[4]"), -35)            # Stealth moves up beside Sprint


POISONS = WIDGETS + r'''
    FostercareTweaks_Config = { ["Show Weapon Enchant Borders"] = 0 }
    FT = {}
    enchants = { [323] = { name = "Instant Poison VI", spellID = 11338 }, [2630] = { name = "Dissolvent Poison II", spellID = 25349 } }
    C_Item = {
        GetEnchantInfo = function(id) return enchants[id] end,
        GetWeaponEnchantInfo = function() return true, 1000, 40, main, true, 1000, 40, off end,
    }
    bag = {}
    walks = 0
    C_Container = {
        GetContainerNumSlots = function(b) if b == 0 then walks = walks + 1 end return b == 0 and 4 or 0 end,
        GetContainerItemInfo = function(b, s, buf) local it = bag[s]; if not it then return nil end
            buf.itemName, buf.iconFileID = it[1], it[2]; return buf end,
    }
    function GetSpellInfo(id) return "proc", "", "proc-icon-" .. id end
    function Button(slot) return Widget({ id = slot, name = "TempEnchant" .. slot }) end
'''


class PoisonIcons(unittest.TestCase):
    def runtime(self):
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute(POISONS)
        lua.execute(between(STANDARD, "local enchantIcons", "local function StyleWeaponEnchants")
                    + "\nRead, Style = ReadEnchants, StyleAuraIcon")
        return lua

    def test_each_weapon_shows_the_poison_item_from_the_bags(self):
        lua = self.runtime()
        lua.execute('''bag[2] = { "Instant Poison VI", "green-vial" }; bag[3] = { "Dissolvent Poison II", "purple-vial" }
            main, off = 323, 2630; Read()
            mh, oh = Button(16), Button(17); Style(mh, true); Style(oh, true)''')
        self.assertEqual(lua.eval("mh.fctPoison.texture"), "green-vial")
        self.assertEqual(lua.eval("oh.fctPoison.texture"), "purple-vial")
        self.assertTrue(lua.eval("mh.fctPoison.shown"))
        walks = lua.eval("walks")
        lua.execute("Read(); Read()")
        self.assertEqual(lua.eval("walks"), walks)                       # found once, kept

    def test_without_the_poison_in_the_bags_the_proc_spell_and_a_later_look(self):
        lua = self.runtime()
        lua.execute("main, off = 323, 0; Read(); mh = Button(16); Style(mh, true)")
        self.assertEqual(lua.eval("mh.fctPoison.texture"), "proc-icon-11338")
        lua.execute('bag[1] = { "Instant Poison VI", "green-vial" }; now = 30; Read(); Style(mh, true)')
        self.assertEqual(lua.eval("mh.fctPoison.texture"), "proc-icon-11338")   # not looked for again yet
        lua.execute("now = 61; Read(); Style(mh, true)")
        self.assertEqual(lua.eval("mh.fctPoison.texture"), "green-vial")

    def test_no_enchant_shows_the_weapon(self):
        lua = self.runtime()
        lua.execute('bag[1] = { "Instant Poison VI", "green-vial" }; main, off = 323, 0; Read(); mh = Button(16); Style(mh, true)')
        lua.execute("main = 0; Read(); Style(mh, true)")
        self.assertFalse(lua.eval("mh.fctPoison.shown"))

    def test_new_enchants_are_read_on_events_not_per_frame(self):
        self.assertIn('inventory:RegisterEvent("WEAPON_SLOT_CHANGED")', STANDARD)
        self.assertNotIn("GetWeaponEnchantInfo", between(STANDARD, "local function StyleAuraIcon", "local function AnchorButtons"))


if __name__ == "__main__":
    unittest.main()
