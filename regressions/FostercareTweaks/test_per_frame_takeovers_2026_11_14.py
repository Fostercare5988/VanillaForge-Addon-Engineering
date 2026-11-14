"""Two stock frames that redrew every frame now redraw on events (2026-11-14).

From a /lag report: FostercareTweaks at 7.0 ms/s and 4.6 KB/s, 18 of 19
garbage collections started inside it. Two causes were the game's own frames
it styles, which redrew every frame:

* the target-of-target frame (TargetFrame.xml OnUpdate), which on each redraw
  also ran the target's whole aura update and its own buffs; Claude shows it
  always (SHOW_TARGET_OF_TARGET_STATE "5");
* the weapon enchant frame (BuffFrame.xml TemporaryEnchantFrame OnUpdate),
  which a rogue with poisons has shown all the time.

Now the first redraws on UNIT_TARGET and NamPower's GUID events for the unit
it shows, the second on inventory events and when its duration label next
changes; the stock redraw runs per frame only while an enchant flashes.
"""
import os
import unittest
from pathlib import Path

import ft_env

ROOT = Path(os.environ["VANILLAFORGE_ADDON_ROOT"])

TOT = r'''
tot = { exists = true, guid = "0xAAA", name = "Rogue" }
targetHealth = 500
function UnitGUID(u) if u == "targettarget" and tot.exists then return tot.guid end end
function UnitName(u) if u == "targettarget" and tot.exists then return tot.name end end
function GetUnitName(u) return UnitName(u) end
function UnitHealth(u) if u == "target" then return targetHealth end return 100 end
calls = { update = 0, health = 0, mana = 0, buffs = 0, portrait = 0, dead = 0, perFrame = 0 }
TargetofTargetFrame = CreateFrame("Button", "TargetofTargetFrame")
TargetofTargetFrame.unit = "targettarget"
TargetofTargetFrame.portrait = CreateFrame("Frame")
TargetofTargetFrame.name = CreateFrame("Frame")
TargetofTargetFrame.healthbar = CreateFrame("StatusBar")
TargetofTargetFrame.manabar = CreateFrame("StatusBar")
TargetofTargetFrame:SetScript("OnUpdate", function() calls.perFrame = calls.perFrame + 1; TargetofTarget_Update() end)
-- The stock update: shown while there is a living target with a target.
function TargetofTarget_Update()
    calls.update = calls.update + 1
    if tot.exists and targetHealth > 0 then TargetofTargetFrame:Show() else TargetofTargetFrame:Hide() end
end
function UnitFrameHealthBar_Update() calls.health = calls.health + 1 end
function UnitFrameManaBar_Update() calls.mana = calls.mana + 1 end
function TargetofTarget_CheckDead() calls.dead = calls.dead + 1 end
function RefreshBuffs() calls.buffs = calls.buffs + 1 end
function SetPortraitTexture() calls.portrait = calls.portrait + 1 end
'''


def tot_world():
    lua = ft_env.world(["mods/target-of-target.lua"], TOT)
    return ft_env.start(lua)


