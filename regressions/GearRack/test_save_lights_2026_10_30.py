"""GearRack: Save lights up while the set editor holds unsaved changes, 2026-10-30.

The player asked for it: after loading a saved set and changing anything, the
Save button should show that a save is needed. It lights (the selected pill)
for a new set and whenever icon, slots, worn items, hide, helm or cloak differ
from what is stored; a save turns it off. The pill colour itself stays an
in-game check.
"""
from pathlib import Path
import os
import unittest
from lupa.lua51 import LuaRuntime

ROOT = Path(os.environ["VANILLAFORGE_ADDON_ROOT"])
EQUIPMENT = (ROOT / "src/Equipment.lua").read_text("utf-8")


def between(text, start, end):
    return text[text.index(start):text.index(end)]


def runtime():
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute('''
        GearRack = { enabled = true, UpdateSetMacro = function() end }
        GearRackUIText = { SAVED = "%s: %d" }
        GearRackDB = { sets = { Me = { Sets = {} } } }
        GearRackUI = { SetBuild = { [1] = 1, [16] = 1 }, SelectedIcon = "iconA" }
        worn = { [1] = "10:0:0", [16] = "20:0:0" }
        GearRackEngine = { ForgetSetUndo = function() end,
            GetItemInfo = function(slot) return nil, worn[slot] or 0 end }
        function widget(t) t = t or {}
            t.Enable = function() end; t.Disable = function() end; t.SetAlpha = function() end
            return t end
        setName = "Tank"
        GearRackUI_Sets_Name = widget({ GetText = function() return setName end, ClearFocus = function() end })
        hidden = nil
        GearRackUI_Sets_HideSet = widget({ GetChecked = function() return hidden end })
        GearRackUI_ShowHelm, GearRackUI_ShowCloak = {}, {}
        GearRackUI_Sets_SaveButton = widget({ fill = {} })
        GearRackUI_Sets_RemoveButton, GearRackUI_Sets_BindButton = widget(), widget()
        GearRackUI_Sets_HideSetText = {}
        UI = { SetEnabled = function() end, Color = function() end }
        ns = { SelectPill = function(button, on) button.lit = on end }
        local user = "Me"
        local function get_item_info(slot) if slot == 16 then return nil, nil, "Mace", "INVTYPE_WEAPON" end end
        local function sets_message() end
        local function build_icon() end
        local validate_set_buttons
    ''' + between(EQUIPMENT, "-- Whether Save would change what is stored", "function GearRackUI_Sets_InvToggle()")
        + between(EQUIPMENT, "function GearRackUI_Sets_Save_OnClick()", "-- equips a set by name, usable in macros")
        + '''
        function check() validate_set_buttons(); return GearRackUI_Sets_SaveButton.lit end
    ''')
    return lua


class SaveLightsTests(unittest.TestCase):
    def setUp(self):
        self.lua = runtime()

    def lit_after(self, change):
        lua = self.lua
        lua.execute("GearRackUI_Sets_Save_OnClick()")
        self.assertFalse(lua.eval("check()"), "saved set is not lit")
        lua.execute(change)
        return lua.eval("check()")

    def test_new_set_is_lit_and_save_clears_it(self):
        self.assertTrue(self.lua.eval("check()"))
        self.lua.execute("GearRackUI_Sets_Save_OnClick()")
        self.assertFalse(self.lua.eval("check()"))

    def test_each_kind_of_change_lights_save(self):
        changes = {
            "icon": 'GearRackUI.SelectedIcon = "iconB"',
            "slot added": "GearRackUI.SetBuild[2] = 1",
            "slot removed": "GearRackUI.SetBuild[1] = 0",
            "other item worn": 'worn[16] = "21:0:0"',
            "hide": "hidden = 1",
            "helm": "GearRackUI_ShowHelm.tristate = 0",
            "cloak": "GearRackUI_ShowCloak.tristate = 1",
        }
        for name, change in changes.items():
            self.lua = runtime()
            self.assertTrue(self.lit_after(change), name)

    def test_undoing_a_change_turns_it_off(self):
        self.assertTrue(self.lit_after('GearRackUI.SelectedIcon = "iconB"'))
        self.lua.execute('GearRackUI.SelectedIcon = "iconA"')
        self.assertFalse(self.lua.eval("check()"))

    def test_no_name_or_no_slots_is_not_lit(self):
        self.lua.execute('setName = ""')
        self.assertFalse(self.lua.eval("check()"))
        self.lua.execute('setName = "Tank"; GearRackUI.SetBuild = {}')
        self.assertFalse(self.lua.eval("check()"))


if __name__ == "__main__":
    unittest.main()
