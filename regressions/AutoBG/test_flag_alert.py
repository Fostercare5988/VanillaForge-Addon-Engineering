"""Flag alert (AutoBG_FlagAlert.lua): its own card, apart from the stealth warning.

AutoBG_AlertCard.lua, AutoBG_Spy.lua and AutoBG_FlagAlert.lua run with the Spy
widget mocks. The Opening icon comes from GetSpellInfo once a cast taught the
spell ID. The card's look, its screen position and the chat line stay in-game
checks.
"""
import unittest
from lupa.lua51 import LuaRuntime

import addon_loader
from test_spy_nearby import BASE, SPY

FLAG_ALERT = (addon_loader.ROOT / "AutoBG_FlagAlert.lua").read_text("utf-8-sig")
ROGUE = "0x0000000000000002"
EXTRA = r'''
announced, picks, sounds = {}, {}, {}
function AutoBG_SendAnnouncement(msg) table.insert(announced, msg) end
AutoBG_Targets.SelectEnemy = function(name, guid, button) table.insert(picks, name .. "|" .. button) end
function GetSpellInfo(id) if id == 90001 then return "Opening", "", "Interface\\Icons\\Learned" end end
function PlaySound(name) table.insert(sounds, name) end
function click(card, button) card.scripts.OnClick(card, button or "LeftButton") end
'''


def runtime():
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(BASE)
    lua.execute(EXTRA)
    addon_loader.load(lua, SPY, "AutoBG_Spy.lua")
    addon_loader.load(lua, FLAG_ALERT, "AutoBG_FlagAlert.lua")
    lua.execute('AutoBG_SpyEventFrame.scripts.OnEvent(AutoBG_SpyEventFrame, "PLAYER_LOGIN")')
    return lua


def warn(lua):
    lua.execute('AutoBG_FlagAlert:Show("Sneaky", "ROGUE", "%s", "Blacksmith")' % ROGUE)


class FlagAlertTests(unittest.TestCase):
    def test_warning_names_the_flag_and_plays_its_own_sound(self):
        lua = runtime()
        warn(lua)
        self.assertTrue(lua.eval('AutoBG_FlagAlertFrame.shown'))
        self.assertEqual(lua.eval('AutoBG_FlagAlertFrame.Title.text'), "|cff00ffffOpening Blacksmith|r")
        self.assertEqual(lua.eval('AutoBG_FlagAlertFrame.Name.text'), "Sneaky")
        # Not RaidWarning, which the stealth warning plays.
        self.assertEqual(list(lua.eval('sounds').values()), ["igPVPUpdate"])

    def test_ctrl_click_announces_and_plain_clicks_select(self):
        lua = runtime()
        warn(lua)
        lua.execute('ctrl = true; click(AutoBG_FlagAlertFrame); ctrl = false')
        self.assertEqual(lua.eval('announced[1]'), "Sneaky is opening Blacksmith")
        lua.execute('click(AutoBG_FlagAlertFrame); click(AutoBG_FlagAlertFrame, "RightButton")')
        self.assertEqual(list(lua.eval('picks').values()), ["Sneaky|LeftButton", "Sneaky|RightButton"])

    def test_icon_is_the_learned_opening_spell(self):
        lua = runtime()
        warn(lua)  # creates the card
        lua.execute('function AutoBG_FlagAlertFrame.Icon:SetTexture(t) self.texture = t end')
        warn(lua)
        self.assertEqual(lua.eval('AutoBG_FlagAlertFrame.Icon.texture'), "Interface\\Icons\\INV_Misc_QuestionMark")
        lua.execute('AutoBG_FlagAlert:LearnOpening(90001)')
        warn(lua)
        self.assertEqual(lua.eval('AutoBG_FlagAlertFrame.Icon.texture'), "Interface\\Icons\\Learned")
        self.assertEqual(lua.eval('AutoBG_Settings.OpeningSpell'), 90001)

    def test_stealth_and_flag_warnings_show_side_by_side(self):
        lua = runtime()
        warn(lua)
        lua.execute('AutoBG_Spy:ShowAlert("Stealth", "Sneaky", "ROGUE", "%s")' % ROGUE)
        self.assertTrue(lua.eval('AutoBG_FlagAlertFrame.shown'))
        self.assertTrue(lua.eval('AutoBG_SpyAlertWindow.shown'))
        self.assertEqual(lua.eval('AutoBG_SpyAlertWindow.Title.text'), "|cff00ffffStealth|r")

    def test_preview_stays_until_turned_off(self):
        lua = runtime()
        lua.execute('AutoBG_FlagAlert:SetPreview(true)')
        lua.execute('local d = deferred; deferred = {}; for _, fn in ipairs(d) do fn() end')
        self.assertTrue(lua.eval('AutoBG_FlagAlertFrame.shown'))
        lua.execute('AutoBG_FlagAlert:SetPreview(false)')
        self.assertFalse(lua.eval('AutoBG_FlagAlertFrame.shown'))

    def test_warning_hides_after_a_while(self):
        lua = runtime()
        warn(lua)
        lua.execute('local d = deferred; deferred = {}; for _, fn in ipairs(d) do fn() end')
        self.assertFalse(lua.eval('AutoBG_FlagAlertFrame.shown'))


if __name__ == "__main__":
    unittest.main()
