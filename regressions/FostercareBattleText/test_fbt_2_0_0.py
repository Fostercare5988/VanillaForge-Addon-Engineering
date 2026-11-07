"""FostercareBattleText 2.0.0, 2026-11-03: the rename and the rewritten paths.

MSBT 1.2.2 became FostercareBattleText: one namespace (FostercareBattleText,
FBT in the files) instead of MikSBT, MikCEH, MikTRO, MikSBTOpt and
MSBT_REQUIREMENTS_MET; frames made in Lua instead of two XML files; honor and
skill lines matched by patterns built from their GlobalStrings; one scroll
function for the six curves. These tests pin the moved paths. Lua model only.
"""
import unittest

import _fbt_runtime as m


def display(lua):
    lua.execute("FBT.CombatEventsHandler = RealCombatEventsHandler")


def texts(lua, area="Notification"):
    return lua.eval(f'''(function()
      local out = {{}}
      for _, slot in ipairs(FBT.scrollAreas.{area}.Slots) do
        if slot.IsActive then table.insert(out, slot.FontObject.text) end
      end
      return out end)()''')


class Namespace(unittest.TestCase):
    def test_only_the_namespace_saved_table_and_slash_are_global(self):
        lua = m.runtime()
        for name in ("MikSBT", "MikCEH", "MikTRO", "MikSBTOpt", "MSBT_REQUIREMENTS_MET",
                     "MCEHEventFrame", "MSBTEventFrame", "MSBTFrameIncoming"):
            self.assertIsNone(lua.eval(f"rawget(_G, '{name}')"), name)
        self.assertEqual(lua.eval("FostercareBattleText.DisplayMessage ~= nil"), True)
        self.assertEqual(lua.eval("type(FostercareBattleTextDB.Profiles.Default)"), "table")

    def test_without_classicapi_nothing_loads(self):
        lua = m.wowkit.runtime()
        lua.execute(m.BOOT)
        lua.execute("CLASSIC_API_VERSION = nil")
        load = lua.eval('''function(source, name)
          local chunk = assert(loadstring(source, "@" .. name)); chunk("FostercareBattleText", NS)
        end''')
        lua.execute("NS = {}")
        for name in m.toc_lua_files():
            load(m.wowkit.lua50((m.ROOT / name).read_text("utf-8-sig")), name)
        self.assertIsNone(lua.eval("FostercareBattleText"))
        self.assertIsNone(lua.eval("NS.Combat"))
        self.assertIn("ClassicAPI", lua.eval("chat[1]"))


class ChatLines(unittest.TestCase):
    def test_honor_and_skill_lines(self):
        lua = m.runtime()
        lua.execute('''
          sent = {}
          Fire("CHAT_MSG_COMBAT_HONOR_GAIN", "Bob dies, honorable kill Rank: Private (Estimated Honor Points: 12)")
          Fire("CHAT_MSG_COMBAT_HONOR_GAIN", "You have been awarded 198 honor points.")
          Fire("CHAT_MSG_COMBAT_HONOR_GAIN", "Something else.")
          Fire("CHAT_MSG_SKILL", "Your skill in Swords has increased to 120.")
        ''')
        sent, ceh = lua.globals().sent, lua.eval("FBT.Combat")
        got = [(e.NotificationType, e.Amount, e.EffectName) for e in sent.values()]
        self.assertEqual(got, [(ceh.NOTIFICATIONTYPE_HONOR_GAIN, "12", None),
                               (ceh.NOTIFICATIONTYPE_HONOR_GAIN, "198", None),
                               (ceh.NOTIFICATIONTYPE_SKILL_GAIN, "120", "Swords")])


class Slash(unittest.TestCase):
    def test_fbt_and_the_old_msbt_command(self):
        lua = m.runtime()
        self.assertEqual(lua.eval("SLASH_FOSTERCAREBATTLETEXT1"), "/fbt")
        self.assertEqual(lua.eval("SLASH_FOSTERCAREBATTLETEXT2"), "/msbt")
        lua.execute('SlashCmdList.FOSTERCAREBATTLETEXT("")')
        self.assertTrue(lua.eval("FBT_Options:IsShown()"))
        lua.execute('SlashCmdList.FOSTERCAREBATTLETEXT("disable")')
        self.assertTrue(lua.eval("FostercareBattleTextDB.UserDisabled"))
        self.assertEqual(lua.eval("cvars.CombatDamage"), "1")
        self.assertEqual(lua.eval("next(FBT.Combat.frame.events)"), None)
        lua.execute('SlashCmdList.FOSTERCAREBATTLETEXT("ENABLE")')
        self.assertFalse(lua.eval("FostercareBattleTextDB.UserDisabled"))
        self.assertEqual(lua.eval("cvars.CombatDamage"), "0")


