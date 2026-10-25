"""find_holes.py finds each kind of hole in small made-up addons."""
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))
SPEC = importlib.util.spec_from_file_location("find_holes", TOOLS / "find_holes.py")
HOLES = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HOLES)


def write(root, files):
    for rel, text in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


class FindHoles(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.root = Path(self.dir.name)
        write(self.root / "Owner", {
            "Owner.toc": "## Title: Owner\n## SavedVariables: Owner_Config\nOwner.lua\nDead.lua\n",
            "Owner.lua": (
                "Owner = {}\n"
                "if not Alias then\n    Alias = Owner\nend\n"
                "local cfg = { description = 'x', enabled = true }\n"
                "leak = 1\n"
                "-- UNVERIFIED: test in game. C_Item.GetItemSellPriceByID is not in the VanillaForge references.\n"
                "if Banzai and Banzai.Check then end\n"
                "local MIN_CLASSIC_API = 11600\n"
                "seterrorhandler(function() end)\n"
                "local f = CreateFrame('Frame', 'OwnerFrame')\n"
                "if OwnerFrame then end\n"
            ),
            "Dead.lua": "-- Remove the line below to activate.\nif true then return end\nlocal x = 1\n",
            "Unloaded.lua": "local y = 2\n",
            "img/used.tga": "", "img/unused.tga": "",
        })
        (self.root / "Owner" / "Owner.lua").write_text(
            (self.root / "Owner" / "Owner.lua").read_text() + "local t = 'Interface\\\\AddOns\\\\Owner\\\\img\\\\used'\n")
        write(self.root / "Reader", {
            "Reader.toc": "## Title: Reader\nReader.lua\n",
            "Reader.lua": "local price = Alias and Alias.Price\nlocal timers = { Owner = {} }\n",
        })
        self.everyone = [HOLES.Addon(self.root / name) for name in ("Owner", "Reader")]
        self.owner = self.everyone[0]

    def tearDown(self):
        self.dir.cleanup()

    def test_hidden_connection_in_both_directions(self):
        links = HOLES.connections(self.owner, self.everyone, set())
        alias = [l for l in links if l["name"] == "Alias"]
        self.assertEqual(len(alias), 1)
        self.assertEqual((alias[0]["reader"], alias[0]["owner"], alias[0]["declared"]), ("Reader", "Owner", False))
        # A table key named like another addon's global is not a connection.
        self.assertFalse([l for l in links if l["name"] == "Owner"])

    def test_ghost_names(self):
        names = [g["name"] for g in HOLES.ghosts(self.owner, self.everyone, set(), set(), set())]
        self.assertIn("Banzai", names)
        self.assertNotIn("OwnerFrame", names)  # created by name with CreateFrame

    def test_leaked_globals_not_table_fields(self):
        names = [l["name"] for l in HOLES.leaks(self.owner, set())]
        self.assertEqual(names, ["leak"])

    def test_unused_files(self):
        found = {f["file"]: f["why"] for f in HOLES.unused_files(self.owner)}
        self.assertIn("Unloaded.lua", found)
        self.assertIn("img/unused.tga", found)
        self.assertNotIn("img/used.tga", found)
        self.assertIn("returns before", found["Dead.lua"])

    def test_stale_note(self):
        notes = HOLES.stale_notes(self.owner, "### `C_Item.GetItemSellPriceByID(item)`")
        self.assertEqual(notes[0]["covered"], ["C_Item.GetItemSellPriceByID"])

    def test_replacements(self):
        ids = [r["id"] for r in HOLES.replacements(self.owner)]
        self.assertIn("error-handler-silenced", ids)

    def test_version_drift(self):
        drift = HOLES.version_drift(self.owner)
        self.assertTrue(any(d["found"] == "11600" for d in drift))

    def test_settings_off_everywhere_and_stale(self):
        wtf = self.root / "WTF"
        for i, saved in enumerate(["Owner_Config = { Old = 1, ['Owner'] = 0 }",
                                   "Owner_Config = { ['Owner'] = 0 }"]):
            write(wtf / "Account" / "A" / "Realm" / ("Char%d" % i) / "SavedVariables", {"Owner.lua": saved})
        result = HOLES.saved_settings(self.owner, wtf)
        self.assertEqual(result["characters"], 2)
        self.assertEqual([s["key"] for s in result["off_everywhere"]], ["Owner"])
        self.assertEqual([s["key"] for s in result["not_in_code"]], ["Old"])


if __name__ == "__main__":
    unittest.main()
