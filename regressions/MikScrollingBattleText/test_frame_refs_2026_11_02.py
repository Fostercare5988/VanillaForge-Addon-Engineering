"""Scroll areas keep their frames, 2026-11-02.

Every message used to look its scroll area's frame up by name, twice
(getglobal(AssociatedFrame) to check it was shown, then to show it). Each area
now holds its frame from setup on. Fails on the code before: with the names gone
from the globals, the message finds no frame.
"""
import unittest

import _msbt_runtime as m


class FrameRefs(unittest.TestCase):
    def test_a_message_looks_up_no_frame_by_name(self):
        lua = m.runtime()
        lua.execute('''
            MikSBT.CombatEventsHandler = RealCombatEventsHandler
            area = MSBTFrameNotification
            area.shown = false
            setmetatable(_G, nil)
            for _, name in ipairs({ "MSBTFrameIncoming", "MSBTFrameOutgoing", "MSBTFrameNotification" }) do
                rawset(_G, name, nil)
            end
            lookups = 0
            getglobal = function(name) lookups = lookups + 1; return rawget(_G, name) end
            Fire("PLAYER_REGEN_DISABLED")
        ''')
        self.assertEqual(lua.eval("lookups"), 0)
        self.assertTrue(lua.eval("area.shown"))


if __name__ == "__main__":
    unittest.main()
