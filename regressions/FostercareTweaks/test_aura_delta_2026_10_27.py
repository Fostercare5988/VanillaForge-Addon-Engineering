"""Aura frames follow ClassicAPI 1.17.10 UNIT_AURA_DELTA, 2026-10-27.

UNIT_AURA_DELTA (docs/API.md) fires once per unit token per frame with the
added, updated and removed aura instance IDs; GetAuraDataByAuraInstanceID
reads one into a reused buffer. The player and target rows and the raid
buttons used to reread every aura on each UNIT_AURA (and the player row also
on PLAYER_AURAS_CHANGED, coalesced on a timer). Now a refresh or stack change
rewrites only its own button; a new or lost aura, a full update or a change
with no button reads the row again.

Every test here fails on 248c570, which has no UNIT_AURA_DELTA handler. Real
delta payloads, which token gets them, and whether a refresh the client cannot
see stays silent remain in-game checks.
"""
from pathlib import Path
import os
import unittest
from lupa.lua51 import LuaRuntime

ROOT = Path(os.environ["VANILLAFORGE_ADDON_ROOT"])


def source(name):
    return (ROOT / name).read_text("utf-8-sig").replace("\r\n", "\n")


def between(text, start, end):
    i = text.index(start)
    return text[i:text.index(end, i)]


AURAS = source("mods/unitframes/auras.lua")
RAID = source("mods/unitframes/raid.lua")

DATA = r'''
auras = {}
C_UnitAuras = { GetAuraDataByAuraInstanceID = function(unit, id, buf)
    local a = auras[id]
    if not a then return nil end
    -- As documented: the caster fields are cleared, other keys are kept.
    buf.sourceUnit, buf.sourceGUID = nil, nil
    for k, v in pairs(a) do buf[k] = v end
    return buf
end }
function GetTime() return 10 end
function UnitGUID(u) return "0x" .. u end
local T = {}
T.__index = T
function T:SetText(t) self.text = t end
function T:Show() self.shown = true end
function T:Hide() self.shown = false end
function T:IsShown() return self.shown end
function Text(p) return setmetatable(p or {}, T) end
'''


def rows():
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(DATA + r'''
        reads = { player = 0, target = 0 }
        Auras = { UpdateBlizzPlayerAuras = function() reads.player = reads.player + 1 end,
                  UpdateBlizzTargetAuras = function() reads.target = reads.target + 1 end }
        auraEventFrame = { RegisterEvent = function() end }
        FT = { SetEventHandler = function(_, fn) handler = fn end }
        timings = 0
        function UpdateAuraTiming(btn, guid, id, src, duration, expiration)
            timings = timings + 1; btn.expiration = expiration
        end
        local function Btn(id, src) return { isOccupied = true, spellId = id, timerSourceGUID = src, countText = Text() } end
        UF = { blizzPlayerAuras = Text({ shown = true, buffButtons = { Btn(10, "0xme"), Btn(11) }, debuffButtons = { Btn(20) } }),
               blizzTargetAuras = Text({ shown = false, buffButtons = {}, debuffButtons = {} }) }
        auras[7] = { spellId = 10, sourceGUID = "0xme", isHelpful = true, applications = 3, duration = 20, expirationTime = 30 }
        auras[8] = { spellId = 99, isHelpful = true, applications = 1, duration = 5, expirationTime = 15 }
        auras[9] = { spellId = 20, isHelpful = false, applications = 1, duration = 8, expirationTime = 18 }
    ''')
    lua.execute(between(AURAS, "local function SetCount", "function Auras:UpdateContainer")
                + between(AURAS, "-- A refresh or stack change rewrites only", "\nend)\n") + "\nend)\n")
    return lua


