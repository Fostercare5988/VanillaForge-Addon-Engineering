"""Loads FostercareAuras and FostercareAuras_Edit in lupa with a permissive
WoW widget mock, so tests can open the editor and click its controls.

Widgets accept any method: setters do nothing, getters return safe values.
Undefined globals stay nil, so `if SomeAPI then` checks behave as written;
the stubs below cover what the addon calls at load and in the editor.
"""
from pathlib import Path
import os
from lupa.lua51 import LuaRuntime

ADDON = Path(os.environ["VANILLAFORGE_ADDON_ROOT"])
EDITOR = ADDON.parent / "FostercareAuras_Edit"

MOCK = r'''
local W = {}
local numbers = {
  GetWidth = 100, GetHeight = 20, GetLeft = 0, GetRight = 100, GetTop = 100, GetBottom = 0,
  GetScale = 1, GetEffectiveScale = 1, GetAlpha = 1, GetValue = 0, GetNumPoints = 1,
  GetFrameLevel = 1, GetID = 0, GetVerticalScroll = 0, GetVerticalScrollRange = 0,
  GetHorizontalScroll = 0, GetStringWidth = 50, GetStringHeight = 12, GetNumber = 0,
  GetCursorPosition = 0, GetNumLines = 0, GetValueStep = 1, GetMaxLetters = 0,
}
local children = {
  GetFontString = true, GetNormalTexture = true, GetHighlightTexture = true, GetPushedTexture = true,
  GetCheckedTexture = true, GetDisabledTexture = true, GetDisabledCheckedTexture = true,
  GetThumbTexture = true, GetScrollChild = true, GetStatusBarTexture = true,
}
W.__index = function(self, k)
  local v = rawget(W, k)
  if v then return v end
  -- Fields (lowercase, _private) are plain nil; WoW methods are capitalized.
  if type(k) ~= "string" or not string.find(k, "^%u") then return nil end
  if numbers[k] then local n = numbers[k]; return function() return n end end
  if string.find(k, "^Is") or string.find(k, "^Has") or k == "GetChecked" or k == "GetTexture"
      or k == "GetScript" or k == "GetParent" or k == "GetFont" then
    return function() return nil end
  end
  if children[k] then
    return function(self)
      local c = rawget(self, "_c_" .. k)
      if not c then c = NEW(nil, self); rawset(self, "_c_" .. k, c) end
      return c
    end
  end
  if string.find(k, "^Get") then return function() return nil end end
  return function() end
end
function W:GetName() return rawget(self, "_name") end
function W:SetScript(h, f) self._scripts[h] = f end
function W:GetScript(h) return self._scripts[h] end
function W:HookScript(h, f)
  local old = self._scripts[h]
  self._scripts[h] = function(...) if old then old(...) end f(...) end
end
function W:Show() self._shown = true end
function W:Hide() self._shown = false end
function W:IsShown() return self._shown and 1 or nil end
function W:IsVisible()
  local f = self
  while f do
    if not f._shown then return nil end
    f = rawget(f, "_parent")
  end
  return 1
end
function W:SetChecked(v) self._checked = (v and v ~= 0) and 1 or nil end
function W:GetChecked() return self._checked end
function W:SetText(t) self._text = t end
function W:GetText() return self._text or "" end
function W:SetTexture(t) self._tex = t end
function W:GetTexture() return self._tex end
function W:SetValue(v) self._value = v end
function W:GetValue() return self._value or 0 end
function W:GetMinMaxValues() return 0, 100 end
function W:SetPoint(p, rel, rp, x, y)
  if type(rel) == "number" then x, y, rel = rel, rp, nil end
  if type(rp) == "number" then y, x, rp = x, rp, nil end
  self._point = { p, rel, rp, x or 0, y or 0 }
  if p == "TOPLEFT" then self._tl = self._point end
end
function W:GetPoint()
  local pt = self._point
  if pt then return pt[1], pt[2], pt[3], pt[4], pt[5] end
  return "CENTER", UIParent, "CENTER", 0, 0
end
function W:GetParent() return self._parent end
function W:GetFont() return "Fonts\\FRIZQT__.TTF", 12, "" end
function W:GetTextColor() return 1, 1, 1, 1 end
function W:GetVertexColor() return 1, 1, 1, 1 end
function W:GetBackdropColor() return 0, 0, 0, 1 end
function W:GetRegions() return end
function W:GetChildren() return end
function W:RegisterEvent(e) self._events[e] = true; FRAMES[self] = true end
function W:UnregisterEvent(e) self._events[e] = nil end
function W:IsEventRegistered(e) return self._events[e] and 1 or nil end
function W:RegisterAllEvents() end
function W:UnregisterAllEvents() self._events = {} end

local function New(name, parent)
  return NEW(name, parent)
end
function NEW(name, parent)
  local o = setmetatable({ _name = name, _scripts = {}, _events = {}, _parent = parent, _shown = true }, W)
  if name then _G[name] = o end
  return o
end
function W:CreateFontString(name) return New(name, self) end
function W:CreateTexture(name) return New(name, self) end
function W:CreateAnimationGroup() return New(nil, self) end

FRAMES = {}
CREATED = {}
function CreateFrame(kind, name, parent, template)
  local f = New(name, parent)
  f._kind = kind
  f._template = template
  if name and template then
    -- Template children the addon reaches by name.
    for _, suffix in ipairs({ "Text", "Low", "High", "Button", "Middle", "Left", "Right",
                              "ScrollBar", "ScrollChildFrame", "Icon", "Count", "NormalTexture" }) do
      _G[name .. suffix] = New(name .. suffix, f)
    end
    _G[name .. "ScrollBarScrollUpButton"] = New(nil, f)
    _G[name .. "ScrollBarScrollDownButton"] = New(nil, f)
  end
  f.text = _G[(name or "") .. "Text"] or New(nil, f)
  table.insert(CREATED, f)
  return f
end

for _, n in ipairs({ "GameFontNormal", "GameFontNormalSmall", "GameFontNormalLarge", "GameFontHighlight",
  "GameFontHighlightSmall", "GameFontHighlightLarge", "GameFontDisable", "GameFontDisableSmall",
  "GameFontGreen", "GameFontRed", "GameFontWhite", "NumberFontNormal", "NumberFontNormalLarge",
  "NumberFontNormalSmall", "ChatFontNormal", "SystemFont", "TextStatusBarText" }) do
  New(n)
end
UIParent = New("UIParent")
WorldFrame = New("WorldFrame")
Minimap = New("Minimap")
GameTooltip = New("GameTooltip")
DEFAULT_CHAT_FRAME = New("ChatFrame1")
ChatFrame1 = DEFAULT_CHAT_FRAME
UISpecialFrames = {}
DropDownList1 = New("DropDownList1")
SlashCmdList = {}
StaticPopupDialogs = {}
BOOKTYPE_SPELL, BOOKTYPE_PET = "spell", "pet"
STANDARD_TEXT_FONT = "Fonts\\FRIZQT__.TTF"
UIDROPDOWNMENU_MAXBUTTONS, UIDROPDOWNMENU_MENU_LEVEL, UIDROPDOWNMENU_OPEN_MENU = 32, 1, nil
UIDROPDOWNMENU_INIT_MENU = nil
MAX_SKILLLINE_TABS = 8

local function none() end
for _, n in ipairs({ "UIDropDownMenu_SetWidth", "UIDropDownMenu_SetText", "UIDropDownMenu_SetSelectedValue",
  "UIDropDownMenu_SetSelectedName", "UIDropDownMenu_SetSelectedID", "UIDropDownMenu_JustifyText",
  "UIDropDownMenu_EnableDropDown", "UIDropDownMenu_DisableDropDown", "UIDropDownMenu_SetButtonWidth",
  "UIDropDownMenu_Refresh", "CloseDropDownMenus", "ToggleDropDownMenu", "PlaySound", "PlaySoundFile",
  "HideUIPanel", "ShowUIPanel", "CooldownFrame_SetTimer", "InterfaceOptions_AddCategory",
  "RegisterCVar", "SetCVar", "ResetCursor", "SetCursor", "PanelTemplates_SetNumTabs" }) do
  _G[n] = none
end
MENU_ADDS = 0
function UIDropDownMenu_Initialize(dd, fn) dd._init = fn end
function UIDropDownMenu_AddButton(info) MENU_ADDS = MENU_ADDS + 1 end
function UIDropDownMenu_CreateInfo() return {} end
function UIDropDownMenu_GetSelectedValue() return nil end
function UIDropDownMenu_GetText(dd) return dd and dd._ddtext end

CLASSIC_API_VERSION = 11711
function GetNampowerVersion() return 4, 6, 2 end
NOW = 1000
function GetTime() return NOW end
function GetCVar() return "0" end
function GetLocale() return "enUS" end
function GetAddOnMetadata() return "test" end
function UnitClass() return "Rogue", "ROGUE" end
function UnitName(u) return (u == "player") and "Claude" or nil end
function UnitRace() return "Human", "Human" end
function UnitLevel() return 60 end
function UnitGUID(u) return (u == "player") and "0x01" or nil end
function UnitExists(u) return u == "player" and 1 or nil end
function UnitIsDead() return nil end
function UnitIsDeadOrGhost() return nil end
function UnitIsFriend() return nil end
function UnitCanAttack() return nil end
function UnitAffectingCombat() return nil end
function UnitHealth() return 100 end
function UnitHealthMax() return 100 end
function UnitMana() return 100 end
function UnitManaMax() return 100 end
function UnitPowerType() return 3 end
function UnitCreatureType() return nil end
function UnitClassification() return "normal" end
function UnitIsUnit(a, b) return a == b end
function UnitIsPlayer(u) return u == "player" end
function GetComboPoints() return 0 end
function GetNumPartyMembers() return 0 end
function GetNumRaidMembers() return 0 end
function GetShapeshiftForm() return 0 end
function GetNumShapeshiftForms() return 0 end
function GetShapeshiftFormInfo() return nil end
function GetNumSpellTabs() return 0 end
function GetSpellTabInfo() return nil, nil, 0, 0 end
function GetSpellName() return nil end
function GetSpellTexture() return nil end
function GetSpellCooldown() return 0, 0, 1 end
function IsUsableSpell() return 1 end
function IsSpellInRange() return 1 end
function GetNumTalentTabs() return 0 end
function GetNumTalents() return 0 end
function GetTalentInfo() return nil end
function GetInventoryItemLink() return nil end
function GetInventoryItemTexture() return nil end
function GetInventoryItemCooldown() return 0, 0, 0 end
function GetInventorySlotInfo() return 16 end
function GetContainerNumSlots() return 0 end
function GetContainerItemLink() return nil end
function GetContainerItemInfo() return nil end
function GetContainerItemCooldown() return 0, 0, 0 end
function GetItemInfo() return nil end
function GetItemCount() return 0 end
function GetWeaponEnchantInfo() return nil end
function GetScreenWidth() return 1920 end
function GetScreenHeight() return 1080 end
function GetFramerate() return 60 end
function GetCursorPosition() return 0, 0 end
function InCombatLockdown() return nil end
function IsShiftKeyDown() return nil end
function IsControlKeyDown() return nil end
function IsAltKeyDown() return nil end
function GetMouseFocus() return nil end
function hooksecurefunc() end
function GetSpellInfo() return nil end
function GetSpellNameAndRankForId() return nil end
function GetSpellIdForName() return nil end
function GetSpellSlotTypeIdForName() return 0, "unknown", 0 end
function GetEquippedItem() return nil end
function GetUnitField() return {} end
function UnitAuraBySlot() return nil end
function strcmputf8i(a, b) a, b = string.lower(a), string.lower(b); if a == b then return 0 end; return a < b and -1 or 1 end
C_UnitAuras = { GetAuraSlots = function() return nil end }
C_Item = { GetWeaponEnchantInfo = function() return nil end, GetEnchantInfo = function() return nil end }
C_Spell = { GetSpellInfo = function() return nil end }
C_Timer = {
  After = function(d, f) end,
  NewTimer = function(d, f) return { Cancel = function() end } end,
  NewTicker = function(d, f) return { Cancel = function() end } end,
}
function RegisterUnitEvent(f, e) if f and f.RegisterEvent then f:RegisterEvent(e) end end
function getglobal(n) return _G[n] end
function setglobal(n, v) _G[n] = v end
function tinsert(t, v) table.insert(t, v) end
function tremove(t, i) return table.remove(t, i) end
strfind, strsub, strlower, strupper, strlen, format, gsub, strrep =
  string.find, string.sub, string.lower, string.upper, string.len, string.format, string.gsub, string.rep
floor, ceil, abs, min, max, mod = math.floor, math.ceil, math.abs, math.min, math.max, math.mod or math.fmod
function string.trim(s) return (string.gsub(s, "^%s*(.-)%s*$", "%1")) end
strtrim = string.trim
function wipe(t) for k in pairs(t) do t[k] = nil end return t end
table.wipe = wipe
function debugstack() return "" end
function geterrorhandler() return function(e) error(e) end end
function seterrorhandler() end
function issecurevariable() return nil end

-- Fire an event at every frame registered for it.
function FIRE(e, a1, a2, a3, a4)
  event, arg1, arg2, arg3, arg4 = e, a1, a2, a3, a4
  for f in pairs(FRAMES) do
    if f._events[e] and f._scripts.OnEvent then
      this = f
      f._scripts.OnEvent(f, e, a1, a2, a3, a4)
    end
  end
end

-- Run a widget's script as the game would (this = the widget).
function RUN(f, h, a1)
  local s = f and f._scripts[h]
  if s then this = f; arg1 = a1; s(f, a1) end
end
'''


