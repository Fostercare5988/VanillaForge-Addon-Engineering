"""The page (4.1, 4.7 "Every addon"), what runs at rest (4.2), the globals."""
import unittest
from ff_env import load, GLOBALS, MOCK

SWITCHES = ("classColors", "targetCastbar", "energyTicks", "playerBuffs", "playerDebuffs", "targetBuffs",
            "targetDebuffs", "topBuffs", "topDebuffs", "enchants", "buffBorders", "debuffBorders", "enchantBorders")


class Page(unittest.TestCase):
    def test_each_switch_a_checkbox_on_by_default(self):
        lua = load()
        for key in SWITCHES:
            self.assertTrue(lua.eval(f"UnitFramesDB.{key}"), key)
            self.assertEqual(lua.eval(f"Settings.GetSetting('UnitFrames_{key}'):GetDefaultValue()"), True, key)
            name = lua.eval(f"Settings.GetSetting('UnitFrames_{key}'):GetName()")
            self.assertIsNotNone(lua.eval(f"settingsWindow.row(settingsWindow.find('UnitFrames'), {name!r})"), key)

    def test_defaults_puts_them_back(self):
        lua = load()
        for key in SWITCHES:
            lua.execute(f"settingsWindow.use('UnitFrames_{key}', false)")
        lua.execute("settingsWindow.defaults(settingsWindow.find('UnitFrames'))")
        for key in SWITCHES:
            self.assertTrue(lua.eval(f"UnitFramesDB.{key}"), key)
        self.assertTrue(lua.eval("UnitFramesTopDebuffs:IsShown()"))

    def test_a_saved_choice_is_kept(self):
        lua = load(saved="UnitFramesDB = { enchants = false }")
        self.assertFalse(lua.eval("UnitFramesDB.enchants"))
        self.assertFalse(lua.eval("UnitFramesEnchants:IsShown()"))

    def test_the_slash_command_opens_the_page(self):
        lua = load()
        lua.execute("SlashCmdList.UNITFRAMES('')")
        self.assertEqual(lua.eval("settingsWindow.opened:GetName()"), "UnitFrames")
        self.assertEqual(lua.eval("SLASH_UNITFRAMES1"), "/ffr")


class AtRest(unittest.TestCase):
    def test_no_redraw_runs_each_frame_with_nothing_happening(self):
        lua = load(setup="unit('player', 'Grom', 'WARRIOR', { power = 1 })")  # no tick line on rage
        running = lua.eval("""(function()
            local out = {}
            for _, w in ipairs(widgets) do
                if w.scripts.OnUpdate and w:IsVisible() then out[#out + 1] = w:GetName() or w.kind end
            end
            return table.concat(out, ',') end)()""")
        self.assertEqual(running, "")

    def test_only_the_listed_events_at_rest(self):
        lua = load()
        events = set(lua.eval("""(function()
            local out = {}
            for _, w in ipairs(widgets) do
                if type(w.name) ~= 'string' or not string.find(w.name, '^BuffButton') then
                    for e in pairs(w.events) do out[#out + 1] = e end
                end
            end
            return out end)()""").values())
        self.assertEqual(events, {
            "MODIFIER_STATE_CHANGED",                                     # the handles
            "PLAYER_TARGET_CHANGED", "RAID_ROSTER_UPDATE", "UNIT_TARGET", "UNIT_HEALTH",  # target of target
            "UNIT_SPELLCAST_START", "UNIT_SPELLCAST_STOP", "UNIT_SPELLCAST_INTERRUPTED",   # target cast bar
            "UNIT_SPELLCAST_CHANNEL_START", "UNIT_SPELLCAST_CHANNEL_STOP",
            "UNIT_SPELLCAST_INTERRUPTIBLE", "UNIT_SPELLCAST_NOT_INTERRUPTIBLE",
            "PLAYER_ENTERING_WORLD", "PLAYER_DEAD", "PLAYER_ALIVE", "PLAYER_UNGHOST", "UI_SCALE_CHANGED",
            "SPELL_ENERGIZE_ON_SELF", "UNIT_DISPLAYPOWER", "UNIT_POWER_UPDATE",                  # energy ticks
            "UNIT_AURA_DELTA",                                                                   # auras
            "WEAPON_ENCHANT_CHANGED", "WEAPON_SLOT_CHANGED",                                     # enchants
        })

    def test_unit_events_only_for_player_and_target(self):
        lua = load()
        lua.execute("unit('party1', 'Bob', 'MAGE'); a = aura('party1', 'HELPFUL', { name = 'X', icon = 'x' })")
        reads = lua.eval("count('GetAuraSlots')")
        lua.execute("delta('party1', { isFullUpdate = true }); fire('UNIT_POWER_UPDATE', 'party1')")
        self.assertEqual(lua.eval("count('GetAuraSlots')"), reads)


class FirstLogin(unittest.TestCase):
    def test_every_frame_placed_by_hand_waits_for_the_client(self):
        # At a first login the client puts back the frames it saved
        # (layout-cache.txt) only after PLAYER_ENTERING_WORLD (ActionBars,
        # 2026-11-17): nothing may need their place before that.
        names = ["PlayerBuffs", "PlayerDebuffs", "TargetBuffs", "TargetDebuffs", "TopBuffs", "TopDebuffs",
                 "Enchants", "TargetCast"]
        cache = "; ".join(f"layoutCache['UnitFrames{n}'] = {{ 640, -300 }}" for n in names)
        lua = load(setup=cache + "; aura('player', 'HELPFUL', { name = 'Fort', icon = 'fort' })"
                   "; playerBuffs.HELPFUL = { { id = 1, icon = 'fort', ends = now + 600 } }; spell(1, 'Fort', 'fort')")
        lua.execute("playerAuras(); runTimers()")
        for n in names:
            self.assertEqual(lua.eval(f"UnitFrames{n}:GetNumPoints()"), 0, f"{n}: the addon left it to the client")
        lua.execute("step(0)")
        for n in names:
            self.assertEqual(lua.eval(f"UnitFrames{n}:GetLeft()"), 640, n)


class Globals(unittest.TestCase):
    def test_only_the_listed_globals(self):
        import wowkit
        names = "(function() local t = {} for k in pairs(_G) do t[#t + 1] = k end return t end)()"
        bare = wowkit.runtime()
        bare.execute(MOCK)
        bare.execute("unit('player', 'Claude', 'ROGUE')")
        before = set(bare.eval(names).values())
        lua = load()
        after = set(lua.eval(names).values())
        hooked = {"PlayerFrame_Update", "TargetFrame_CheckFaction", "PartyMemberFrame_UpdateMember",
                  "TextStatusBar_UpdateTextString", "TargetFrame_CheckDead", "SetRaidTarget",
                  "UIParent_ManageFramePositions", "TargetDebuffButton_Update", "BuffButton_Update",
                  "BuffButtons_UpdatePositions"}
        made = {n for n in after - before if n not in ("F", "__addon_ns", "this", "event") and not n.startswith("arg")}
        self.assertEqual(made, set(GLOBALS))
        self.assertEqual({n for n in hooked if lua.eval(f"{n} ~= nil")}, hooked)


if __name__ == "__main__":
    unittest.main()