class PlayerAndTargetRows(unittest.TestCase):
    def delta(self, lua, unit, info):
        lua.execute('handler(nil, "UNIT_AURA_DELTA", "%s", %s)' % (unit, info))

    def test_a_refresh_rewrites_only_its_button(self):
        lua = rows()
        self.delta(lua, "player", "{ updatedAuraInstanceIDs = { 7, 9 } }")
        self.assertEqual(lua.eval("reads.player"), 0)
        self.assertEqual(lua.eval("timings"), 2)
        self.assertEqual(lua.eval("UF.blizzPlayerAuras.buffButtons[1].countText.text"), 3)
        self.assertEqual(lua.eval("UF.blizzPlayerAuras.buffButtons[1].expiration"), 30)

    def test_a_new_or_lost_aura_reads_the_row(self):
        lua = rows()
        self.delta(lua, "player", "{ addedAuraInstanceIDs = { 8 } }")
        self.delta(lua, "player", "{ removedAuraInstanceIDs = { 5 }, updatedAuraInstanceIDs = { 7 } }")
        self.delta(lua, "player", "{ isFullUpdate = true }")
        self.assertEqual(lua.eval("reads.player"), 3)

    def test_a_refresh_with_no_button_reads_the_row(self):
        lua = rows()
        self.delta(lua, "player", "{ updatedAuraInstanceIDs = { 8 } }")
        self.delta(lua, "player", "{ updatedAuraInstanceIDs = { 404 } }")
        self.assertEqual(lua.eval("reads.player"), 2)

    def test_hidden_target_row_reads_through_the_target_path(self):
        lua = rows()
        self.delta(lua, "target", "{ updatedAuraInstanceIDs = { 7 } }")
        self.assertEqual(lua.eval("reads.target"), 1)
        self.assertEqual(lua.eval("timings"), 0)

    def test_other_tokens_are_ignored(self):
        lua = rows()
        for unit in ("nameplate3", "raid5", "mark1", "focus"):
            self.delta(lua, unit, "{ isFullUpdate = true }")
        self.assertEqual(lua.eval("reads.player + reads.target"), 0)

    def test_the_old_events_are_gone(self):
        self.assertNotIn('"PLAYER_AURAS_CHANGED"', AURAS)
        self.assertNotIn('"UNIT_AURA"', AURAS)
        self.assertNotIn("C_Timer.After(0, FlushPlayerAuras)", AURAS)


def raid():
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(DATA + r'''
        shown = 0
        function ShowRaidAura(btn, badge, a, size, x, y)
            shown = shown + 1; badge.lastStacks, badge.lastSize = a.stacks, size
        end
        btn = Text({ unit = "raid3", shown = true,
            buffCandidates = { { id = 10, source = "player", stacks = 1 }, { id = 11, stacks = 1 } },
            debuffCandidates = { { id = 20, stacks = 1 } },
            buffBadges = { Text({ shown = true, spellId = 10, fctSize = 12, fctX = 2, fctY = 3 }),
                           Text({ shown = false }) },
            debuffBadges = {} })
        auras[7] = { spellId = 10, sourceUnit = "player", isHelpful = true, applications = 4, duration = 20, expirationTime = 30 }
        auras[8] = { spellId = 11, isHelpful = true, applications = 2, duration = 9, expirationTime = 19 }
        auras[9] = { spellId = 77, isHelpful = false, applications = 1, duration = 8, expirationTime = 18 }
    ''')
    tail = "\n    return true\nend\n"
    lua.execute(between(RAID, "local deltaAura = {}", tail) + tail + "Patch = UpdateChangedRaidAuras")
    return lua


class RaidButtons(unittest.TestCase):
    def test_a_refresh_patches_its_entry_and_badge(self):
        lua = raid()
        self.assertTrue(lua.eval("Patch(btn, { updatedAuraInstanceIDs = { 7, 8 } })"))
        self.assertEqual(lua.eval("btn.buffCandidates[1].stacks"), 4)
        self.assertEqual(lua.eval("btn.buffCandidates[2].expiration"), 19)
        # Only the shown badge is redrawn, at its own size and place.
        self.assertEqual(lua.eval("shown"), 1)
        self.assertEqual(lua.eval("btn.buffBadges[1].lastSize"), 12)

    def test_anything_else_reads_the_button(self):
        lua = raid()
        for info in ("{ addedAuraInstanceIDs = { 7 } }", "{ removedAuraInstanceIDs = { 7 } }",
                     "{ isFullUpdate = true }", "{ updatedAuraInstanceIDs = { 9 } }",
                     "{ updatedAuraInstanceIDs = { 404 } }"):
            self.assertFalse(lua.eval("Patch(btn, %s)" % info), info)

    def test_raid_listens_to_the_delta(self):
        members = between(RAID, "local MEMBER_EVENTS", "local MEMBER_UNITS")
        self.assertNotIn('"UNIT_AURA"', members)
        self.assertIn('raidFrame:RegisterEvent("UNIT_AURA_DELTA")', RAID)
        self.assertIn("if not UpdateChangedRaidAuras(btn, a2) then UpdateButtonAuras(btn) end", RAID)


if __name__ == "__main__":
    unittest.main()
