"""Auras 1.0 (watched auras, split out of UnitFrames 2026-11-18) on the
shared game model (wowkit) and UnitFrames' mocks of the stock frames
(ff_env.MOCK).

The game loads Auras before UnitFrames (alphabetical): `load` does the same,
each with its own namespace (A and F), so UnitFrames' rows and top right
ask the real Auras.Hidden. `frames=False` leaves UnitFrames out. The
UnitFrames folder is the one beside the Auras folder.
"""
from pathlib import Path
import os
import sys
import wowkit

sys.path.append(str(Path(__file__).resolve().parents[1] / "UnitFrames"))  # after this suite: its test_page wins
import ff_env  # noqa: E402

ROOT = Path(os.environ["VANILLAFORGE_ADDON_ROOT"])
FRAMES = ROOT.parent / "UnitFrames"
# Where you are (GetInstanceInfo's instanceType; a test sets `instanceType` and
# fires PLAYER_ENTERING_WORLD, as a loading screen does). The dropdowns as
# ClassicAPI's menu system builds them (Menu/DropdownButton.lua): SetupMenu keeps
# the generator and, on a shown dropdown, runs it and asks each radio whether it
# is selected at once (DropdownButton.lua:254, the Auras error of 2026-11-18); `menu(dd)` runs it and gives the radios and buttons, `pick(dd,
# text)` chooses the one whose text starts with `text`, `selected(dd)` the text
# of the checked radio.
MOCK = ff_env.MOCK + r"""
instanceType = 'none'
-- Animation groups, a bar's timer and duration objects (ClassicAPI): enough to see
-- that a group plays, a bar has its time span.
function Widget:CreateAnimationGroup()
    local g = { playing = false }
    function g:SetLooping() end
    function g:Play() self.playing = true end
    function g:Stop() self.playing = false end
    function g:CreateAnimation() return setmetatable({}, { __index = function() return function() end end }) end
    return g
end
function Widget:SetTimerDuration(duration) self.timer = duration end
Enum.StatusBarInterpolation = Enum.StatusBarInterpolation or { Immediate = 0 }
Enum.StatusBarTimerDirection = Enum.StatusBarTimerDirection or { ElapsedTime = 0, RemainingTime = 1 }
C_DurationUtil = { CreateDuration = function()
    local d = {}
    function d:SetTimeFromStart(start, length) self.start, self.length = start, length end
    return d
end }
-- The loss-of-control effects on you (### C_LossOfControl): `loc[i]` as
-- GetActiveLossOfControlData gives it, a new table per read.
loc = {}
C_LossOfControl = {
    GetActiveLossOfControlDataCount = function() return #loc end,
    GetActiveLossOfControlData = function(i)
        local d = loc[i]
        if not d then return nil end
        local t = {}
        for k, v in pairs(d) do t[k] = v end
        return t
    end,
}
C_Spell.GetSchoolString = function(mask) return ({ [4] = 'Fire', [16] = 'Frost' })[mask] end
LOSS_OF_CONTROL_DISPLAY_INTERRUPT_SCHOOL = '%s Locked'
function GetInstanceInfo() return 'Kalimdor', instanceType end
function Widget:SetupMenu(generator)
    self.generator = generator
    if self:IsShown() then menu(self) end
end
function menu(dd)
    local items = {}
    local root = {}
    function root:CreateRadio(text, isSelected, setSelected, data)
        items[#items + 1] = { text = text, checked = isSelected(data), pick = function() setSelected(data) end }
    end
    function root:CreateButton(text, onClick) items[#items + 1] = { text = text, pick = onClick } end
    function root:CreateTitle() end
    dd.generator(dd, root)
    return items
end
function pick(dd, text)
    for _, item in ipairs(menu(dd)) do
        if string.sub(item.text, 1, #text) == text then return item.pick() end
    end
    error('no menu item ' .. text)
end
function selected(dd)
    for _, item in ipairs(menu(dd)) do if item.checked then return item.text end end
end
"""
target = ff_env.target
GLOBALS = ("AurasDB", "Auras", "SLASH_AURAS1", "AurasList", "AurasListName", "AurasListGroupName")


def load(saved="", setup="", world=True, frames=True):
    """Auras over `saved` (Lua that sets AurasDB), then UnitFrames, as the
    rogue Claude logs in with no target; with `world`, the login events fired."""
    lua = wowkit.runtime()
    lua.execute(MOCK)
    lua.execute("unit('player', 'Claude', 'ROGUE')")
    lua.execute(setup)
    wowkit.load_addon(lua, ROOT, "Auras", saved=saved or None)
    lua.execute("A = __addon_ns; __addon_ns = nil")
    if frames:
        wowkit.load_addon(lua, FRAMES, "UnitFrames")
        lua.execute("F = __addon_ns")
    if world:
        lua.execute('fire("VARIABLES_LOADED") fire("PLAYER_ENTERING_WORLD") runTimers()')
    return lua
