"""Broad events do no per-event work when they cannot affect the view (P3-5, P3-6).

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


class CastbarFanoutTests(unittest.TestCase):
    def test_other_units_cast_events_do_not_query_target(self):
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute(BASE + r'''
            TargetFrame = CreateFrame("Frame", "TargetFrame")
            guidQueries = 0
            function UnitGUID(unit) guidQueries = guidQueries + 1; return "0xTARGET" end
            function UnitExists() return true end
            function UnitIsDeadOrGhost() return false end
            function UnitIsUnit() return false end
            C_Spell = { UnitCastingInfo = function() end, UnitChannelInfo = function() end }
        ''')
        lua.execute(CASTBAR)
        lua.execute(r'''
            local module = FostercareTweaks.mods["Enemy Castbars"]
            module:enable()
            local handler = handlers[module.frame]
            handler(nil, "PLAYER_TARGET_CHANGED")
            guidQueries = 0
            for i = 1, 100 do handler(nil, "UNIT_CASTEVENT", "0xOTHER" .. i, nil, "MAINHAND", 0, 0) end
        ''')
        self.assertEqual(lua.eval('guidQueries'), 0)


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
