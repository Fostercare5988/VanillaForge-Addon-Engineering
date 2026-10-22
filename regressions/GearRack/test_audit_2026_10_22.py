"""GearRack regressions for the 2026-10-22 review and Ember restyle.

- Ammo is read from NamPower GetAmmo(), not a hidden tooltip and a bag search.
- One-hand weapons go to the off hand only when ClassicAPI CanDualWield() says so.
- The event script tip names functions that exist.
- The windows load the ForgeUI skin: tabs are pills on a track, the selected tab
  and list rows fill with the accent, trinket rows are outlined so item-quality
  names stay readable, and the gear bars keep their own art.

The mocks do not prove how the client draws the windows; check them in game.
"""
import unittest
import gr_env

CORE = ["Bootstrap.lua", "ForgeUI.lua", "Core.lua", "Constants.lua", "Events.lua", "Equipment.lua"]

STUBS = r'''
function GetInventoryItemLink() end
function GetInventoryItemQuality(_, slot) if slot == 0 then return 1 end end
function GetInventorySlotInfo() return 0, "Interface\\PaperDoll\\UI-PaperDoll-Slot-Ammo" end
function GetInventoryItemTexture(_, slot) if slot == 0 then return "Interface\\Icons\\INV_Ammo_Arrow_02" end end
function GetContainerNumSlots() return 0 end
function GetAmmo() return 2512, 200 end
ITEMS = {
    ["2512"] = { "Rough Arrow", "link", 1, 5, "Projectile", "Arrow", 200, "INVTYPE_AMMO", "Interface\\Icons\\INV_Ammo_Arrow_02" },
    ["1234"] = { "Blade", "link", 3, 60, "Weapon", "Swords", 1, "INVTYPE_WEAPON", "Interface\\Icons\\INV_Sword_04" },
}
function GetItemInfo(id) local i = ITEMS[tostring(id)]; if i then return unpack(i) end end
canDualWield = false
function CanDualWield() return canDualWield end
C_PlayerInfo = { CanUseItem = function() return true end }
C_Item = { GetItemGUID = function() end }
GearRackTrinkets = { UpdateCombatQueue = function() end, CombatQueue = {}, QueueItemIDs = {} }
newWidget("FontString", "GearRackUI_ItemTooltipTextLeft1").text = "Rough Arrow"
function sameColor(c, ref)
    return c ~= nil and math.abs(c[1] - ref[1]) < 1e-6 and math.abs(c[2] - ref[2]) < 1e-6
        and math.abs(c[3] - ref[3]) < 1e-6 and math.abs((c[4] or 1) - (ref[4] or 1)) < 1e-6
end
'''


def env(files):
    e = gr_env.Env([])
    e.run(STUBS)
    loader = e.lua.eval('function(src, name, ns) local f = assert(loadstring(src, name)); return f("GearRack", ns) end')
    for f in files:
        # Versions before the restyle have no ForgeUI kit.
        if f == "ForgeUI.lua" and not (gr_env.SRC / f).exists():
            continue
        loader(gr_env.text(f), f, e.ns)
    e.lua.globals().UI = e.ns.UI
    return e


class DLLs(unittest.TestCase):
    def test_ammo_slot_comes_from_nampower(self):
        e = env(CORE)
        info = e.eval("{GearRackEngine.GetItemInfo(0)}")
        self.assertEqual(info[2], "2512:0:0")
        self.assertEqual(info[3], "Rough Arrow")
        self.assertEqual(info[4], "INVTYPE_AMMO")
        self.assertEqual(info[5], 1)
        self.assertEqual(len(list(e.eval("GearRackUI_ItemTooltip.calls").values())), 0,
                         "the ammo slot must not be read from a tooltip")

    def test_off_hand_weapon_follows_can_dual_wield(self):
        e = env(CORE)
        request = 'GearRack.RequestItem(17, { id = "1234:0:0", name = "Blade", guid = "0xA" })'
        e.run("canDualWield = false; " + request)
        self.assertIsNone(e.eval("GearRack.Requests[17]"))
        self.assertIn("cannot be equipped", e.eval("messages[#messages]"))
        e.run("canDualWield = true; " + request)
        self.assertIsNotNone(e.eval("GearRack.Requests[17]"))


