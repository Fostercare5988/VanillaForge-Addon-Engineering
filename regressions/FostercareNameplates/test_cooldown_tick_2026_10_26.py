"""FostercareNameplates enemy cooldown tick (audit 2026-10-26).

Every 0.2 s each enemy with observed cooldowns was redrawn: five settings
lookups, unit checks, the text and a full plate layout, though the text
changes once a second. Fails on 1.4.2.
"""
import unittest
from fnp_env import load

PRELUDE = '''
    function GetNampowerVersion() return 4, 6, 2 end
    function GetSpellRecField(id, field)
        if field == "recoveryTime" then return 120000 end
        if field == "name" then return "Blind" end
        if field == "spellIconID" then return 1 end
        return 0
    end
    function GetSpellIconTexture() return "Interface\\\\Icons\\\\Spell_Shadow_MindSteal" end
    function CooldownFrame_SetTimer() end
    function UnitExists(u) return u == "0xF1" end
    function UnitIsPlayer(u) return u == "0xF1" end
    C_Timer.NewTicker = function(_, f) tick = f; return { Cancel = function() end } end
    local create = CreateFrame
    function CreateFrame(kind, name)
        local frame = create(kind, name)
        frame.GetFrameLevel = function() return 1 end
        return frame
    end
'''


class CooldownTick(unittest.TestCase):
    def test_unchanged_ticks_do_no_work(self):
        lua = load(None, PRELUDE)
        lua.execute('''
            plate = nativePlate("0xF1", "nameplate1")
            FNPEnemyCooldownEvents.scripts.OnEvent(FNPEnemyCooldownEvents, "SPELL_GO_OTHER", 0, 2094, "0xF1", "0x0", 0, 1, 0)
            local icon = plate.fnpEnemyCooldowns.icons[1]
            lookups, layouts, texts = 0, 0, 0
            local get, layout, set = FostercareNameplates.GetOverride, FostercareNameplates.Nameplates.LayoutExtras, icon.text.SetText
            FostercareNameplates.GetOverride = function(...) lookups = lookups + 1; return get(...) end
            FostercareNameplates.Nameplates.LayoutExtras = function(...) layouts = layouts + 1; return layout(...) end
            icon.text.SetText = function(...) texts = texts + 1; return set(...) end
            now = now + 0.05
            for _ = 1, 4 do tick(); now = now + 0.2 end
        ''')
        self.assertTrue(lua.eval('plate.fnpEnemyCooldowns.shown'))
        self.assertEqual(lua.eval('lookups'), 0)
        self.assertEqual(lua.eval('layouts'), 0)
        self.assertLessEqual(lua.eval('texts'), 1, "text set more than once a second")


if __name__ == "__main__":
    unittest.main()
