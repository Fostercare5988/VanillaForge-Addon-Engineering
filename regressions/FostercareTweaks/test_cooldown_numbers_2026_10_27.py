"""Cooldown numbers and ClassicAPI 1.17.9 native countdowns, 2026-10-27.

ClassicAPI 1.17.9 gives every native Cooldown frame countdown numbers, shown
while the player's countdownForCooldowns CVar is 1 (docs/API.md,
CreateFrame("Cooldown")). The stock buttons' cooldowns are 1.12 indicator
Models and get none, so Cooldown Numbers stays for them. On a native frame
whose numbers show, ours stand aside; frames that keep their own timer text
(aura buttons) hide the native numbers. GearRack's buttons are native
Cooldown frames since 2026-11-01, so it needs no special case.

Three failed on c143613: native frames got double numbers and the aura buttons
left native numbers on. Since 2026-11-13 the stock Models get native numbers
too (CooldownNumbers below). The native font over a Model stays an in-game check.
"""
from pathlib import Path
import os
import re
import unittest
from wowlua import LuaRuntime

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
function W:GetFrameLevel() return 1 end
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
FT.Countdown = { FormatNumber = function(_, r) return tostring(math.ceil(r)) end }
function hooksecurefunc(name, fn) if name == "CooldownFrame_SetTimer" then SetTimer = fn end end

function Cooldown(kind, name)
    return Widget({ kind = kind, name = name, parent = Widget() })
end
function Number(cd)
    local t = rawget(cd, "cooldowntext")
    return t and rawget(t, "shown") and rawget(t.text, "text_")
end
'''


class CooldownNumbers(unittest.TestCase):
    """2026-11-13 (1.20.0): the client draws the stock buttons' numbers too. Each
    Model gets a native Cooldown child with no sweep and the addon's formatter;
    the 0.1 s ticker, the sync on page changes and the old flags are gone. These
    fail on 701d8b1."""

    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute(BASE)
        self.lua.execute(r'''
            local W = getmetatable(Widget())
            function W:SetCooldown(s, d) rawset(self, "running", { s, d }); calls = (calls or 0) + 1 end
            function W:Clear() rawset(self, "running", false) end
            function W:GetCountdownFontString() local f = rawget(self, "fs") or Widget(); rawset(self, "fs", f); return f end
            function W:SetCountdownFormatter(f) rawset(self, "formatter", f) end
            function W:SetDrawSwipe(on) rawset(self, "swipe", on) end
            local create = CreateFrame
            function CreateFrame(kind, name, parent) local f = create(kind, name, parent); rawset(f, "kind", kind); return f end
        ''')
        self.lua.execute(source("mods/cooldown-numbers.lua").replace("\r\n", "\n")
                         .replace("local module = FT:register", "module = FT:register"))
        self.lua.execute("module:enable()")

    def test_a_stock_model_gets_native_numbers_without_a_sweep(self):
        lua = self.lua
        lua.execute('model = Cooldown("Model"); SetTimer(model, 95, 30, 1)')
        self.assertEqual(lua.eval("model.fctNumbers.kind"), "Cooldown")
        self.assertTrue(lua.eval("model.fctNumbers.parent == model"))      # hides with the Model
        self.assertEqual(lua.eval("model.fctNumbers.swipe"), False)
        self.assertTrue(lua.eval("model.fctNumbers.formatter == FT.Countdown"))
        self.assertEqual(list(lua.eval("model.fctNumbers.running").values()), [95, 30])

    def test_no_timer_runs(self):
        self.lua.execute('for i = 1, 5 do SetTimer(Cooldown("Model"), 95, 30, 1) end')
        self.assertEqual(self.lua.eval("tickers"), 0)
        self.assertNotIn("NewTicker", source("mods/cooldown-numbers.lua"))

    def test_the_same_cooldown_again_does_not_restart_it(self):
        lua = self.lua
        lua.execute('model = Cooldown("Model"); calls = 0; SetTimer(model, 95, 30, 1); SetTimer(model, 95, 30, 1)')
        self.assertEqual(lua.eval("calls"), 1)

    def test_a_cleared_cooldown_clears_the_numbers(self):
        lua = self.lua
        lua.execute('model = Cooldown("Model"); SetTimer(model, 95, 30, 1); SetTimer(model, 0, 0, 1)')
        self.assertEqual(lua.eval("model.fctNumbers.running"), False)

    def test_a_native_cooldown_is_left_alone(self):
        lua = self.lua
        lua.execute('cd = Cooldown("Cooldown"); SetTimer(cd, 95, 30, 1)')
        self.assertEqual(lua.eval("cd.fctNumbers"), False)

    def test_no_old_flags(self):
        for path in ROOT.rglob("*.lua"):
            text = path.read_text("utf-8-sig")
            self.assertNotIn("noCooldownCount", text, path.name)
            self.assertNotIn(".readable", text, path.name)


class AuraButtonsUseNativeNumbers(unittest.TestCase):
    """Aura buttons show the client's countdown through one formatter, not their own text."""

    def test_aura_cooldowns_use_the_native_countdown(self):
        auras = source("mods/unitframes/auras.lua")
        body = auras[auras.index("local function CreateAuraButton"):auras.index("function Auras:ResetContainer")]
        self.assertRegex(body, re.compile(r"btn\.cooldown:SetCountdownFormatter\(FT\.Countdown\)"))
        self.assertNotRegex(body, re.compile(r"SetHideCountdownNumbers\(true\)"))


if __name__ == "__main__":
    unittest.main()
