"""The grid in place of the game's own (spec R1, 4.2 "The client's grid stays
out"), the page (4.1, 4.7 "Every addon"), the test grid (R7) and the globals.
"""
import unittest
from fr_env import load, in_party, GLOBALS

MEMBER = "GroupClusterFrame3MemberFrame2"


class ClientGrid(unittest.TestCase):
    def test_quiet_while_ours_shows_and_its_choice_left_alone(self):
        lua = in_party()
        self.assertEqual(lua.eval("listening(GroupFrame)"), "PLAYER_ENTERING_WORLD", "its setup still runs")
        self.assertEqual(lua.eval("count('GroupFrame:PLAYER_ENTERING_WORLD')"), 1)
        self.assertFalse(lua.eval("GroupFrame:IsShown()"))
        self.assertFalse(lua.eval("GroupClusterFrame1:IsShown()"))
        self.assertEqual(lua.eval(f"listening({MEMBER})"), "")
        self.assertIsNone(lua.eval(f"{MEMBER}.scripts.OnUpdate"))
        self.assertEqual(lua.eval("listening(GroupPetsClusterFramePet1)"), "")
        self.assertEqual(lua.eval("GROUP_ENABLED"), "1")
        lua.execute("GroupFrame_Toggle(); GroupFrame_Update(); GroupFrame_UpdateLayout()")
        self.assertEqual(lua.eval("count('GroupFrame_Toggle') + count('GroupFrame_Update')"), 0,
                         "its options panel calls them by name; they do nothing")

    def test_back_when_ours_goes(self):
        lua = in_party()
        lua.execute("settingsWindow.use('FostercareRaid_enabled', false)")
        self.assertEqual(lua.eval("count('GroupFrame_Toggle')"), 1)
        self.assertTrue(lua.eval("GroupFrame:IsShown()"))
        self.assertIn("RAID_ROSTER_UPDATE", lua.eval("listening(GroupFrame)"))
        self.assertIn("UNIT_HEALTH", lua.eval(f"listening({MEMBER})"))
        self.assertEqual(lua.eval("listening(GroupPetsClusterFramePet1)"), "UNIT_HEALTH")
        self.assertFalse(lua.eval("grid():IsShown()"))
        self.assertEqual(lua.eval("listening(grid())"), "")

    def test_its_option_off_brings_the_party_frames_back(self):
        lua = in_party(setup="GROUP_ENABLED = '0'")
        self.assertFalse(lua.eval("PartyMemberFrame1:IsShown()"))
        lua.execute("PartyMemberFrame1:Show()")
        self.assertFalse(lua.eval("PartyMemberFrame1:IsShown()"), "the game shows them again; they hide")
        lua.execute("settingsWindow.use('FostercareRaid_enabled', false)")
        self.assertTrue(lua.eval("PartyMemberFrame1:IsShown()"))
        self.assertTrue(lua.eval("PartyMemberFrame2:IsShown()"))

    def test_on_again_takes_over_again(self):
        lua = in_party()
        lua.execute("settingsWindow.use('FostercareRaid_enabled', false)")
        lua.execute("settingsWindow.use('FostercareRaid_enabled', true)")
        self.assertEqual(lua.eval("listening(GroupFrame)"), "PLAYER_ENTERING_WORLD")
        self.assertEqual(lua.eval(f"listening({MEMBER})"), "")
        self.assertEqual(lua.eval("shown(1, 2)"), "Ann")


