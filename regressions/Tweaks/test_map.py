"""Minimap and world map (spec T9, T10, 4.7 "Tweaks"): minimap size from the
page; the clock wakes once a minute; the pieces move with Ctrl+Shift and come
back; the map window's size; coordinates write only on change and stop with
the map; group dots in class colours.
"""
import unittest
from ftr_env import load


class Minimap(unittest.TestCase):
    def test_size_scales_the_map_and_keeps_the_icons_size(self):
        lua = load()
        self.assertEqual(lua.eval("Minimap:GetScale()"), 1.6)
        self.assertAlmostEqual(lua.eval("MiniMapMailFrame:GetScale()"), 1 / 1.6)
        self.assertAlmostEqual(lua.eval("MinimapClock:GetScale()"), 1 / 1.6)

    def test_square_and_round(self):
        lua = load()
        self.assertEqual(lua.eval("Minimap.mask"), "Interface\\Buttons\\WHITE8X8")
        self.assertIsNone(lua.eval("MinimapBorder:GetTexture()"))
        lua.execute("settingsWindow.use('Tweaks_minimapSquare', false)")
        self.assertEqual(lua.eval("Minimap.mask"), "Textures\\MinimapMask")
        self.assertEqual(lua.eval("MinimapBorder:GetTexture()"), "Interface\\Minimap\\UI-Minimap-Border")

    def test_tidy_hides_the_clutter_and_the_wheel_zooms(self):
        lua = load()
        self.assertFalse(lua.eval("MinimapZoomIn:IsShown()"))
        self.assertIs(lua.eval("Minimap.wheel"), True)
        lua.execute("run(Minimap, 'OnMouseWheel', 1)")
        self.assertEqual(lua.eval("last('zoom')"), 1)
        lua.execute("GameTimeFrame:Show()")
        self.assertFalse(lua.eval("GameTimeFrame:IsShown()"), "the game shows it again; it stays hidden")
        lua.execute("settingsWindow.use('Tweaks_minimapTidy', false)")
        self.assertTrue(lua.eval("MinimapZoomIn:IsShown()"))
        self.assertIs(lua.eval("Minimap.wheel"), False)

    def test_the_clock_wakes_once_a_minute_and_stops_when_off(self):
        lua = load()
        text = "(function() for _, w in ipairs(widgets) do if w.parent == MinimapClock and w.kind == 'FontString' " \
               "then return w:GetText() end end end)()"
        self.assertEqual(lua.eval(text), "13:07")
        lua.execute("clockAt.M, clockAt.S = '08', '00'; step(18)")
        self.assertEqual(lua.eval(text), "13:07", "not before the minute turns")
        lua.execute("step(1)")
        self.assertEqual(lua.eval(text), "13:08")
        lua.execute("settingsWindow.use('Tweaks_minimapClock', false); step(61)")
        self.assertEqual(lua.eval("liveTimers()"), 0)
        self.assertFalse(lua.eval("MinimapClock:IsShown()"))

    def test_ctrl_shift_moves_a_piece_and_it_comes_back(self):
        lua = load()
        handle = "(function() for _, w in ipairs(widgets) do if w.parent == MiniMapMailFrame then return w end end end)()"
        lua.execute("press(true, true)")
        self.assertTrue(lua.eval("MiniMapMailFrame:IsShown()"), "shown while the keys are held")
        lua.execute(f"local h = {handle}; run(h, 'OnMouseDown'); run(h, 'OnMouseUp')")
        lua.execute("press(false, false)")
        self.assertFalse(lua.eval("MiniMapMailFrame:IsShown()"), "no mail: the game's rule again")
        self.assertEqual(list(lua.eval("TweaksDB.pieces.mail").values()), [700, 300])
        self.assertTrue(lua.eval("MiniMapMailFrame.dontSave"))
        again = load("TweaksDB = { pieces = { mail = { 700, 300 } } }")
        self.assertEqual(again.eval("(function() local p, to, rel, x, y = MiniMapMailFrame:GetPoint("
                                    "#MiniMapMailFrame.points); return table.concat({ p, tostring(to == UIParent),"
                                    " rel, x, y }, ' ') end)()"), "CENTER true BOTTOMLEFT 700 300")

    def test_letting_go_while_dragging_still_saves(self):
        lua = load()
        lua.execute("press(true, true); for _, w in ipairs(widgets) do if w.parent == MinimapZoneTextButton "
                    "then run(w, 'OnMouseDown') end end; press(false, false)")
        self.assertIsNotNone(lua.eval("TweaksDB.pieces.zone"))


