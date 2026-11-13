"""FostercareNameplates audit, 2026-11-13.

Each class names what the old code did. They fail on 1.7.1 (`0c24a6e`):
`tools/run_suite.py FostercareNameplates test_audit_2026_11_13.py --old 0c24a6e`.
"""
import unittest
from fnp_env import load

# A plate with every native region, in client order (Lifecycle.lua InitPlate).
FULL = '''
    function fullPlate(guid, token)
        local r = {}
        for i = 1, 7 do r[i] = CreateFrame((i == 3 or i == 4) and "FontString" or "Texture") end
        return nativePlate(guid, token, r)
    end
    function setTarget(plate, guid)
        local forUnit, unitGUID = C_NamePlate.GetNamePlateForUnit, UnitGUID
        C_NamePlate.GetNamePlateForUnit = function(u) if u == "target" then return plate end return forUnit(u) end
        UnitGUID = function(u) if u == "target" then return guid end return unitGUID(u) end
        fire("PLAYER_TARGET_CHANGED")
    end
'''


class ModuleStart(unittest.TestCase):
    def test_a_failing_module_reaches_the_error_handler(self):
        """pcall printed the message to chat and dropped the stack (KP-63)."""
        lua = load(prelude='''
            handled = {}
            function geterrorhandler() return function(e) table.insert(handled, e) end end
            local create = CreateFrame
            function CreateFrame(kind, name, parent)
                if name == "FNPEnemyCooldownEvents" then error("boom") end
                return create(kind, name, parent)
            end
        ''')
        self.assertEqual(lua.eval("#handled"), 1)
        self.assertIn("boom", lua.eval("handled[1]"))
        self.assertFalse(lua.eval('string.find(table.concat(chat, "\\n"), "Enemy Nameplate Cooldowns") ~= nil'))
        # The modules after it still start.
        self.assertTrue(lua.eval("next(FNPNameplateCastEvents.events) ~= nil"))

    def test_nampower_is_required(self):
        """The cooldowns read NamPower's spell records and events; the guard
        checked only ClassicAPI and SuperWoW."""
        lua = load(prelude="GetNampowerVersion = nil")
        self.assertIsNone(lua.eval("FostercareNameplates"))
        self.assertIn("NamPower", lua.eval('table.concat(chat, "\\n")'))


class SavedKeys(unittest.TestCase):
    def test_keys_nothing_owns_are_cleared_in_one_sweep(self):
        """Each retired key had its own clearing line (KP-64); others stayed."""
        lua = load('''{ nameplatesEnabled = 1, ["Nameplate Castbar"] = 1, ["Old Feature"] = 1,
            nameplate_layout_version = 1,
            overwrites = { nameplate_scale = 0.9, nameplate_old = 1, nameplate_uninterruptible = 0 } }''')
        config = "FostercareNameplates_Config"
        self.assertIsNone(lua.eval(config + '["Old Feature"]'))
        self.assertIsNone(lua.eval(config + ".nameplate_layout_version"))
        self.assertIsNone(lua.eval(config + ".overwrites.nameplate_old"))
        self.assertIsNone(lua.eval(config + ".overwrites.nameplate_uninterruptible"))
        self.assertEqual(lua.eval(config + ".overwrites.nameplate_scale"), 0.9)
        self.assertEqual(lua.eval(config + '["Nameplate Castbar"]'), 1)
        self.assertEqual(lua.eval(config + ".nameplatesEnabled"), 1)


class LoadingScreen(unittest.TestCase):
    def test_plates_keep_their_text_through_a_loading_screen(self):
        """Details cleared every plate at PLAYER_ENTERING_WORLD and drew it a
        frame later: the flicker CLAUDE.md warns about."""
        lua = load('{ overwrites = { nameplate_health_target = 0 } }')
        lua.execute('plate = nativePlate("0xF1", "nameplate1")')
        self.assertTrue(lua.eval("plate.fnpHealth:IsShown()"))
        lua.execute('fire("PLAYER_ENTERING_WORLD")')
        self.assertTrue(lua.eval("plate.fnpHealth:IsShown()"))


