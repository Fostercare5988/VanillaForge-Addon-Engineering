"""Ctrl+Shift moves the player's own cast bar (2026-11-02)."""
import unittest
from lupa.lua51 import LuaRuntime
from test_event_fanout import BASE, ROOT

SOURCE = (ROOT / "mods/player-castbar.lua").read_text("utf-8-sig")


class PlayerCastbarMover(unittest.TestCase):
    def build(self, saved):
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute(BASE + r'''
            CastingBarFrame = CreateFrame("StatusBar", "CastingBarFrame")
            local FT = FostercareTweaks
            hooked = {}
            FT.hooksecurefunc = function(name, fn) hooked[name] = fn end
            placed = 0
            FT.RestoreFramePosition = function(frame, key) placed = placed + 1; return %s end
            FT.RegisterFrameMover = function(frame, key, label, rel, onStop) mover = { frame, key, label, rel, onStop } end
        ''' % saved)
        lua.execute(SOURCE)
        lua.execute('FostercareTweaks.mods["Movable Cast Bar"]:enable()')
        return lua

    def test_registers_a_mover_on_the_game_bar(self):
        lua = self.build("false")
        self.assertTrue(lua.eval('mover[1] == CastingBarFrame and mover[2] == "player_castbar"'))

    def test_the_saved_spot_is_reapplied_when_the_game_lays_out_the_screen(self):
        lua = self.build("true")
        lua.execute('hooked.UIParent_ManageFramePositions()')
        self.assertEqual(lua.eval("placed"), 2)

    def test_nothing_is_reapplied_without_a_saved_spot_until_it_is_moved(self):
        lua = self.build("false")
        lua.execute('hooked.UIParent_ManageFramePositions()')
        self.assertEqual(lua.eval("placed"), 1)
        lua.execute('mover[5](); hooked.UIParent_ManageFramePositions()')
        self.assertEqual(lua.eval("placed"), 2)

    def test_the_bar_hides_after_the_keys_unless_casting(self):
        lua = self.build("false")
        lua.execute('local b = CastingBarFrame; b:Show(); b.fctRestoreShown(b)')
        self.assertFalse(lua.eval("CastingBarFrame:IsShown()"))
        lua.execute('local b = CastingBarFrame; b:Show(); b.casting = 1; b.fctRestoreShown(b)')
        self.assertTrue(lua.eval("CastingBarFrame:IsShown()"))
