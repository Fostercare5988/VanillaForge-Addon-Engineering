"""GearRack's cooldown numbers are the client's, 2026-11-01.

Its equipment, trinket and flyout buttons used to carry a FontString each and
write the time left from a polling pass. Each button now has a native ClassicAPI
Cooldown frame ("<button>CD"); the client draws the numbers while the player's
countdownForCooldowns CVar is 1 and GearRack only styles the font. Whether the
frame sits right on the button, takes no clicks and shows the numbers stays an
in-game check.
"""
import os
import re
import unittest
from pathlib import Path

ROOT = Path(os.environ["VANILLAFORGE_ADDON_ROOT"])
SRC = ROOT / "src"


def text(name):
    return (SRC / name).read_text("utf-8-sig")


class NativeCooldownTests(unittest.TestCase):
    def test_every_button_has_a_native_cooldown_and_no_time_text(self):
        equipment, trinkets = text("Equipment.xml"), text("Trinkets.xml")
        self.assertEqual(len(re.findall(r'<Cooldown name="\$parentCD" inherits="GearRackUICooldownTemplate"/>', equipment)), 2)
        self.assertEqual(len(re.findall(r'<Cooldown name="\$parentCD" parent="GearRackTrinkets_\w+" inherits="GearRackTrinketsCooldownTemplate"/>', trinkets)), 32)
        for xml in (equipment, trinkets):
            self.assertNotIn("TimeTemplate", xml)
            self.assertNotIn('"$parentTime"', xml)

    def test_no_hand_made_countdown_remains(self):
        code = "".join(text(n) for n in ("Core.lua", "Engine.lua", "Equipment.lua", "Trinkets.lua", "TrinketOptions.lua"))
        for gone in ("WriteCooldown", "HasCooldownNumbers", "UpdateCooldownNumbers", "SetCooldownFont",
                     "WriteWornCooldowns", "WriteMenuCooldowns", "ReflectCooldownFont"):
            self.assertNotIn(gone, code)
        self.assertNotRegex(code, r'"(Time|Cooldown)"\]|\.\."(Time|Cooldown)"')

    def test_the_font_is_styled_from_the_cooldowns_own_string(self):
        core = text("Core.lua")
        self.assertIn("cooldown:GetCountdownFontString()", core)


if __name__ == "__main__":
    unittest.main()
