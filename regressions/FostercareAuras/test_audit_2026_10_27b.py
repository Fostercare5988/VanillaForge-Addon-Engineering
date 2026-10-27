"""FostercareAuras audit 2026-10-27 (phase 1 reproductions).

P2-1: FostercareBars registers NamPower's per-unit UNIT_HEALTH_GUID and power
GUID events at load, for every unit the client tracks, and each event walks
every saved tracker looking for a bar. With no bar configured (the player's
case) that work is pure waste. This fails on 29c4fee.

P2-2: FostercareBuffData holds Turtle WoW spell data (Hot Streak, Lightning
Strike 51387-52422, Wrath rank 9 45967, Natural/Astral Boon) that is not from
the OctoWoW database. This fails on 29c4fee.
"""
from pathlib import Path
import os
import re
import unittest

ADDON = Path(os.environ["VANILLAFORGE_ADDON_ROOT"])
GUID_EVENTS = ("UNIT_HEALTH_GUID", "UNIT_MANA_GUID", "UNIT_RAGE_GUID", "UNIT_ENERGY_GUID", "UNIT_FOCUS_GUID")


def loaded_files():
    toc = (ADDON / "FostercareAuras.toc").read_text("utf-8", "replace")
    for line in toc.splitlines():
        line = line.strip()
        if line and not line.startswith("#") and line.lower().endswith(".lua"):
            yield ADDON / line.replace("\\", "/")


class PerUnitEventTests(unittest.TestCase):
    def test_no_loaded_file_takes_per_unit_health_or_power_events(self):
        found = []
        for path in loaded_files():
            text = path.read_text("utf-8-sig", "replace")
            for ev in GUID_EVENTS:
                if re.search(r'RegisterEvent\(\s*"%s"' % ev, text):
                    found.append("%s %s" % (path.name, ev))
        self.assertEqual(found, [])


class ServerDataTests(unittest.TestCase):
    def test_no_turtle_wow_spell_data(self):
        for path in loaded_files():
            text = path.read_text("utf-8-sig", "replace")
            for marker in ("Hot Streak", "Natural Boon", "Astral Boon", "[51387]", "[45967]"):
                self.assertNotIn(marker, text, "%s: %s" % (path.name, marker))


if __name__ == "__main__":
    unittest.main()
