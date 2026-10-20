"""Reproductions for the 2026-10-20 FostercareNameplates audit
(.private/audit-FostercareNameplates-2026-10-20.md).

Each test fails on FostercareNameplates 1.0.0 for the reason in its docstring.
Lua 5.1 with generic mocks; native plates and engine timing stay in-game checks.
"""
import unittest
from fnp_env import load


class AuditReproductions(unittest.TestCase):
    def test_p2_master_switch_off_is_honored(self):
        """P2-1: Lifecycle.lua reads the saved master switch at file scope, before
        the client restores SavedVariables, so a saved 0 still claims every plate."""
        lua = load("{ nameplatesEnabled = 0, overwrites = {}, settingsVersion = 1 }")
        self.assertFalse(lua.eval("FostercareNameplates.nameplatesEnabled"))
        self.assertFalse(lua.eval("FostercareNameplates.OwnsNameplates() and true or false"))
        self.assertIsNone(lua.eval('FNPLibNameplate.events.NAME_PLATE_UNIT_ADDED'))

    def test_p2_saved_module_choice_reaches_initialize(self):
        """P2-1: Core.lua keeps a local alias of the pre-restore table, so Initialize
        reads defaults, not the saved module choice, when deciding what to enable."""
        lua = load('{ ["Nameplate Castbar"] = 0, overwrites = {}, settingsVersion = 1 }')
        self.assertEqual(lua.eval('FostercareNameplates_Config["Nameplate Castbar"]'), 0)
        self.assertIsNone(lua.eval('rawget(_G, "FNPNameplateCastEvents")'))

    def test_p2_guid_lookup_uses_guid_api(self):
        """P2-2: GUIDs went to GetNamePlateForUnit, which ClassicAPI documents for unit
        tokens; GetNamePlateForGUID is the documented GUID lookup."""
        lua = load(prelude='''
            plate = CreateFrame("Button")
            C_NamePlate.GetNamePlateForUnit = function(u)
                if string.find(u, "^0x") then return nil end
                if u == "nameplate1" then return plate end
            end
            C_NamePlate.GetNamePlateForGUID = function(g) if g == "0xF1" then return plate end end
        ''')
        lua.execute('plate.fnpUnitGUID = "0xF1"')
        self.assertEqual(lua.eval("FostercareNameplates.GetNameplateUnit(plate)"), "0xF1")

    def test_p3_plate_binding_checked_on_slow_cadence(self):
        """P3-1: every plate re-validated its GUID binding every frame (60 lookups a second)."""
        lua = load()
        lua.execute('plate = nativePlate("0xF1", "nameplate1"); calls = {}; runFrames(plate, 60)')
        self.assertLessEqual(lua.eval('calls.GetNamePlateForGUID or 0'), 3)

    def test_p3_no_plate_work_when_nothing_renders(self):
        """P3-1: after the per-frame modules were switched off in settings, the
        per-plate hook kept running its lookup every frame."""
        lua = load()
        lua.execute('''
            plate = nativePlate("0xF1", "nameplate1")
            for _, title in ipairs({ "Nameplate Details", "Nameplate Castbar", "Nameplate Class Colors" }) do
                FostercareNameplates_Config[title] = 0
                FostercareNameplates.mods[title]:enable()
            end
            calls = {}; runFrames(plate, 60)
        ''')
        self.assertEqual(lua.eval('calls.GetNamePlateForGUID or 0'), 0)

    def test_p3_own_auras_walk_once(self):
        """P3-2: own debuffs were read with by-index UnitAura, which re-walks the aura array per index."""
        lua = load()
        lua.execute('''
            plate = nativePlate("0xF1", "nameplate1"); calls = {}
            FostercareNameplates.Nameplates:Auras(plate, "0xF1")
        ''')
        self.assertIsNone(lua.eval('calls["UnitAura HARMFUL|PLAYER"]'))
        self.assertEqual(lua.eval('calls.GetAuraSlots'), 1)

    def test_p3_idle_castbar_query_backstop(self):
        """P3-3: an idle plate re-queried cast info five times a second despite cast events."""
        lua = load()
        lua.execute('plate = nativePlate("0xF1", "nameplate1"); calls = {}; runFrames(plate, 60)')
        self.assertLessEqual(lua.eval('calls.UnitCastingInfo or 0'), 2)

    def test_p3_layout_slider_does_not_requery_plates(self):
        """P3-4: every slider step re-queued health, auras and targeting for every plate."""
        lua = load()
        lua.execute('''
            plate = nativePlate("0xF1", "nameplate1"); calls = {}
            FostercareNameplates.Nameplates.pending = {}
            FNPPlateSlidernameplate_scale:SetValue(1.5)
            FNPPlateSlidernameplate_scale.scripts.OnValueChanged()
        ''')
        self.assertIsNone(lua.eval('next(FostercareNameplates.Nameplates.pending)'))


FADE = '''
    plate = nativePlate("0xF1", "nameplate1")
    function fade(key) FostercareNameplates.SetOverride(key, 1); FostercareNameplates.Nameplates:ApplyConfiguration() end
'''


class UnitFilters(unittest.TestCase):
    """F3: fade critters, totems, other players' minions, grey and idle neutral units."""

    def alpha(self, lua, frames=2):
        lua.execute("runFrames(plate, %d)" % frames)
        return round(lua.eval("plate:GetAlpha()"), 2)

    def test_off_by_default(self):
        lua = load(prelude='units["0xF1"] = { type = 8 }')
        lua.execute(FADE)
        self.assertEqual(self.alpha(lua), 1)

    def test_each_fixed_filter_fades(self):
        for key, unit in (("nameplate_fade_critters", "{ type = 8 }"),
                          ("nameplate_fade_totems", "{ type = 11 }"),
                          ("nameplate_fade_pets", "{ type = 1, pet = true }"),
                          ("nameplate_fade_trivial", "{ type = 7, trivial = 1 }")):
            lua = load(prelude='units["0xF1"] = %s' % unit)
            lua.execute(FADE + 'fade("%s")' % key)
            self.assertEqual(self.alpha(lua), 0.3, key)

    def test_other_kinds_stay_opaque(self):
        lua = load(prelude='units["0xF1"] = { type = 7 }')
        lua.execute(FADE + 'fade("nameplate_fade_critters"); fade("nameplate_fade_totems")')
        self.assertEqual(self.alpha(lua), 1)

    def test_target_is_never_faded(self):
        lua = load(prelude='units["0xF1"] = { type = 8 }')
        lua.execute(FADE + 'fade("nameplate_fade_critters"); FostercareNameplates.Nameplates.targetGUID = "0xF1"')
        self.assertEqual(self.alpha(lua), 1)

    def test_neutral_fades_only_out_of_combat(self):
        lua = load(prelude='units["0xF1"] = { type = 1, reaction = 4, combat = 1 }')
        lua.execute(FADE + 'fade("nameplate_fade_neutral")')
        self.assertEqual(self.alpha(lua), 1)
        lua.execute('units["0xF1"].combat = nil')
        self.assertEqual(self.alpha(lua, 40), 0.3)

    def test_opacity_setting_applies(self):
        lua = load(prelude='units["0xF1"] = { type = 8 }')
        lua.execute(FADE + 'FostercareNameplates.SetOverride("nameplate_fade_alpha", 0.5); fade("nameplate_fade_critters")')
        self.assertEqual(self.alpha(lua), 0.5)


if __name__ == "__main__":
    unittest.main()
