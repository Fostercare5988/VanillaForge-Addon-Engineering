"""Class-colored name bars show the true class color (2026-10-21).

The player and target frames keep a 50% black square on the BACKGROUND layer
where the name sits, so a class color on that layer read dark (a rogue's yellow
looked olive, only in some sessions since the draw order is not fixed). Class
bars now sit on BORDER, above the square and below the
frame art, as one flat class color at 85%; NPC targets keep Blizzard's own
name background. The complete module file runs with generic widget mocks; the
look itself stays an in-game check.
"""
from pathlib import Path
import os
import unittest
from lupa.lua51 import LuaRuntime

from test_event_fanout import BASE

ROOT = Path(os.environ["VANILLAFORGE_ADDON_ROOT"])
MODULE = (ROOT / "mods/unitframes-classcolor.lua").read_text("utf-8-sig")

SETUP = r'''
-- Textures that remember their file, layer and visibility.
local Tex = setmetatable({}, { __index = function() return function() end end })
function Tex:SetTexture(t) self.texture = t end
function Tex:Show() self.shown = true end
function Tex:Hide() self.shown = false end
local function NewTexture(_, _, layer) return setmetatable({ layer = layer }, { __index = Tex }) end
RAID_CLASS_COLORS = { ROGUE = { r = 1, g = 0.96, b = 0.41 } }
PlayerFrame = CreateFrame("Frame", "PlayerFrame")
PlayerFrame.CreateTexture = NewTexture
TargetFrame = CreateFrame("Frame", "TargetFrame")
function TargetFrame:CreateTexture(name, layer) targetBar = NewTexture(self, name, layer); return targetBar end
TargetFrameNameBackground = NewTexture(nil, nil, "BACKGROUND")
TargetFrameNameBackground.texture = "blizzard"
MAX_PARTY_MEMBERS = 4
targetIsPlayer = true
function UnitExists(u) return u == "player" or u == "target" end
function UnitIsPlayer(u) return u == "player" or (u == "target" and targetIsPlayer) end
function UnitClass() return "Rogue", "ROGUE" end
function UnitName() return "Claude" end
'''

LUNA = "Interface\\Buttons\\WHITE8X8"  # one flat class color


def runtime():
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(BASE + SETUP)
    lua.execute(MODULE)
    lua.execute('FostercareTweaks.mods["Unit Frame Class Colors"]:enable()')
    return lua


class ClassColorNameBarTests(unittest.TestCase):
    def test_player_name_bar_sits_above_the_black_square(self):
        lua = runtime()
        self.assertEqual(lua.eval('PlayerFrameNameBackground.texture'), LUNA)
        self.assertEqual(lua.eval('PlayerFrameNameBackground.layer'), "BORDER")

    def test_player_target_gets_a_class_bar_above_blizzards(self):
        lua = runtime()
        self.assertEqual((lua.eval('targetBar.texture'), lua.eval('targetBar.layer')), (LUNA, "BORDER"))
        self.assertTrue(lua.eval('targetBar.shown'))
        self.assertEqual(lua.eval('TargetFrameNameBackground.texture'), "blizzard")

    def test_npc_target_shows_only_blizzards_name_background(self):
        lua = runtime()
        lua.execute('targetIsPlayer = false; FostercareTweaks.mods["Unit Frame Class Colors"]:apply()')
        self.assertFalse(lua.eval('targetBar.shown'))
        self.assertEqual(lua.eval('TargetFrameNameBackground.texture'), "blizzard")
        self.assertTrue(lua.eval('TargetFrameNameBackground.shown'))


if __name__ == '__main__':
    unittest.main()
