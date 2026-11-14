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
                "_tick = 0\n"
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
            "img/Nodes/Farm_Horde.tga": "", "img/Nodes/Mill_Horde.tga": "",
        })
        (self.root / "Owner" / "Owner.lua").write_text(
            (self.root / "Owner" / "Owner.lua").read_text() + "local t = 'Interface\\\\AddOns\\\\Owner\\\\img\\\\used'\n"
            + "local kinds = { 'Farm' }\nlocal p = 'Interface\\\\AddOns\\\\Owner\\\\img\\\\Nodes\\\\' .. kinds[1] .. '_' .. 'Horde'\n")
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

    def test_stale_mocks(self):
        mock = "\n".join([
            "MOCK = r'''",
            "function OwnerRemovedLongAgo() end",
            "function TestHelperRun() end",
            "C_Owner = {}",
            "function C_Owner.GoneFunction() end",
            "function GetTime() return 1 end",
            "function OwnerFrameShow() end",
            "'''",
            "lua.execute('TestHelperRun()')",
        ])
        write(self.root / "regressions" / "Owner", {"test_owner.py": mock})
        owner = HOLES.Addon(self.root / "Owner")
        stale = HOLES.stale_mocks(owner, [owner], {"GetTime"}, set(), regressions=self.root / "regressions")
        self.assertEqual([s["name"] for s in stale], ["C_Owner.GoneFunction", "OwnerFrameShow", "OwnerRemovedLongAgo"])
        self.assertEqual(stale[-1]["where"], ["test_owner.py:2"])

    def test_ghost_names(self):
        names = [g["name"] for g in HOLES.ghosts(self.owner, self.everyone, set(), set(), set())]
        self.assertIn("Banzai", names)
        self.assertNotIn("OwnerFrame", names)  # created by name with CreateFrame

    def test_numbered_names_the_game_builds_are_not_ghosts(self):
        # WorldStateFrame.lua: name = "AlwaysUpFrame"..alwaysUpShown; CreateFrame("Frame", name, ...)
        game = HOLES.global_defs('local name = "AlwaysUpFrame"..alwaysUpShown\nlocal f = CreateFrame("Frame", name)\n')
        write(self.root / "Owner", {"Owner.lua": "if AlwaysUpFrame1 and AlwaysUpFrame1:IsShown() then end\nif Banzai then end\n"})
        owner = HOLES.Addon(self.root / "Owner")
        names = [g["name"] for g in HOLES.ghosts(owner, [owner], game, set(), set())]
        self.assertNotIn("AlwaysUpFrame1", names)
        self.assertIn("Banzai", names)

    def test_leaked_globals_not_table_fields(self):
        names = [l["name"] for l in HOLES.leaks(self.owner, set())]
        self.assertEqual(names, ["_tick", "leak"])

    def test_unused_files(self):
        found = {f["file"]: f["why"] for f in HOLES.unused_files(self.owner)}
        self.assertIn("Unloaded.lua", found)
        self.assertIn("img/unused.tga", found)
        self.assertNotIn("img/used.tga", found)
        # Built from parts: the folder and each part of the name are in the code.
        self.assertNotIn("img/Nodes/Farm_Horde.tga", found)
        self.assertIn("img/Nodes/Mill_Horde.tga", found)
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

    def test_version_drift_for_every_dll(self):
        write(self.root / "Pinned", {
            "Pinned.toc": "## Title: Pinned\n## X-NamPower-Min-Version: 4.6.2\nPinned.lua\n",
            "Pinned.lua": 'local s = string.find(tostring(SUPERWOW_VERSION or ""), "^(%d+)")\n'
                          'local major = GetNampowerVersion()\n'
                          'if SUPERWOW_VERSION and GetNampowerVersion then ok = true end\n',
        })
        drift = HOLES.version_drift(HOLES.Addon(self.root / "Pinned"))
        self.assertEqual(len(drift), 3)
        self.assertEqual(drift[0]["found"], "4.6.2")

    def test_settings_off_everywhere_and_stale(self):
        wtf = self.root / "WTF"
        for i, saved in enumerate(["Owner_Config = { Old = 1, ['Owner'] = 0 }",
                                   "Owner_Config = { ['Owner'] = 0 }"]):
            write(wtf / "Account" / "A" / "Realm" / ("Char%d" % i) / "SavedVariables", {"Owner.lua": saved})
        result = HOLES.saved_settings(self.owner, wtf)
        self.assertEqual(result["characters"], 2)
        self.assertEqual([s["key"] for s in result["off_everywhere"]], ["Owner"])
        self.assertEqual([s["key"] for s in result["not_in_code"]], ["Old"])


