"""ClassicAPI 1.18.5 pass, 2026-10-30.

GearRackUI_GetForm, which the stock form events call, reads the active
stance-bar index from GetShapeshiftForm (1.18.0, docs/API.md) instead of
looping over the bar. It returns that form's name, or nil with no form and
for a form that is not on the bar (index = bar size + 1).
"""
from pathlib import Path
import os
import unittest
from lupa.lua51 import LuaRuntime

ROOT = Path(os.environ["VANILLAFORGE_ADDON_ROOT"])
SOURCE = (ROOT / "src/Equipment.lua").read_text("utf-8-sig")


def form_runtime(names, active):
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(r'''
        forms, active, infoCalls = {}, 0, 0
        function GetShapeshiftForm() return active end
        function GetNumShapeshiftForms() return table.getn(forms) end
        function GetShapeshiftFormInfo(i)
            infoCalls = infoCalls + 1
            return "tex", forms[i], i == active and 1 or nil
        end
    ''')
    for i, name in enumerate(names):
        lua.execute('forms[%d] = "%s"' % (i + 1, name))
    lua.execute('active = %d' % active)
    start = SOURCE.index('function GearRackUI_GetForm()')
    lua.execute(SOURCE[start:SOURCE.index('\nend\n', start) + 5])
    return lua


class GetFormTests(unittest.TestCase):
    BAR = ["Bear Form", "Aquatic Form", "Cat Form", "Travel Form"]

    def test_names_the_active_form_with_one_lookup(self):
        lua = form_runtime(self.BAR, 3)
        self.assertEqual(lua.eval('GearRackUI_GetForm()'), "Cat Form")
        self.assertEqual(lua.eval('infoCalls'), 1)

    def test_no_form_and_off_bar_form_are_nil(self):
        for index in (0, len(self.BAR) + 1):
            lua = form_runtime(self.BAR, index)
            self.assertIsNone(lua.eval('GearRackUI_GetForm()'), index)
            self.assertEqual(lua.eval('infoCalls'), 0)

    def test_guard_names_no_version(self):
        # The version lives only in VanillaForge's UPSTREAM_VERSIONS.json (2026-10-30).
        boot = (ROOT / "src/Bootstrap.lua").read_text("utf-8-sig")
        self.assertIn('type(CLASSIC_API_VERSION)~="number" then', boot)
        self.assertNotIn("X-ClassicAPI-Min-Version", (ROOT / "GearRack.toc").read_text("utf-8-sig"))


if __name__ == "__main__":
    unittest.main()