class PerFrame(unittest.TestCase):
    def test_a_frame_asks_nothing_while_nothing_changes(self):
        """Render asked the unit's reaction and combat every 0.5 s and read the
        raid icon every frame; events say when these change."""
        lua = load('{ overwrites = { nameplate_fade_neutral = 1 } }', FULL + '''
            units["0xF1"] = { reaction = 4 }
            marks = { ["0xF1"] = 8 }
            asked = 0
            local reaction, combat = UnitReaction, UnitAffectingCombat
            function UnitReaction(u, o) asked = asked + 1; return reaction(u, o) end
            function UnitAffectingCombat(u) asked = asked + 1; return combat(u) end
        ''')
        lua.execute('''
            plate = fullPlate("0xF1", "nameplate1")
            local icon, shown, point = plate.raidicon, plate.raidicon.IsShown, plate.raidicon.GetPoint
            function icon:IsShown() asked = asked + 1; return shown(self) end
            function icon:GetPoint(i) asked = asked + 1; return point(self, i) end
            runFrames(plate, 1); asked = 0; runFrames(plate, 120)
        ''')
        self.assertEqual(lua.eval("asked"), 0)

    def test_a_neutral_unit_fades_by_its_flags(self):
        """Combat start lifted the neutral fade up to 0.5 s late; UNIT_FLAGS
        fires for the nameplate token when the unit's combat flag changes."""
        lua = load('{ overwrites = { nameplate_fade_neutral = 1 } }', 'units["0xF1"] = { reaction = 4 }')
        lua.execute('plate = nativePlate("0xF1", "nameplate1")')
        self.assertAlmostEqual(lua.eval("plate:GetAlpha()"), 0.3)
        self.assertTrue(lua.eval("receives(FNPNameplateDetailsEvents, 'UNIT_FLAGS', 'nameplate1')"))
        self.assertFalse(lua.eval("receives(FNPNameplateDetailsEvents, 'UNIT_FLAGS', 'target')"))
        lua.execute('units["0xF1"].combat = true; fire("UNIT_FLAGS", "nameplate1")')
        self.assertEqual(lua.eval("plate:GetAlpha()"), 1)

    def test_unit_flags_are_heard_only_with_the_neutral_fade(self):
        lua = load()
        lua.execute('plate = nativePlate("0xF1", "nameplate1")')
        self.assertFalse(lua.eval("receives(FNPNameplateDetailsEvents, 'UNIT_FLAGS', 'nameplate1')"))

    def test_a_target_change_sets_every_alpha_and_the_glow_at_once(self):
        """Alpha and the target glow waited for the plates' next frame."""
        lua = load('{ overwrites = { nameplate_target_glow = 1 } }', FULL)
        lua.execute('''
            a = fullPlate("0xF1", "nameplate1")
            b = fullPlate("0xF2", "nameplate2")
            setTarget(a, "0xF1")
        ''')
        self.assertEqual(lua.eval("a:GetAlpha()"), 1)
        self.assertAlmostEqual(lua.eval("b:GetAlpha()"), 0.8)
        self.assertTrue(lua.eval("a.fnpTargetGlow ~= nil and a.fnpTargetGlow:IsShown()"))
        lua.execute('setTarget(nil, nil)')
        self.assertEqual(lua.eval("b:GetAlpha()"), 1)
        self.assertFalse(lua.eval("a.fnpTargetGlow:IsShown()"))

    def test_a_marked_plate_never_fades(self):
        lua = load('{ overwrites = { nameplate_fade_critters = 1 } }', FULL + '''
            units["0xF1"] = { type = 8 }
            marks = {}
        ''')
        lua.execute('plate = fullPlate("0xF1", "nameplate1")')
        self.assertAlmostEqual(lua.eval("plate:GetAlpha()"), 0.3)
        lua.execute('marks["0xF1"] = 8; fire("RAID_TARGET_UPDATE")')
        self.assertAlmostEqual(lua.eval("plate:GetAlpha()"), 0.9)


