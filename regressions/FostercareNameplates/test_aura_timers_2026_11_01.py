"""Nameplate aura timers are native Cooldown frames, 2026-11-01.

Each aura icon used to carry its own text, rewritten every 0.2 s by a ticker
(TickAuras, NP.timed). The icon now has a ClassicAPI Cooldown frame that draws
only the countdown number (no sweep, no flash, minutes from 60 s); its
OnCooldownDone redraws the row when the aura runs out. Whether the number shows
and sits right on the icon stays an in-game check (the CVar countdownForCooldowns
must be 1).
"""
import unittest
import fnp_env

SRC = (fnp_env.ROOT / "Details.lua").read_text("utf-8-sig")


class NativeAuraTimers(unittest.TestCase):
    def test_no_timer_or_hand_made_text_remains(self):
        for gone in ("TickAuras", "StopTimer", "NP.timed", "self.timed", "icon.time", "icon.ends", "NewTicker"):
            self.assertNotIn(gone, SRC)

    def test_the_icon_gets_a_numbers_only_countdown(self):
        for needle in ('CreateFrame("Cooldown", nil, icon, "CooldownFrameTemplate")', "SetDrawSwipe(false)",
                       "SetDrawBling(false)", "SetCountdownAbbrevThreshold(60)", "GetCountdownFontString()",
                       'SetScript("OnCooldownDone"'):
            self.assertIn(needle, SRC)

    def test_a_timed_aura_starts_its_cooldown_once_and_an_untimed_one_clears_it(self):
        start = SRC.index("    icon.plate = auraPlate")
        body = SRC[start:SRC.index("    Visible(icon, true)", start)]
        self.assertIn("icon.sweep:SetCooldown(start, duration)", body)
        self.assertIn("icon.cdStart ~= start or icon.cdDuration ~= duration", body)
        self.assertIn("icon.sweep:Clear()", body)

    def test_a_timed_aura_runs_one_native_countdown(self):
        lua = fnp_env.load(None, '''
            UnitCanAttack = function() return true end
            C_UnitAuras.GetAuraSlots = function() return nil, 0 end
            C_UnitAuras.UnitAura = function(_, i, filter)
                if filter == "HARMFUL|CROWD_CONTROL" and i == 1 then return "Sheep", "tex", 1, nil, 10, now + 6, nil, nil, nil, 77 end
            end
            sets = 0
        ''')
        lua.execute('''
            NP = FostercareNameplates.Nameplates
            NP.settings.own, NP.settings.cc, NP.settings.buffs, NP.settings.auraSize, NP.settings.auraCount = false, true, false, 20, 3
            plate = nativePlate("0xF1", "nameplate1")
            NP:Auras(plate, "0xF1")
            icon = plate.fnpAuras.icons[1]
            local set = icon.sweep.SetCooldown
            icon.sweep.SetCooldown = function(self, s, d) sets = sets + 1; started, length = s, d end
            icon.cdStart = nil
            NP:Auras(plate, "0xF1"); NP:Auras(plate, "0xF1")
        ''')
        self.assertEqual(lua.eval("sets"), 1)
        self.assertEqual(lua.eval("length"), 10)
        self.assertEqual(lua.eval("plate.fnpAuras.icons[1].textureID"), "tex")


if __name__ == "__main__":
    unittest.main()
