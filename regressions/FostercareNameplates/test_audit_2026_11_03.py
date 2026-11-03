"""FostercareNameplates audit, 2026-11-03.

With plate details turned off, every settings change (a castbar slider, for
example) ran the details shutdown again on every plate: it cleared the plate,
restored the mark and level and wrote alpha 1 over the game's own alpha.
Fails on 1.5.0.
"""
import unittest
from fnp_env import load


class DisabledDetails(unittest.TestCase):
    def test_settings_changes_leave_plates_alone_while_details_is_off(self):
        lua = load('{ ["Nameplate Details"] = 0, overwrites = {} }')
        lua.execute('''
            plate = nativePlate("0xF1", "nameplate1")
            plate:SetAlpha(0.5)
            FostercareNameplates.Nameplates:ApplyConfiguration()
            FostercareNameplates.Nameplates:ApplyConfiguration(true)
        ''')
        self.assertEqual(lua.eval("plate:GetAlpha()"), 0.5)

    def test_turning_details_off_restores_plates_once(self):
        lua = load()
        lua.execute('''
            plate = nativePlate("0xF1", "nameplate1")
            plate:SetAlpha(0.3)
            FostercareNameplates_Config["Nameplate Details"] = 0
            FostercareNameplates.Nameplates:ApplyConfiguration()
        ''')
        self.assertEqual(lua.eval("plate:GetAlpha()"), 1)
        lua.execute('plate:SetAlpha(0.5); FostercareNameplates.Nameplates:ApplyConfiguration()')
        self.assertEqual(lua.eval("plate:GetAlpha()"), 0.5)


class Lifecycle(unittest.TestCase):
    def test_logout_stops_every_module(self):
        """Only Lifecycle's and Details' events stopped at logout; the cooldown
        driver and the cast events stayed live. Fails on 1.5.0."""
        lua = load()
        lua.execute('plate = nativePlate("0xF1", "nameplate1"); fire("PLAYER_LOGOUT")')
        for name in ("FNPLibNameplate", "FNPNameplateDetailsEvents", "FNPNameplateCastEvents", "FNPEnemyCooldownEvents"):
            self.assertIsNone(lua.eval("next(%s.events)" % name), name)

    def test_a_loading_screen_announces_plates_that_changed_unit(self):
        """Fails on 1.5.0: the new GUID waited for the next plate frame."""
        lua = load()
        lua.execute('''
            plate = nativePlate("0xF1", "nameplate1")
            local forGUID = C_NamePlate.GetNamePlateForGUID
            C_NamePlate.GetNamePlateForGUID = function(g) if g == "0xF2" then return plate end return forGUID(g) end
            C_NamePlate.GetNamePlateGUIDs = function() return { "0xF2" } end
            local unitGUID = UnitGUID
            UnitGUID = function(u) if u == "0xF2" then return u end return unitGUID(u) end
            fire("PLAYER_ENTERING_WORLD")
        ''')
        self.assertEqual(lua.eval("plate.fnpUnitGUID"), "0xF2")
        self.assertEqual(lua.eval("plate.fnpDetailGUID"), "0xF2")

    def test_unit_events_are_heard_for_nameplate_tokens_only(self):
        lua = load()
        lua.execute('plate = nativePlate("0xF1", "nameplate1")')
        self.assertTrue(lua.eval("FNPNameplateDetailsEvents.events.UNIT_HEALTH.nameplate40"))
        self.assertIsNone(lua.eval("FNPNameplateDetailsEvents.events.UNIT_HEALTH.raid1"))
        lua.execute('far = nativePlate("0xF9", "nameplate57")')
        self.assertTrue(lua.eval("FNPNameplateDetailsEvents.events.UNIT_HEALTH.nameplate57"))
        self.assertTrue(lua.eval("FNPNameplateCastEvents.events.UNIT_SPELLCAST_START.nameplate57"))


class HealthText(unittest.TestCase):
    def test_unchanged_health_writes_nothing(self):
        lua = load('{ overwrites = { nameplate_health_target = 0, nameplate_health = 2 } }', '''
            AbbreviateNumbers = function(n) calls.Abbreviate = (calls.Abbreviate or 0) + 1; return tostring(n) end
        ''')
        lua.execute('''
            plate = nativePlate("0xF1", "nameplate1")
            calls = {}
            for _ = 1, 5 do FostercareNameplates.Nameplates:Health(plate, "0xF1") end
        ''')
        self.assertIsNone(lua.eval("calls.Abbreviate"))
        self.assertEqual(lua.eval("plate.fnpHealth.fnpText"), "50")


if __name__ == "__main__":
    unittest.main()