class DeadAndDuplicateFunctions(unittest.TestCase):
    BODY = "".join("  local v%d = %d\n" % (i, i) for i in range(7))

    def test_unreferenced_and_repeated_functions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root / "Toy", {
                "Toy.toc": "## Title: Toy\nToy.lua\nToy.xml\n",
                "Toy.lua": ("function Dead()\n" + self.BODY + "end\nfunction Alive()\n" + self.BODY + "end\n"
                            "function FromXml()\nend\nfunction FromBinding()\nend\nAlive()\n"),
                "Toy.xml": "<Ui><Button name='B'><Scripts><OnClick>FromXml()</OnClick></Scripts></Button></Ui>",
                # Loaded by the client without a TOC line.
                "Bindings.xml": "<Bindings><Binding name='TOY'>FromBinding()</Binding></Bindings>",
            })
            addon = HOLES.Addon(root / "Toy")
            self.assertEqual([f["name"] for f in HOLES.unreferenced_functions(addon)], ["Dead"])
            self.assertEqual(len(HOLES.duplicate_functions(addon)), 1)


class RepeatingWork(unittest.TestCase):
    def test_every_ticker_and_on_update_is_listed_with_whether_it_stops(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root / "Toy", {
                "Toy.toc": "## Title: Toy\nForever.lua\nStops.lua\nToy.xml\n",
                "Forever.lua": ("-- C_Timer.NewTicker(1, f) in a comment is no timer\n"
                                "C_Timer.NewTicker(1, function() end)\n"
                                "frame:SetScript('OnUpdate', function() end)\n"),
                "Stops.lua": ("local t = C_Timer.NewTicker(1, function() end)\nt:Cancel()\n"
                              "f:SetScript(\"OnUpdate\", step)\nf:SetScript(\"OnUpdate\", nil)\n"),
                "Toy.xml": "<Ui><Frame name='F'><Scripts><OnUpdate>Step()</OnUpdate></Scripts></Frame></Ui>",
            })
            found = [(f["kind"], f["where"], f["stops"]) for f in HOLES.repeating_work(HOLES.Addon(root / "Toy"))]
            self.assertEqual(found, [
                ("ticker", "Forever.lua:2", False), ("OnUpdate", "Forever.lua:3", False),
                ("ticker", "Stops.lua:1", True), ("OnUpdate", "Stops.lua:3", True),
                ("XML OnUpdate", "Toy.xml:1", False)])


class StockPerFrame(unittest.TestCase):
    """2026-11-13: FostercareTweaks' biggest saving was FrameXML's own
    ActionButton_OnUpdate on 72 buttons, which no section saw."""

    def test_the_games_onupdate_on_frames_the_addon_touches_is_listed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root / "game", {
                "Interface/FrameXML/ActionButton.lua": ("function ActionButton_OnUpdate(e) end\n"
                                                        "function ActionButton_Update() end\n"
                                                        "function UIParent_Helper() end\n"),
                "Interface/FrameXML/ActionBarFrame.xml": (
                    "<Ui><CheckButton name='ActionButton1'><Scripts><OnUpdate>ActionButton_OnUpdate(arg1);"
                    "</OnUpdate></Scripts></CheckButton><Frame name='UIParentish'/></Ui>"),
            })
            write(root / "Bars", {
                "Bars.toc": "## Title: Bars\nBars.lua\n",
                "Bars.lua": ("hooksecurefunc('ActionButton_Update', f)\nUIParent_Helper()\n"),
            })
            write(root / "Plain", {"Plain.toc": "## Title: Plain\nPlain.lua\n", "Plain.lua": "UIParent_Helper()\n"})
            work = HOLES.stock_frame_work(root / "game")
            found = HOLES.stock_per_frame(HOLES.Addon(root / "Bars"), work)
            self.assertEqual([(f["function"], f["touched"], f["names"]) for f in found],
                             [("ActionButton_OnUpdate", [("ActionButton_Update", "Bars.lua:1")], False)])
            # A helper of the same file without the prefix is not the frame's family.
            self.assertEqual(HOLES.stock_per_frame(HOLES.Addon(root / "Plain"), work), [])