class CastBackstop(unittest.TestCase):
    PRELUDE = '''
        cast = { name = "Polymorph", s = now * 1000, e = (now + 3) * 1000 }
        C_Spell.UnitCastingInfo = function() if cast then return cast.name, "", "tex", cast.s, cast.e, false, 1, false end end
        C_Spell.UnitChannelInfo = function() end
        -- Timers that will still run, whichever kind (After cannot be cancelled).
        later, tickers = {}, 0
        local function wait(seconds, f)
            local t = { seconds = seconds, f = f }
            function t:Cancel() self.cancelled = true end
            if seconds > 0 then table.insert(later, t) end
            return t
        end
        C_Timer.After, C_Timer.NewTimer = wait, wait
        C_Timer.NewTicker = function() tickers = tickers + 1; return { Cancel = function() end } end
        function live()
            local n, first = 0
            for _, t in ipairs(later) do if not t.cancelled then n = n + 1; first = first or t end end
            return n, first
        end
    '''

    def test_the_backstop_wakes_when_the_cast_ends(self):
        """A 0.5 s ticker ran while any bar was up: six passes for a 3 s cast."""
        lua = load(prelude=self.PRELUDE)
        lua.execute('plate = nativePlate("0xF1", "nameplate1"); fire("UNIT_SPELLCAST_START", "nameplate1")')
        self.assertEqual(lua.eval("tickers"), 0)
        self.assertEqual(lua.eval("(live())"), 1)
        self.assertAlmostEqual(lua.eval("select(2, live()).seconds"), 3)
        # A STOP that never came: the bar hides at the end, and nothing is left waiting.
        lua.execute("cast = nil; local _, t = live(); now = now + t.seconds; later = {}; t.f()")
        self.assertFalse(lua.eval("plate.fnpCastbar:IsShown()"))
        self.assertEqual(lua.eval("(live())"), 0)

    def test_an_earlier_end_moves_the_backstop(self):
        lua = load(prelude=self.PRELUDE)
        lua.execute('''
            a = nativePlate("0xF1", "nameplate1"); fire("UNIT_SPELLCAST_START", "nameplate1")
            cast = { name = "Frostbolt", s = now * 1000, e = (now + 1) * 1000 }
            b = nativePlate("0xF2", "nameplate2"); fire("UNIT_SPELLCAST_START", "nameplate2")
        ''')
        self.assertEqual(lua.eval("(live())"), 1)
        self.assertAlmostEqual(lua.eval("select(2, live()).seconds"), 1)
        # At 1 s the short bar goes and the long one waits for its own end.
        lua.execute("local _, t = live(); now = now + 1; later = {}; t.f()")
        self.assertFalse(lua.eval("b.fnpCastbar:IsShown()"))
        self.assertTrue(lua.eval("a.fnpCastbar:IsShown()"))
        self.assertAlmostEqual(lua.eval("select(2, live()).seconds"), 2)


class CooldownFrames(unittest.TestCase):
    def test_timers_are_plain_cooldown_frames(self):
        """CooldownFrameTemplate is the 1.12 Model template (Cooldown.xml) with
        a per-frame OnUpdateModel script; a Cooldown needs no template
        (ClassicAPI API.md, CreateFrame("Cooldown"))."""
        lua = load(prelude='''
            templates = {}
            local create = CreateFrame
            function CreateFrame(kind, name, parent, template)
                if kind == "Cooldown" and template then table.insert(templates, template) end
                return create(kind, name, parent)
            end
            C_UnitAuras.UnitAura = function(_, _, filter)
                if filter == "HARMFUL|CROWD_CONTROL" then return "Sheep", "tex", 0, nil, 10, now + 5, nil, nil, nil, 118 end
            end
        ''')
        lua.execute('''
            plate = nativePlate("0xF1", "nameplate1")
            FostercareNameplates.NameplateCooldowns.enabled = true
            GetSpellRecField = function(_, f) if f == "recoveryTime" then return 60000 elseif f == "name" then return "Blink" end return 1 end
            GetSpellIconTexture = function() return "tex" end
            UnitIsPlayer = function() return 1 end
            FostercareNameplates.NameplateCooldowns:Observe("0xF1", 1953)
        ''')
        self.assertTrue(lua.eval("plate.fnpAuras ~= nil and plate.fnpEnemyCooldowns ~= nil"))
        self.assertEqual(lua.eval("#templates"), 0)


if __name__ == "__main__":
    unittest.main()
