"""Layouts by zone retired, 2026-11-03 (the player: "I can't do anything with it").

Only one character ever turned it on, and nothing in the window showed what a
layout held. The live settings stay as they are; Core clears the saved switch
and both layout keys. The mover code that re-placed frames after a switch goes
with it. Also: watched-aura icons no longer sit in HIGH strata, where they drew
over the battleground scoreboard (the game raises its windows inside MEDIUM).
In game: the scoreboard, map and bags open over a watched icon; icons still
sit in front of the unit frames.
"""
import os
import unittest
from pathlib import Path

ROOT = Path(os.environ["VANILLAFORGE_ADDON_ROOT"])


def text(name):
    return (ROOT / name).read_text("utf-8-sig")


class LayoutsRetired(unittest.TestCase):
    def test_module_file_and_toc_entry_are_gone(self):
        self.assertFalse((ROOT / "Profiles.lua").exists())
        self.assertNotIn("Profiles.lua", text("FostercareTweaks.toc"))

    def test_core_clears_the_saved_keys(self):
        # Core clears every key nothing reads (test_saved_keys_and_offline.py).
        core = text("Core.lua")
        self.assertIn("SAVED_TABLES", core)
        for key in ("Zone Layouts", "profiles"):
            self.assertNotIn(key, core)

    def test_nothing_else_still_speaks_of_layout_switches(self):
        for path in ROOT.rglob("*.lua"):
            body = path.read_text("utf-8-sig")
            for word in ("SwitchLayout", "CopyLayoutToAll", "RestoreFramePositions", "onRestore", "fctHome",
                         "CaptureLayout", "LAYOUT_NAMES", "RefreshSettings"):
                self.assertNotIn(word, body, "%s in %s" % (word, path.name))


class WatchedIconsBehindWindows(unittest.TestCase):
    def test_icons_are_not_in_high_strata(self):
        self.assertNotIn('SetFrameStrata("HIGH")', text("mods/watched-auras.lua"))


if __name__ == "__main__":
    unittest.main()
