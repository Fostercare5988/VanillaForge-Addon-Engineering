"""The grid and a slot: drawing, redraws, clicks, new items, the enchant badge
(spec 4.5, tests 4, 5, 6, 10 and 11). Bags 1.0, written new 2026-11-22.
"""
import unittest
from bags_env import load, frame


def opened(setup=""):
    lua = load(setup=setup)
    lua.execute("ToggleBackpack()")
    return lua


class Grid(unittest.TestCase):
    def test_twelve_columns_of_every_slot_of_bags_0_to_4(self):
        lua = opened()
        self.assertEqual(lua.eval("shownButtons('inventory')"), 36)
        self.assertEqual(lua.eval("(select(4, button('inventory', 0, 12):GetPoint(1)))"), 8 + 11 * 40)
        self.assertEqual(lua.eval("(select(5, button('inventory', 0, 13):GetPoint(1)))"), -30 - 40)
        self.assertEqual(lua.eval("(select(4, button('inventory', 1, 1):GetPoint(1)))"), 8 + 4 * 40)
        self.assertEqual(lua.eval("BagsInventory:GetWidth()"), 12 * 40 + 13)
        self.assertEqual(lua.eval("BagsInventory:GetHeight()"), 30 + 3 * 40 + 33)

    def test_the_backpack_alone_with_empty_slots(self):
        lua = opened("bags[1] = nil; bags[0].slots = {}")
        self.assertEqual(lua.eval("shownButtons('inventory')"), 16)
        self.assertIsNone(lua.eval("button('inventory', 0, 1).hasItem"))
        self.assertEqual(lua.eval("BagsInventory.free:GetText()"), "16 / 16 Free")

    def test_a_bag_put_in_swapped_and_taken_out(self):
        lua = opened()
        lua.execute("bags[2] = { size = 6, slots = {} }; fire('BAG_UPDATE', 2); fire('BAG_UPDATE_DELAYED')")
        self.assertEqual(lua.eval("shownButtons('inventory')"), 42)
        lua.execute("bags[2] = { size = 18, slots = {} }; fire('BAG_UPDATE', 2); fire('BAG_UPDATE_DELAYED')")
        self.assertEqual(lua.eval("shownButtons('inventory')"), 54)
        lua.execute("bags[2] = nil; fire('BAG_CLOSED', 2)")
        frame(lua)
        self.assertEqual(lua.eval("shownButtons('inventory')"), 36, "BAG_CLOSED alone lays it out again")
        self.assertIsNone(lua.eval("luaErrors[1]"))

    def test_a_closed_window_reads_nothing(self):
        lua = load()
        lua.execute("forget(); fire('BAG_UPDATE', 0); fire('BAG_UPDATE_DELAYED'); fire('ITEM_LOCK_CHANGED')")
        frame(lua)
        self.assertEqual(lua.eval("count('GetContainerItemInfo')"), 0)

    def test_only_the_bag_that_changed_is_read(self):
        lua = opened()
        lua.execute("forget(); put(0, 2, { id = 8928, count = 3 }); fire('BAG_UPDATE', 0); fire('BAG_UPDATE_DELAYED')")
        self.assertEqual(lua.eval("count('GetContainerItemInfo')"), 16)
        self.assertEqual(lua.eval("button('inventory', 0, 2).count"), 3)


