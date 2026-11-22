"""Nothing at rest (spec 4.5, test 17): no OnUpdate, no repeating timer, a closed
window hears only its show events. Bags 1.0, written new 2026-11-22.
"""
import unittest
from bags_env import load, frame


class AtRest(unittest.TestCase):
    def test_no_onupdate_and_no_timer_after_login_a_zone_change_and_a_loading_screen(self):
        lua = load()
        lua.execute("fire('ZONE_CHANGED_NEW_AREA'); fire('PLAYER_ENTERING_WORLD'); step(1); step(1)")
        self.assertEqual(lua.eval("onUpdates()"), 0)
        self.assertEqual(lua.eval("liveTimers()"), 0)
        self.assertIsNone(lua.eval("luaErrors[1]"))

    def test_closed_windows_listen_to_nothing(self):
        lua = load()
        self.assertEqual(lua.eval("listening(BagsInventory)"), "")
        self.assertEqual(lua.eval("listening(BagsBank)"), "")
        lua.execute("ToggleBackpack(); ToggleBackpack()")
        self.assertEqual(lua.eval("listening(BagsInventory)"), "")

    def test_a_loot_burst_with_both_windows_closed_calls_no_container_function(self):
        lua = load()
        lua.execute("forget()")
        for i in range(12):
            lua.execute(f"fire('BAG_UPDATE', {i % 5}); fire('ITEM_LOCK_CHANGED'); fire('BAG_UPDATE_COOLDOWN')")
        lua.execute("fire('BAG_UPDATE_DELAYED'); fire('BAG_NEW_ITEMS_UPDATED')")
        frame(lua)
        self.assertEqual(lua.eval("count('GetContainerItemInfo')"), 0)
        self.assertEqual(lua.eval("count('GetItemTempEnchantInfo')"), 0)

    def test_an_open_window_coalesces_a_burst_into_one_timer_per_frame(self):
        lua = load()
        lua.execute("ToggleBackpack(); forget()")
        for _ in range(6):
            lua.execute("fire('ITEM_LOCK_CHANGED'); fire('BAG_UPDATE_COOLDOWN')")
        self.assertEqual(lua.eval("liveTimers()"), 1)
        frame(lua)
        self.assertEqual(lua.eval("liveTimers()"), 0)
        self.assertEqual(lua.eval("count('GetContainerItemInfo')"), 36)

    def test_the_stock_bank_frame_no_longer_opens(self):
        lua = load()
        self.assertFalse(lua.eval("receives(BankFrame, 'BANKFRAME_OPENED')"))

    def test_stray_saved_keys_are_swept(self):
        lua = load("BagsDB = { bagBar = { inventory = true, bank = false }, cols = 10, showSortButton = 0 }")
        self.assertIsNone(lua.eval("BagsDB.cols"))
        self.assertIsNone(lua.eval("BagsDB.showSortButton"))
        self.assertTrue(lua.eval("BagsDB.bagBar.inventory"))


if __name__ == "__main__":
    unittest.main()
