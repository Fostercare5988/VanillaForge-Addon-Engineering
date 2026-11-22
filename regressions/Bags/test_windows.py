"""The windows: first login, the stock routes, opening by itself, the bank (spec 4.5,
tests 1, 2 and 3). Bags 1.0, written new 2026-11-22.
"""
import unittest
from bags_env import load, frame


def shown(lua, kind):
    return bool(lua.eval(f"window('{kind}'):IsShown()"))


class FirstLogin(unittest.TestCase):
    def test_named_movable_and_put_back_by_the_client_at_the_first_frame(self):
        lua = load(world=False, layout={"BagsInventory": (1068, -386), "BagsBank": (380, -54)})
        self.assertTrue(lua.eval("BagsInventory:IsUserPlaced()"))
        self.assertEqual(lua.eval("BagsInventory:GetNumPoints()"), 0, "no place of ours over the client's")
        lua.execute('fire("VARIABLES_LOADED") fire("PLAYER_LOGIN") fire("PLAYER_ENTERING_WORLD") step()')
        self.assertEqual(lua.eval("BagsInventory:GetLeft()"), 1068)
        self.assertEqual(lua.eval("BagsBank:GetLeft()"), 380)
        self.assertEqual(lua.eval("luaErrors[1]"), None)

    def test_with_no_cache_the_first_install_places(self):
        lua = load()
        self.assertEqual(lua.eval("(function() local p, r, q, x, y = BagsInventory:GetPoint(1);"
                                  " return table.concat({ p, tostring(r == UIParent), q, x, y }, ' ') end)()"),
                         "TOPLEFT true BOTTOMLEFT 1078 495")
        self.assertEqual(lua.eval("(select(4, BagsBank:GetPoint(1)))"), 192)

    def test_escape_closes_both(self):
        lua = load()
        self.assertEqual(lua.eval("table.concat(UISpecialFrames, ',')"), "BagsInventory,BagsBank")

    def test_a_drag_moves_it_and_the_client_keeps_the_place(self):
        lua = load()
        lua.execute("ToggleBackpack(); run(BagsInventory, 'OnDragStart')")
        self.assertTrue(lua.eval("BagsInventory.moving"))
        self.assertTrue(lua.eval("BagsInventory:IsUserPlaced()"))
        lua.execute("run(BagsInventory, 'OnDragStop')")
        self.assertIsNone(lua.eval("BagsInventory.moving"))


class StockRoutes(unittest.TestCase):
    def test_the_game_keys_toggle_the_inventory(self):
        lua = load()
        for call in ("ToggleBackpack()", "OpenAllBags()", "ToggleBag(0)", "ToggleBag(4)"):
            lua.execute(call)
            self.assertTrue(shown(lua, "inventory"), call)
            lua.execute(call)
            self.assertFalse(shown(lua, "inventory"), call)
        lua.execute("OpenAllBags(true); OpenAllBags(true)")
        self.assertTrue(shown(lua, "inventory"))
        lua.execute("CloseAllBags()")
        self.assertFalse(shown(lua, "inventory"))

    def test_other_bags_keep_the_stock_functions(self):
        lua = load()
        lua.execute("ToggleBag(5); OpenBag(-2); CloseBag(7)")
        self.assertEqual(lua.eval("calls.ToggleBag"), 5)
        self.assertEqual(lua.eval("calls.OpenBag"), -2)
        self.assertEqual(lua.eval("calls.CloseBag"), 7)
        self.assertFalse(shown(lua, "inventory"))

    def test_a_merchant_opens_it_by_itself_and_closes_only_that(self):
        lua = load()
        lua.execute("OpenBackpack()")
        self.assertTrue(shown(lua, "inventory"))
        lua.execute("CloseBackpack()")
        self.assertFalse(shown(lua, "inventory"))
        lua.execute("ToggleBackpack(); OpenBackpack(); CloseBackpack()")
        self.assertTrue(shown(lua, "inventory"), "a window opened by hand stays")

    def test_opened_by_itself_then_by_hand_stays(self):
        lua = load()
        lua.execute("OpenBackpack(); OpenAllBags(true); CloseBackpack()")
        self.assertTrue(shown(lua, "inventory"))

    def test_the_mailbox_and_the_auction_house(self):
        lua = load()
        lua.execute("OpenBackpack(); fire('MAIL_CLOSED')")
        self.assertFalse(shown(lua, "inventory"))
        lua.execute("fire('AUCTION_HOUSE_SHOW')")
        self.assertTrue(shown(lua, "inventory"))
        lua.execute("fire('AUCTION_HOUSE_CLOSED')")
        self.assertFalse(shown(lua, "inventory"))
        lua.execute("ToggleBackpack(); fire('AUCTION_HOUSE_SHOW'); fire('AUCTION_HOUSE_CLOSED')")
        self.assertTrue(shown(lua, "inventory"))


class Bank(unittest.TestCase):
    def test_a_banker_shows_ours_and_the_inventory_never_the_stock_frame(self):
        lua = load()
        lua.execute("openBank()")
        self.assertTrue(shown(lua, "bank"))
        self.assertTrue(shown(lua, "inventory"))
        self.assertFalse(lua.eval("BankFrame:IsShown()"))
        self.assertTrue(lua.eval("BagsBank:Live()"))
        self.assertEqual(lua.eval("BagsBank.holders[-1].size"), 24)

    def test_closing_our_bank_closes_the_bank(self):
        lua = load()
        lua.execute("openBank(); BagsBank:Hide()")
        self.assertEqual(lua.eval("count('CloseBankFrame')"), 1)
        self.assertFalse(shown(lua, "inventory"), "it opened by itself")

    def test_leaving_the_banker_hides_both_but_a_hand_opened_inventory_stays(self):
        lua = load()
        lua.execute("ToggleBackpack(); openBank(); closeBank()")
        self.assertFalse(shown(lua, "bank"))
        self.assertTrue(shown(lua, "inventory"))
        self.assertEqual(lua.eval("count('CloseBankFrame')"), 0)

    def test_away_from_a_banker_the_bank_button_shows_the_stored_bank(self):
        lua = load()
        lua.execute("openBank(); closeBank(); ToggleBackpack()")
        self.assertTrue(lua.eval("BagsInventory.bankButton:IsEnabled()"))
        lua.execute("click(BagsInventory.bankButton)")
        self.assertTrue(shown(lua, "bank"))
        self.assertFalse(lua.eval("BagsBank:Live()"))
        self.assertEqual(lua.eval("BagsBank.holders[-1].size"), 24)
        self.assertEqual(lua.eval("button('bank', -1, 24).link"), "item:15138:2619:0:0")
        self.assertEqual(lua.eval("button('bank', 5, 3).count"), 2)
        self.assertFalse(lua.eval("BagsBank.sort:IsEnabled()"))

    def test_no_bank_visit_no_bank_button(self):
        lua = load()
        lua.execute("ToggleBackpack()")
        self.assertFalse(lua.eval("BagsInventory.bankButton:IsEnabled()"))


if __name__ == "__main__":
    unittest.main()
