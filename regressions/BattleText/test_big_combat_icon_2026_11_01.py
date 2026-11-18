"""Enter/Leave Combat can show a large icon beside "+Combat" / "-Combat", 2026-11-01.

The Notices tab has an "Icon" button on those two rows (FBT.BIG_ICONS). When
it is on, the message carries the event's icon at twice the font size; when it
is off, nothing changes. Both show crossed swords, greyed and tinted: red in
combat, green out of it (2026-11-02, the player's choice: the old gold check mark
looked wrong; 1.2.2 swapped 1.2.1's green-in/red-out). The text matches; profiles
that kept white or 1.2.1's colours change.
"""
import unittest

import _fbt_runtime as m

DRAW = '''
    -- Record textures and text heights on every widget the display layer makes.
    local make = NewWidget
    NewWidget = function(name, kind, parent)
        local w = make(name, kind, parent)
        w.SetTexture = function(self, t) self.tex = t end
        w.SetTexCoord = function(self, a) self.coordLeft = a end
        w.SetTextHeight = function(self, h) self.textHeight = h; lastTextHeight = h end
        w.SetDesaturated = function(self, d) self.grey = d end
        w.SetVertexColor = function(self, r, g, b) self.tint = { r, g, b } end
        return w
    end
    for _, w in ipairs(frames) do
        w.SetTexture = function(self, t) self.tex = t end
        w.SetTexCoord = function(self, a) self.coordLeft = a end
        w.SetTextHeight = function(self, h) self.textHeight = h; lastTextHeight = h end
        w.SetDesaturated = function(self, d) self.grey = d end
        w.SetVertexColor = function(self, r, g, b) self.tint = { r, g, b } end
    end
    FBT.CombatEventsHandler = RealCombatEventsHandler
    function BigTextures()
        local out = {}
        for _, w in ipairs(frames) do
            if w.kind == "Texture" and w.tex and (string.find(w.tex, "Icons") or string.find(w.tex, "CheckBox")) then out[#out + 1] = w end
        end
        return out
    end
    function FontHeight() return lastTextHeight end
'''


class BigCombatIcon(unittest.TestCase):
    def runtime(self, enter=None, leave=None):
        lua = m.runtime()
        lua.execute(DRAW)
        e = lua.eval("FBT.CurrentProfile.EventSettings")
        if enter is not None:
            e.MSBT_EVENTTYPE_NOTIFICATION_COMBAT_ENTER.BigIcon = enter
        if leave is not None:
            e.MSBT_EVENTTYPE_NOTIFICATION_COMBAT_LEAVE.BigIcon = leave
        return lua

    def test_default_is_text_only(self):
        lua = self.runtime()
        lua.execute('Fire("PLAYER_REGEN_DISABLED"); Fire("PLAYER_REGEN_ENABLED")')
        self.assertEqual(len(lua.eval("BigTextures()")), 0)

    def test_enter_combat_icon_is_twice_the_text(self):
        lua = self.runtime(enter=True)
        lua.execute('Fire("PLAYER_REGEN_DISABLED")')
        icons = lua.eval("BigTextures()")
        self.assertEqual(len(icons), 1)
        self.assertIn("Ability_DualWield", icons[1].tex)
        self.assertEqual(icons[1].coordLeft, 0.125)
        self.assertEqual(icons[1].width, 2 * lua.eval("FontHeight()"))
        self.assertEqual(icons[1].height, icons[1].width)

    def test_leave_combat_shows_the_swords_in_green(self):
        lua = self.runtime(enter=False, leave=True)
        lua.execute('Fire("PLAYER_REGEN_DISABLED"); Fire("PLAYER_REGEN_ENABLED")')
        icons = lua.eval("BigTextures()")
        self.assertEqual(len(icons), 1)
        self.assertIn("Ability_DualWield", icons[1].tex)
        self.assertTrue(icons[1].grey)
        self.assertEqual(list(icons[1].tint.values()), [0.2, 1, 0.2])

    def test_enter_combat_shows_the_swords_in_red(self):
        lua = self.runtime(enter=True)
        lua.execute('Fire("PLAYER_REGEN_DISABLED")')
        icon = lua.eval("BigTextures()")[1]
        self.assertTrue(icon.grey)
        self.assertEqual(list(icon.tint.values()), [1, 0.2, 0.2])

    def test_combat_notices_are_red_and_green(self):
        lua = m.runtime()
        d = lua.eval("FBT.DEFAULT_CONFIG.EventSettings")
        enter = d.MSBT_EVENTTYPE_NOTIFICATION_COMBAT_ENTER.FontSettings.Color
        leave = d.MSBT_EVENTTYPE_NOTIFICATION_COMBAT_LEAVE.FontSettings.Color
        self.assertEqual((enter.r, enter.g, enter.b), (1, 0.25, 0.25))
        self.assertEqual((leave.r, leave.g, leave.b), (0.25, 1, 0.25))

    def test_only_those_two_events_offer_the_icon(self):
        lua = m.runtime()
        keys = sorted(lua.eval("(function() local t = {} for k in pairs(FBT.BIG_ICONS) do t[#t + 1] = k end return t end)()").values())
        self.assertEqual(keys, ["MSBT_EVENTTYPE_NOTIFICATION_COMBAT_ENTER", "MSBT_EVENTTYPE_NOTIFICATION_COMBAT_LEAVE"])


if __name__ == "__main__":
    unittest.main()