class WorldMap(unittest.TestCase):
    def test_the_window_takes_the_pages_size_and_full_screen_is_never_scaled(self):
        lua = load()
        self.assertEqual(lua.eval("WorldMapFrame:GetScale()"), 1.65)
        lua.execute("WorldMapFrame_Maximize()")
        self.assertEqual(lua.eval("WorldMapFrame:GetScale()"), 1)
        lua.execute("WorldMapFrame_Minimize()")
        self.assertEqual(lua.eval("WorldMapFrame:GetScale()"), 1.65)

    def test_ctrl_wheel_changes_the_size_within_its_range(self):
        lua = load()
        lua.execute("ctrl = true; run(WorldMapFrame, 'OnMouseWheel', 1)")
        self.assertAlmostEqual(lua.eval("TweaksDB.mapScale"), 1.7)
        self.assertAlmostEqual(lua.eval("Settings.GetValue('Tweaks_mapScale')"), 1.7)
        for _ in range(10):
            lua.execute("run(WorldMapFrame, 'OnMouseWheel', 1)")
        self.assertEqual(lua.eval("TweaksDB.mapScale"), 2)
        lua.execute("ctrl = false; run(WorldMapFrame, 'OnMouseWheel', -1)")
        self.assertEqual(lua.eval("TweaksDB.mapScale"), 2, "no Ctrl: the map's own wheel")

    def test_coordinates_only_while_the_map_shows_and_written_on_change(self):
        lua = load()
        self.assertEqual(lua.eval("liveTimers()"), 1, "the clock only")
        lua.execute("WorldMapFrame:Show()")
        label = "(function() for _, w in ipairs(widgets) do if w.parent == WorldMapButton and w.title and " \
                "string.find(w.title, 'Player') then return w end end end)()"
        self.assertEqual(lua.eval(f"{label}:GetText()"), "|cffffcc00Player: |r45.7 / 12.3")
        lua.execute(f"{label}.text = 'untouched'; mapPos = {{ 0.4568, 0.1231 }}; step(0.1)")
        self.assertEqual(lua.eval(f"{label}:GetText()"), "untouched", "the same tenth: not written")
        lua.execute("mapPos = { 0, 0 }; step(0.1)")
        self.assertEqual(lua.eval(f"{label}:GetText()"), "|cffffcc00Player: |rN/A")
        lua.execute("WorldMapFrame:Hide(); calls.mapPos = nil; step(1)")
        self.assertEqual(lua.eval("count('mapPos')"), 0)
        self.assertEqual(lua.eval("liveTimers()"), 1)

    def test_group_members_as_class_dots(self):
        lua = load(setup="names.party1 = 'Ann'; classes.party1 = 'MAGE'")
        lua.execute("WorldMapParty1:Show(); WorldMapRaid1.name = 'Zed'; known.Zed = 'ROGUE'; WorldMapRaid1:Show();"
                    "WorldMapFrame:Show(); step(0.1)")
        self.assertEqual(lua.eval("WorldMapParty1.ftDot.color[1]"), 0.41)
        self.assertEqual(lua.eval("WorldMapParty1.ftDot:GetTexture()"),
                         "Interface\\AddOns\\Tweaks\\img\\circleparty")
        self.assertEqual(lua.eval("WorldMapRaid1.ftDot:GetTexture()"),
                         "Interface\\AddOns\\Tweaks\\img\\circleraid")
        self.assertEqual(lua.eval("WorldMapRaid1.ftDot.color[1]"), 1)
        lua.execute("WorldMapRaid2.name = 'Unseen'; WorldMapRaid2:Show(); step(0.2)")
        self.assertEqual(lua.eval("WorldMapRaid2.ftDot.color[2]"), 1, "an unknown class: green")

    def test_the_battleground_map_once_it_loads(self):
        lua = load()
        lua.execute("mapButtons('BattlefieldMinimap'); loaded.Blizzard_BattlefieldMinimap = true; fire('ADDON_LOADED', 'Blizzard_BattlefieldMinimap');"
                    "BattlefieldMinimap:Hide(); BattlefieldMinimap:Show()")
        self.assertEqual(lua.eval("liveTimers()"), 2)
        lua.execute("BattlefieldMinimap:Hide()")
        self.assertEqual(lua.eval("liveTimers()"), 1)
        lua.execute("loadInspect()")
        self.assertNotIn("ADDON_LOADED", lua.eval("listening()"), "nothing else to wait for once both loaded")


if __name__ == "__main__":
    unittest.main()