def load(saved=None):
    """Loads both addons through login; returns the Lua runtime."""
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(MOCK)
    if saved:
        lua.execute(saved)
    lua.execute("NS = {}")
    loader = lua.eval("function(src, name, addon) local f, err = loadstring(src, name); "
                      "if not f then error(err) end; f(addon, NS) end")
    files = []
    for folder, toc_name in ((ADDON, "FostercareAuras.toc"), (EDITOR, "FostercareAuras_Edit.toc")):
        for line in (folder / toc_name).read_text("utf-8", "replace").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and line.lower().endswith(".lua"):
                files.append((folder, line.replace("\\", "/")))
    for folder, rel in files:
        if folder == EDITOR:
            continue
        loader((folder / rel).read_text("utf-8-sig"), "@" + rel, "FostercareAuras")
    assert not lua.eval("FostercareAuras_LoadBlocked"), "the version guard blocked the load"
    lua.execute('FIRE("ADDON_LOADED", "FostercareAuras"); FIRE("VARIABLES_LOADED"); '
                'FIRE("PLAYER_LOGIN"); FIRE("PLAYER_ENTERING_WORLD")')
    # The editor loads on demand, after login, the way LoadAddOn does it.
    editor_files = [(f, r) for f, r in files if f == EDITOR]

    def load_editor():
        for folder, rel in editor_files:
            loader((folder / rel).read_text("utf-8-sig"), "@" + rel, "FostercareAuras_Edit")
        lua.execute('FIRE("ADDON_LOADED", "FostercareAuras_Edit")')
        return True
    lua.globals().LoadAddOn = lambda name: (load_editor(), None)
    return lua
