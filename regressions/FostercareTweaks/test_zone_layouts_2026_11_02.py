"""Layouts by zone (2026-11-02, the player's notes: PvP and PvE settings).

The world, battlegrounds, and dungeons and raids each keep their own frame
positions, raid frames, aura sizes, raid marks, minimap size and action bar
layouts. The live settings hold the active layout; a switch stores them and
loads the next one after the loading screen, or after combat. The extra rows'
spells stay shared. Every test fails on 192e14d, which has no layouts. Whether
each frame lands right on screen stays an in-game check.
"""
import unittest
from lupa.lua51 import LuaRuntime

from test_audit_2026_10_25 import source
from test_audit_2026_10_26 import runtime

PRELUDE = r'''
    NOOP = function() end
    handlers, frames, shown = {}, {}, 0
    function CreateFrame()
        local f = { events = {} }
        function f:RegisterEvent(ev) self.events[ev] = true end
        function f:UnregisterEvent(ev) self.events[ev] = nil end
        frames[#frames + 1] = f
        return f
    end
    kind, combat = "none", false
    function GetInstanceInfo() return "Somewhere", kind end
    function UnitAffectingCombat() return combat end
    DEFAULT_CHAT_FRAME = { AddMessage = function(_, t) said = t end }
    FostercareTweaks_Config = { overwrites = { raid_buff_count = 4 }, ["Show Raid Buffs"] = 1,
        unitframe_positions = { raid = { point = "TOPLEFT", relPoint = "TOPLEFT", x = 10, y = -10 } },
        groupframe_dimensions = { enabled = true, width = 64 },
        actionbars = { enabled = true, bars = { extra2 = { visible = true, x = 100, actions = { { kind = "spell", id = 1 } } } } } }
    FT = { mods = {}, overwrites = {} }
    FostercareTweaks = FT
    function FT:register(m) self.mods[m.title] = m; return m end
    function FT.SetEventHandler(frame, fn) handlers[frame] = fn end
    function FT.IsEnabled(key) return FostercareTweaks_Config[key] ~= 0 end
    function FT.GetNumber(_, d) return d end
    FT.ActionBars = { enabled = true, bars = {} }
    function FT.ActionBars:SetEnabled(v) self.enabled = v end
    function FT.ActionBars:Apply() applied = (applied or 0) + 1 end
    FT.UnitFrames = { ApplyConfiguration = function() shown = shown + 1 end, ApplyGroupDimensions = NOOP,
        UpdateAllRaidFrames = NOOP, GetBuffSize = NOOP, GetDebuffSize = NOOP }
    function FT.RestoreFramePositions() restored = (restored or 0) + 1 end
    FT.ApplyMinimapScale = NOOP
    function FT:RefreshRaidMarks() end
    function Enter(k) kind = k; for f, fn in pairs(handlers) do if f.events.PLAYER_ENTERING_WORLD then fn(f, "PLAYER_ENTERING_WORLD") end end end
    function EndCombat() combat = false; for f, fn in pairs(handlers) do if f.events.PLAYER_REGEN_ENABLED then fn(f, "PLAYER_REGEN_ENABLED") end end end
    C = FostercareTweaks_Config
'''


def layouts():
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(PRELUDE)
    lua.execute(source("Profiles.lua"))
    lua.execute('FT.mods["Zone Layouts"].enable()')
    return lua


