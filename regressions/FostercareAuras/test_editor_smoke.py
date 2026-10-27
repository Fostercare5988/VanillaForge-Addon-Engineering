"""Editor smoke test, 2026-10-27: both addons load through login under a
permissive widget mock; the editor opens on an Ability, a Buff, a Debuff and
both weapon-hand trackers, and every visible checkbox is clicked and every
visible dropdown opened. Any Lua error fails. This guards removals in the
editor: a widget that is gone but still used shows up here instead of in game.
A bag item tracker (Hearthstone) is deleted at login since the rogue pass.
"""
import unittest
import fa_harness

SAVED = r'''
FostercareAurasDB = { spells = {
  Kick_Ability = { type = "Ability", displayName = "Kick", name = "Kick", order = 1, key = "Kick_Ability",
    offsetX = 0, offsetY = 0, iconSize = 36, conditions = { ability = { mode = "notcd" } } },
  SliceAndDice_Buff = { type = "Buff", displayName = "Slice and Dice", order = 2, key = "SliceAndDice_Buff",
    offsetX = 0, offsetY = 0, iconSize = 36, conditions = { aura = { mode = "found", textTimeRemaining = true } } },
  Rupture_Debuff = { type = "Debuff", displayName = "Rupture", order = 3, key = "Rupture_Debuff",
    offsetX = 0, offsetY = 0, iconSize = 36, conditions = { aura = { mode = "found", onlyMine = true, targetHarm = true } } },
  Hearthstone_Item = { type = "Item", displayName = "Hearthstone", order = 4, key = "Hearthstone_Item",
    offsetX = 0, offsetY = 0, iconSize = 36, conditions = { item = { mode = "notcd" } } },
  MainHand_Item = { type = "Item", displayName = "---EQUIPPED WEAPON SLOTS---", shownName = "Main hand poison",
    order = 5, key = "MainHand_Item", offsetX = 0, offsetY = 0, iconSize = 52,
    conditions = { item = { mode = "notcd", inventorySlot = "MAINHAND", textTimeRemaining = true } } },
  OffHand_Item = { type = "Item", displayName = "---EQUIPPED WEAPON SLOTS---", shownName = "Off hand poison",
    order = 6, key = "OffHand_Item", offsetX = 0, offsetY = 0, iconSize = 52,
    conditions = { item = { mode = "notcd", inventorySlot = "OFFHAND", textStackCounter = true } } },
} }
'''
KEYS = ("Kick_Ability", "SliceAndDice_Buff", "Rupture_Debuff", "MainHand_Item", "OffHand_Item")


class EditorSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lua = fa_harness.load(SAVED)

    def test_every_tracker_opens_and_every_control_runs(self):
        lua = self.lua
        lua.execute('FIRSTOPEN = nil')
        clicked = lua.execute(r'''
          local open = FostercareConditions_Show
          if not open then LoadAddOn("FostercareAuras_Edit"); open = FostercareConditions_Show end
          local n = 0
          for _, key in ipairs({ %s }) do
            FostercareConditions_Show(key)
            for _, f in ipairs(CREATED) do
              if f._kind == "CheckButton" and f._scripts.OnClick and f:IsVisible() then
                for _ = 1, 2 do
                  f._checked = (not f._checked) and 1 or nil
                  RUN(f, "OnClick", "LeftButton")
                  n = n + 1
                end
              end
              if f._init and f:IsVisible() then
                this = f
                f._init(f, 1)
              end
            end
          end
          return n
        ''' % ", ".join('"%s"' % k for k in KEYS))
        self.assertGreater(clicked, 50)

    def test_bag_item_trackers_are_gone_after_login(self):
        # 2026-10-27 rogue pass: only the two weapon hands stay item trackers.
        self.assertIsNone(self.lua.eval('FostercareAurasDB.spells.Hearthstone_Item'))
        self.assertIsNotNone(self.lua.eval('FostercareAurasDB.spells.OffHand_Item'))


if __name__ == "__main__":
    unittest.main()
