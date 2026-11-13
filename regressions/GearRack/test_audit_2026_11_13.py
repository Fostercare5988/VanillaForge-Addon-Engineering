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


# Cooldowns per equipped slot ({start, duration}) and a poison on the main hand.
TIMED = r'''
cooldowns = {}
function GetInventoryItemCooldown(_, slot) local c = cooldowns[slot]; if c then return c[1], c[2], 1 end; return 0, 0, 1 end
poisonEnds = nil
C_Item.GetItemTempEnchantInfo = function(loc)
    if loc.equipmentSlotIndex == 16 and poisonEnds and poisonEnds > now then
        return true, (poisonEnds - now) * 1000, nil, 7
    end
    return false
end
function SecondsToTimeAbbrev(s)
    if s > 3600 then return math.ceil(s / 3600) .. " h" end
    if s > 60 then return math.ceil(s / 60) .. " m" end
    return math.floor(s) .. " s"
end
C_Item.GetEnchantInfo = function() return { name = "Instant Poison", spellID = 1 } end
C_Spell = { GetSpellTexture = function() return "Interface\Icons\Ability_Poisons" end }
'''


def wake(env):
    """Seconds until the cooldown timer runs again, or None while it sleeps."""
    return env.eval("(function() local c = GearRackEngine.TimerPool.CooldownUpdate"
                    " return c.enabled and c.deadline and c.deadline - now end)()")


class Flyout(unittest.TestCase):
    def test_lists_carried_weapons_by_name(self):
        env = world(r'''-- The flyout template's parts, as the client makes them.
            local create = CreateFrame
            function CreateFrame(kind, name, parent, template)
                local f = create(kind, name, parent)
                if template == "GearRackUIMenuTemplate" then
                    for _, part in ipairs({ "Icon", "Count", "HotKey", "Name", "Border", "CD" }) do newWidget("Texture", name .. part, f) end
                end
                return f
            end
            ITEMS[300] = { "Axe", "INVTYPE_WEAPON", "x" }; ITEMS[400] = { "Club", "INVTYPE_WEAPON", "x" }
            worn[16] = item(100, '0xA'); bags[0][1] = item(200, '0xS'); bags[0][2] = item(400, '0xC'); bags[0][3] = item(300, '0xX')''')
        env.run("GearRackDB.settings.ShowEmpty = 'OFF'; GearRackUI_BuildMenu(16)")
        names = [env.eval("GearRackUI.BaggedItems[%d].name" % i) for i in range(1, env.eval("GearRackUI.NumberOfItems") + 1)]
        self.assertEqual(names, ["Axe", "Club", "Sword"])
        self.assertEqual(env.eval("GearRackUIMenu1Icon.texture"), "x")


class QueueStats(unittest.TestCase):
    def test_empty_entries_are_dropped_and_set_ones_kept(self):
        # Ticking and clearing a box saved an empty entry ("61095" = {} on every character).
        env = world("")
        env.run('''GearRackCharDB.queues.Stats = { ["61095"] = {}, ["14022"] = { delay = 20 }, ["11122"] = { keep = 1 } }
            GearRackTrinkets.QueueInit()''')
        self.assertIsNone(env.eval('GearRackCharDB.queues.Stats["61095"]'))
        self.assertEqual(env.eval('GearRackCharDB.queues.Stats["14022"].delay'), 20)
        self.assertEqual(env.eval('GearRackCharDB.queues.Stats["11122"].keep'), 1)


class NoIdleTick(unittest.TestCase):
    def test_nothing_to_count_down_means_no_timer(self):
        env = world(TIMED + "worn[16] = item(100, '0xA')")
        settle(env, 3)
        self.assertIsNone(wake(env), "with no poison, alert or queue the cooldown timer sleeps")

    def test_a_long_poison_wakes_once_a_minute(self):
        env = world(TIMED + "worn[16] = item(100, '0xA'); poisonEnds = now + 25 * 60 + 10")
        env.run("fire('UNIT_INVENTORY_CHANGED', 'player')")
        settle(env, 1)
        self.assertGreater(wake(env), 5, "a 25-minute label changes once a minute")
        self.assertEqual(env.eval("GearRackUIInv16.enchantOverlay.duration:GetText()"), "26m")

    def test_poison_put_on_shows_at_once(self):
        env = world(TIMED + "worn[16] = item(100, '0xA')")
        settle(env, 2)
        env.run("poisonEnds = now + 600; fire('UNIT_INVENTORY_CHANGED', 'player')")
        self.assertTrue(env.eval("GearRackUIInv16.enchantOverlay:IsShown()"))
        self.assertIsNotNone(wake(env))

    def test_the_label_turns_red_under_two_minutes(self):
        env = world(TIMED + "worn[16] = item(100, '0xA'); poisonEnds = now + 125")
        env.run("fire('UNIT_INVENTORY_CHANGED', 'player')")
        settle(env, 0.5)
        self.assertGreater(env.eval("GearRackUIInv16.enchantOverlay.green"), .5)
        settle(env, 5)
        self.assertLess(env.eval("GearRackUIInv16.enchantOverlay.green"), .5)