class PiecemealCleanup(unittest.TestCase):
    def test_saved_keys_cleared_one_by_one_are_listed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root / "Old", {
                "Old.toc": "## Title: Old\n## SavedVariables: Old_DB\nOld.lua\n",
                "Old.lua": 'Old_DB["Gone One"] = nil\nOld_DB.gone2 = nil\nlocal x = nil\n',
            })
            write(root / "Swept", {
                "Swept.toc": "## Title: Swept\n## SavedVariables: Swept_DB\nSwept.lua\n",
                "Swept.lua": "for k in pairs(Swept_DB) do if not OWNED[k] then Swept_DB[k] = nil end end\n"
                             'Swept_DB["One"] = nil\n',
            })
            found = HOLES.piecemeal_cleanup(HOLES.Addon(root / "Old"))
            self.assertEqual([(f["key"], f["where"]) for f in found], [("Gone One", "Old.lua:1"), ("gone2", "Old.lua:2")])
            self.assertEqual(HOLES.piecemeal_cleanup(HOLES.Addon(root / "Swept")), [])   # one line is no pattern


class ReplacementUnless(unittest.TestCase):
    def test_a_file_already_on_the_event_is_no_lead(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root / "Toy", {
                "Toy.toc": "## Title: Toy\nPoll.lua\nEvent.lua\n",
                "Poll.lua": "C_Timer.NewTicker(0.25, function() return UnitInRange('party1') end)\n",
                "Event.lua": "local f = CreateFrame('Frame')\nf:RegisterEvent(\"UNIT_IN_RANGE_UPDATE\")\nlocal r = UnitInRange('party1')\n",
            })
            leads = {x["id"]: x for x in HOLES.replacements(HOLES.Addon(root / "Toy"))}
            self.assertEqual(leads["range-poll-ticker"]["where"], ["Poll.lua:1"])


class XmlScriptGhosts(unittest.TestCase):
    def test_a_function_an_xml_script_calls_that_nothing_defines_is_a_ghost(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root / "Probe", {
                "Probe.toc": "## Title: Probe\nProbe.xml\nProbe.lua\n",
                "Probe.lua": "function ProbeKnown() end\n",
                "Probe.xml": '<Ui><Button name="ProbeButton"><Scripts><OnClick>ProbeKnown(); ProbeMissing(this);</OnClick></Scripts></Button></Ui>',
            })
            probe = HOLES.Addon(root / "Probe")
            ghosts = HOLES.ghosts(probe, [probe], set(), set(), set())
        self.assertEqual([g["name"] for g in ghosts], ["ProbeMissing"])
        self.assertIn("(script)", ghosts[0]["where"][0])


class FrameNamesFromHelpersAndParents(unittest.TestCase):
    """GearRack 2026-11-08: names made through a helper (a panel maker that passes its
    name on to UI.Button, then CreateFrame) and $parent under parent="X" were ghosts."""

    def test_helper_names_and_explicit_parents_are_defined(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root / "Probe", {
                "Probe.toc": "## Title: Probe\nProbe.xml\nUI.lua\nProbe.lua\n",
                "UI.lua": "local UI = {}\nfunction UI.Button(name, parent)\n    return CreateFrame(\"Button\", name, parent)\nend\n",
                "Probe.lua": ("function Probe.Pill(frame, name, label)\n    return UI.Button(name, frame)\nend\n"
                              "Probe.Pill(UIParent, \"ProbeNext\", \"Next\")\n"
                              "ProbeNext:Show() ProbeOwnerCD:Show() ProbeMissing:Show()\n"),
                "Probe.xml": ('<Ui><Frame name="ProbeHolder"><Frames><Button name="ProbeOwner"/>'
                              '<Cooldown name="$parentCD" parent="ProbeOwner"/></Frames></Frame></Ui>'),
            })
            probe = HOLES.Addon(root / "Probe")
            ghosts = HOLES.ghosts(probe, [probe], {"CreateFrame", "UIParent"}, set(), set())
        self.assertEqual([g["name"] for g in ghosts], ["ProbeMissing"])


if __name__ == "__main__":
    unittest.main()
