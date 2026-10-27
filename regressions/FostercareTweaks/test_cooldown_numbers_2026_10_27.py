"""Cooldown numbers and ClassicAPI 1.17.9 native countdowns, 2026-10-27.

ClassicAPI 1.17.9 gives every native Cooldown frame countdown numbers, shown
while the player's countdownForCooldowns CVar is 1 (docs/API.md,
CreateFrame("Cooldown")). The stock buttons' cooldowns are 1.12 indicator
Models and get none, so Cooldown Numbers stays for them. On a native frame
whose numbers show, ours stand aside; frames that keep their own timer text
(aura buttons) hide the native numbers. GearRack always draws its own.

Three fail on c143613: native frames get double numbers and the aura buttons
leave native numbers on. The Model and GearRack tests are controls. The CVar's
real value, the native font and the stock buttons' Models stay in-game checks.
"""
from pathlib import Path
import os
import re
import unittest
from lupa.lua51 import LuaRuntime

ROOT = Path(os.environ["VANILLAFORGE_ADDON_ROOT"])


def source(name):
    return (ROOT / name).read_text("utf-8-sig")


BASE = r'''
NOOP = function() end
local W = {}
W.__index = function(_, k)
    local v = rawget(W, k)
    if v ~= nil then return v end
    if string.find(k, "^%u") then return NOOP end
end
function W:GetParent() return rawget(self, "parent") end
function W:GetName() return rawget(self, "name") end
function W:GetObjectType() return rawget(self, "kind") or "Frame" end
function W:GetHideCountdownNumbers() return rawget(self, "hideNumbers") or false end
function W:GetHeight() return 36 end
function W:GetAlpha() return 1 end
function W:IsVisible() return true end
function W:Show() rawset(self, "shown", true) end
function W:Hide() rawset(self, "shown", false) end
function W:SetText(t) rawset(self, "text_", t) end
function W:CreateFontString() return setmetatable({}, W) end
function Widget(props) return setmetatable(props or {}, W) end
function CreateFrame(_, name, parent) return Widget({ name = name, parent = parent }) end
UIParent = Widget()
cvar = "0"
function GetCVar(name) if name == "countdownForCooldowns" then return cvar end end
function GetTime() return 100 end
tickers = 0
C_Timer = { NewTicker = function() tickers = tickers + 1; return { Cancel = NOOP } end }
FT = { }
FostercareTweaks = FT
function FT:register(m) return m end
function FT.SetEventHandler() end
FT.HookAddonOrVariable = NOOP -- c143613 still waited for GearRack
function FT.TimeConvert(r) return tostring(math.ceil(r)) end
function FT.hooksecurefunc(name, fn) if name == "CooldownFrame_SetTimer" then SetTimer = fn end end
GearRack = { HasCooldownNumbers = function(name) return name == "GearRackTrinkets_Trinket0Cooldown" end }

function Cooldown(kind, name)
    return Widget({ kind = kind, name = name, parent = Widget() })
end
function Number(cd)
    local t = rawget(cd, "cooldowntext")
    return t and rawget(t, "shown") and rawget(t.text, "text_")
end
'''


class CooldownNumbers(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute(BASE)
        module = self.lua.execute(source("mods/cooldown-numbers.lua").replace("\r\n", "\n")
                                  .replace("local module = FT:register", "module = FT:register"))
        self.lua.execute("module:enable()")

    def number(self, kind, name=None, setup=""):
        return self.lua.execute(setup + '''
            local cd = Cooldown("%s", %s)
            SetTimer(cd, 95, 30, 1)
            return Number(cd)
        ''' % (kind, '"%s"' % name if name else "nil"))

    def test_stock_models_get_our_numbers(self):
        self.assertEqual(self.number("Model"), "25")
        self.assertEqual(self.number("Model", setup='cvar = "1"'), "25")

    def test_native_numbers_off_means_ours(self):
        self.assertEqual(self.number("Cooldown"), "25")

    def test_native_numbers_on_means_ours_stand_aside(self):
        self.assertFalse(self.number("Cooldown", setup='cvar = "1"'))

    def test_a_running_number_hands_over_to_native(self):
        self.assertFalse(self.lua.execute('''
            local cd = Cooldown("Cooldown")
            SetTimer(cd, 95, 30, 1)
            cvar = "1"
            SetTimer(cd, 96, 30, 1)
            return Number(cd)
        '''))

    def test_hidden_native_numbers_keep_ours(self):
        self.assertEqual(self.lua.execute('''
            cvar = "1"
            local cd = Cooldown("Cooldown"); rawset(cd, "hideNumbers", true)
            SetTimer(cd, 95, 30, 1)
            return Number(cd)
        '''), "25")

    def test_gearrack_keeps_its_own(self):
        self.assertFalse(self.number("Model", "GearRackTrinkets_Trinket0Cooldown"))


class AuraButtonsHideNativeNumbers(unittest.TestCase):
    def test_aura_cooldowns_hide_native_numbers(self):
        auras = source("mods/unitframes/auras.lua")
        body = auras[auras.index("local function CreateAuraButton"):auras.index("function Auras:ResetContainer")]
        self.assertRegex(body, re.compile(r"btn\.cooldown:SetHideCountdownNumbers\(true\)"))


if __name__ == "__main__":
    unittest.main()