class Text(unittest.TestCase):
    def test_event_script_tip_names_real_functions(self):
        sets = gr_env.text("Sets.xml")
        self.assertIn("GearRack.EquipSet()", sets)
        self.assertIn("GearRack.LoadSet()", sets)
        self.assertNotIn("SaveSet()", sets)


class Skin(unittest.TestCase):
    def setUp(self):
        self.e = env(CORE + ["Skin.lua"])

    def color(self, expr, role):
        return self.e.eval("sameColor(%s, UI.%s)" % (expr, role))

    def test_tabs_are_pills_on_a_track(self):
        e = self.e
        self.assertTrue(e.eval("GearRackUI_Sets_Tab1:GetParent() == GearRackUI_Sets_TabTrack"))
        self.assertTrue(e.eval("GearRackUI_Sets_Tab1:GetFrameLevel() > GearRackUI_Sets_TabTrack:GetFrameLevel()"))
        e.run("GearRackUI_Tab(2)")
        self.assertTrue(self.color("GearRackUI_Sets_Tab2.fill[5].color", "selected"))
        self.assertTrue(self.color("GearRackUI_Sets_Tab2.textColor", "text"))
        self.assertTrue(self.color("GearRackUI_Sets_Tab1.fill[5].color", "clear"))
        self.assertTrue(self.color("GearRackUI_Sets_Tab1.textColor", "hint"))

    def test_trinket_queue_checkboxes_sit_on_their_tabs(self):
        e = self.e
        self.assertTrue(e.eval("GearRackTrinkets_Trinket0Check:GetParent() == GearRackTrinkets_Tab3"))
        self.assertTrue(e.eval("GearRackTrinkets_Trinket1Check:GetParent() == GearRackTrinkets_Tab2"))
        self.assertTrue(e.eval("GearRackTrinkets_Trinket0Check:GetFrameLevel() > GearRackTrinkets_Tab3:GetFrameLevel()"))

    def test_buttons_are_control_pills(self):
        self.assertTrue(self.color("GearRackUI_Sets_SaveButton.fill[5].color", "control"))
        self.assertTrue(self.color("GearRackUI_Sets_SaveButton.textColor", "text"))
        self.assertTrue(self.color("GearRackTrinkets_ProfilesLoad.fill[5].color", "control"))

    def test_selected_rows(self):
        e = self.e
        select = e.ns.SelectRow
        select(e.eval("GearRackUI_Event1"), True)
        self.assertTrue(self.color("GearRackUI_Event1.fill[5].color", "selected"))
        # Trinket names keep their quality colors, so the row is outlined, not filled.
        select(e.eval("GearRackTrinkets_Sort1"), True)
        self.assertTrue(self.color("GearRackTrinkets_Sort1.fill[5].color", "accent"))
        self.assertTrue(self.color("GearRackTrinkets_Sort1.inner[5].color", "track"))
        select(e.eval("GearRackTrinkets_Sort1"), False)
        self.assertTrue(self.color("GearRackTrinkets_Sort1.fill[5].color", "clear"))

    def test_set_list_button_is_clickable(self):
        # The name box spans the arrow button; it must not take the button's clicks.
        e = self.e
        self.assertGreaterEqual(e.eval("GearRackUI_Sets_Name.hitInsets[2]"), 24)
        self.assertTrue(e.eval("GearRackUI_Sets_DropDownButton:GetFrameLevel() > GearRackUI_Sets_Name:GetFrameLevel()"))

    def test_gear_keeps_its_art(self):
        # The windows lose the old Blizzard button art and backdrops; the bars keep theirs.
        for name in ("Sets.xml", "TrinketOptions.xml", "TrinketQueues.xml"):
            xml = gr_env.text(name)
            self.assertNotIn("UIPanelButtonGrayTemplate", xml, name)
            self.assertNotIn("GameMenuButtonTemplate", xml, name)
            self.assertNotIn("<Backdrop", xml, name)
        self.assertIn("<Backdrop", gr_env.text("Equipment.xml"))
        self.assertIn("<Backdrop", gr_env.text("Trinkets.xml"))
        self.assertIn("ActionButtonTemplate", gr_env.text("Sets.xml"))


if __name__ == "__main__":
    unittest.main()
