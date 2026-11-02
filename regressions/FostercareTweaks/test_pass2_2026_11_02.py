"""FostercareTweaks audit, second pass of 2026-11-02 (1.15.0 -> 1.16.0): bugs.

- The target aura row guarded against re-entry with a flag that an error left
  set: one bad update stopped the row for the rest of the session.
- Solo raid marks: NamPower's own SetRaidTarget falls back to a local mark when
  you are alone (README, NP_EnableLocalSetRaidTarget, on by default). Tweaks
  replaced SetRaidTargetIcon to do the same, past the player's setting.
- Watched auras read C_Spell.GetSpellCooldown (a new table) for every watched
  buff of yours on every SPELL_UPDATE_COOLDOWN and guessed the global cooldown
  from a 1.5 s duration (isOnGCD says it).
- Extra Rows 2-7: an item whose icon is not loaded yet showed the icon of the
  action that was there before.

Every test fails on 1.15.0 (a798dc8). Local marks and cooldown timing stay
in-game checks.
"""
import unittest

from lupa.lua51 import LuaRuntime

from test_audit_2026_10_25 import BASE as HEALTH_BASE
from test_audit_2026_10_26 import runtime
from test_aura_delta_2026_10_27 import AURAS, between, source
from test_watched_auras_2026_11_02 import watched

WIDGET = r'''
local W = {}
W.__index = function(t, k) return rawget(W, k) or (string.find(k, "^%u") and function() end) or nil end
function W:Show() self.shown = true end
function W:Hide() self.shown = false end
function W:IsShown() return self.shown end
function W:SetTexture(t) self.texture = t end
function W:SetText(t) self.text = t end
function W:GetID() return self.id end
function W:SetWidth(w) self.width = w end
function W:SetHeight(h) self.height = h end
function W:GetWidth() return self.width or 20 end
function W:ClearAllPoints() clears = (clears or 0) + 1 end
function Widget(t) return setmetatable(t or {}, W) end
'''


class TargetAurasRecoverFromAnError(unittest.TestCase):
    def test_one_error_does_not_stop_the_target_row(self):
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute(WIDGET + r'''
            container = Widget({ shown = true })
            UF = { blizzTargetAuras = container }
            Auras = {}
            function Auras:AttachToTargetFrame() return container end
            function Auras:ResetContainer() end
            TargetFrame = Widget({ shown = true })
            function UnitExists() return true end
            function SuppressBlizzTargetAuras() end
            updates, fail = 0, true
            function Auras:UpdateContainer() updates = updates + 1; if fail then fail = false; error("one bad aura") end end
        ''')
        lua.execute(between(AURAS, "function Auras:UpdateBlizzTargetAuras()", "-- Native TargetofTarget_Update"))
        lua.execute("pcall(Auras.UpdateBlizzTargetAuras, Auras); Auras:UpdateBlizzTargetAuras()")
        self.assertEqual(lua.eval("updates"), 2)


class SoloMarksAreNamPowers(unittest.TestCase):
    def setUp(self):
        self.lua = lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute(HEALTH_BASE + r'''
            raid, party, icons = 0, 0, 0
            function GetNumRaidMembers() return raid end
            function GetNumPartyMembers() return party end
            function FrameXMLSetRaidTargetIcon() end
            SetRaidTargetIcon = FrameXMLSetRaidTargetIcon
            function FT.GetNumber(_, d) return d end
            function FT.GetOverride() end
            function TargetFrame_UpdateRaidTargetIcon() icons = icons + 1 end
            TargetRaidTargetIcon = setmetatable({}, { __index = function() return function() end end })
            TargetPortrait = TargetRaidTargetIcon
            function CreateFrame() return { RegisterEvent = function() end } end
            function FT.SetEventHandler() end
        ''')
        lua.execute(source("mods/raid-target-marks.lua"))
        lua.execute("FT.module:enable(); icons = 0")

    def test_the_games_mark_function_is_left_to_namPower(self):
        self.assertTrue(self.lua.eval("SetRaidTargetIcon == FrameXMLSetRaidTargetIcon"))
        self.assertNotIn("SetLocalRaidTargetIndex", source("mods/raid-target-marks.lua"))

    def test_a_solo_mark_redraws_the_frames(self):
        self.lua.execute('hooks.SetRaidTarget("target", 8)')
        self.assertEqual(self.lua.eval("icons"), 1)
        self.lua.execute('party = 2; hooks.SetRaidTarget("target", 8)')       # the server's event does it
        self.assertEqual(self.lua.eval("icons"), 1)


