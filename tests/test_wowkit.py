"""The shared game model (regressions/wowkit.py) behaves as its docstring says."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "regressions"))

try:
    import lupa  # noqa: F401
    import wowkit
    HAVE_LUPA = True
except ImportError:
    HAVE_LUPA = False

try:
    import lxml  # noqa: F401
    HAVE_LXML = True
except ImportError:
    HAVE_LXML = False


@unittest.skipUnless(HAVE_LUPA, "lupa is not installed")
class Events(unittest.TestCase):
    def setUp(self):
        self.lua = wowkit.runtime()
        self.lua.execute('''
            got = {}
            function listener(tag)
                local f = CreateFrame("Frame")
                f:SetScript("OnEvent", function(self, e, a)
                    got[#got + 1] = tag .. ":" .. e .. ":" .. tostring(a) .. ":" .. tostring(arg1) .. ":" .. tostring(this == self)
                end)
                return f
            end
        ''')

    def test_registration_order_and_handler_arguments(self):
        self.lua.execute('''
            local b, a = listener("b"), listener("a")
            a:RegisterEvent("X"); b:RegisterEvent("X")
            fire("X", 7)
        ''')
        self.assertEqual(list(self.lua.eval("got").values()), ["a:X:7:7:true", "b:X:7:7:true"])

    def test_unit_filter_ignores_case_and_lets_non_strings_through(self):
        self.lua.execute('''
            local f = listener("f"); f:RegisterUnitEvent("UNIT_HEALTH", "Player")
            fire("UNIT_HEALTH", "target"); fire("UNIT_HEALTH", "PLAYER"); fire("UNIT_HEALTH", 3)
        ''')
        self.assertEqual(list(self.lua.eval("got").values()), ["f:UNIT_HEALTH:PLAYER:PLAYER:true", "f:UNIT_HEALTH:3:3:true"])

    def test_a_registration_keeps_its_kind(self):
        self.lua.execute('''
            filtered = listener("u"); filtered:RegisterUnitEvent("E", "player"); filtered:RegisterEvent("E")
            plain = listener("p"); plain:RegisterEvent("E"); plain:RegisterUnitEvent("E", "player")
            noUnits = listener("n"); noUnits:RegisterUnitEvent("E", 5)
        ''')
        self.assertFalse(self.lua.eval('receives(filtered, "E", "target")'))
        self.assertTrue(self.lua.eval('receives(plain, "E", "target")'))
        self.assertTrue(self.lua.eval('receives(noUnits, "E", "target")'))
        self.assertEqual(self.lua.eval('{ filtered:IsEventRegistered("E") }')[2], "player")
        self.lua.execute('filtered:UnregisterEvent("E")')
        self.assertIsNone(self.lua.eval('filtered:IsEventRegistered("E")'))

    def test_a_handler_may_fire_another_event(self):
        self.lua.execute('''
            local outer = listener("o"); outer:RegisterEvent("A")
            local inner = listener("i"); inner:RegisterEvent("B")
            outer:SetScript("OnEvent", function() got[#got + 1] = "A"; fire("B", 1); got[#got + 1] = "A done" end)
            fire("A")
        ''')
        self.assertEqual(list(self.lua.eval("got").values()), ["A", "i:B:1:1:true", "A done"])


@unittest.skipUnless(HAVE_LUPA, "lupa is not installed")
class Widgets(unittest.TestCase):
    def setUp(self):
        self.lua = wowkit.runtime()

    def test_show_and_hide_scripts_and_visibility_through_parents(self):
        self.lua.execute('''
            seen = {}
            parent = CreateFrame("Frame"); child = CreateFrame("Frame", "Child", parent)
            child:SetScript("OnHide", function() seen[#seen + 1] = "hide" end)
            child:SetScript("OnShow", function() seen[#seen + 1] = "show" end)
            child:Hide(); child:Hide(); child:Show(); parent:Hide()
        ''')
        self.assertEqual(list(self.lua.eval("seen").values()), ["hide", "show"])
        self.assertEqual(self.lua.eval("child:IsShown()"), 1)
        self.assertIsNone(self.lua.eval("child:IsVisible()"))
        self.assertTrue(self.lua.eval("Child == child"))

    def test_flags_are_1_or_nil(self):
        self.lua.execute('b = CreateFrame("CheckButton"); b:SetChecked(true); b:Disable()')
        self.assertEqual(self.lua.eval("b:GetChecked()"), 1)
        self.assertIsNone(self.lua.eval("b:IsEnabled()"))

    def test_anchors_are_kept(self):
        self.lua.execute('f = CreateFrame("Frame"); f:SetPoint("TOPLEFT", UIParent, "TOPLEFT", 4, -2)')
        self.assertEqual(self.lua.eval("f:GetNumPoints()"), 1)
        self.assertEqual(self.lua.eval("select(5, f:GetPoint(1))"), -2)

    def test_a_suite_may_reuse_the_global_names(self):
        self.lua.execute('''
            function run(seconds) error("the suite's own run") end
            function runTimers() error("the suite's own runTimers") end
            f = CreateFrame("Frame"); f:Hide(); f:Show(); step(1)
        ''')
        self.assertEqual(self.lua.eval("f:IsShown()"), 1)

    def test_the_kit_builds_no_garbage(self):
        kb = self.lua.execute('''
            local f = CreateFrame("Frame"); f:RegisterUnitEvent("UNIT_HEALTH", "player")
            f:SetScript("OnEvent", function() end)
            local g = CreateFrame("Frame"); g:RegisterEvent("UNIT_HEALTH"); g:SetScript("OnEvent", function() end)
            for i = 1, 50 do fire("UNIT_HEALTH", "player"); f:SomeUnknownMethod() end
            collectgarbage("collect"); collectgarbage("stop")
            local before = collectgarbage("count")
            for i = 1, 2000 do fire("UNIT_HEALTH", "player"); f:SomeUnknownMethod() end
            local kb = collectgarbage("count") - before
            collectgarbage("restart")
            return kb
        ''')
        self.assertLess(kb, 1, "%.1f KB for 2000 events" % kb)


@unittest.skipUnless(HAVE_LUPA, "lupa is not installed")
class Time(unittest.TestCase):
    def test_step_runs_due_timers_then_visible_on_updates(self):
        lua = wowkit.runtime()
        lua.execute('''
            log = {}
            C_Timer.After(1, function() log[#log + 1] = "after" end)
            ticker = C_Timer.NewTicker(0.5, function() log[#log + 1] = "tick" end, 3)
            cancelled = C_Timer.NewTimer(0.1, function() log[#log + 1] = "never" end); cancelled:Cancel()
            shown = CreateFrame("Frame"); shown:SetScript("OnUpdate", function(self, dt) log[#log + 1] = "update " .. dt .. " " .. arg1 end)
            hidden = CreateFrame("Frame"); hidden:Hide(); hidden:SetScript("OnUpdate", function() log[#log + 1] = "hidden" end)
            step(1); step(1)
        ''')
        self.assertEqual(list(lua.eval("log").values()),
                         ["tick", "after", "tick", "update 1 1", "tick", "update 1 1"])
        self.assertEqual(lua.eval("GetTime()"), 102)


class Loading(unittest.TestCase):
    def test_lua50_table_loops(self):
        cases = {
            'for _, e in { "A", "B" } do': 'for _, e in pairs({ "A", "B" }) do',
            "for k, v in m.api.X[ key ] do": "for k, v in pairs(m.api.X[ key ]) do",
            'for w in string.gmatch(s, "%a+") do': 'for w in string.gmatch(s, "%a+") do',
            "for k, v in pairs(t) do": "for k, v in pairs(t) do",
        }
        if not HAVE_LUPA:
            self.skipTest("lupa is not installed")
        for source, expected in cases.items():
            self.assertEqual(wowkit.lua50(source), expected)

    @unittest.skipUnless(HAVE_LUPA, "lupa is not installed")
    def test_saved_variables_load_when_the_toc_says(self):
        for first, expected in (("## LoadSavedVariablesFirst: 1\n", "saved"), ("", "default")):
            with tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                (root / "Demo.toc").write_text(first + "## Title: Demo\nCore.lua\n", "utf-8")
                (root / "Core.lua").write_text(
                    'local name, ns = ...\nDemoSeen = DemoDB and DemoDB.v or "default"\nDemoName = name\nDemoDB = DemoDB or { v = "default" }\n',
                    "utf-8")
                lua = wowkit.runtime()
                wowkit.load_addon(lua, root, "Demo", 'DemoDB = { v = "saved" }')
                self.assertEqual(lua.eval("DemoSeen"), expected)
                self.assertEqual(lua.eval("DemoName"), "Demo")
                self.assertEqual(lua.eval("DemoDB.v"), "saved")

    @unittest.skipUnless(HAVE_LUPA and HAVE_LXML, "lupa or lxml is not installed")
    def test_xml_frames_expand_parent_and_templates(self):
        with tempfile.TemporaryDirectory() as folder:
            xml = Path(folder) / "Demo.xml"
            xml.write_text('''<Ui>
  <Button name="DemoRowTemplate" virtual="true"><Layers><Layer><FontString name="$parentLabel"/></Layer></Layers></Button>
  <Frame name="DemoFrame">
    <Frames><Button name="$parentRow1" inherits="DemoRowTemplate"/><CheckButton name="$parentCheck" inherits="UICheckButtonTemplate"/></Frames>
  </Frame>
</Ui>''', "utf-8")
            names = dict(wowkit.xml_frames([xml], {"UICheckButtonTemplate": ["$parentText"]}))
        for name in ("DemoFrame", "DemoFrameRow1", "DemoFrameRow1Label", "DemoFrameCheck", "DemoFrameCheckText"):
            self.assertIn(name, names)
        self.assertNotIn("DemoRowTemplate", names)


if __name__ == "__main__":
    unittest.main()
