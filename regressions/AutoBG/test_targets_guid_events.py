"""Enemy frames follow NamPower GUID events: health, death and stealth for any loaded enemy.

The complete AutoBG_Targets.lua file runs under Lua 5.1 with generic widget mocks.
Event timing and which units NamPower tracks remain in-game checks.
"""
from pathlib import Path
import os
import unittest
from lupa.lua51 import LuaRuntime

import addon_loader

ROOT = Path(os.environ["VANILLAFORGE_ADDON_ROOT"])
TARGETS = (ROOT / "AutoBG_Targets.lua").read_text("utf-8-sig")
GROM = "0x0000000000000042"

BASE = r'''
function table.wipe(t) for k in pairs(t) do t[k] = nil end return t end
CLASSIC_API_VERSION, SUPERWOW_VERSION = 11711, "2.2"
UNKNOWNOBJECT, UKNOWNBEING = "Unknown", "Unknown Being"
local Widget = {}
-- Unknown keys on real frames are nil; only fields the module checks before creating need this.
local DATA_FIELDS = { MainFrame = true, TargetButton = true }
setmetatable(Widget, { __index = function(_, name)
    if not DATA_FIELDS[name] and string.find(name, "^%u") then return function() end end
end })
function Widget:SetText(text) self.text = text end
function Widget:EnableMouse(on) self.mouse = on end
function Widget:SetScript(kind, fn) self.scripts = self.scripts or {}; self.scripts[kind] = fn end
function Widget:IsShown() return self.shown end
function Widget:Show() self.shown = true end
function Widget:Hide() self.shown = false end
function Widget:GetFrameLevel() return 1 end
function Widget:CreateTexture() return setmetatable({}, { __index = Widget }) end
function Widget:CreateFontString() return setmetatable({}, { __index = Widget }) end
function CreateFrame(_, name) local f = setmetatable({ name = name }, { __index = Widget }); if name then _G[name] = f end; return f end
UIParent = CreateFrame("Frame", "UIParent")
local handle = { Cancel = function() end }
C_Timer = { NewTicker = function() return handle end }
C_UnitAuras = { GetAuraSlots = function() return nil, 0 end }
function GetTime() return 1000 end
MAX_BATTLEFIELD_QUEUES = 3
function GetBattlefieldStatus(i) if i == 1 then return "active", "Warsong Gulch" end return "none" end
function RequestBattlefieldScoreData() end
function GetNumBattlefieldScores() return 2 end
function GetBattlefieldScore(i)
    if i == 1 then return "Tester", 0, 0, 0, 0, 1, 0, "Human", "Warrior" end
    if i == 2 then return "Grom", 0, 0, 0, 0, 0, 0, "Orc", "Warrior" end
end
function UnitFactionGroup() return "Alliance" end
target = nil
function UnitExists(u) return u == "player" or (u == "target" and target ~= nil) or u == "0x0000000000000042" end
function UnitIsPlayer() return 1 end
function UnitIsVisible() return 1 end
function UnitIsDeadOrGhost() return nil end
function UnitIsDead() return nil end
function UnitIsGhost() return nil end
inCombat = false
function UnitAffectingCombat() return inCombat end
guidNames = {}
spellInfoCalls = 0
function SpellInfo(id) spellInfoCalls = spellInfoCalls + 1; return "Arcane Intellect" end
function UnitName(u) if u == "player" then return "Tester" end if u == "target" then return target end return guidNames[u] end
function UnitGUID(u)
    if u == "target" and target then return "0x0000000000000042" end
    if u == "0x0000000000000042" then return u end
    return raidTargets[u]
end
health = { hp = 4000, max = 4000 }
function GetUnitField(unit, field)
    if field == "health" then return health.hp elseif field == "maxHealth" then return health.max end
    error("invalid field " .. field)
end
function UnitHealth() return 100 end
function UnitHealthMax() return 100 end
function Widget:SetAlpha(a) self.alpha = a end
-- Group, range, raid icon and cast state the row features read.
raidSize, raidTargets = 0, {}
function GetNumRaidMembers() return raidSize end
function GetNumPartyMembers() return 0 end
yards = {}
function UnitDistanceSquared(u) local d = yards[u]; if not d then return 0, false end return d * d, true end
raidIcons = {}
function GetRaidTargetIndex(u) return raidIcons[u] end
function SetRaidTargetIconTexture(texture, index) texture.raidIndex = index end
casts, channels = {}, {}
C_Spell = {
    UnitCastingInfo = function(u) local c = casts[u]; if c then return c.name, c.name, c.icon, c.start, c.finish, false, nil, c.locked end end,
    UnitChannelInfo = function(u) local c = channels[u]; if c then return c.name, c.name, c.icon, c.start, c.finish, false, c.locked end end,
}
AutoBG_Settings = {}
'''


