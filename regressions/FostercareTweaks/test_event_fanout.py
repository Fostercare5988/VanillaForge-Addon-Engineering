"""Broad events do no per-event work when they cannot affect the view (P3-6).

The castbar fan-out test (P3-5) moved to test_audit_2026_10_26.py: the bar
now hears only the "target" token.

The complete module files run with generic widget mocks; native widget
behavior and real event payloads remain in-game checks.
"""
from pathlib import Path
import os
import unittest
from lupa.lua51 import LuaRuntime

ROOT = Path(os.environ["VANILLAFORGE_ADDON_ROOT"])
CASTBAR = (ROOT / "mods/target-castbar.lua").read_text("utf-8-sig")
REAGENTS = (ROOT / "mods/actionbar-reagents.lua").read_text("utf-8-sig")

BASE = r'''
function table.wipe(t) for k in pairs(t) do t[k] = nil end return t end
local Widget = {}
setmetatable(Widget, { __index = function(_, name)
    if string.find(name, "^%u") then return function() end end
end })
function Widget:GetFont() return "f", 12 end
function Widget:IsShown() return self.shown end
function Widget:Show() self.shown = true end
function Widget:Hide() self.shown = false end
function Widget:GetName() return self.name end
function Widget:CreateTexture() return setmetatable({}, { __index = Widget }) end
function Widget:CreateFontString() return setmetatable({}, { __index = Widget }) end
function CreateFrame(_, name) local f = setmetatable({ name = name }, { __index = Widget }); if name then _G[name] = f end; return f end
timers, handlers = {}, {}
C_Timer = { After = function(_, fn) table.insert(timers, fn) end }
FostercareTweaks_Config = {}
FostercareTweaks = {
    register = function(self, mod) self.mods = self.mods or {}; self.mods[mod.title] = mod; return mod end,
    IsEnabled = function() return true end,
    SetEventHandler = function(frame, fn) handlers[frame] = fn end,
    hooksecurefunc = function() end,
}
function hooksecurefunc() end
'''


class CastbarInterruptibleTests(unittest.TestCase):
    """ClassicAPI 1.17: a target cast that becomes uninterruptible mid-cast turns silver."""

    def test_mid_cast_flip_recolors_the_bar(self):
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute(BASE + r'''
            registered = {}
            local create = CreateFrame
            function CreateFrame(kind, name)
                local f = create(kind, name)
                f.RegisterEvent = function(_, ev) registered[ev] = true end
                f.RegisterUnitEvent = function(_, ev) registered[ev] = true end
                f.UnregisterAllEvents = function() registered = {} end
                return f
            end
            TargetFrame = CreateFrame("Frame", "TargetFrame")
            locked = nil
            function GetTime() return 1 end
            function UnitGUID() return "0xTARGET" end
            function UnitExists() return true end
            function UnitIsDeadOrGhost() return false end
            function UnitIsUnit() return false end
            C_Spell = {
                UnitCastingInfo = function()
                    return "Fireball", "Fireball", "icon", 500, 3500, nil, "cast-1", locked
                end,
                UnitChannelInfo = function() end,
            }
        ''')
        lua.execute(CASTBAR)
        lua.execute(r'''
            FCTweaksTargetCastbar.SetStatusBarColor = function(_, r) barRed = r end
            FCTweaksTargetCastbar.GetWidth = function() return 140 end
            local module = FostercareTweaks.mods["Enemy Castbars"]
            module:enable()
            handler = handlers[module.frame]
            handler(nil, "UNIT_SPELLCAST_START", "target")
            before = barRed
            locked = 1
            if registered["UNIT_SPELLCAST_NOT_INTERRUPTIBLE"] then
                handler(nil, "UNIT_SPELLCAST_NOT_INTERRUPTIBLE", "target")
            end
        ''')
        self.assertTrue(lua.eval('registered["UNIT_SPELLCAST_INTERRUPTIBLE"] == true'))
        self.assertNotEqual(lua.eval('before'), 0.65)
        self.assertEqual(lua.eval('barRed'), 0.65)


class ReagentFanoutTests(unittest.TestCase):
    def runtime(self, macros):
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute(BASE + r'''
            NUM_ACTIONBAR_BUTTONS = 12
            for _, prefix in ipairs({"Action", "BonusAction", "MultiBarBottomLeft",
                "MultiBarBottomRight", "MultiBarLeft", "MultiBarRight"}) do
                for i = 1, 12 do CreateFrame("CheckButton", prefix .. "Button" .. i) end
            end
            updates, macroSpell = 0, 1
            function ActionButton_UpdateCount() updates = updates + 1 end
            function ActionButton_GetPagedID() return 1 end
            function GetActionInfo(slot)
                if MACROS and slot == 5 then return "macro", 7 end
                if slot == 1 then return "spell", 100 end
            end
            function GetMacroSpell() return nil, nil, macroSpell end
            C_Spell = { GetSpellReagents = function(id) return { 17020 } end,
                        GetSpellCastCount = function() return 3 end }
        ''')
        lua.execute('MACROS = %s' % ('true' if macros else 'false'))
        lua.execute(REAGENTS)
        lua.execute(r'''
            local module = FostercareTweaks.mods["Reagent Counter"]
            module:enable()
            for frame, fn in pairs(handlers) do handler = fn end
            timers = {}; updates = 0
        ''')
        return lua

    def flush(self, lua):
        lua.execute('local t = timers; timers = {}; for _, fn in ipairs(t) do fn() end')

    def test_modifier_change_without_macro_change_refreshes_nothing(self):
        lua = self.runtime(macros=True)
        lua.execute('handler(nil, "MODIFIER_STATE_CHANGED"); handler(nil, "PLAYER_TARGET_CHANGED")')
        self.flush(lua)
        self.assertEqual(lua.eval('updates'), 0)

    def test_macro_spell_change_still_refreshes(self):
        lua = self.runtime(macros=True)
        lua.execute('macroSpell = 2; handler(nil, "MODIFIER_STATE_CHANGED")')
        self.flush(lua)
        self.assertGreater(lua.eval('updates'), 0)

    def test_bag_update_still_refreshes_counts(self):
        lua = self.runtime(macros=False)
        lua.execute('handler(nil, "BAG_UPDATE_DELAYED")')
        self.flush(lua)
        self.assertGreater(lua.eval('updates'), 0)


if __name__ == '__main__':
    unittest.main()
