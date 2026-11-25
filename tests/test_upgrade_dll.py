"""upgrade_dll.py names the gaps a release may cover (no network: the pure parts)."""
import contextlib
import importlib.util
import io
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))
SPEC = importlib.util.spec_from_file_location("upgrade_dll", TOOLS / "upgrade_dll.py")
UPGRADE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(UPGRADE)


class ApiNames(unittest.TestCase):
    def test_api_shaped_names_only(self):
        text = ("`C_AddOnProfiler.GetAddOnMetric(name, metric)` and GetDefaultNamePlateSize; "
                "SPELL_RANGE_CHECK_UPDATE fires; the nameplateShowClassColor cvar. "
                "Until the Frame shows, Use it.")
        self.assertEqual(UPGRADE.api_names(text), {
            "C_AddOnProfiler", "GetAddOnMetric", "GetDefaultNamePlateSize",
            "SPELL_RANGE_CHECK_UPDATE", "nameplateShowClassColor"})


class GapHits(unittest.TestCase):
    GAPS = [
        {"where": "Nameplates Core.lua:202", "text": "a DLL should give C_NamePlate.GetDefaultNamePlateSize()"},
        {"where": "AutoBG Core.lua:230", "text": "no event (UNIT_DISTANCE_CHECK_UPDATE is for your group)"},
    ]

    def test_only_a_gap_that_names_what_the_release_adds(self):
        # UNIT_DISTANCE_CHECK_UPDATE was documented before: comparing old and
        # new docs keeps a gap that only mentions it from being a hit.
        added = {"GetDefaultNamePlateSize", "UnitCombatReach"}
        hits = UPGRADE.gap_hits(self.GAPS, added)
        self.assertEqual(hits, [dict(self.GAPS[0], names=["GetDefaultNamePlateSize"])])

    def test_the_report_puts_the_hits_first_and_lists_every_code_gap(self):
        planned = [{"where": "WISHLIST.md:9", "text": "| `C_Timer` swallows errors | !ErrorLog | `TimerGuard` |"}]
        with contextlib.redirect_stdout(io.StringIO()) as out:
            UPGRADE.report_gaps(self.GAPS, planned, {"GetDefaultNamePlateSize", "TimerGuard"})
        lines = out.getvalue().splitlines()
        self.assertEqual(lines[1], "Gaps that name an API the newer docs add (2; read these first):")
        self.assertEqual(lines[2:4], ["  Nameplates Core.lua:202: GetDefaultNamePlateSize",
                                      "  WISHLIST.md:9: TimerGuard"])
        self.assertEqual(lines[5], "Every gap in the maintained addons (2; does the release do one of them?):")
        self.assertEqual(len(lines), 8)


class WishlistGaps(unittest.TestCase):
    def test_table_rows_without_the_separators(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "WISHLIST.md"
            path.write_text("# Wishlist\n\n| Gap | Addon |\n| --- | --- |\n| No `UnequipItem` | GearRack |\n"
                            "- not a row\n", encoding="utf-8")
            self.assertEqual(UPGRADE.wishlist_gaps(path), [
                {"where": "WISHLIST.md:3", "text": "| Gap | Addon |"},
                {"where": "WISHLIST.md:5", "text": "| No `UnequipItem` | GearRack |"}])
            self.assertEqual(UPGRADE.wishlist_gaps(Path(tmp) / "missing.md"), [])


if __name__ == "__main__":
    unittest.main()
