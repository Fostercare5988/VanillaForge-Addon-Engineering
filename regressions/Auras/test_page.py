"""The page, /auras, what runs at rest, the first login and the globals."""
import unittest
import wowkit
from auras_env import load, GLOBALS, MOCK

WATCH = ("AurasDB = { watched = { { name = 'Rupture', unit = 'target', icon = true, "
         "topRight = false, inRow = false, mine = true, cooldown = false } } }")


class Page(unittest.TestCase):
    def test_auras_opens_the_list_and_the_page_has_its_button(self):
        lua = load()
        self.assertEqual(lua.eval("SLASH_AURAS1"), "/auras")
        lua.execute("SlashCmdList.AURAS('')")
        self.assertTrue(lua.eval("AurasList:IsShown()"))
        lua.execute("AurasList:Hide()")
        lua.execute("settingsWindow.click(settingsWindow.row(settingsWindow.find('Auras'), 'Watched auras'))")
        self.assertTrue(lua.eval("AurasList:IsShown()"))


class AtRest(unittest.TestCase):
    def test_only_the_listed_events_and_no_onupdate(self):
        lua = load(saved=WATCH, frames=False)
        events = set(lua.eval("""(function()
            local out = {}
            for _, w in ipairs(widgets) do if w ~= TargetFrame then for e in pairs(w.events) do out[#out + 1] = e end end end  -- TargetFrame: the stock one
            return out end)()""").values())
        self.assertEqual(events, {"MODIFIER_STATE_CHANGED", "PLAYER_ENTERING_WORLD", "PLAYER_TARGET_CHANGED",
                                  "UNIT_AURA_DELTA", "SPELL_UPDATE_COOLDOWN", "SPELLS_CHANGED",
                                  "LOSS_OF_CONTROL_UPDATE"})
        running = lua.eval("""(function() local n = 0
            for _, w in ipairs(widgets) do  -- ours: unnamed, or named Auras*
                local ours = type(w.name) ~= 'string' or string.find(w.name, '^Auras')
                if ours and w.scripts.OnUpdate and w:IsVisible() then n = n + 1 end
            end
            return n end)()""")
        self.assertEqual(running, 0)

    def test_aura_events_only_for_player_and_target(self):
        lua = load(saved=WATCH, frames=False)
        lua.execute("unit('party1', 'Bob', 'MAGE'); aura('party1', 'HARMFUL', { name = 'Rupture', icon = 'r' })")
        reads = lua.eval("count('GetAuraSlots')")
        lua.execute("delta('party1', { isFullUpdate = true })")
        self.assertEqual(lua.eval("count('GetAuraSlots')"), reads)


class FirstLogin(unittest.TestCase):
    def test_a_placed_icon_waits_for_the_client(self):
        lua = load(saved=WATCH, frames=False, setup="layoutCache['AurasWatch_target_Rupture'] = { 640, -300 }")
        self.assertEqual(lua.eval("AurasWatch_target_Rupture:GetNumPoints()"), 0)
        lua.execute("step(0)")
        self.assertEqual(lua.eval("AurasWatch_target_Rupture:GetLeft()"), 640)


class Globals(unittest.TestCase):
    def test_only_the_listed_globals(self):
        names = "(function() local t = {} for k in pairs(_G) do t[#t + 1] = k end return t end)()"
        bare = wowkit.runtime()
        bare.execute(MOCK)
        bare.execute("unit('player', 'Claude', 'ROGUE')")
        before = set(bare.eval(names).values())
        lua = load(frames=False)
        made = {n for n in set(lua.eval(names).values()) - before
                if n not in ("A", "__addon_ns", "this", "event") and not n.startswith("arg")
                and not n.startswith("AurasWatch_")}
        self.assertEqual(made, set(GLOBALS))


if __name__ == "__main__":
    unittest.main()
