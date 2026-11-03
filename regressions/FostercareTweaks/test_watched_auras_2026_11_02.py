"""Watched auras (2026-11-02, the player's notes: movable specific auras).

Chosen buffs on you and debuffs on your target, each its own icon with the
time left, shown while the aura is up and moved with Ctrl+Shift. They replace
FostercareAuras, retired in 1.9.1 with the one-time import that 1.9.0 ran. Every
test fails on 192e14d, which has no watched auras. The icons' look and the
countdown drawing stay in-game checks.
"""
import unittest

from test_audit_2026_10_25 import source
from test_audit_2026_10_26 import runtime
from test_settings_2026_10_25 import window

SETUP = r'''
    FT.Countdown = {}
    lists = 0
    FT.ApplyStandardAuraSettings = function() lists = lists + 1 end
    FT.UnitFrames = { Auras = { UpdateBlizzPlayerAuras = function() end, UpdateBlizzTargetAuras = function() end } }
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


RECORD = r'''
    local create = CreateFrame
    CreateFrame = function(...)
        local f = create(...)
        f.SetFrameStrata = function(self, s) self.strata = s end
        f.SetPoint = function(self, ...) self.pt = { ... } end
        f.GetPoint = function(self) return unpack(self.pt) end
        return f
    end
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

    def test_icons_draw_in_front_and_new_ones_start_clear(self):
        # 2026-11-02 in play: the eighth icon (Blind) started on the target frame,
        # under its mover, and could not be found.
        lua = watched(RECORD)
        for name in ("A", "B", "C", "D", "E", "F", "G", "Blind", "I"):
            lua.execute('W.Add("%s", "player")' % name)
        blind = icon(lua, "watch_player_Blind")
        self.assertNotEqual(blind.strata, "HIGH")      # 2026-11-03: windows draw over them
        points = lua.eval('(function() local t = {} for _, k in ipairs({"A", "Blind", "I"}) do'
                          ' local _, _, _, px, py = _G["FCTweaksWatch_watch_player_" .. k]:GetPoint(1); t[#t + 1] = px; t[#t + 1] = py end return t end)()')
        ax, ay, bx, by, ix, iy = (points[i] for i in range(1, 7))
        self.assertGreater(ay, 0)                      # above the centre, not on the unit frames
        self.assertEqual(by, ay)
        self.assertEqual(bx, -ax)                      # a row of eight, centred
        self.assertEqual((ix, iy), (ax, ay + 42))      # the ninth starts the next row

    def test_each_icon_moves_with_its_own_key(self):
        # Positions sit with the other frames, so each zone layout keeps its own.
        lua = watched()
        lua.execute('W.Add("Envenom", "player")')
        self.assertEqual(icon(lua, "watch_player_Envenom").moverKey, "watch_player_Envenom")


class AfterTheImport(unittest.TestCase):
    # 1.9.0 copied FostercareAuras setups once; 1.9.1 has no import.
    def test_a_fostercare_auras_setup_is_not_read(self):
        lua = watched('FostercareAurasDB = { spells = { E = { type = "Buff", displayName = "Envenom", order = 1 } } }')
        self.assertEqual(lua.eval("#W.List()"), 0)


class WatchedAurasSettings(unittest.TestCase):
    def test_type_a_name_and_pick_where_it_shows(self):
        lua = window()
        lua.execute('heights = {}; FostercareTweaksSettingsGUI.SetHeight = function(_, h) heights[#heights + 1] = h end;'
                    ' FostercareTweaks.OpenSettings("auras")')
        before = lua.eval("heights[#heights]")
        lua.execute('widgets.FTOpt_WatchName:SetText("Rupture"); widgets.FTOpt_WatchDebuff:Click()')
        self.assertEqual(lua.eval("watched[1].unit"), "target")
        self.assertTrue(lua.eval("widgets.FTOpt_WatchChip1.shown"))
        self.assertTrue(lua.eval("widgets.FTOpt_WatchCard.shown"))          # a new aura opens its card
        self.assertFalse(lua.eval("widgets.FTOpt_WatchTop.shown"))          # top right is for your buffs
        self.assertGreater(lua.eval("heights[#heights]"), before)
        lua.execute('widgets.FTOpt_WatchMine:Click(); widgets.FTOpt_WatchRow:Click()')
        self.assertIsNone(lua.eval("watched[1].mine"))
        self.assertTrue(lua.eval("watched[1].inRow"))
        lua.execute('widgets.FTOpt_WatchChip1:Click()')                     # click again: the card closes
        self.assertFalse(lua.eval("widgets.FTOpt_WatchCard.shown"))
        lua.execute('widgets.FTOpt_WatchChip1:Click(); widgets.FTOpt_WatchRemove:Click()')
        self.assertFalse(lua.eval("widgets.FTOpt_WatchChip1.shown"))
        self.assertFalse(lua.eval("widgets.FTOpt_WatchCard.shown"))

    def test_the_list_is_two_chips_a_row(self):
        # 2026-11-02 in play: fifteen auras made a list longer than the screen.
        lua = window()
        lua.execute('FostercareTweaks.OpenSettings("auras")')
        for name in ("A", "B", "C", "D", "E"):
            lua.execute('widgets.FTOpt_WatchName:SetText("%s"); widgets.FTOpt_WatchBuff:Click()' % name)
        lua.execute('widgets.FTOpt_WatchChip5:Click()')                     # close the card
        tops = [lua.eval("widgets.FTOpt_WatchChip%d.pt[5]" % i) for i in (1, 2, 3, 5)]
        self.assertEqual(tops[0], tops[1])
        self.assertEqual(tops[2] - tops[3], 28)
        self.assertEqual(tops[0] - tops[3], 56)


if __name__ == "__main__":
    unittest.main()
