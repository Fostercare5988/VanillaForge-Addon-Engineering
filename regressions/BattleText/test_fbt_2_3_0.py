"""BattleText 2.3.0, 2026-11-13: what the reference addon does that 2.2.0 did not.

The engine filters the combat log (ClassicAPI's CombatLogAddFilter), so the
nearby combat of others never reaches Lua; ticks of damage and healing over
time and power gains were throttled for 3 s (taken out again in 2.4.1); buff and debuff stacks show their count. Each
test fails on 2.2.0 (ccf7444). Lua model only (_fbt_runtime.py).
"""
import unittest

import _fbt_runtime as m


def display(lua):
    lua.execute("FBT.CombatEventsHandler = RealCombatEventsHandler")


def texts(lua, area):
    return list(lua.eval(f'''(function()
      local out = {{}}
      for _, slot in ipairs(FBT.scrollAreas.{area}.Slots) do
        if slot.IsActive then table.insert(out, slot.FontObject.text) end
      end
      return out end)()''').values())


class EngineFilter(unittest.TestCase):
    def test_no_frame_takes_the_whole_combat_log(self):
        lua = m.runtime()
        self.assertEqual(lua.eval('''(function() local n = 0
          for _, w in ipairs(widgets) do if w.events.COMBAT_LOG_EVENT_UNFILTERED then n = n + 1 end end
          return n end)()'''), 0)
        self.assertGreater(lua.eval("#combatFilters"), 0)

    def test_others_combat_never_reaches_the_addon(self):
        lua = m.runtime()
        lua.execute('''
          handled = 0
          for _, w in ipairs(widgets) do
            if w.events.COMBAT_LOG_EVENT then
              local f = w.scripts.OnEvent
              w.scripts.OnEvent = function(...) handled = handled + 1; return f(...) end
            end
          end
          for i = 1, 50 do CL("SPELL_DAMAGE", "0xF13000AAAA", "Ogre", "0x0000BBBB", "Ally", 133, "Fireball", 4, 500, 0, 4) end
          CL("SWING_DAMAGE", "0xPLAYER", "Hero", "0xENEMY", "Twin", 100, 0, 1)
          CL("SWING_DAMAGE", "0xENEMY", "Twin", "0xPET", "Wolf", 80, 0, 1)
          CL("SWING_DAMAGE", "0xPET", "Wolf", "0xENEMY", "Twin", 60, 0, 1)
          CL("ENVIRONMENTAL_DAMAGE", nil, nil, "0xPLAYER", "Hero", "FALLING", 220, 0, 1)
        ''')
        self.assertEqual(lua.eval("handled"), 4)
        self.assertEqual(len(lua.globals().sent), 4)

    def test_off_leaves_the_client_filter_empty(self):
        lua = m.runtime()
        lua.execute("FBT.SetOptionUserDisabled(true)")
        self.assertEqual(lua.eval("#combatFilters"), 0)
        lua.execute("FBT.SetOptionUserDisabled(false)")
        self.assertGreater(lua.eval("#combatFilters"), 0)


class EveryTick(unittest.TestCase):
    """2.4.1, 2026-11-16: the 3 s throttle of 2.3.0 is gone; players found the
    merged dots confusing. Each tick shows on its own. Fails on 2.4.0 (9e7d7d1)."""

    def tick(self, lua, amount=50):
        lua.execute(f'CL("SPELL_PERIODIC_DAMAGE", "0xPLAYER", "Hero", "0xENEMY", "Twin", 1943, "Rupture", 1, {amount}, 0, 1)')

    def test_each_damage_over_time_tick_shows_on_its_own(self):
        lua = m.runtime()
        display(lua)
        self.tick(lua)
        lua.execute("RunTimersUpTo(0.5)")
        self.tick(lua, amount=60)
        lua.execute("RunTimersUpTo(1.0)")
        shown = texts(lua, "Outgoing")
        self.assertEqual(len(shown), 2)
        self.assertFalse(any("Hits" in t for t in shown))

    def test_direct_damage_still_shows_at_once(self):
        lua = m.runtime()
        display(lua)
        lua.execute('CL("SPELL_DAMAGE", "0xPLAYER", "Hero", "0xENEMY", "Twin", 1752, "Sinister Strike", 1, 200, 0, 1)')
        lua.execute("RunTimersUpTo(0.3)")
        self.assertEqual(len(texts(lua, "Outgoing")), 1)

    def test_heal_over_time_ticks_show_within_the_merge_delay(self):
        lua = m.runtime()
        display(lua)
        lua.execute('CL("SPELL_PERIODIC_HEAL", "0xHEALER", "Priest", "0xPLAYER", "Hero", 139, "Renew", 2, 100, 0, 0)')
        lua.execute("RunTimersUpTo(0.3)")
        shown = texts(lua, "Incoming")
        self.assertEqual(len(shown), 1)
        self.assertIn("+100", shown[0])

    def test_each_power_gain_shows_at_once(self):
        lua = m.runtime()
        display(lua)
        for _ in range(3):
            lua.execute('CL("SPELL_PERIODIC_ENERGIZE", "0xPLAYER", "Hero", "0xPLAYER", "Hero", 12051, "Evocation", 64, 10, 0)')
        shown = texts(lua, "Notification")
        self.assertEqual(len(shown), 3)
        self.assertTrue(all("+10 Mana" in t for t in shown))


class Stacks(unittest.TestCase):
    def test_a_stack_gain_shows_the_count(self):
        lua = m.runtime()
        display(lua)
        lua.execute('''
          CL("SPELL_AURA_APPLIED_DOSE", "0xENEMY", "Twin", "0xPLAYER", "Hero", 7386, "Sunder Armor", 1, "DEBUFF", 3)
          CL("SPELL_AURA_APPLIED_DOSE", "0xPLAYER", "Hero", "0xPLAYER", "Hero", 23735, "Stack Buff", 1, "BUFF", 2)
          CL("SPELL_AURA_APPLIED", "0xPLAYER", "Hero", "0xPLAYER", "Hero", 1784, "Stealth", 1, "BUFF")
        ''')
        shown = texts(lua, "Notification")
        self.assertIn("[Sunder Armor 3]", shown)
        self.assertIn("[Stack Buff 2]", shown)
        self.assertIn("[Stealth]", shown)

    def test_stack_rows_are_in_the_notices_tab(self):
        lua = m.runtime()
        lua.execute("FBT.Options.ShowTab(5)")
        labels = [lua.eval(f"FBT_NotificationRow{i}ShowText:GetText()") for i in range(1, 11)]
        self.assertIn("Debuff Stacks", labels)
        self.assertIn("Buff Stacks", labels)


if __name__ == "__main__":
    unittest.main()