class ZoneLayouts(unittest.TestCase):
    def test_the_first_world_entry_keeps_the_live_layout(self):
        lua = layouts()
        lua.execute('Enter("none")')
        self.assertEqual(lua.eval("C.profile"), "world")
        self.assertEqual(lua.eval("shown"), 0)
        self.assertEqual(lua.eval("C.unitframe_positions.raid.x"), 10)

    def test_each_zone_keeps_its_own_layout(self):
        lua = layouts()
        lua.execute('Enter("none"); Enter("pvp")')
        self.assertEqual(lua.eval("C.profile"), "bg")              # starts as a copy
        lua.execute('C.unitframe_positions.raid.x = 500; C.overwrites.raid_buff_count = 8; C["Show Raid Buffs"] = 0;'
                    ' C.groupframe_dimensions.width = 40; C.actionbars.bars.extra2.x = 900')
        lua.execute('Enter("none")')
        self.assertEqual(lua.eval("C.unitframe_positions.raid.x"), 10)
        self.assertEqual(lua.eval("C.overwrites.raid_buff_count"), 4)
        self.assertEqual(lua.eval('C["Show Raid Buffs"]'), 1)
        self.assertEqual(lua.eval("C.groupframe_dimensions.width"), 64)
        self.assertEqual(lua.eval("C.actionbars.bars.extra2.x"), 100)
        self.assertGreater(lua.eval("shown"), 0)
        self.assertGreater(lua.eval("restored"), 0)
        lua.execute('Enter("pvp")')
        self.assertEqual(lua.eval("C.unitframe_positions.raid.x"), 500)
        self.assertEqual(lua.eval("C.overwrites.raid_buff_count"), 8)
        self.assertIn("Battlegrounds", lua.eval("said"))

    def test_dungeons_and_raids_share_one_layout(self):
        lua = layouts()
        lua.execute('Enter("party")')
        self.assertEqual(lua.eval("C.profile"), "instance")
        lua.execute('Enter("raid")')
        self.assertEqual(lua.eval("C.profile"), "instance")

    def test_extra_row_spells_are_shared(self):
        lua = layouts()
        lua.execute('Enter("none"); Enter("pvp"); C.actionbars.bars.extra2.actions[2] = { kind = "item", id = 7 }; Enter("none")')
        self.assertEqual(lua.eval("C.actionbars.bars.extra2.actions[2].id"), 7)
        self.assertIsNone(lua.eval("C.profiles.world.bars.extra2.actions"))

    def test_combat_waits(self):
        lua = layouts()
        lua.execute('Enter("none"); combat = true; Enter("pvp")')
        self.assertEqual(lua.eval("C.profile"), "world")
        lua.execute("EndCombat()")
        self.assertEqual(lua.eval("C.profile"), "bg")

    def test_switched_off_means_one_layout(self):
        lua = layouts()
        lua.execute('Enter("none"); C["Zone Layouts"] = 0; Enter("pvp")')
        self.assertEqual(lua.eval("C.profile"), "world")

    def test_one_layout_can_go_everywhere(self):
        lua = layouts()
        lua.execute('Enter("none"); C.unitframe_positions.raid.x = 77; FT.CopyLayoutToAll(); Enter("raid")')
        self.assertEqual(lua.eval("C.unitframe_positions.raid.x"), 77)

    def test_new_characters_start_without_layout_copies(self):
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
        from export_defaults import clean
        config = clean({"profiles": {"world": {}}, "profile": "world", "Auto Dismount": 1})
        self.assertEqual(config, {"Auto Dismount": 1})


class FramesGoHome(unittest.TestCase):
    """A layout without a saved spot puts a frame back where it first stood."""

    def test_unsaved_frames_return_home_and_saved_ones_move(self):
        lua = runtime()
        lua.execute(r'''
            function IsLeftShiftKeyDown() end; IsRightShiftKeyDown, IsLeftControlKeyDown, IsRightControlKeyDown = IsLeftShiftKeyDown, IsLeftShiftKeyDown, IsLeftShiftKeyDown
            local function Movable(x)
                local f = Widget({ points = { { "CENTER", UIParent, "CENTER", x, 0 } } })
                function f:GetNumPoints() return #self.points end
                function f:GetPoint(i) local p = self.points[i]; return p[1], p[2], p[3], p[4], p[5] end
                function f:ClearAllPoints() self.points = {} end
                function f:SetPoint(a, b, c, d, e) self.points[#self.points + 1] = { a, b, c, d, e } end
                function f:GetFrameLevel() return 1 end
                return f
            end
            one, two = Movable(5), Movable(6)
            FostercareTweaks_Config.unitframe_positions = { two_key = { point = "TOP", relPoint = "TOP", x = 1, y = 2 } }
        ''')
        lua.execute(source("mods/move-unitframes.lua"))
        lua.execute(r'''
            FT.RestoreFramePosition(one, "one_key"); FT.RegisterFrameMover(one, "one_key", "One")
            FT.RestoreFramePosition(two, "two_key"); FT.RegisterFrameMover(two, "two_key", "Two", nil, nil,
                function(saved) twoSaved = saved end)
            -- The next layout: one has a saved spot, two has none.
            FostercareTweaks_Config.unitframe_positions = { one_key = { point = "LEFT", relPoint = "LEFT", x = 9, y = 9 } }
            FT.RestoreFramePositions()
        ''')
        self.assertEqual(lua.eval("one.points[1][1]"), "LEFT")
        self.assertEqual(lua.eval("two.points[1][1]"), "CENTER")      # home
        self.assertEqual(lua.eval("two.points[1][4]"), 6)
        self.assertFalse(lua.eval("twoSaved"))


if __name__ == "__main__":
    unittest.main()
