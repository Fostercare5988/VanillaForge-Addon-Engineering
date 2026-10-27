"""Rogue pass, 2026-10-27 (FostercareAuras 1.3.0-local).

- Weapon-slot trackers show the poison (or oil) on that weapon: ClassicAPI
  C_Item.GetWeaponEnchantInfo gives the temp enchant ID, GetEnchantInfo its
  proc spell, GetSpellInfo that spell's icon. No enchant: the weapon's icon.
- The Weapon tab (Main hand / Off hand) creates a ready 52-pixel weapon-slot
  tracker with time left; hovering it shows the weapon and its poison.
- Slot trackers keep their texture on themselves: both weapon slots share one
  display name, so the by-name cache made one hand show the other's icon.
- FostercareAuras is listed in ClassicAPI's AddOn Options.

The real icon and the poison's look stay in-game checks.
"""
from pathlib import Path
import os
import unittest
from lupa.lua51 import LuaRuntime

ADDON = Path(os.environ["VANILLAFORGE_ADDON_ROOT"])
MAIN = (ADDON / "FostercareAuras.lua").read_text("utf-8-sig")
CONDITIONS = (ADDON / "Modules/FostercareConditions.lua").read_text("utf-8-sig")


def enchant_runtime(main_id, off_id):
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute('''
        lookups = 0
        C_Item = {
            GetWeaponEnchantInfo = function() return true, 1000, 40, %s, true, 1000, 40, %s end,
            GetEnchantInfo = function(id)
                lookups = lookups + 1
                if id == 2630 then return { enchantID = id, name = "Deadly Poison V", spellID = 25349 } end
                if id == 2629 then return { enchantID = id, name = "Brilliant Mana Oil" } end
            end,
        }
        function GetSpellInfo(id) if id == 25349 then return "Deadly Poison V", "", "Interface\\\\Icons\\\\Ability_Rogue_DualWeild" end end
    ''' % (main_id, off_id))
    start = CONDITIONS.index("local _enchantIcon = {}")
    end = CONDITIONS.index("local function _EnsureItemTexture")
    lua.execute(CONDITIONS[start:end] + "\nIcon = _TempEnchantIcon\n")
    return lua


class PoisonIconTests(unittest.TestCase):
    def test_poisoned_hand_shows_the_poison_icon_once_looked_up(self):
        lua = enchant_runtime(2630, 0)
        self.assertEqual(lua.eval('Icon("MAINHAND")'), "Interface\\Icons\\Ability_Rogue_DualWeild")
        self.assertEqual(lua.eval('Icon("MAINHAND")'), "Interface\\Icons\\Ability_Rogue_DualWeild")
        self.assertEqual(lua.eval("lookups"), 1)

    def test_empty_hand_or_oil_falls_back_to_the_weapon(self):
        lua = enchant_runtime(2629, 0)
        self.assertIsNone(lua.eval('Icon("MAINHAND")'))
        self.assertIsNone(lua.eval('Icon("OFFHAND")'))

    def test_slot_textures_stay_off_the_shared_cache(self):
        start = CONDITIONS.index("local function _EnsureItemTexture")
        body = CONDITIONS[start:CONDITIONS.index("-- === Time-logic helpers", start)]
        self.assertNotIn("FostercareAurasDB.cache[nameKey]", body)
        self.assertIn("data.iconTexture or cache[displayName]", MAIN)


class PresetTests(unittest.TestCase):
    def test_weapon_tab_offers_both_hands(self):
        self.assertIn('{ "Ability", "Buff", "Debuff", "Weapon" }', MAIN)
        self.assertIn('local HANDS = { "Main hand poison", "Off hand poison" }', MAIN)
        self.assertIn('["Main hand poison"] = "MAINHAND", ["Off hand poison"] = "OFFHAND"', MAIN)

    def test_weapon_tooltip_reads_the_slot_not_a_bag_search(self):
        self.assertIn('GameTooltip:SetInventoryItem("player", slot)', MAIN)
        self.assertNotIn("FindPlayerItemSlot", MAIN)


class SpellIconTests(unittest.TestCase):
    def test_tracker_icons_come_from_a_name_lookup_not_a_book_walk(self):
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute(r'''
            BOOKTYPE_SPELL, BOOKTYPE_PET = "spell", "pet"
            lookups, walks = 0, 0
            function GetNumSpellTabs() walks = walks + 1; return 4 end
            function GetSpellSlotTypeIdForName(n)
                lookups = lookups + 1
                if n == "Kick" then return 12, "spell", 1769 end
                return 0, "unknown", 0
            end
            function GetSpellTexture(slot, book) return "kick-icon" end
            FostercareAuras = {}
            FostercareAurasDB = { cache = {}, spells = {
                k = { type = "Ability", displayName = "Kick" },
                r = { type = "Debuff", displayName = "Rupture" } } }
            local function FA_Cache() return FostercareAurasDB.cache end
        ''' + MAIN[MAIN.index("-- Icons for trackers named after a spell in the book."):
                    MAIN.index("-- ClassicAPI GetSpellInfo answers for any spell ID")] + r'''
            FostercareAuras_RebuildSpellTextureCache()
        ''')
        self.assertEqual(lua.eval("walks"), 0)
        self.assertEqual(lua.eval("lookups"), 2)
        self.assertEqual(lua.eval("FostercareAurasDB.spells.k.iconTexture"), "kick-icon")
        self.assertIsNone(lua.eval("FostercareAurasDB.cache.Rupture"))

    def test_spell_id_icons_from_classicapi_get_spell_info(self):
        self.assertNotIn("GetSpellIconTexture", MAIN + CONDITIONS)
        self.assertIn("local _, _, icon = GetSpellInfo(sid)", MAIN)


class OptionsEntryTests(unittest.TestCase):
    def test_listed_in_addon_options(self):
        self.assertIn('entry.name = "FostercareAuras"', MAIN)
        self.assertIn("InterfaceOptions_AddCategory(entry)", MAIN)


if __name__ == "__main__":
    unittest.main()