class Slot(unittest.TestCase):
    def test_icon_count_and_quality_from_one_call_per_slot(self):
        lua = load()
        lua.execute("forget(); ToggleBackpack()")
        self.assertEqual(lua.eval("count('GetContainerItemInfo')"), 36)
        b = "button('inventory', 0, 1)"
        self.assertEqual(lua.eval(f"{b}.icon:GetTexture()"), "Interface\\Icons\\Ability_Poisons")
        self.assertEqual(lua.eval(f"{b}.countText:GetText()"), 10)
        self.assertFalse(lua.eval(f"{b}.edge:IsShown()"), "common: no border")
        self.assertTrue(lua.eval("button('inventory', 0, 16).edge:IsShown()"))
        self.assertEqual(lua.eval("button('inventory', 1, 2).edge.edgeColor[2]"), 0.55, "legendary orange")
        self.assertFalse(lua.eval("button('inventory', 1, 2).countText:IsShown()"))

    def test_an_item_not_cached_yet_draws_when_its_data_arrives(self):
        lua = opened("put(0, 3, { id = 777 })")
        b = "button('inventory', 0, 3)"
        self.assertEqual(lua.eval(f"{b}.icon:GetTexture()"), "Interface\\Icons\\INV_Misc_QuestionMark")
        self.assertFalse(lua.eval(f"{b}.edge:IsShown()"))
        lua.execute("items[777] = { name = 'Late', quality = 4, icon = 'late' }; fire('GET_ITEM_INFO_RECEIVED', 777, true)")
        frame(lua)
        self.assertEqual(lua.eval(f"{b}.icon:GetTexture()"), "late")
        self.assertTrue(lua.eval(f"{b}.edge:IsShown()"))

    def test_a_lock_greys_once_per_frame(self):
        lua = opened()
        lua.execute("forget(); bags[0].slots[1].locked = true; fire('ITEM_LOCK_CHANGED'); fire('ITEM_LOCK_CHANGED')")
        self.assertEqual(lua.eval("count('GetContainerItemInfo')"), 0)
        frame(lua)
        self.assertEqual(lua.eval("count('GetContainerItemInfo')"), 36)
        self.assertTrue(lua.eval("button('inventory', 0, 1).icon.desaturated"))
        self.assertEqual(lua.eval("liveTimers()"), 0)

    def test_the_cooldown_on_a_native_cooldown_and_the_dim_of_one_not_started(self):
        lua = opened()
        lua.execute("cds['0:1'] = { 200, 60, 1 }; fire('BAG_UPDATE_COOLDOWN')")
        frame(lua)
        cd = "button('inventory', 0, 1).cooldown"
        self.assertEqual(lua.eval(f"{cd}:GetObjectType()"), "Cooldown")
        self.assertEqual(lua.eval(f"{cd}.cdDuration"), 60)
        lua.execute("cds['0:1'] = { 200, 60, 0 }; fire('BAG_UPDATE_COOLDOWN')")
        frame(lua)
        self.assertIsNone(lua.eval(f"{cd}.cdDuration"))
        self.assertEqual(lua.eval("button('inventory', 0, 1).icon.color[1]"), 0.4)
        lua.execute("fire('ITEM_LOCK_CHANGED')")
        frame(lua)
        self.assertEqual(lua.eval("button('inventory', 0, 1).icon.color[1]"), 0.4, "the lock step keeps the dim")


class Clicks(unittest.TestCase):
    def test_the_click_reaches_a_wrapper_installed_after_our_load(self):
        lua = opened()
        lua.execute("local old = ContainerFrameItemButton_OnClick;"
                    " function ContainerFrameItemButton_OnClick(...) calls.wrapped = true; old(...) end")
        lua.execute("click(button('inventory', 1, 16), 'RightButton')")
        self.assertTrue(lua.eval("calls.wrapped"))
        self.assertEqual(lua.eval("calls.click[1] == button('inventory', 1, 16)"), True)
        self.assertEqual(lua.eval("calls.click[1]:GetParent():GetID()"), 1)
        self.assertEqual(lua.eval("calls.click[2]"), "RightButton")

    def test_drag_picks_up(self):
        lua = opened()
        lua.execute("run(button('inventory', 0, 1), 'OnDragStart')")
        self.assertEqual(lua.eval("calls.click[2]"), "LeftButton")
        self.assertEqual(lua.eval("calls.click[3]"), 1)

    def test_the_bank_slots_show_their_tooltip_through_the_inventory_slot(self):
        lua = load()
        lua.execute("openBank(); enter(button('bank', -1, 24))")
        self.assertEqual(lua.eval("GameTooltip.inventory"), 39 + 24)
        lua.execute("enter(button('bank', 5, 3))")
        self.assertEqual(lua.eval("calls.enter == button('bank', 5, 3)"), True)