class TargetOfTarget(unittest.TestCase):
    def test_no_redraw_while_nothing_changes(self):
        lua = tot_world()
        before = lua.eval("calls.update")
        lua.execute("for _ = 1, 60 do step(0.016) end")
        self.assertIsNone(lua.eval("TargetofTargetFrame.scripts.OnUpdate"))
        self.assertEqual(lua.eval("calls.perFrame"), 0)
        self.assertEqual(lua.eval("calls.update"), before)

    def test_only_its_units_changes_redraw_its_parts(self):
        lua = tot_world()
        lua.execute('fire("UNIT_HEALTH_GUID", "0xBBB", 0, 0, 0, 0, 0, 0)')     # someone else
        self.assertEqual(lua.eval("calls.health"), 0)
        lua.execute('fire("UNIT_HEALTH_GUID", "0xAAA", 0, 0, 0, 0, 0, 0)')
        self.assertEqual((lua.eval("calls.health"), lua.eval("calls.dead")), (1, 1))
        lua.execute('fire("UNIT_ENERGY_GUID", "0xAAA", 0, 0, 0, 0, 0, 0)')
        lua.execute('fire("UNIT_AURA_GUID", "0xAAA", 0, 0, 0, 0, 0, 0)')
        self.assertEqual((lua.eval("calls.mana"), lua.eval("calls.buffs")), (1, 1))
        self.assertEqual(lua.eval("calls.update"), 0)     # no full redraw

    def test_the_target_picks_someone_else(self):
        lua = tot_world()
        portraits = lua.eval("calls.portrait")
        lua.execute('tot.guid, tot.name = "0xBBB", "Warrior"; fire("UNIT_TARGET", "party1")')
        self.assertEqual(lua.eval("calls.portrait"), portraits)    # not the target's
        lua.execute('fire("UNIT_TARGET", "target")')
        self.assertEqual(lua.eval("calls.portrait"), portraits + 1)
        self.assertEqual(lua.eval("TargetofTargetFrame.name.text"), "Warrior")
        lua.execute('fire("UNIT_HEALTH_GUID", "0xAAA", 0, 0, 0, 0, 0, 0)')
        self.assertEqual(lua.eval("calls.health"), 0)              # the old unit is ignored
        lua.execute('fire("UNIT_HEALTH_GUID", "0xBBB", 0, 0, 0, 0, 0, 0)')
        self.assertEqual(lua.eval("calls.health"), 1)

    def test_guid_events_only_while_it_shows_someone(self):
        lua = tot_world()
        driver = "FCTweaksTargetOfTarget"
        self.assertTrue(lua.eval('receives(%s, "UNIT_HEALTH_GUID")' % driver))
        lua.execute('tot.exists = false; fire("UNIT_TARGET", "target")')
        self.assertFalse(lua.eval("TargetofTargetFrame.shown"))
        self.assertFalse(lua.eval('receives(%s, "UNIT_HEALTH_GUID")' % driver))
        lua.execute('tot.exists = true; fire("UNIT_TARGET", "target")')
        self.assertTrue(lua.eval('receives(%s, "UNIT_HEALTH_GUID")' % driver))

    def test_a_dying_target_redraws_once(self):
        lua = tot_world()
        before = lua.eval("calls.update")
        lua.execute('targetHealth = 300; fire("UNIT_HEALTH", "target")')
        self.assertEqual(lua.eval("calls.update"), before)         # still alive: nothing to do
        lua.execute('targetHealth = 0; fire("UNIT_HEALTH", "target"); fire("UNIT_HEALTH", "target")')
        self.assertEqual(lua.eval("calls.update"), before + 1)
        self.assertFalse(lua.eval("TargetofTargetFrame.shown"))

    def test_the_file_loads(self):
        toc = (ROOT / "FostercareTweaks.toc").read_text("utf-8")
        self.assertIn("mods\\target-of-target.lua", toc)


ENCHANTS = r'''
SHOW_BUFF_DURATIONS, BUFF_WARNING_TIME = "1", 31
mainEnds = nil -- when the main-hand poison runs out (GetTime seconds)
function GetWeaponEnchantInfo()
    local left = mainEnds and (mainEnds - now) * 1000
    if left and left > 0 then return 1, left, 0, nil, nil, 0 end
end
C_Item = C_Item or {}
C_Item.GetWeaponEnchantInfo = function() return nil, nil, nil, 0, nil, nil, nil, 0 end
C_Item.GetEnchantInfo = function() end
function GetInventoryItemQuality() return 2 end
function GetItemQualityColor() return 1, 1, 1 end
function BuffButton_Update() end
function BuffButtons_UpdatePositions() end
redraws = 0
function BuffFrame_Enchant_OnUpdate() redraws = redraws + 1 end
BuffFrame = CreateFrame("Frame", "BuffFrame")
TemporaryEnchantFrame = CreateFrame("Frame", "TemporaryEnchantFrame")
TemporaryEnchantFrame:SetScript("OnUpdate", function() BuffFrame_Enchant_OnUpdate(arg1) end)
for i = 1, 2 do
    local b = CreateFrame("Button", "TempEnchant" .. i)
    b.id = 18 - i
    b.FostercareTweaks_border = false -- the kit answers capitalised fields with a function
    CreateFrame("FontString", "TempEnchant" .. i .. "Duration")
    CreateFrame("Texture", "TempEnchant" .. i .. "Icon")
    CreateFrame("Texture", "TempEnchant" .. i .. "Border")
end
'''