class Scrolling(unittest.TestCase):
    def run_one(self, style, direction):
        lua = m.runtime()
        lua.execute(f'''
          local s = FBT.CurrentProfile.DisplaySettings.Notification
          s.AnimationStyle, s.ScrollDirection, s.ScrollHeight = {style}, {direction}, 200
          FBT.DisplayMessage("x", FBT.DISPLAYTYPE_NOTIFICATION, false)
          slot = FBT.scrollAreas.Notification.Slots[1]
          startY = slot.PositionY
          now = now + 0.2; FBT.OnUpdateAnimationFrame(FBT.scrollAreas.Notification.Frame)
        ''')
        return lua

    def test_straight_up_moves_by_time_and_fades_in_the_top_half(self):
        lua = self.run_one(1, 1)
        # 1.5 per 0.02 s, for 0.2 s.
        self.assertEqual((lua.eval("startY"), lua.eval("slot.PositionX")), (0, 0))
        self.assertAlmostEqual(lua.eval("slot.PositionY"), 15)
        self.assertEqual(lua.eval("slot.Alpha"), 1)
        lua.execute("now = now + 2; FBT.OnUpdateAnimationFrame(FBT.scrollAreas.Notification.Frame)")
        self.assertAlmostEqual(lua.eval("slot.Alpha"), 1 - (165 - 100) / 100)

    def test_down_starts_at_the_top(self):
        lua = self.run_one(1, 2)
        self.assertEqual((lua.eval("startY"), lua.eval("slot.PositionY")), (200, 185))

    def test_curves_left_and_right(self):
        # x = ceil(mid / 4) - ceil((y - mid)^2 / (4 * mid)), mirrored for the left.
        left, right = self.run_one(2, 1), self.run_one(3, 1)
        # At y = 15 of 200: 25 - ceil(85^2 / 400) = 25 - 19.
        self.assertEqual(left.eval("slot.PositionX"), -6)
        self.assertEqual(right.eval("slot.PositionX"), 6)

    def test_the_area_hides_when_the_text_ends(self):
        lua = self.run_one(1, 1)
        lua.execute("now = now + 10; FBT.OnUpdateAnimationFrame(FBT.scrollAreas.Notification.Frame)")
        self.assertFalse(lua.eval("slot.IsActive"))
        lua.execute("FBT.OnUpdateAnimationFrame(FBT.scrollAreas.Notification.Frame)")
        self.assertFalse(lua.eval("FBT.scrollAreas.Notification.Frame.shown"))


class Stickies(unittest.TestCase):
    def positions(self, direction):
        lua = m.runtime()
        lua.execute(f'''
          local s = FBT.CurrentProfile.DisplaySettings.Notification
          s.ScrollDirection, s.ScrollHeight = {direction}, 200
          for i = 1, 3 do FBT.DisplayMessage("s" .. i, FBT.DISPLAYTYPE_NOTIFICATION, true, nil, nil, nil, 20) end
        ''')
        return [lua.eval(f"FBT.scrollAreas.Notification.Slots[{i}].PositionY") for i in (11, 12, 13)]

    def test_three_stickies_stack_around_the_middle(self):
        # Up: oldest on top. Down: oldest at the bottom. 20 high, 8 apart.
        self.assertEqual(self.positions(1), [128, 100, 72])
        self.assertEqual(self.positions(2), [72, 100, 128])


class MergeTrailer(unittest.TestCase):
    def test_three_hits_on_one_target_show_as_one_line(self):
        lua = m.runtime()
        display(lua)
        lua.execute('''
          CL("SWING_DAMAGE", "0xPLAYER", "Hero", "0xENEMY", "Twin", 100, 0, 1)
          CL("SWING_DAMAGE", "0xPLAYER", "Hero", "0xENEMY", "Twin", 150, 0, 1, nil, nil, nil, 1)
          CL("SWING_DAMAGE", "0xPLAYER", "Hero", "0xENEMY", "Twin", 50, 0, 1)
          RunTimers()
        ''')
        self.assertEqual(list(texts(lua, "Outgoing").values()), ["300 [3 Hits, 1 Crit]"])


if __name__ == "__main__":
    unittest.main()
