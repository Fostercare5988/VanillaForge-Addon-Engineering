"""The set icon picker lists ClassicAPI's spell and item icons (2026-11-14).

The stock GetMacroIconInfo list has no INV_ item icons (ClassicAPI API.md,
GetMacroIcons); GearRack padded it with a hand-kept list of two banners.
ClassicAPI's four lists give every spell and item icon, as in BrainwasherPro.
"""
import unittest

import gr_env


class SetIcons(unittest.TestCase):
    def picker(self):
        env = gr_env.logged_in(r'''
            function Widget:LockHighlight() self.locked = true end
            function Widget:UnlockHighlight() self.locked = false end''')
        env.run("GearRackUI_Sets_Initialize()")
        return env

    def test_item_icons_are_listed_with_their_path(self):
        env = self.picker()
        icons = [env.eval("GearRackUI.SetIcons[%d]" % i) for i in range(21, 23)]
        self.assertEqual(icons, [r"Interface\Icons\ABILITY_KICK", r"Interface\Icons\INV_SWORD_25"])
        self.assertIsNone(env.eval('rawget(_G, "GearRackUIExtraIcons")'))
        self.assertEqual(env.eval("#errors"), 0)

    def test_a_set_saved_with_other_casing_is_still_marked(self):
        env = self.picker()
        env.run(r'GearRackUI.SelectedIcon = "Interface\\Icons\\INV_Sword_25"; GearRackUI_Sets_ScrollFrame_Update()')
        self.assertTrue(env.eval("GearRackUI_Sets_Icon22.locked"))
        self.assertFalse(env.eval("GearRackUI_Sets_Icon21.locked"))


if __name__ == "__main__":
    unittest.main()
