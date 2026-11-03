"""FostercareNameplates enemy cooldown rows (audit 2026-10-26, reworked 2026-11-03).

2026-10-26: every 0.2 s each enemy with observed cooldowns was redrawn (settings
lookups, unit checks, the text and a plate layout). Fixed in 1.4.3.
2026-11-03: the 0.2 s ticker is gone. The client counts each estimate down
itself (a ClassicAPI countdown formatter writes "~43", then "~3m"), and the
cooldown's OnCooldownDone redraws the row when it runs out. A cast nearby with
no cooldown worth showing is answered from the spell cache before any unit is
asked about. Fails on 1.5.0. That the numbers show and read right stays an
in-game check (the player's countdownForCooldowns CVar must be 1).
"""
import unittest
from fnp_env import load

PRELUDE = '''
    function GetSpellRecField(id, field)
        if field == "recoveryTime" then return id == 133 and 0 or 120000 end
        if field == "name" then return "Blind" end
        if field == "spellIconID" then return 1 end
        return 0
    end
    function GetSpellIconTexture() return "Interface\\\\Icons\\\\Spell_Shadow_MindSteal" end
    function UnitIsPlayer(u) return u == "0xF1" end
    tickers = 0
    C_Timer.NewTicker = function() tickers = tickers + 1; return { Cancel = function() end } end
    local create = CreateFrame
    function CreateFrame(kind, name)
        local frame = create(kind, name)
        frame.GetFrameLevel = function() return 1 end
        frame.SetCountdownFormatter = function(self, f) self.formatter = f end
        frame.SetCooldown = function(self, s, d) self.start, self.duration = s, d end
        return frame
    end
    function cast(id, guid)
        FNPEnemyCooldownEvents.scripts.OnEvent(FNPEnemyCooldownEvents, "SPELL_GO_OTHER", 0, id, guid or "0xF1", "0x0", 0, 1, 0)
    end
'''


class CooldownRow(unittest.TestCase):
    def setUp(self):
        self.lua = load(None, PRELUDE)
        self.lua.execute('plate = nativePlate("0xF1", "nameplate1"); cast(2094); icon = plate.fnpEnemyCooldowns.icons[1]')

    def test_no_ticker_runs(self):
        self.assertTrue(self.lua.eval("plate.fnpEnemyCooldowns.shown and icon.shown"))
        self.assertEqual(self.lua.eval("tickers"), 0)

    def test_the_client_counts_the_estimate_down(self):
        self.assertEqual(self.lua.eval("icon.sweep.duration"), 120)
        self.assertEqual(self.lua.eval("icon.sweep.formatter.breakpoints[1].format"), "~%d")
        self.assertEqual(self.lua.eval("icon.sweep.formatter.breakpoints[2].format"), "~%dm")
        self.assertEqual(self.lua.eval("icon.sweep.formatter.breakpoints[2].threshold"), 60)
        self.assertIsNone(self.lua.eval("icon.text"))

    def test_a_finished_estimate_leaves_the_row(self):
        self.lua.execute("now = now + 120; this = icon.sweep; icon.sweep.scripts.OnCooldownDone()")
        self.assertFalse(self.lua.eval("plate.fnpEnemyCooldowns.shown"))
        self.assertIsNone(self.lua.eval("FostercareNameplates.NameplateCooldowns.states['0xF1']"))

    def test_casts_without_a_cooldown_ask_about_no_unit(self):
        self.lua.execute('''
            asked = 0
            local isPlayer = UnitIsPlayer
            UnitIsPlayer = function(u) asked = asked + 1; return isPlayer(u) end
            cast(133); cast(133, "0xF2")
        ''')
        self.assertEqual(self.lua.eval("asked"), 0)

    def test_a_plate_that_comes_back_shows_its_estimates(self):
        self.lua.execute('''
            fire("NAME_PLATE_UNIT_REMOVED", "nameplate1")
            assert(not plate.fnpEnemyCooldowns.shown)
            again = nativePlate("0xF1", "nameplate2")
        ''')
        self.assertTrue(self.lua.eval("again.fnpEnemyCooldowns and again.fnpEnemyCooldowns.shown"))


if __name__ == "__main__":
    unittest.main()
