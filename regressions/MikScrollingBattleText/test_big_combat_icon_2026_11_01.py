"""Enter/Leave Combat can show a large icon beside "+Combat" / "-Combat", 2026-11-01.

The Notices tab has an "Icon" button on those two rows (MikSBT.BIG_ICONS). When
it is on, the message carries the event's icon at twice the font size; when it
is off, nothing changes. The icon files are UNVERIFIED in this client: check
that both show a picture and not a green square.
"""
import unittest

import _msbt_runtime as m

DRAW = '''
    -- Record textures and text heights on every widget the display layer makes.
    local make = NewWidget
    NewWidget = function(name, kind, parent)
        local w = make(name, kind, parent)
        w.SetTexture = function(self, t) self.tex = t end
        w.SetTextHeight = function(self, h) self.textHeight = h; lastTextHeight = h end
        return w
    end
    for _, w in ipairs(frames) do
        w.SetTexture = function(self, t) self.tex = t end
        w.SetTextHeight = function(self, h) self.textHeight = h; lastTextHeight = h end
    end
    MikSBT.CombatEventsHandler = RealCombatEventsHandler
    function BigTextures()
        local out = {}
        for _, w in ipairs(frames) do
            if w.kind == "Texture" and w.tex and string.find(w.tex, "Icons") then out[#out + 1] = w end
        end
        return out
    end
    function FontHeight() return lastTextHeight end
'''


class BigCombatIcon(unittest.TestCase):
    def runtime(self, enter=None, leave=None):
        lua = m.runtime()
        lua.execute(DRAW)
        e = lua.eval("MikSBT.CurrentProfile.EventSettings")
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
        self.assertEqual(icons[1].width, 2 * lua.eval("FontHeight()"))
        self.assertEqual(icons[1].height, icons[1].width)

    def test_leave_combat_has_its_own_icon_and_switch(self):
        lua = self.runtime(enter=False, leave=True)
        lua.execute('Fire("PLAYER_REGEN_DISABLED"); Fire("PLAYER_REGEN_ENABLED")')
        icons = lua.eval("BigTextures()")
        self.assertEqual(len(icons), 1)
        self.assertIn("Spell_Nature_Sleep", icons[1].tex)

    def test_only_those_two_events_offer_the_icon(self):
        lua = m.runtime()
        keys = sorted(lua.eval("(function() local t = {} for k in pairs(MikSBT.BIG_ICONS) do t[#t + 1] = k end return t end)()").values())
        self.assertEqual(keys, ["MSBT_EVENTTYPE_NOTIFICATION_COMBAT_ENTER", "MSBT_EVENTTYPE_NOTIFICATION_COMBAT_LEAVE"])


if __name__ == "__main__":
    unittest.main()
