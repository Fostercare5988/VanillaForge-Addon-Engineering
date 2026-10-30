"""FostercareNameplates enemy cooldowns hear NamPower's cast events (2026-10-30).

SuperWoW's UNIT_CASTEVENT also fires on every melee swing near the player; the
cooldown row only needs finished casts and channel starts. Fails on 1.4.4.
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


class CastEvents(unittest.TestCase):
    def setUp(self):
        self.lua = load(None, PRELUDE)
        self.lua.execute('plate = nativePlate("0xF1", "nameplate1")')

    def fire(self, ev, *args):
        self.lua.globals().fire_args = self.lua.table_from(list(args))
        self.lua.execute('FNPEnemyCooldownEvents.scripts.OnEvent(FNPEnemyCooldownEvents, "%s", unpack(fire_args))' % ev)

    def shown(self):
        return self.lua.eval("plate.fnpEnemyCooldowns ~= nil and #plate.fnpEnemyCooldowns.icons > 0")

    def test_a_finished_cast_starts_the_cooldown(self):
        self.fire("SPELL_GO_OTHER", 0, 2094, "0xF1", "0x0", 0, 1, 0)
        self.assertTrue(self.shown())

    def test_a_channel_start_counts_but_a_cast_start_does_not(self):
        self.fire("SPELL_START_OTHER", 0, 2094, "0xF1", "0x0", 0, 1500, 0, 0)
        self.assertFalse(self.shown())
        self.fire("SPELL_START_OTHER", 0, 2094, "0xF1", "0x0", 0, 0, 5000, 1)
        self.assertTrue(self.shown())

    def test_swing_events_are_not_heard(self):
        self.assertFalse(self.lua.eval('FNPEnemyCooldownEvents.events.UNIT_CASTEVENT'))


if __name__ == "__main__":
    unittest.main()