def enchant_world():
    lua = ft_env.world([], ENCHANTS)
    lua.execute('''
        function FT.RestoreFramePosition() end
        function FT.RegisterFrameMover() end
        function FT.IsAuraHidden() return false end''')
    ft_env.wowkit.load_files(lua, ROOT, ["mods/standard-player-auras.lua"], "FostercareTweaks")
    return ft_env.start(lua)


class WeaponEnchants(unittest.TestCase):
    def test_no_poison_no_redraw(self):
        lua = enchant_world()
        lua.execute('fire("PLAYER_ENTERING_WORLD")')
        before = lua.eval("redraws")
        lua.execute("for _ = 1, 60 do step(0.016) end; step(600)")
        self.assertIsNone(lua.eval("TemporaryEnchantFrame.scripts.OnUpdate"))
        self.assertEqual(lua.eval("redraws"), before)

    def test_a_long_poison_redraws_when_its_minutes_change(self):
        lua = enchant_world()
        # 29.5 minutes: "30 m" until 29 minutes are left, 30 s from now.
        lua.execute('mainEnds = now + 1770; fire("UNIT_INVENTORY_CHANGED", "player")')
        self.assertIsNone(lua.eval("TemporaryEnchantFrame.scripts.OnUpdate"))
        before = lua.eval("redraws")
        lua.execute("for _ = 1, 100 do step(0.016) end; step(28)")
        self.assertEqual(lua.eval("redraws"), before)
        lua.execute("step(0.5)")
        self.assertEqual(lua.eval("redraws"), before + 1)
        lua.execute("step(59.8)")
        self.assertEqual(lua.eval("redraws"), before + 1)
        lua.execute("step(0.2)")                                         # the next minute
        self.assertEqual(lua.eval("redraws"), before + 2)

    def test_the_last_seconds_flash_then_it_stops(self):
        lua = enchant_world()
        lua.execute('mainEnds = now + 33.5; fire("UNIT_INVENTORY_CHANGED", "player")')
        self.assertIsNone(lua.eval("TemporaryEnchantFrame.scripts.OnUpdate"))
        lua.execute("step(1.1); step(1.1); step(1.1)")                   # 30.2 s left
        self.assertIsNotNone(lua.eval("TemporaryEnchantFrame.scripts.OnUpdate"))
        before = lua.eval("redraws")
        lua.execute("step(0.016); step(0.016)")
        self.assertGreaterEqual(lua.eval("redraws"), before + 2)        # flashing: every frame
        lua.execute("step(31)")                                          # gone
        self.assertIsNone(lua.eval("TemporaryEnchantFrame.scripts.OnUpdate"))

    def test_the_duration_option_redraws_at_once(self):
        lua = enchant_world()
        lua.execute('mainEnds = now + 1770; fire("UNIT_INVENTORY_CHANGED", "player")')
        before = lua.eval("redraws")
        lua.execute('SHOW_BUFF_DURATIONS = "0"; BuffButtons_UpdatePositions()')
        self.assertEqual(lua.eval("redraws"), before + 1)


if __name__ == "__main__":
    unittest.main()