def runtime(sighting=True):
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(BASE)
    addon_loader.load(lua, TARGETS, "AutoBG_Targets.lua")
    for event in ("PLAYER_LOGIN", "UPDATE_BATTLEFIELD_STATUS"):
        lua.execute('AutoBG_Targets.scripts.OnEvent(AutoBG_Targets, "%s")' % event)
    if sighting:
        # One sighting maps the GUID; afterwards no token is needed.
        lua.execute('target = "Grom"; AutoBG_Targets.scripts.OnEvent(AutoBG_Targets, "PLAYER_TARGET_CHANGED"); target = nil')
    return lua


def fire(lua, event, *args):
    values = ", ".join(repr(a) if isinstance(a, str) else str(a) for a in args)
    lua.execute('AutoBG_Targets.scripts.OnEvent(AutoBG_Targets, "%s", %s)' % (event, values))


def row_text(lua):
    return lua.eval('AutoBG_TargetButton1.HealthText.text')


class TargetsGuidEventTests(unittest.TestCase):
    def test_roster_row_starts_at_full_health(self):
        lua = runtime()
        self.assertEqual(lua.eval('AutoBG_TargetButton1.targetName'), "Grom")
        self.assertEqual(row_text(lua), "100%")

    def test_unit_health_guid_updates_an_untargeted_enemy(self):
        lua = runtime()
        lua.execute('health.hp = 1000')
        fire(lua, "UNIT_HEALTH_GUID", GROM, 0, 0, 0, 0, 0, 0)
        self.assertEqual(row_text(lua), "25%")

    def test_unit_died_marks_the_row_dead(self):
        lua = runtime()
        fire(lua, "UNIT_DIED", GROM)
        self.assertEqual(row_text(lua), "|cffff4040DEAD|r")

    def test_buff_events_set_and_clear_stealth(self):
        lua = runtime()
        fire(lua, "BUFF_ADDED_OTHER", GROM, 1, 1787, 1, 60, 5, 0)
        self.assertEqual(row_text(lua), "|cffc7b5ffSTEALTH|r")
        fire(lua, "BUFF_REMOVED_OTHER", GROM, 1, 1787, 0, 60, 5, 1)
        self.assertEqual(row_text(lua), "100%")

    def test_trinket_aura_starts_the_trinket_timer_by_spell_id(self):
        lua = runtime()
        fire(lua, "BUFF_ADDED_OTHER", GROM, 1, 23276, 1, 60, 5, 0)
        self.assertEqual(lua.eval('AutoBG_TargetButton1.Trinket.Text.text'), "3:00")

    def test_never_targeted_enemy_is_learned_from_its_guid(self):
        lua = runtime(sighting=False)
        lua.execute('guidNames["%s"] = "Grom"; health.hp = 2000' % GROM)
        fire(lua, "UNIT_HEALTH_GUID", GROM, 0, 0, 0, 0, 0, 0)
        self.assertEqual(row_text(lua), "50%")

    def test_uncached_name_is_asked_again_on_the_next_event(self):
        lua = runtime(sighting=False)
        lua.execute('guidNames["%s"] = "Unknown"; health.hp = 2000' % GROM)
        fire(lua, "UNIT_HEALTH_GUID", GROM, 0, 0, 0, 0, 0, 0)
        lua.execute('guidNames["%s"] = "Grom"; health.hp = 1000' % GROM)
        fire(lua, "UNIT_HEALTH_GUID", GROM, 0, 0, 0, 0, 0, 0)
        self.assertEqual(row_text(lua), "25%")

    def test_stealth_check_names_each_spell_once(self):
        lua = runtime()
        lua.execute('spellInfoCalls = 0; for i = 1, 100 do AutoBG_Targets.CheckIsStealthSpell(10157) end')
        self.assertEqual(lua.eval('spellInfoCalls'), 1)

    def test_header_counts_living_enemies_and_drags_only_out_of_combat(self):
        lua = runtime()
        self.assertEqual(lua.eval('AutoBG_TargetsMainFrame.MoveText.text'), "Enemies 1/1")
        self.assertTrue(lua.eval('AutoBG_TargetsMainFrame.DragHeader.mouse'))
        lua.execute('inCombat = true')
        fire(lua, "PLAYER_REGEN_DISABLED", 0)
        self.assertFalse(lua.eval('AutoBG_TargetsMainFrame.DragHeader.mouse'))
        fire(lua, "UNIT_DIED", GROM)
        self.assertEqual(lua.eval('AutoBG_TargetsMainFrame.MoveText.text'), "Enemies 0/1")
        lua.execute('inCombat = false')
        fire(lua, "PLAYER_REGEN_ENABLED", 0)
        self.assertTrue(lua.eval('AutoBG_TargetsMainFrame.DragHeader.mouse'))

    def test_header_offers_dragging_only_in_preview(self):
        lua = runtime()
        lua.execute('AutoBG_Targets:EnableConfigMode(10)')
        # The preview also teaches the green stripe: 8 of its 10 samples are in range.
        self.assertEqual(lua.eval('AutoBG_TargetsMainFrame.MoveText.text'), "Drag to move  |cff59ff728 in range|r")
        self.assertTrue(lua.eval('AutoBG_TargetsMainFrame.DragHeader.mouse'))

    def test_header_counts_enemies_in_range_only_when_there_are_some(self):
        lua = runtime()
        lua.execute('yards["%s"] = 95; AutoBG_Targets.UpdateRowStatus()' % GROM)
        self.assertEqual(lua.eval('AutoBG_TargetsMainFrame.MoveText.text'), "Enemies 1/1")
        lua.execute('yards["%s"] = 30; AutoBG_Targets.UpdateRowStatus()' % GROM)
        self.assertEqual(lua.eval('AutoBG_TargetsMainFrame.MoveText.text'), "Enemies 1/1  |cff59ff721 in range|r")

    def test_new_install_starts_with_the_chosen_look(self):
        lua = runtime()
        o = 'AutoBG_Settings.Targets.'
        for size in (10, 15):
            got = [lua.eval(o + k + '[%d]' % size) for k in ("ButtonFontSize", "ButtonWidth", "ButtonHeight", "ButtonScale",
                                                              "ButtonHideRealm", "DimStealthed", "ShowTrinket")]
            self.assertEqual(got, [20, 195, 25, 1, True, True, True], size)
        self.assertEqual(lua.eval(o + 'ButtonFontSize[40]'), 11)  # 40v40 stays compact
        self.assertEqual((lua.eval(o + 'TrinketPos'), lua.eval(o + 'CastPos')), ("LEFT", "LEFT"))

    def test_old_save_keeps_its_cast_bars_away_from_the_trinket(self):
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute(BASE)
        lua.execute('AutoBG_Settings = { Targets = { TrinketPos = "LEFT" } }')
        addon_loader.load(lua, TARGETS, "AutoBG_Targets.lua")
        lua.execute('AutoBG_Targets.scripts.OnEvent(AutoBG_Targets, "PLAYER_LOGIN")')
        self.assertEqual(lua.eval('AutoBG_Settings.Targets.CastPos'), "RIGHT")

    def test_unknown_guids_are_ignored(self):
        lua = runtime()
        lua.execute('health.hp = 1000')
        fire(lua, "UNIT_HEALTH_GUID", "0x0000000000000099", 0, 0, 0, 0, 0, 0)
        self.assertEqual(row_text(lua), "100%")


if __name__ == '__main__':
    unittest.main()