class Page(unittest.TestCase):
    SWITCHES = ("enabled", "aggro", "hots", "buffs", "debuffs")
    NUMBERS = {"width": 58, "height": 35, "scale": 1.05, "gapX": 2, "gapY": 3,
               "buffCount": 8, "buffSize": 14, "debuffCount": 8, "debuffSize": 12}

    def test_each_switch_a_checkbox_on_by_default_and_each_number_the_players(self):
        lua = load()
        for key in self.SWITCHES:
            self.assertEqual(lua.eval(f"Settings.GetSetting('FostercareRaid_{key}'):GetDefaultValue()"), True, key)
            self.assertEqual(lua.eval(f"FostercareRaidDB.{key}"), True, key)
        for key, value in self.NUMBERS.items():
            self.assertEqual(lua.eval(f"FostercareRaidDB.{key}"), value, key)

    def test_defaults_puts_them_back(self):
        lua = in_party()
        lua.execute("settingsWindow.use('FostercareRaid_width', 90); settingsWindow.use('FostercareRaid_buffs', false)")
        self.assertEqual(lua.eval("btn(1, 1):GetWidth()"), 90)
        lua.execute("settingsWindow.defaults(settingsWindow.find('FostercareRaid'))")
        self.assertEqual(lua.eval("FostercareRaidDB.width"), 58)
        self.assertEqual(lua.eval("FostercareRaidDB.buffs"), True)
        self.assertEqual(lua.eval("btn(1, 1):GetWidth()"), 58)

    def test_sizes_and_gaps_lay_out_again(self):
        lua = in_party()
        lua.execute("settingsWindow.use('FostercareRaid_height', 40); settingsWindow.use('FostercareRaid_gapY', 5)")
        self.assertEqual(lua.eval("btn(1, 2):GetHeight()"), 40)
        self.assertEqual(lua.eval("(select(5, btn(1, 3):GetPoint()))"), -90)
        lua.execute("settingsWindow.use('FostercareRaid_scale', 1.5)")
        self.assertEqual(lua.eval("grid():GetScale()"), 1.5)

    def test_rows_grey_with_their_switch(self):
        lua = load()
        row = "settingsWindow.row(settingsWindow.find('FostercareRaid'), %r)"
        self.assertTrue(lua.eval(f"settingsWindow.enabled({row % 'Buff size'})"))
        lua.execute("settingsWindow.use('FostercareRaid_buffs', false)")
        self.assertFalse(lua.eval(f"settingsWindow.enabled({row % 'Buff size'})"))
        self.assertTrue(lua.eval(f"settingsWindow.enabled({row % 'Debuff size'})"))
        lua.execute("settingsWindow.use('FostercareRaid_enabled', false)")
        for name in ("Width", "Aggro corner", "Test grid", "Debuff size"):
            self.assertFalse(lua.eval(f"settingsWindow.enabled({row % name})"), name)

    def test_the_slash_command_opens_the_page(self):
        lua = load()
        lua.execute("SlashCmdList.FOSTERCARERAID('')")
        self.assertEqual(lua.eval("settingsWindow.opened:GetName()"), "FostercareRaid")


class TestGrid(unittest.TestCase):
    def test_forty_samples_then_back_to_the_group(self):
        lua = in_party()
        row = "settingsWindow.row(settingsWindow.find('FostercareRaid'), 'Test grid')"
        lua.execute(f"settingsWindow.click({row})")
        self.assertEqual(lua.eval("(function() local n = 0; for g = 1, 8 do for k = 1, 5 do "
                                  "if btn(g, k):IsShown() then n = n + 1 end end end; return n end)()"), 40)
        self.assertIn("Dead", lua.eval("btn(2, 4).hp.text"))
        self.assertIn("Off", lua.eval("btn(8, 5).hp.text"))
        self.assertIsNone(lua.eval("btn(1, 2):GetAttribute('unit')"), "a sample is no one")
        self.assertIsNone(lua.eval("unitsOf('UNIT_HEALTH')"))
        self.assertEqual(lua.eval("iconsOf(btn(1, 2))"), "Interface\\Icons\\Spell_Holy_Renew@14 "
                         "Interface\\Icons\\Spell_Holy_Renew@12", "a full row of buffs, one Magic debuff: one of each fits")
        lua.execute("settingsWindow.use('FostercareRaid_width', 100)")
        self.assertEqual(lua.eval("btn(5, 5):GetWidth()"), 100)
        lua.execute(f"settingsWindow.click({row})")
        self.assertEqual(lua.eval("shown(1, 2)"), "Ann")
        self.assertFalse(lua.eval("btn(5, 5):IsShown()"))
        self.assertEqual(lua.eval("unitsOf('UNIT_HEALTH')"), "player,party1,party2")


class Globals(unittest.TestCase):
    def test_only_the_listed_globals(self):
        import wowkit
        bare = wowkit.runtime()
        from fr_env import MOCK
        bare.execute(MOCK)
        before = set(bare.eval("(function() local t = {} for k in pairs(_G) do t[#t + 1] = k end return t end)()").values())
        lua = load()
        after = set(lua.eval("(function() local t = {} for k in pairs(_G) do t[#t + 1] = k end return t end)()").values())
        made = {n for n in after - before if not n.startswith("FostercareRaidG") and n not in ("R", "__addon_ns", "this", "event")
                and not n.startswith("arg")}
        self.assertEqual(made, set(GLOBALS) - {"GroupFrame_Toggle", "GroupFrame_Update", "GroupFrame_UpdateLayout"})


if __name__ == "__main__":
    unittest.main()
