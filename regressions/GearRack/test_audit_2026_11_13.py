"""GearRack regressions for the 2026-11-13 audit.

Sets remember the exact copy of an item (its ClassicAPI GUID, which ClassicAPI's
own equipment sets keep between sessions): two identical daggers carrying
different poisons are two different set items. When the saved copy is gone, any
copy of the item still does, as before.

The world below is a model of bags, equipped slots, links and GUIDs. It does not
prove the client's timing; the swap itself is checked in game.
"""
import unittest
import gr_env

# Bag 0 has four slots. Item 100 is a dagger; two copies, GUIDs 0xA and 0xB.
WORLD = r'''
ITEMS = {
    [100] = { "Dagger", "INVTYPE_WEAPON", "Interface\\Icons\\INV_Weapon_ShortBlade_01" },
    [200] = { "Sword", "INVTYPE_WEAPON", "Interface\\Icons\\INV_Sword_04" },
}
bags = { [0] = {} }
worn = {}
function item(id, guid) return { id = id, guid = guid } end
local function at(loc)
    if loc.equipmentSlotIndex then return worn, loc.equipmentSlotIndex end
    return bags[loc.bagID] or {}, loc.slotIndex
end
local function link(it) return it and ("|cffffffff|Hitem:" .. it.id .. ":0:0:0|h[" .. ITEMS[it.id][1] .. "]|h|r") end
function GetItemInfo(id)
    local base = tonumber(string.match(tostring(id or ""), "(%d+)"))
    local i = ITEMS[base]
    if i then return i[1], "link", 2, 1, "Weapon", "Daggers", 1, i[2], i[3] end
end
function GetContainerNumSlots(bag) return bag == 0 and 4 or 0 end
function GetContainerItemLink(bag, slot) return link(bags[bag] and bags[bag][slot]) end
function GetContainerItemInfo(bag, slot) local it = bags[bag] and bags[bag][slot]; if it then return ITEMS[it.id][3], 1, nil end end
function GetInventoryItemLink(_, slot) return link(worn[slot]) end
function GetInventoryItemID(_, slot) return worn[slot] and worn[slot].id end
function GetInventoryItemTexture(_, slot) return worn[slot] and ITEMS[worn[slot].id][3] end
function GetInventoryItemQuality(_, slot) return worn[slot] and 2 end
function IsInventoryItemLocked() return nil end
function CursorHasItem() return nil end
function GetCursorInfo() end
function SpellIsTargeting() end
equips = 0
C_Container = {
    GetContainerItemID = function(bag, slot) local it = bags[bag] and bags[bag][slot]; return it and it.id end,
    GetContainerNumFreeSlots = function(bag) local n = 0; for s = 1, GetContainerNumSlots(bag) do if not bags[bag][s] then n = n + 1 end end; return n, 0 end,
    GetContainerFreeSlots = function(bag) local t = {}; for s = 1, GetContainerNumSlots(bag) do if not bags[bag][s] then t[#t + 1] = s end end; return t end,
}
C_Item = {
    GetItemGUID = function(loc) local t, k = at(loc); return t[k] and t[k].guid end,
    GetItemTempEnchantInfo = function() return false end,
    EquipItemByName = function(loc, slot)
        local t, k = at(loc)
        t[k], worn[slot] = worn[slot], t[k]
        equips = equips + 1
        fire("ITEM_LOCK_CHANGED")
        fire("UNIT_INVENTORY_CHANGED", "player")
    end,
}
-- One-hand weapons go in either hand.
function CanDualWield() return true end
'''


def world(setup):
    env = gr_env.logged_in(WORLD + setup)
    env.run('fire("PLAYER_ENTERING_WORLD"); GearRack.InvalidateBag(); step(0.1)')
    return env


def settle(env, seconds=3):
    for _ in range(int(seconds / 0.1)):
        env.run("step(0.1)")


SAVE_MAIN_HAND = r'''
GearRackUI_Sets_Name:SetText("Instant")
for i = 0, 19 do GearRackUI.SetBuild[i] = 0 end
GearRackUI.SetBuild[16] = 1
GearRackUI_Sets_Save_OnClick()
'''


class SetsRememberTheCopy(unittest.TestCase):
    def test_save_keeps_the_worn_copy(self):
        env = world("worn[16] = item(100, '0xA'); bags[0][1] = item(100, '0xB')")
        env.run(SAVE_MAIN_HAND)
        self.assertEqual(env.eval('GearRackDB.sets["Claude of Y\'Shaarj"].Sets.Instant[16].guid'), "0xA")

    def test_equip_puts_the_saved_copy_back(self):
        # The other copy is worn now (another poison); the set must swap to its own.
        env = world("worn[16] = item(100, '0xA'); bags[0][1] = item(100, '0xB')")
        env.run(SAVE_MAIN_HAND)
        env.run("worn[16], bags[0][1] = bags[0][1], worn[16]; fire('UNIT_INVENTORY_CHANGED', 'player'); fire('BAG_UPDATE', 0)")
        settle(env, 0.5)
        self.assertFalse(env.eval("GearRack.IsSetEquipped('Instant')"))
        env.run("GearRack.EquipSet('Instant')")
        settle(env)
        self.assertEqual(env.eval("worn[16].guid"), "0xA")
        self.assertTrue(env.eval("GearRack.IsSetEquipped('Instant')"))

    def test_any_copy_does_when_the_saved_one_is_gone(self):
        env = world("worn[16] = item(200, '0xS'); bags[0][1] = item(100, '0xB')")
        env.run(r'''GearRackDB.sets["Claude of Y'Shaarj"].Sets.Instant = { icon = "x",
            [16] = { id = "100:0:0", name = "Dagger", guid = "0xGONE" } }''')
        env.run("GearRack.EquipSet('Instant')")
        settle(env)
        self.assertEqual(env.eval("worn[16].guid"), "0xB")
        self.assertTrue(env.eval("GearRack.IsSetEquipped('Instant')"))

    def test_restore_returns_the_copy_it_replaced(self):
        # Instant (copy A) replaces copy B; restoring must bring B back, not A.
        env = world("worn[16] = item(100, '0xA'); bags[0][1] = item(100, '0xB')")
        env.run(SAVE_MAIN_HAND)
        env.run("worn[16], bags[0][1] = bags[0][1], worn[16]; fire('UNIT_INVENTORY_CHANGED', 'player'); fire('BAG_UPDATE', 0)")
        settle(env, 0.5)
        env.run("GearRack.EquipSet('Instant')")
        settle(env)
        self.assertEqual(env.eval("worn[16].guid"), "0xA")
        env.run("GearRack.LoadSet('Instant')")
        settle(env)
        self.assertEqual(env.eval("worn[16].guid"), "0xB")

    def test_save_lights_up_for_the_other_copy(self):
        # Save is lit while saving would change the set: wearing the other copy does.
        env = world("worn[16] = item(100, '0xA'); bags[0][1] = item(100, '0xB')")
        env.run(SAVE_MAIN_HAND)
        lit = "(function() GearRackUI_Sets_Name_OnTextChanged(); return GearRackUI_Sets_SaveButton.selected end)()"
        self.assertFalse(env.eval(lit))
        env.run("worn[16], bags[0][1] = bags[0][1], worn[16]")
        self.assertTrue(env.eval(lit))


if __name__ == "__main__":
    unittest.main()
