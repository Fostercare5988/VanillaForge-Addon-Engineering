"""ClassicAPI 1.18.5 pass, 2026-10-30.

The "not on cooldown" check reads C_Spell.GetSpellCooldown(name).isOnGCD
(1.17.13, docs/API.md) instead of guessing that any duration up to 1.5 s is
the global cooldown. The guess called a real cooldown of 1.5 s or less "off
cooldown". Fails on 008454a.
"""
from pathlib import Path
import os
import unittest
from lupa.lua51 import LuaRuntime

ADDON = Path(os.environ["VANILLAFORGE_ADDON_ROOT"])
SOURCE = (ADDON / "Modules/FostercareConditions.lua").read_text("utf-8-sig").replace("\r\n", "\n")


def cooldown_runtime(duration, on_gcd):
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute('''
        BOOKTYPE_SPELL = "spell"
        cd = { startTime = 100, duration = %s, isEnabled = true, modRate = 1, isOnGCD = %s }
        C_Spell = { GetSpellCooldown = function(spell) asked = spell; return cd end }
        function GetSpellCooldown() return cd.startTime, cd.duration, 1 end
    ''' % (duration, "true" if on_gcd else "false"))
    start = SOURCE.index("local function _IsSpellOnCooldown(")
    body = SOURCE[start:SOURCE.index("\nend\n", start) + 5]
    lua.execute(body + "\nfunction onCd(...) return _IsSpellOnCooldown(...) end")
    return lua


class GlobalCooldownTests(unittest.TestCase):
    def test_gcd_is_not_a_cooldown(self):
        for duration in (1, 1.5):
            lua = cooldown_runtime(duration, True)
            self.assertFalse(lua.eval('onCd("Sinister Strike")'), duration)

    def test_short_real_cooldown_counts(self):
        lua = cooldown_runtime(1, False)
        self.assertTrue(lua.eval('onCd("Sinister Strike")'))
        self.assertEqual(lua.eval("asked"), "Sinister Strike")

    def test_no_cooldown_and_unknown_spell(self):
        lua = cooldown_runtime(0, False)
        self.assertFalse(lua.eval('onCd("Kick")'))
        lua.execute("cd = nil")
        self.assertFalse(lua.eval('onCd("Kick")'))
        self.assertFalse(lua.eval("onCd(nil)"))


if __name__ == "__main__":
    unittest.main()
