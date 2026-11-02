"""Watched auras (2026-11-02, the player's notes: movable specific auras).

Chosen buffs on you and debuffs on your target, each its own icon with the
time left, shown while the aura is up and moved with Ctrl+Shift. A
FostercareAuras setup is imported once. Every test fails on 192e14d, which has
no watched auras. The icons' look and the countdown drawing stay in-game checks.
"""
import unittest

from test_audit_2026_10_25 import source
from test_audit_2026_10_26 import runtime
from test_settings_2026_10_25 import window

SETUP = r'''
    FT.Countdown = {}
    FT.RestoreFramePosition = function(frame, key) restoredKeys = (restoredKeys or 0) + 1 end
    FT.RegisterFrameMover = function(frame, key) frame.moverKey = key end
    auras = { player = {}, target = {} }
    C_UnitAuras = {
        GetAuraSlots = function(unit, filter, max, token, buf)
            for k in pairs(buf) do buf[k] = nil end
            for i = 1, #auras[unit] do buf[i] = i end
            return nil, #auras[unit]
        end,
        UnitAuraBySlot = function(unit, slot)
            local a = auras[unit][slot]
            return a.name, "icon", a.count or 1, nil, 10, 105, a.source, nil, nil, a.id
        end,
    }
    spells = { [5171] = "Slice and Dice" }
    function GetSpellInfo(id) return spells[id], "Rank 1", "Interface\\Icons\\Spell" end
    function UnitIsUnit(a, b) return a == b end
'''


def watched(extra=""):
    lua = runtime()
    lua.execute(SETUP + extra)
    lua.execute(source("mods/watched-auras.lua"))
    lua.execute('FT.mods["Watched Auras"].enable(); W = FT.WatchedAuras; events = frames[#frames]')
    return lua


def icon(lua, key):
    return lua.eval('_G["FCTweaksWatch_%s"]' % key)


class WatchedAuras(unittest.TestCase):
    def test_a_buff_shows_while_it_is_up(self):
        lua = watched()
        lua.execute('W.Add("5171", "player")')                    # by ID: the spell's name
        self.assertEqual(lua.eval("W.List()[1].name"), "Slice and Dice")
        frame = icon(lua, "watch_player_SliceandDice")
        self.assertFalse(frame.shown)
        lua.execute('auras.player[1] = { name = "Slice and Dice", id = 6774 }; fire(events, "UNIT_AURA_DELTA", "player", {})')
        self.assertTrue(frame.shown)                              # any rank, by name
        lua.execute('auras.player = {}; fire(events, "UNIT_AURA_DELTA", "player", {})')
        self.assertFalse(frame.shown)

    def test_target_debuffs_are_yours_unless_switched(self):
        lua = watched()
        lua.execute('W.Add("Expose Armor", "target"); auras.target[1] = { name = "Expose Armor", source = "party2" }')
        lua.execute('fire(events, "PLAYER_TARGET_CHANGED")')
        frame = icon(lua, "watch_target_ExposeArmor")
        self.assertFalse(frame.shown)
        lua.execute('W.SetMine(1, false)')
        self.assertTrue(frame.shown)
        lua.execute('W.SetMine(1, true); auras.target[1].source = "player"; fire(events, "PLAYER_TARGET_CHANGED")')
        self.assertTrue(frame.shown)

    def test_only_player_and_target_deltas_arrive(self):
        lua = watched()
        fire = lua.globals().fire
        for unit in ("nameplate2", "raid4", "mark1"):
            self.assertFalse(fire(lua.eval("events"), "UNIT_AURA_DELTA", unit, lua.eval("{}")), unit)

    def test_held_ctrl_shift_keeps_it_up_to_be_moved(self):
        lua = watched()
        lua.execute('W.Add("Envenom", "player"); local f = FCTweaksWatch_watch_player_Envenom; f.shown = true; f.fctForcedShown = true')
        lua.execute('fire(events, "UNIT_AURA_DELTA", "player", {})')
        self.assertTrue(icon(lua, "watch_player_Envenom").shown)

    def test_no_duplicates_and_removed_icons_go(self):
        lua = watched()
        lua.execute('W.Add("Envenom", "player"); W.Add(" Envenom ", "player")')
        self.assertEqual(lua.eval("#W.List()"), 1)
        lua.execute('auras.player[1] = { name = "Envenom" }; fire(events, "UNIT_AURA_DELTA", "player", {}); W.Remove(1)')
        self.assertFalse(icon(lua, "watch_player_Envenom").shown)
        self.assertEqual(lua.eval("#W.List()"), 0)

    def test_each_icon_moves_with_its_own_key(self):
        # Positions sit with the other frames, so each zone layout keeps its own.
        lua = watched()
        lua.execute('W.Add("Envenom", "player")')
        self.assertEqual(icon(lua, "watch_player_Envenom").moverKey, "watch_player_Envenom")


