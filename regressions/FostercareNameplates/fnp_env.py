"""Shared Lua 5.1 environment for the FostercareNameplates regressions.

Runs the selected addon's TOC files in order with generic widget mocks, then
models the client's SavedVariables load: a stock 1.12 client restores saved
tables after the addon's files run; ClassicAPI restores them first when the TOC
declares `## LoadSavedVariablesFirst: 1`. Native nameplate rendering, real event
payloads and engine timing remain in-game checks.
"""
from pathlib import Path
import os
import re
from lupa.lua51 import LuaRuntime

ROOT = Path(os.environ["VANILLAFORGE_ADDON_ROOT"])
TOC = (ROOT / "FostercareNameplates.toc").read_text("utf-8-sig")
FILES = [line.strip() for line in TOC.splitlines()
         if line.strip() and not line.startswith("#")]
SV_FIRST = re.search(r"^## LoadSavedVariablesFirst:\s*1\s*$", TOC, re.M) is not None

BASE = r'''
CLASSIC_API_VERSION, SUPERWOW_VERSION = 11600, "2.2"
messages = {}
DEFAULT_CHAT_FRAME = { AddMessage = function(_, m) table.insert(messages, m) end }
STANDARD_TEXT_FONT = "Fonts\\FRIZQT__.TTF"
UISpecialFrames, RAID_CLASS_COLORS = {}, { MAGE = { r = 0.4, g = 0.8, b = 1 } }
CLOSE, SlashCmdList = "Close", {}

local Widget = {}
local Meta = { __index = function(_, k)
    if Widget[k] then return Widget[k] end
    if string.find(k, "^%u") then return function() end end
end }
frames = {}
local function widget(name)
    local w = setmetatable({ name = name, scripts = {}, events = {}, shown = true }, Meta)
    if name then rawset(_G, name, w) end
    table.insert(frames, w)
    return w
end
function Widget:GetName() return self.name end
function Widget:Show() self.shown = true end
function Widget:Hide() self.shown = false end
function Widget:IsShown() return self.shown end
function Widget:SetScript(k, f) self.scripts[k] = f end
function Widget:GetScript(k) return self.scripts[k] end
function Widget:RegisterEvent(e) self.events[e] = true end
function Widget:UnregisterAllEvents() self.events = {} end
function Widget:GetWidth() return 110 end
function Widget:GetHeight() return 14 end
function Widget:GetScale() return 1 end
function Widget:GetFont() return STANDARD_TEXT_FONT, 12, "" end
function Widget:GetFontString() self.fs = self.fs or widget(); return self.fs end
function Widget:GetNormalTexture() return widget() end
function Widget:GetPushedTexture() return widget() end
function Widget:GetDisabledTexture() return widget() end
function Widget:GetHighlightTexture() return widget() end
function Widget:GetCheckedTexture() return widget() end
function Widget:CreateTexture() return widget() end
function Widget:CreateFontString() return widget() end
function Widget:GetChecked() return self.checked end
function Widget:SetChecked(v) self.checked = v end
function Widget:GetValue() return self.value or 0 end
function Widget:SetValue(v) self.value = v end
UIParent = widget("UIParent")
setmetatable(_G, { __index = function(_, k)
    if type(k) == "string" and string.find(k, "^FNP") then return widget(k) end
end })
function CreateFrame(_, name) return widget(name) end
function SetRaidTargetIconTexture() end
now = 100
function GetTime() return now end
calls = {}
local function count(name) calls[name] = (calls[name] or 0) + 1 end
function UnitGUID() return nil end
function UnitIsPlayer() end
function UnitClass() end
function UnitCanAttack() return 1 end
function UnitHealth() return 50 end
function UnitHealthMax() return 100 end
function UnitIsUnit() end
function GetComboPoints() return 0 end
C_NamePlate = { GetNamePlateGUIDs = function() return {} end, GetNamePlateForUnit = function() end,
    GetNamePlateForGUID = function() end }
C_Timer = { After = function() count("After") end,
    NewTicker = function() return { Cancel = function() end } end }
C_Spell = { UnitCastingInfo = function() count("UnitCastingInfo") end,
    UnitChannelInfo = function() count("UnitChannelInfo") end }
C_UnitAuras = { UnitAura = function(_, _, filter) count("UnitAura " .. tostring(filter)) end,
    GetAuraSlots = function() count("GetAuraSlots"); return nil, 0 end,
    UnitAuraBySlot = function() count("UnitAuraBySlot") end }

-- A native-shaped plate: a Button whose first region is the stock border.
function nativePlate(guid, token)
    local plate = CreateFrame("Button")
    local border = CreateFrame("Texture")
    function border:GetObjectType() return "Texture" end
    function border:GetTexture() return "Interface\\Tooltips\\Nameplate-Border" end
    function plate:GetObjectType() return "Button" end
    function plate:GetRegions() return border end
    function plate:GetChildren() return CreateFrame("StatusBar") end
    local forUnit, forGUID = C_NamePlate.GetNamePlateForUnit, C_NamePlate.GetNamePlateForGUID
    C_NamePlate.GetNamePlateForUnit = function(u)
        if u == token then return plate end
        return forUnit(u)
    end
    C_NamePlate.GetNamePlateForGUID = function(g)
        count("GetNamePlateForGUID")
        if g == guid then return plate end
        return forGUID(g)
    end
    local unitGUID = UnitGUID
    UnitGUID = function(u) if u == token or u == guid then return guid end return unitGUID(u) end
    fire("NAME_PLATE_UNIT_ADDED", token)
    return plate
end

-- Run the plate's hooked OnUpdate for `frames` frames at 60 fps.
function runFrames(plate, frames)
    for _ = 1, frames do
        now = now + 1 / 60
        plate.scripts.OnUpdate(plate)
    end
end

function fire(ev, a1)
    for _, f in ipairs(frames) do
        if f.events[ev] and f.scripts.OnEvent then f.scripts.OnEvent(f, ev, a1) end
    end
end
'''


def load(saved=None, prelude=""):
    """Run the addon. `saved` is Lua source for the restored saved table."""
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(BASE)
    lua.execute(prelude)
    restore = "FostercareNameplates_Config = %s" % saved if saved else ""
    if restore and SV_FIRST:
        lua.execute(restore)
    for name in FILES:
        source = (ROOT / name.replace("\\", "/")).read_text("utf-8-sig")
        lua.execute(source)
    if restore and not SV_FIRST:
        lua.execute(restore)
    lua.execute('fire("VARIABLES_LOADED")')
    return lua
