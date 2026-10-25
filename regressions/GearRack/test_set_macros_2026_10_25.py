"""Gear sets on action bars (2026-10-25), and the help text's version line.

SetMacros.lua runs under Lua 5.1 with a recording macro API that follows the
ClassicAPI docs (C_Macro.CreateMacro/EditMacro, names in GetMacroInfo/
DeleteMacro). Whether the client shortens long macro names, and macro use in
combat, stay in-game checks.
"""
from pathlib import Path
import os
import unittest
from lupa.lua51 import LuaRuntime

ROOT = Path(os.environ["VANILLAFORGE_ADDON_ROOT"])
SET_MACROS = (ROOT / "src/SetMacros.lua").read_text("utf-8")
SETS_XML = (ROOT / "src/Sets.xml").read_text("utf-8")


def runtime():
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(r'''
        GearRack = { enabled = true, CharacterKey = function() return "Me" end }
        GearRackDB = { sets = { Me = { Sets = {
            Tank = { icon = "Interface\\Icons\\INV_Shield_06" },
            Own = { icon = "Interface\\AddOns\\GearRack\\media\\GearRack-Icon.tga" } } } } }
        macros, picked, said = {}, {}, {}
        DEFAULT_CHAT_FRAME = { AddMessage = function(_, m) table.insert(said, m) end }
        local function find(key)
            if type(key) == "number" then return macros[key] and key end
            for i, m in ipairs(macros) do if m.name == key then return i end end
        end
        function GetMacroIndexByName(name) return find(name) or 0 end
        function GetMacroInfo(key) local i = find(key); if i then return macros[i].name, macros[i].icon, macros[i].body end end
        function DeleteMacro(key) local i = find(key); if i then table.remove(macros, i) end end
        function PickupMacro(i) table.insert(picked, i) end
        full = false
        C_Macro = {
            CreateMacro = function(name, icon, body, perChar)
                if full then return nil end
                table.insert(macros, { name = name, icon = icon, body = body, perChar = perChar })
                return #macros
            end,
            EditMacro = function(i, name, icon, body) if icon then macros[i].icon = icon end return i end,
        }
    ''')
    lua.execute(SET_MACROS)
    return lua


class SetMacroTests(unittest.TestCase):
    def test_first_drag_makes_one_character_macro_and_picks_it_up(self):
        lua = runtime()
        lua.execute('GearRack.PickupSetMacro("Tank"); GearRack.PickupSetMacro("Tank")')
        self.assertEqual(lua.eval('#macros'), 1)
        self.assertEqual(lua.eval('macros[1].body'), "/gr equip Tank")
        self.assertEqual(lua.eval('macros[1].icon'), "INV_Shield_06")
        self.assertTrue(lua.eval('macros[1].perChar'))
        self.assertEqual(list(lua.eval('picked').values()), [1, 1])

    def test_icon_outside_interface_icons_falls_back(self):
        lua = runtime()
        lua.execute('GearRack.PickupSetMacro("Own")')
        self.assertEqual(lua.eval('macros[1].icon'), "INV_Misc_QuestionMark")

    def test_save_updates_icon_and_remove_deletes_the_macro(self):
        lua = runtime()
        lua.execute('''GearRack.PickupSetMacro("Tank")
            GearRackDB.sets.Me.Sets.Tank.icon = "Interface\\\\Icons\\\\INV_Sword_25"
            GearRack.UpdateSetMacro("Tank")''')
        self.assertEqual(lua.eval('macros[1].icon'), "INV_Sword_25")
        lua.execute('GearRack.DeleteSetMacro("Tank")')
        self.assertEqual(lua.eval('#macros'), 0)

    def test_players_own_macro_of_the_same_name_is_left_alone(self):
        lua = runtime()
        lua.execute('''table.insert(macros, { name = "Tank", body = "/say mine" })
            GearRack.PickupSetMacro("Tank")
            GearRack.DeleteSetMacro("Tank")''')
        self.assertEqual(lua.eval('#macros'), 1)
        self.assertEqual(lua.eval('macros[1].body'), "/say mine")
        self.assertEqual(lua.eval('#picked'), 0)
        self.assertEqual(lua.eval('#said'), 1)

    def test_full_macro_tab_says_so_and_does_not_pick_up(self):
        lua = runtime()
        lua.execute('full = true; GearRack.PickupSetMacro("Tank")')
        self.assertEqual(lua.eval('#picked'), 0)
        self.assertIn("full", lua.eval('said[1]'))


class HelpTextTests(unittest.TestCase):
    def test_help_text_reads_the_addon_version(self):
        # The 1.0.0 refactor removed GearRackUI_Version; the help box still read it.
        self.assertNotIn("GearRackUI_Version", SETS_XML)


if __name__ == "__main__":
    unittest.main()
