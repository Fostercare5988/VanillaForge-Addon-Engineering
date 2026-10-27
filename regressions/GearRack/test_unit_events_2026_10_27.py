"""GearRack hears UNIT_INVENTORY_CHANGED for the player only, 2026-10-27.

ClassicAPI fires unit events once per token, nameplateN and markN included
(docs/API.md, RegisterUnitEvent), and both GearRack handlers act only on
"player". frame:RegisterUnitEvent drops the other tokens before Lua runs.
Fails on 2b07347. The event rate saved in a battleground stays an in-game check.
"""
from pathlib import Path
import os
import re
import unittest

ROOT = Path(os.environ["VANILLAFORGE_ADDON_ROOT"])


class InventoryEventFilter(unittest.TestCase):
    def test_registered_for_the_player_only(self):
        sources = {p.name: p.read_text("utf-8-sig") for p in (ROOT / "src").glob("*.lua")}
        plain = [n for n, s in sources.items() if re.search(r'RegisterEvent\(\s*"UNIT_INVENTORY_CHANGED"', s)]
        self.assertEqual(plain, [])
        self.assertIn('f:RegisterUnitEvent("UNIT_INVENTORY_CHANGED", "player")', sources["Equipment.lua"])


if __name__ == "__main__":
    unittest.main()
