"""Bagnon 2026-11-12: the bank always opens in Bagnon's window.

The "Use Bagnon's bank window" option is retired. Opening the bank opens
Banknon whatever the old setting said, the old setting is cleared on load,
and bank bag slots always belong to Banknon.
"""
import unittest
from bgn_env import ROOT, load

SETUP = '''
    scripts, opened = {}, {}
    function CreateFrame(kind, name)
        local w = widget(name)
        function w:SetScript(n, fn) scripts[n] = fn end
        return w
    end
    BankFrame = widget("BankFrame")
    C_Container.SetBankAutosortDisabled = function() end
    Bagnon = widget("Bagnon"); Banknon = widget("Banknon"); BanknonTitle = widget("BanknonTitle")
    Banknon.title = "%s's Bank"
    function BagnonFrame_Open(name) opened[#opened + 1] = name end
    function Banknon_UpdatePurchaseButtonVis() purchase = true end
    function ShowUIPanel(frame) panel = frame end
'''


def run_file(lua, name):
    lua.execute((ROOT / name).read_text("utf-8-sig"), name)


class BankWindow(unittest.TestCase):
    def open_bank(self, saved):
        lua = load("utility")
        lua.execute(SETUP + saved)
        run_file(lua, "Events.lua")
        lua.execute('''
            scripts.OnEvent(widget(), "ADDON_LOADED", "Bagnon")
            scripts.OnEvent(widget(), "BANKFRAME_OPENED")
        ''')
        return lua

    def test_bank_opens_in_bagnon_with_the_old_setting_off(self):
        lua = self.open_bank("BagnonSets.showBankAtBank = nil; BagnonSets.showBagsAtBank = nil")
        self.assertEqual(list(lua.eval("opened").values()), ["Banknon"])
        self.assertTrue(lua.eval("purchase"))
        self.assertIsNone(lua.eval("panel"))  # the standard bank window stays away

    def test_old_setting_is_cleared_on_load(self):
        lua = self.open_bank("BagnonSets.showBankAtBank = 1")
        self.assertIsNone(lua.eval("BagnonSets.showBankAtBank"))

    def test_a_first_install_has_no_such_setting(self):
        lua = self.open_bank("BagnonSets = nil")
        self.assertIsNone(lua.eval("BagnonSets.showBankAtBank"))

    def test_bank_bag_slots_belong_to_the_bank_window(self):
        lua = load("utility")
        lua.execute('''
            BagnonSets.Banknon = { bags = { -1, 5, 6 } }
            toggled, native = 0, 0
            function ToggleBag() native = native + 1 end
            function OpenBag() end
            function CloseBag() end
            function ToggleKeyRing() end
            function BagnonFrame_Toggle() toggled = toggled + 1 end
        ''')
        run_file(lua, "core/Overrides.lua")
        lua.execute("ToggleBag(5)")
        self.assertEqual(lua.eval("native"), 0)
        self.assertEqual(lua.eval("toggled"), 0)


if __name__ == "__main__":
    unittest.main()
