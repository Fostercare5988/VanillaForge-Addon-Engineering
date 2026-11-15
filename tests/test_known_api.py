"""Rules K1 and K2: a call or an event that neither the client nor a DLL doc knows."""
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))


def load(name):
    spec = importlib.util.spec_from_file_location(name, TOOLS / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


KNOWN = load("known_api")
LINTER = load("vanillaforge_linter")

DOCS = {
    "classicapi/docs/API.md": "### `C_Timer.After(seconds, callback)`\n### `WEAPON_ENCHANT_CHANGED` event\n"
                              "`GetWeaponEnchantInfo()` and `Settings.RegisterAddOnSetting`\n",
    "classicapi/docs/raw_globals.txt": "    0: 0x0046CD70  CreateFrame\n    1: 0x0046CD71  GetTime\n",
    "classicapi/docs/raw_methods.txt": "    0: 0x004C1880  RegisterEvent\n    1: 0x004C1881  SetScript\n",
    # What upstream still wants to build is not what exists.
    "classicapi/TODO.md": "- `GetActiveTalentGroup()` and `PLAYER_TALENT_UPDATE`\n",
}
FRAMEXML = {"Interface/FrameXML/UIParent.lua": "function ShowUIPanel(frame) end\nUIParent:RegisterEvent('PLAYER_LOGIN')\n"}


class KnownApiTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        for base, files in (("upstream", DOCS), ("framexml", FRAMEXML)):
            for name, text in files.items():
                path = self.root / base / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text, "utf-8")
        self.known = KNOWN.KnownAPI(self.root / "upstream", self.root / "framexml")
        self.addon = self.root / "MyAddon"
        self.addon.mkdir()

    def check(self, **files):
        for name, text in files.items():
            (self.addon / name.replace("__", ".")).write_text(text, "utf-8")
        result = KNOWN.check_addon(self.addon, self.known)
        return sorted(message.split("'")[1] for messages in result.values() for message in messages)

    def test_documented_and_client_names_pass(self):
        self.assertEqual(self.check(Core__lua='''
local f = CreateFrame("Frame")
f:RegisterEvent("WEAPON_ENCHANT_CHANGED")
f:RegisterEvent("PLAYER_LOGIN")
f:SetScript("OnEvent", function() ShowUIPanel(f) end)
C_Timer.After(1, function() local has = GetWeaponEnchantInfo() end)
local text = string.format("%d", math.floor(GetTime()))
'''), [])

    def test_invented_names_fail(self):
        self.assertEqual(self.check(Core__lua='''
local f = CreateFrame("Frame")
f:RegisterEvent("PLAYER_SPEC_CHANGED")
f:SetShownNicely(true)
local spec = GetCurrentSpecialization()
C_Timer.AfterAWhile(1, print)
C_Invented.Call()
if event == "BAG_SORT_FINISHED" then end
'''), [":SetShownNicely", "BAG_SORT_FINISHED", "C_Invented.Call", "C_Timer.AfterAWhile",
       "GetCurrentSpecialization", "PLAYER_SPEC_CHANGED"])

    def test_upstreams_wish_list_is_not_a_source(self):
        self.assertEqual(self.check(Core__lua='local group = GetActiveTalentGroup()\n'
                                              'f:RegisterEvent("PLAYER_TALENT_UPDATE")\n'),
                         ["GetActiveTalentGroup", "PLAYER_TALENT_UPDATE"])

    def test_the_addons_own_names_pass_across_files(self):
        self.assertEqual(self.check(
            MyAddon__toc="## Interface: 11200\n## SavedVariables: MyAddonDB\nCore.lua\nView.lua\nView.xml\n",
            Core__lua='''
MyAddon = {}
local function helper(callback, ...) return callback(...) end
function MyAddon:Refresh() helper(self.Draw, self) end
MyAddon.handlers = { OnClick = function(button) button:Refresh() end }
for index, row in ipairs(MyAddon.handlers) do row(index) end
''',
            View__lua='MyAddon:Refresh()\nMyAddon.handlers.OnClick(MyAddonFrame)\nMyAddonDB.sort(MyAddonDB)\n'
                      'local bar = CreateFrame("Frame", "MyAddonBar")\nMyAddonBar.Layout()\n',
            View__xml='<Ui><Frame name="MyAddonFrame"><Scripts><OnLoad>MyAddon:Refresh()</OnLoad></Scripts>'
                      '</Frame></Ui>\n'), [])

    def test_a_kept_global_is_still_checked(self):
        # `local X = X` defines nothing: the name must still exist.
        self.assertEqual(self.check(Core__lua='local GetTime, GetSpec = GetTime, GetSpec\n'
                                              'local now, spec = GetTime(), GetSpec()\n'), ["GetSpec"])

    def test_comments_and_strings_are_not_calls(self):
        self.assertEqual(self.check(Core__lua='-- Invented(1)\n--[[ AlsoInvented() ]]\n'
                                              'local text = "NotACall() and f:Nothing()"\n'), [])

    def test_xml_script_bodies_are_checked(self):
        self.assertEqual(self.check(View__xml='<Ui><Frame name="A"><Scripts>\n<OnLoad>\nInventedSetup(this)\n'
                                              '</OnLoad></Scripts></Frame></Ui>\n'), ["InventedSetup"])
        result = KNOWN.check_addon(self.addon, self.known)
        self.assertIn("Line 3:", result["View.xml"][0])

    def test_a_marked_call_into_another_addon_passes(self):
        self.assertEqual(self.check(Core__lua='OtherAddon_Load("x") -- vanillaforge-ignore: K1 (OtherAddon)\n'
                                              'OtherAddon_Save("x")\n'), ["OtherAddon_Save"])

    def test_nothing_is_checked_without_the_doc_copies(self):
        (self.addon / "Core.lua").write_text("Invented()\n", "utf-8")
        missing = KNOWN.KnownAPI(self.root / "none", self.root / "none")
        self.assertFalse(missing.loaded)
        self.assertEqual(KNOWN.check_addon(self.addon, missing), {})

    def test_the_linter_fails_the_addon(self):
        (self.addon / "Core.lua").write_text("local spec = GetCurrentSpecialization()\n", "utf-8")
        results, _, _, _, errors, _, _ = LINTER.VanillaForgeAuditor(known=self.known).audit_addon_dir(str(self.addon))
        self.assertEqual(errors, 1)
        self.assertIn("Rule K1", results["Core.lua"][0][0])
        self.assertEqual(LINTER.VanillaForgeAuditor().audit_addon_dir(str(self.addon))[4], 0)
        self.assertEqual(LINTER.VanillaForgeAuditor(["K1"], self.known).audit_addon_dir(str(self.addon))[4], 0)


if __name__ == "__main__":
    unittest.main()