FOSTERCARE_AURAS = r'''
    FostercareAurasDB = { spells = {
        Rupture_Debuff = { type = "Debuff", displayName = "Rupture", spellid = 8640, order = 4, offsetX = 172, offsetY = -105,
            iconTexture = "Interface\\Icons\\Ability_Rogue_Rupture", conditions = { aura = { onlyMine = true } } },
        Envenom_Buff = { type = "Buff", displayName = "Envenom", spellid = 52531, order = 1, offsetX = -241, offsetY = -120 },
        ExposeArmor_Debuff = { type = "Debuff", displayName = "Expose Armor", spellid = 8649, order = 9,
            conditions = { aura = { onlyMine = false } } },
        Poison_Item = { type = "Item", displayName = "---EQUIPPED WEAPON SLOTS---", order = 8 },
    } }
'''


class ImportFromFostercareAuras(unittest.TestCase):
    def test_buffs_and_debuffs_come_over_once_in_order(self):
        lua = watched(FOSTERCARE_AURAS)
        names = [lua.eval("W.List()[%d].name" % i) for i in range(1, 4)]
        self.assertEqual(names, ["Envenom", "Rupture", "Expose Armor"])
        self.assertEqual(lua.eval("W.List()[2].unit"), "target")
        self.assertTrue(lua.eval("W.List()[2].mine"))
        self.assertIsNone(lua.eval("W.List()[3].mine"))
        self.assertEqual(lua.eval("#W.List()"), 3)                 # the weapon slot is the Weapon enchants area
        pos = lua.eval("FostercareTweaks_Config.unitframe_positions.watch_target_Rupture")
        self.assertEqual((pos.point, pos.x, pos.y), ("CENTER", 172, -105))
        lua.execute('FT.mods["Watched Auras"].enable()')
        self.assertEqual(lua.eval("#W.List()"), 3)

    def test_without_fostercare_auras_the_list_starts_empty(self):
        lua = watched()
        self.assertEqual(lua.eval("#W.List()"), 0)


class WatchedAurasSettings(unittest.TestCase):
    def test_type_a_name_and_pick_where_it_shows(self):
        lua = window()
        lua.execute('heights = {}; FostercareTweaksSettingsGUI.SetHeight = function(_, h) heights[#heights + 1] = h end;'
                    ' FostercareTweaks.OpenSettings("auras")')
        before = lua.eval("heights[#heights]")
        lua.execute('widgets.FTOpt_WatchName:SetText("Rupture"); widgets.FTOpt_WatchDebuff:Click()')
        self.assertEqual(lua.eval("watched[1].unit"), "target")
        self.assertEqual(lua.eval("widgets.FTOpt_WatchRow1.shown"), True)
        self.assertGreater(lua.eval("heights[#heights]"), before)
        lua.execute('widgets.FTOpt_WatchMine1:Click()')
        self.assertIsNone(lua.eval("watched[1].mine"))
        lua.execute('widgets.FTOpt_WatchRemove1:Click()')
        self.assertFalse(lua.eval("widgets.FTOpt_WatchRow1.shown"))


if __name__ == "__main__":
    unittest.main()
