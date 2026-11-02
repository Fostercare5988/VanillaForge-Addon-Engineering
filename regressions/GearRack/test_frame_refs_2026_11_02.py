"""Trinket buttons are looked up once, 2026-11-02.

The drawer's cooldowns and the worn trinkets' queue badges built a frame name
and called getglobal on every update. Trinkets.lua now keeps each button, icon,
cooldown and badge after the first lookup. Fails on the code before: with the
names gone from the globals, the next update finds no frame.
"""
import unittest

import gr_env


class FrameRefs(unittest.TestCase):
    def setUp(self):
        self.e = gr_env.Env([])
        self.e.run('''
            GearRack = GearRack or {}; GearRack.enabled = true
            set = {}
            function GetContainerItemCooldown(bag, slot) return 10, 30, 1 end
            function CooldownFrame_SetTimer(frame) set[#set + 1] = frame end
        ''')
        loader = self.e.lua.eval('function(src, ns) return assert(loadstring(src, "Trinkets.lua"))("GearRack", ns) end')
        loader(gr_env.text("Trinkets.lua"), self.e.ns)
        self.e.run('''
            GearRackTrinkets.NumberOfTrinkets = 2
            GearRackTrinkets.BaggedTrinkets = { { bag = 0, slot = 1 }, { bag = 0, slot = 2 } }
            cd1, badge = GearRackTrinkets_Menu1CD, GearRackTrinkets_Trinket0Queue
            GearRackTrinkets.UpdateMenuCooldowns()
            GearRackTrinkets.ReflectQueueState(0, nil)
            for _, name in ipairs({ "GearRackTrinkets_Menu1CD", "GearRackTrinkets_Menu2CD", "GearRackTrinkets_Trinket0Queue" }) do
                rawset(_G, name, nil)
            end
            set = {}
        ''')

    def test_drawer_cooldowns_keep_their_frames(self):
        self.e.run("GearRackTrinkets.UpdateMenuCooldowns()")
        self.assertEqual(self.e.eval("#set"), 2)
        self.assertTrue(self.e.eval("set[1] == cd1"))

    def test_queue_badge_keeps_its_frame(self):
        self.e.run('GearRackTrinkets.ReflectQueueState(0, "delay")')
        self.assertTrue(self.e.eval("badge.gearRackDelayed"))


if __name__ == "__main__":
    unittest.main()