class ReadyAlerts(unittest.TestCase):
    def test_used_item_alerts_once_thirty_seconds_before_ready(self):
        env = world(TIMED + "worn[13] = item(100, '0xT')")
        env.run("cooldowns[13] = { now, 120 }; GearRackUI.OnUseInventoryItem(13)")
        settle(env, 5)
        self.assertGreater(wake(env), 60, "no once-a-second polling while the cooldown runs")
        before = env.eval("#chat")
        settle(env, 86)
        self.assertEqual(env.eval("#chat"), before + 1)
        self.assertIn("ready soon", env.eval("chat[#chat]"))
        settle(env, 40)
        self.assertEqual(env.eval("#chat"), before + 1, "one alert")
        self.assertIsNone(wake(env))

    def test_an_item_without_a_cooldown_is_dropped(self):
        env = world(TIMED + "worn[16] = item(100, '0xA')")
        env.run("GearRackUI.OnUseInventoryItem(16)")
        settle(env, 5)
        self.assertIsNone(env.eval("next(GearRackCharDB.ItemsUsed)"))
        self.assertIsNone(wake(env))

    def test_saved_trinket_watch_moves_to_the_shared_watch(self):
        # Older versions kept the trinkets' watch apart; the client restores it before login.
        env = world(TIMED + "worn[14] = item(100, '0xT'); cooldowns[14] = { now - 10, 120 }")
        env.run("GearRackCharDB.trinkets.ItemsUsed = { [100] = 30 }; GearRackCharDB.ItemsUsed = nil; GearRack.NormalizeSavedData()")
        self.assertEqual(env.eval("GearRackCharDB.ItemsUsed[100]"), 30)
        self.assertIsNone(env.eval("GearRackCharDB.trinkets.ItemsUsed"))

    def test_an_enabled_queue_still_looks_every_second(self):
        env = world(TIMED + "worn[13] = item(100, '0xT')")
        env.run("GearRack.SetTrinketQueue(0, 'ON')")
        settle(env, 2)
        self.assertLessEqual(wake(env), 1.01)


class BuffsOnDemand(unittest.TestCase):
    EVENTS = r'''
        GearRackDB.settings.EnableEvents = "ON"
        GearRackDB.events.Probe = { trigger = "%s", delay = 0,
            script = "seen = GearRackUI.Buffs['Spirit Tap'] and 1 or 0" }
        GearRackDB.sets["Claude of Y'Shaarj"].Sets.Probe = { icon = "x" }
        GearRackDB.bars["Claude of Y'Shaarj"].Events.Probe = { setname = "Probe", enabled = 1 }
        GearRackUI_SetsFrame:Hide()
        GearRackUI_EnableAllEvents()
    '''
    AURAS = r'''
        C_UnitAuras = {
            GetAuraSlots = function(_, _, _, _, out) out[1] = 1; return nil, 1 end,
            UnitAuraBySlot = function() return "Spirit Tap", "Interface\Icons\Spell_Shadow_Requiem" end,
        }
    '''

    def test_no_buff_reading_without_a_buff_event(self):
        env = world(self.AURAS)
        env.run(self.EVENTS % "PLAYER_TARGET_CHANGED")
        self.assertFalse(env.eval("GearRackUIFrame.events.PLAYER_AURAS_CHANGED ~= nil"))
        # A script on another trigger still sees the current buffs.
        env.run("fire('PLAYER_TARGET_CHANGED')")
        self.assertEqual(env.eval("seen"), 1)

    def test_a_buff_event_watches_auras(self):
        env = world(self.AURAS)
        env.run(self.EVENTS % "GEARRACK_BUFFS_CHANGED")
        self.assertTrue(env.eval("GearRackUIFrame.events.PLAYER_AURAS_CHANGED ~= nil"))
        env.run("fire('PLAYER_AURAS_CHANGED')")
        self.assertEqual(env.eval("seen"), 1)
        env.run("GearRackUI_DisableAllEvents()")
        self.assertFalse(env.eval("GearRackUIFrame.events.PLAYER_AURAS_CHANGED ~= nil"))


if __name__ == "__main__":
    unittest.main()
