"""Nameplate auras follow ClassicAPI 1.17.10 UNIT_AURA_DELTA, 2026-10-27.

The row shows the first crowd control, your own debuffs (capped) and, when
chosen, the first two buffs. 1.4.3 rebuilt it on every UNIT_AURA, so in a
battleground every other player's debuff on an enemy redrew that plate.
UNIT_AURA_DELTA (docs/API.md) lists the changed aura instance IDs. Now a
refresh redraws only when the row shows that spell, and a new or lost aura
only when the row's inputs moved: your debuff count, the first crowd control,
the first two buffs. Cooldown icons hide the native countdown numbers
(1.17.9), which would print over their "~" estimate.

Fails on 5a8cd9f (no AuraDeltaShows, no UNIT_AURA_DELTA). Real payloads, the
aura order and the frame time saved in a battleground stay in-game checks.
"""
import unittest
import fnp_env

AURAS = r'''
own, cc, buff1, buff2, aura = 2, nil, nil, nil, {}
C_UnitAuras.GetAuraSlots = function(_, filter) if filter == "HARMFUL|PLAYER" then return nil, own end return nil, 0 end
C_UnitAuras.UnitAura = function(_, i, filter)
    local id
    if filter == "HARMFUL|CROWD_CONTROL" then id = i == 1 and cc
    elseif filter == "HELPFUL" then id = i == 1 and buff1 or (i == 2 and buff2) end
    if id then return "n", "t", 1, nil, 0, 0, nil, nil, nil, id end
end
C_UnitAuras.GetAuraDataByAuraInstanceID = function(_, id, buf)
    local a = aura[id]; if not a then return nil end
    buf.spellId = a; return buf
end
'''

SCENE = r'''
NP = FostercareNameplates.Nameplates
NP.settings.own, NP.settings.cc, NP.settings.buffs = true, true, false
local function Icon(id, shown) return { spellID = id, IsShown = function() return shown end } end
plate = { fnpOwnTotal = 2, fnpCCID = nil, fnpAuras = { icons = { Icon(100, true), Icon(101, true), Icon(300, false) } } }
aura[1], aura[2], aura[3] = 100, 555, 300
function Shows(info) return NP:AuraDeltaShows(plate, "nameplate1", info) end
'''


def scene():
    lua = fnp_env.load()
    lua.execute(AURAS)
    lua.execute(SCENE)
    return lua


class NameplateAuraDelta(unittest.TestCase):
    def test_another_players_debuff_leaves_the_row(self):
        lua = scene()
        self.assertFalse(lua.eval("Shows({ addedAuraInstanceIDs = { 2 } })"))
        self.assertFalse(lua.eval("Shows({ removedAuraInstanceIDs = { 2 } })"))

    def test_your_new_or_lost_debuff_redraws(self):
        lua = scene()
        lua.execute("own = 3")
        self.assertTrue(lua.eval("Shows({ addedAuraInstanceIDs = { 9 } })"))
        lua.execute("own = 1")
        self.assertTrue(lua.eval("Shows({ removedAuraInstanceIDs = { 9 } })"))

    def test_new_first_crowd_control_redraws(self):
        lua = scene()
        lua.execute("cc = 853")
        self.assertTrue(lua.eval("Shows({ addedAuraInstanceIDs = { 9 } })"))

    def test_refresh_redraws_only_a_shown_spell(self):
        lua = scene()
        self.assertTrue(lua.eval("Shows({ updatedAuraInstanceIDs = { 1 } })"))
        # 555 is not on the row; 300's icon is hidden.
        self.assertFalse(lua.eval("Shows({ updatedAuraInstanceIDs = { 2, 3, 404 } })"))

    def test_full_update_redraws(self):
        self.assertTrue(scene().eval("Shows({ isFullUpdate = true })"))

    def test_buffs_count_only_when_chosen(self):
        lua = scene()
        lua.execute("buff1 = 10")
        self.assertFalse(lua.eval("Shows({ addedAuraInstanceIDs = { 9 } })"))
        lua.execute("NP.settings.buffs = true")
        self.assertTrue(lua.eval("Shows({ addedAuraInstanceIDs = { 9 } })"))
        lua.execute("plate.fnpBuff1 = 10")
        self.assertFalse(lua.eval("Shows({ addedAuraInstanceIDs = { 9 } })"))


class Wiring(unittest.TestCase):
    def test_details_listen_to_the_delta(self):
        src = (fnp_env.ROOT / "Details.lua").read_text("utf-8-sig")
        events = src[src.index("local DETAIL_EVENTS"):src.index("}", src.index("local DETAIL_EVENTS"))]
        self.assertIn('"UNIT_AURA_DELTA"', events)
        self.assertNotIn('"UNIT_AURA"', events)
        self.assertIn("if NP:AuraDeltaShows(plate, unit, info) then NP:Queue(plate, kind) end", src)

    def test_cooldown_icons_hide_native_numbers(self):
        src = (fnp_env.ROOT / "Cooldowns.lua").read_text("utf-8-sig")
        self.assertIn("icon.sweep:SetHideCountdownNumbers(true)", src)
        self.assertNotIn("CooldownFrame_SetTimer", src)


if __name__ == "__main__":
    unittest.main()