COOLDOWNS = r'''
    now = 100
    function GetTime() return now end
    ids = { Stealth = 1784, Evasion = 5277, Sprint = 2983 }
    cd = { [1784] = { 0, 0, false }, [5277] = { 0, 0, false }, [2983] = { 0, 0, false } }
    lookups = 0
    C_Spell = { GetSpellCooldown = function(id)
        lookups = lookups + 1
        local c = cd[id]; return { startTime = c[1], duration = c[2], isOnGCD = c[3] }
    end }
    function FindSpellBookSlotByID(id) if cd[id] then return id, "spell" end end
    function GetSpellCooldown(slot) local c = cd[slot]; return c[1], c[2], 1 end
    function GetSpellInfo(id)
        if ids[id] then return id, "", "icon", 0, nil, 0, 0, 0, 0, ids[id] end
        return spells[id], "Rank 1", "icon"
    end
'''


class WatchedCooldownsReadNoTables(unittest.TestCase):
    def setUp(self):
        self.lua = watched(COOLDOWNS)
        self.lua.execute('W.Add("Stealth", "player"); W.Add("Evasion", "player"); W.Add("Sprint", "player"); lookups = 0')

    def cooldown(self, gcd=None, **own):
        for spell, spell_id in (("Stealth", 1784), ("Evasion", 5277), ("Sprint", 2983)):
            if spell in own:
                self.lua.execute("cd[%d] = { 100, %s, false }" % (spell_id, own[spell]))
            elif gcd:
                self.lua.execute("cd[%d] = { 100, %s, true }" % (spell_id, gcd))
        self.lua.execute('fire(events, "SPELL_UPDATE_COOLDOWN")')

    def test_nothing_on_cooldown_reads_nothing(self):
        self.cooldown()
        self.assertEqual(self.lua.eval("lookups"), 0)

    def test_the_global_cooldown_is_read_once(self):
        self.cooldown(gcd=1)                           # a rogue's GCD is 1 s
        self.cooldown(gcd=1)
        self.assertLessEqual(self.lua.eval("lookups"), 1)
        self.assertFalse(self.lua.eval("FCTweaksWatch_watch_player_Stealth.shown"))

    def test_a_spells_own_cooldown_is_read_once_and_shows(self):
        self.cooldown(gcd=1, Evasion=300)
        self.cooldown(gcd=1, Evasion=300)
        self.assertLessEqual(self.lua.eval("lookups"), 2)
        self.assertTrue(self.lua.eval("FCTweaksWatch_watch_player_Evasion.shown"))

    def test_a_short_cooldown_is_not_taken_for_the_global_one(self):
        self.cooldown(Sprint=1.5)
        self.assertTrue(self.lua.eval("FCTweaksWatch_watch_player_Sprint.shown"))


class ExtraRowItemIcons(unittest.TestCase):
    def test_an_item_not_loaded_yet_shows_a_question_mark(self):
        lua = runtime()
        lua.execute(WIDGET + r'''
            EA = {}
            itemCounts, reagentSpells, castCounts = {}, {}, {}
            settings = { actions = { [1] = { kind = "item", id = 2459 } } }
            FT.ActionBars = { GetSettings = function() return settings end }
            C_Item = { GetItemIconByID = function() return nil end, IsUsableItem = function() return true, false end,
                IsItemInRange = function() end, IsConsumableItem = function() return false end }
            function GetItemCooldown() return 0, 0, 0 end
            CooldownFrame_SetTimer = NOOP
            GameTooltip = { IsOwned = function() return false end }
            button = Widget({ id = 1, fctBar = { showEmpty = false, definition = { id = "extra2" } }, fctSpellID = 133,
                icon = Widget({ fctTexture = "Interface\\Icons\\Spell_Fire_FlameBolt" }),
                count = Widget(), hotkey = Widget(), flash = Widget(), cooldown = Widget() })
        ''')
        lua.execute(between(source("ExtraActions.lua").replace("\r\n", "\n"), "local function Actions(bar)",
                            "local function UpdateHotkey") + "\nDisplay(button, true)")
        self.assertEqual(lua.eval("button.icon.fctTexture"), "Interface\\Icons\\INV_Misc_QuestionMark")

if __name__ == "__main__":
    unittest.main()
