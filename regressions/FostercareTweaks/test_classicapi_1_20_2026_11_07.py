"""FostercareTweaks on ClassicAPI 1.20, 2026-11-07 (1.18.0).

Reagent Counter scanned all 120 action slots (GetActionInfo, GetMacroSpell) into
its own tables and asked GetSpellReagents for a reagent list per spell. It now
asks ClassicAPI per button, inside the ActionButton_UpdateCount hook:
C_ActionBar.GetSpell(slot) (1.19.3: the spell of a spell slot, or the spell a
macro's button shows), IsConsumableSpell (uses reagents) and
C_Spell.GetSpellCastCount. Extra Rows 2-7 ask IsConsumableSpell too. Most of
these fail on 1.17.1; real counts and macro conditions stay in-game checks.
"""
from pathlib import Path
import os
import unittest
from lupa.lua51 import LuaRuntime

ROOT = Path(os.environ["VANILLAFORGE_ADDON_ROOT"])


def source(name):
    return (ROOT / name).read_text("utf-8-sig").replace("\r\n", "\n")


BASE = r'''
function table.wipe(t) for k in pairs(t) do t[k] = nil end return t end
local Widget = {}
Widget.__index = Widget
function Widget:SetText(t) self.text = t end
function Widget:Show() self.shown = true end
function Widget:GetName() return self.name end
function Widget:RegisterEvent(ev) self.events = self.events or {}; self.events[ev] = true end
function CreateFrame(_, name) local f = setmetatable({ name = name }, Widget); if name then _G[name] = f end; return f end
timers, handler = {}, nil
C_Timer = { After = function(_, fn) table.insert(timers, fn) end }
function flush() local t = timers; timers = {}; for _, fn in ipairs(t) do fn() end end
FostercareTweaks = {
    mods = {},
    register = function(self, mod) self.mods[mod.title] = mod; return mod end,
    SetEventHandler = function(_, fn) handler = fn end,
}
NUM_ACTIONBAR_BUTTONS = 12
slots = {}
local n = 0
for _, prefix in ipairs({ "Action", "BonusAction", "MultiBarBottomLeft",
    "MultiBarBottomRight", "MultiBarLeft", "MultiBarRight" }) do
    for i = 1, 12 do
        n = n + 1
        local b = CreateFrame("CheckButton", prefix .. "Button" .. i)
        b.slot = n
        _G[prefix .. "Button" .. i .. "Count"] = CreateFrame("FontString")
    end
end
function ActionButton_GetPagedID(button) return button.slot end
-- The game's own count: an item's stack, else nothing.
function ActionButton_UpdateCount()
    local s = slots[this.slot]
    _G[this:GetName() .. "Count"]:SetText(s and s.kind == "item" and "20" or "")
end
function hooksecurefunc(name, fn)
    local original = _G[name]
    _G[name] = function(b) original(b); fn(b) end
end
function GetActionInfo(slot) local s = slots[slot]; if s then return s.kind, s.id end end
function IsItemAction(slot) local s = slots[slot]; return s and s.kind == "item" and 1 or nil end
reagentSpells = { [23028] = true, [20484] = true }
function IsConsumableSpell(id) return reagentSpells[id] == true end
C_ActionBar = { GetSpell = function(slot) local s = slots[slot]; return s and s.spell or 0 end }
C_Spell = { GetSpellCastCount = function(id) return id == 23028 and 7 or 1200 end }
'''


def reagents(slots):
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(BASE)
    lua.execute(slots)
    lua.execute(source("mods/actionbar-reagents.lua"))
    lua.execute('FostercareTweaks.mods["Reagent Counter"]:enable()')
    return lua


def count(lua, n):
    return lua.eval('ActionButton%dCount.text' % n)


class ReagentCounterAsksClassicAPI(unittest.TestCase):
    def test_a_reagent_spell_shows_its_cast_count(self):
        lua = reagents('slots[1] = { kind = "spell", id = 23028, spell = 23028 }')
        self.assertEqual(count(lua, 1), "7")

    def test_a_large_count_is_a_star(self):
        lua = reagents('slots[2] = { kind = "spell", id = 20484, spell = 20484 }')
        self.assertEqual(count(lua, 2), "*")

    def test_a_spell_without_reagents_and_an_item_keep_the_games_count(self):
        lua = reagents('''
            slots[3] = { kind = "spell", id = 133, spell = 133 }
            slots[4] = { kind = "item", id = 929, spell = 23028 }
        ''')
        self.assertEqual(count(lua, 3), "")
        self.assertEqual(count(lua, 4), "20")

    def test_a_macro_shows_the_count_of_the_spell_its_button_shows(self):
        lua = reagents('slots[5] = { kind = "macro", id = 7, spell = 133 }')
        self.assertEqual(count(lua, 5), "")
        lua.execute('slots[5].spell = 23028; handler(nil, "MODIFIER_STATE_CHANGED"); flush()')
        self.assertEqual(count(lua, 5), "7")

    def test_a_modifier_redraws_only_macros_whose_spell_changed(self):
        lua = reagents('''
            slots[1] = { kind = "spell", id = 23028, spell = 23028 }
            slots[5] = { kind = "macro", id = 7, spell = 23028 }
        ''')
        lua.execute('''
            redraws = 0
            local update = ActionButton_UpdateCount
            ActionButton_UpdateCount = function(b) redraws = redraws + 1; update(b) end
            handler(nil, "MODIFIER_STATE_CHANGED"); handler(nil, "PLAYER_TARGET_CHANGED"); flush()
        ''')
        self.assertEqual(lua.eval('redraws'), 0)
        lua.execute('handler(nil, "BAG_UPDATE_DELAYED"); flush()')
        self.assertEqual(lua.eval('redraws'), 72)

    def test_no_slot_scan_and_no_reagent_lists(self):
        code = source("mods/actionbar-reagents.lua")
        for old in ("1, 120", "GetMacroSpell", "GetSpellReagents", "hasReagents", "macroSlots"):
            self.assertNotIn(old, code)
        self.assertNotIn("GetSpellReagents", source("ExtraActions.lua"))
        self.assertNotIn("reagentSpells", source("ExtraActions.lua"))


if __name__ == "__main__":
    unittest.main()
