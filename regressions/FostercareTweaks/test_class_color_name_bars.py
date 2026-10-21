"""Class-colored name bars show the true class color (2026-10-21).

Blizzard's name background texture is grey and partly see-through, so a rogue's
yellow read as olive. Players now get the raid frames' Luna bar at full color; NPC targets keep Blizzard's
texture so its reaction colors are unchanged. The complete module file runs with
generic widget mocks; the look itself stays an in-game check.
"""
from pathlib import Path
import os
import unittest
from lupa.lua51 import LuaRuntime

from test_event_fanout import BASE

ROOT = Path(os.environ["VANILLAFORGE_ADDON_ROOT"])
MODULE = (ROOT / "mods/unitframes-classcolor.lua").read_text("utf-8-sig")

SETUP = r'''
-- Textures that remember their file.
local Tex = setmetatable({}, { __index = function() return function() end end })
function Tex:SetTexture(t) self.texture = t end
local function NewTexture() return setmetatable({}, { __index = Tex }) end
RAID_CLASS_COLORS = { ROGUE = { r = 1, g = 0.96, b = 0.41 } }
PlayerFrame = CreateFrame("Frame", "PlayerFrame")
PlayerFrame.CreateTexture = NewTexture
TargetFrameNameBackground = NewTexture()
MAX_PARTY_MEMBERS = 4
targetIsPlayer = true
function UnitExists(u) return u == "player" or u == "target" end
function UnitIsPlayer(u) return u == "player" or (u == "target" and targetIsPlayer) end
function UnitClass() return "Rogue", "ROGUE" end
function UnitName() return "Claude" end
'''

WHITE = "Interface\\AddOns\\FostercareTweaks\\img\\bar-luna.tga"  # the raid frames' bar
LEVEL = "Interface\\TargetingFrame\\UI-TargetingFrame-LevelBackground"


def runtime():
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(BASE + SETUP)
    lua.execute(MODULE)
    lua.execute('FostercareTweaks.mods["Unit Frame Class Colors"]:enable()')
    return lua


class ClassColorNameBarTests(unittest.TestCase):
    def test_player_and_player_target_get_a_plain_fill(self):
        lua = runtime()
        self.assertEqual(lua.eval('PlayerFrameNameBackground.texture'), WHITE)
        self.assertEqual(lua.eval('TargetFrameNameBackground.texture'), WHITE)

    def test_npc_target_keeps_blizzards_texture(self):
        lua = runtime()
        lua.execute('targetIsPlayer = false; FostercareTweaks.mods["Unit Frame Class Colors"]:apply()')
        self.assertEqual(lua.eval('TargetFrameNameBackground.texture'), LEVEL)


if __name__ == '__main__':
    unittest.main()