class NewItems(unittest.TestCase):
    def test_a_new_item_glows_until_pointed_at(self):
        lua = opened("newItems['0:16'] = true")
        b = "button('inventory', 0, 16)"
        self.assertTrue(lua.eval(f"{b}.glow:IsShown()"))
        self.assertTrue(lua.eval(f"{b}.glow.pulse:IsPlaying()"))
        lua.execute(f"enter({b})")
        self.assertEqual(lua.eval("count('RemoveNewItem')"), 1)
        self.assertFalse(lua.eval(f"{b}.glow:IsShown()"))

    def test_closing_the_inventory_clears_them_all(self):
        lua = opened("newItems['0:16'] = true")
        lua.execute("ToggleBackpack()")
        self.assertEqual(lua.eval("count('ClearAll')"), 1)

    def test_new_items_redraw_only_while_it_shows(self):
        lua = opened()
        self.assertTrue(lua.eval("receives(BagsInventory, 'BAG_NEW_ITEMS_UPDATED')"))
        lua.execute("newItems['1:16'] = true; fire('BAG_NEW_ITEMS_UPDATED')")
        frame(lua)
        self.assertTrue(lua.eval("button('inventory', 1, 16).glow:IsShown()"))
        lua.execute("ToggleBackpack()")
        self.assertFalse(lua.eval("receives(BagsInventory, 'BAG_NEW_ITEMS_UPDATED')"))
        self.assertEqual(lua.eval("onUpdates()"), 0)


class Enchant(unittest.TestCase):
    def test_a_poisoned_weapon_shows_its_icon_and_counts_down_once(self):
        lua = opened("enchants['1:2'] = { ms = 1800000, id = 7 }")
        badge = "button('inventory', 1, 2).badge"
        self.assertTrue(lua.eval(f"{badge}:IsShown()"))
        self.assertEqual(lua.eval(f"{badge}.icon:GetTexture()"), "Interface\\Icons\\Ability_Poisons")
        self.assertEqual(lua.eval(f"{badge}.timer.cdDuration"), 1800)
        lua.execute("forget(); fire('BAG_UPDATE', 1); fire('BAG_UPDATE_DELAYED')")
        self.assertEqual(lua.eval("count('SetCooldown')"), 0, "the same enchant read again keeps its countdown")

    def test_few_charges_show_instead_of_the_time(self):
        lua = opened("enchants['1:2'] = { ms = 1800000, charges = 3, id = 7 }")
        self.assertEqual(lua.eval("button('inventory', 1, 2).badge.text:GetText()"), "3c")
        self.assertIsNone(lua.eval("button('inventory', 1, 2).badge.timer.cdDuration"))

    def test_an_enchant_with_no_spell_shows_the_question_mark(self):
        lua = opened("enchants['1:2'] = { ms = 60000, id = 99 }")
        self.assertEqual(lua.eval("button('inventory', 1, 2).badge.icon:GetTexture()"), "Interface\\Icons\\INV_Misc_QuestionMark")

    def test_the_end_reads_the_slot_again(self):
        lua = opened("enchants['1:2'] = { ms = 60000, id = 7 }")
        lua.execute("enchants['1:2'] = nil; run(button('inventory', 1, 2).badge.timer, 'OnCooldownDone')")
        self.assertFalse(lua.eval("button('inventory', 1, 2).badge:IsShown()"))

    def test_never_on_bank_slots(self):
        lua = load("", "enchants['5:3'] = { ms = 60000, id = 7 }")
        lua.execute("forget(); openBank()")
        self.assertIsNone(lua.eval("button('bank', 5, 3).badge"))
        lua.execute("ToggleBackpack()")


if __name__ == "__main__":
    unittest.main()
