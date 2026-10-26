"""GearRack audit of 2026-10-25: reproductions that fail on the audited code.

Each test runs the addon's own functions, cut from the source files, under
Lua 5.1 with small mocks. They fail on commit 03888af and pass on the refactored
1.0.0. How the windows look and what the server sends stay
in-game checks.
"""
from pathlib import Path
import os
import re
import unittest
from lupa.lua51 import LuaRuntime

ROOT = Path(os.environ["VANILLAFORGE_ADDON_ROOT"])
EQUIPMENT = (ROOT / "src/Equipment.lua").read_text("utf-8")
CONSTANTS = (ROOT / "src/Constants.lua").read_text("utf-8")
SETS_XML = (ROOT / "src/Sets.xml").read_text("utf-8")


def between(text, start, end):
    return text[text.index(start):text.index(end)]


def runtime():
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(r'''
        GearRack = { enabled = true }
        table.wipe = function(t) for k in pairs(t) do t[k] = nil end return t end
        messages, calls = {}, {}
        DEFAULT_CHAT_FRAME = { AddMessage = function(_, m) table.insert(messages, m) end }
    ''')
    lua.execute(CONSTANTS)
    return lua


class ResetEventsTests(unittest.TestCase):
    """Reset Events wiped every character's "put my old gear back" data."""

    def test_reset_events_keeps_each_sets_restore_data(self):
        lua = runtime()
        lua.execute('''
            GearRackDB = { events = { Mine = { trigger = "X", delay = 0, script = "" } },
                bars = { ["Me of R"] = { Events = {} } },
                sets = { ["Me of R"] = { Sets = { Tank = { [16] = { id = "1:0:0", old = "2:0:0" } } } },
                         ["Alt of R"] = { Sets = { Heal = { [1] = { id = "3:0:0", old = "4:0:0" } } } } } }
            GearRackUI_DefaultEvents = {}
            function GearRackUI_DisableAllEvents() end
            function GearRackUI_EnableAllEvents() end
            function GearRackUI_MigrateDefaultEvents() end
            function GearRackUI_Build_eventList() end
            GearRackUI_Events_ScrollFrameScrollBar = { SetValue = function() end }
            local user = "Me of R"
        ''' + between(EQUIPMENT, 'local function initialize_events(v1)', 'function GearRackUI_OnEvent(')
          + ' initialize_events("reset")')
        self.assertEqual(lua.eval('GearRackDB.sets["Me of R"].Sets.Tank[16].old'), "2:0:0")
        self.assertEqual(lua.eval('GearRackDB.sets["Alt of R"].Sets.Heal[1].old'), "4:0:0")

    def test_reset_events_button_asks_before_deleting(self):
        button = SETS_XML[SETS_XML.index('name="GearRackUI_ResetEventsButton"'):]
        body = re.search(r'<OnClick>(.*?)</OnClick>', button, re.S).group(1)
        lua = runtime()
        lua.execute('''
            function GearRackUI_SlashHandler(cmd) table.insert(calls, "slash:" .. cmd) end
            StaticPopupDialogs = {}
            function StaticPopup_Show(name) table.insert(calls, "popup:" .. name) end
        ''')
        if "function GearRackUI_ConfirmResetEvents()" in EQUIPMENT:
            lua.execute("local function initialize_events() end local function sets_message() end "
                        + between(EQUIPMENT, "function GearRackUI_ConfirmResetEvents()", "--[[ Main bar"))
        lua.execute(body)
        shown = list(lua.eval('calls').values())
        self.assertFalse(any(c.startswith("slash:") for c in shown), shown)
        self.assertTrue(any(c.startswith("popup:") for c in shown), shown)


class BrainwashingGossipTests(unittest.TestCase):
    """Non-activate options of the device printed a debug line to chat."""

    def click(self, text):
        lua = runtime()
        lua.execute('''
            GearRackDB = { settings = { EnableEvents = "ON" } }
            GossipFrameNpcNameText = { GetText = function() return "Goblin Brainwashing Device" end }
            function original_gossip_click() table.insert(calls, "native") end
            function GearRackUI_RegisterFrame_OnEvent(ev, a1) table.insert(calls, ev .. ":" .. tostring(a1 or arg1)) end
            function UnitName() return "Me" end
        ''' + between(EQUIPMENT, 'function gossip_click(...)', '--[[ Inv Movement ]]'))
        lua.globals().optionText = text
        lua.execute('this = { type = "Gossip", GetText = function() return optionText end }'
                    ' gossip_click()')
        return list(lua.eval('messages').values()), list(lua.eval('calls').values())

    def test_buy_tab_option_prints_nothing(self):
        said, calls = self.click("Buy 4th Specialization tab for 200 gold.")
        self.assertEqual(said, [])
        self.assertEqual(calls, ["native"])

    def test_activate_option_still_fires_the_event(self):
        # Control: passes before and after the fix.
        said, calls = self.click("Activate 2nd Specialization  (41/10/0)")
        self.assertEqual(said, [])
        self.assertEqual(calls, ["GEARRACK_GBD:2", "native"])


class SetBuilderTests(unittest.TestCase):
    """Saving a set with a two-hander silently untagged the off hand for later saves."""

    def test_off_hand_survives_an_earlier_two_hander_save(self):
        lua = runtime()
        lua.execute('''
            GearRackDB = { sets = { ["Me"] = { Sets = {} } } }
            GearRack.UpdateSetMacro = function() end
            GearRackUI = { SetBuild = { [16] = 1, [17] = 1 }, SelectedIcon = "icon" }
            mainHand = "INVTYPE_2HWEAPON"
            setName = "Two"
            GearRackUI_Sets_Name = { GetText = function() return setName end, ClearFocus = function() end }
            GearRackUI_Sets_HideSet = { GetChecked = function() end }
            GearRackUI_ShowHelm, GearRackUI_ShowCloak = {}, {}
            GearRackEngine = { ForgetSetUndo = function() end,
                GetItemInfo = function(slot) return nil, slot .. ":0:0" end }
            local user = "Me"
            local function get_item_info(slot)
                if slot == 16 then return nil, nil, "Weapon", mainHand end
                return nil, nil, "Item " .. slot
            end
            local function sets_message() end
            local function draw_minimap_icon() end
            local function validate_set_buttons() end
        ''' + between(EQUIPMENT, '-- save button clicked', '-- equips a set by name, usable in macros')
          + '''
            GearRackUI_Sets_Save_OnClick()
            mainHand, setName = "INVTYPE_WEAPON", "Dual"
            GearRackUI_Sets_Save_OnClick()
        ''')
        self.assertIsNone(lua.eval('GearRackDB.sets.Me.Sets.Two[17]'))
        self.assertIsNotNone(lua.eval('GearRackDB.sets.Me.Sets.Dual[17]'))


class VersionTests(unittest.TestCase):
    """GearRack stays at 1.0.0 until the owner names a new version."""

    def test_version_is_1_0_0(self):
        toc = (ROOT / "GearRack.toc").read_text("utf-8")
        bootstrap = (ROOT / "src/Bootstrap.lua").read_text("utf-8")
        readme = (ROOT / "README.md").read_text("utf-8")
        self.assertIn("## Version: 1.0.0", toc)
        self.assertIn('version="1.0.0"', bootstrap)
        self.assertNotIn("1.1.0", readme)


if __name__ == "__main__":
    unittest.main()
