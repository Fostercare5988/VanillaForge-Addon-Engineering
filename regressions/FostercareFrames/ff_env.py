"""FostercareFrames 1.0 (a rebuild: the unit frames of the old FostercareTweaks)
on the shared game model (wowkit).

The addon lives outside AddOns while the old FostercareTweaks plays
(`Interface/Rebuild/FostercareFrames`); point VANILLAFORGE_ADDON_ROOT at it
(tools/audit_addon.py does when given that folder).

The stock frames are modelled from the client's FrameXML (.private/framexml):
BuffFrame.lua's BuffButton_Update and BuffFrame_Enchant_OnUpdate as they run,
TextStatusBar.lua's TextStatusBar_UpdateTextString, TargetFrame.lua's target of
target (shown while the target has a target), and the frames' stock OnUpdate
scripts as counters. The DLL calls are modelled as ClassicAPI's docs/API.md
gives them: RegisterUnitEvent filters by unit; UNIT_AURA_DELTA carries the
changed instance IDs; GetAuraSlots fills a table, UnitAuraBySlot gives the
positional values; C_Item.GetWeaponEnchantInfo gives the enchant IDs. NamPower's
GUID events carry the GUID first. The mocks do not prove drawing, the client's
saved positions (layout-cache.txt), or when the client sends events.
"""
from pathlib import Path
import os
import wowkit

ROOT = Path(os.environ["VANILLAFORGE_ADDON_ROOT"])

MOCK = r'''
CLASSIC_API_VERSION = 12100
STANDARD_TEXT_FONT = 'Fonts\\FRIZQT__.TTF'
MAX_PARTY_MEMBERS, BUFF_WARNING_TIME, SHOW_BUFF_DURATIONS = 4, 31, '1'
NORMAL_FONT_COLOR = { r = 1, g = 0.82, b = 0 }
calls = {}
function count(name) return calls[name] or 0 end
function hit(name) calls[name] = (calls[name] or 0) + 1 end

-- hooksecurefunc(name, fn), as the client runs it: the stock function, then the hook.
function hooksecurefunc(name, hook)
    local stock = _G[name]
    _G[name] = function(...) local r = stock(...); hook(...); return r end
end

-- Widgets: what the addon reads back.
-- Positions, dragging and the client's saved places: the kit's (wowkit.py, "Positions").
function Widget:SetCooldown(start, duration) self.cooldown = { start, duration }; hit('SetCooldown') end
function Widget:Clear() self.cooldown = nil end
function Widget:GetCountdownFontString() self.numbers = self.numbers or CreateFrame('FontString'); return self.numbers end
function Widget:SetCountdownFormatter(f) self.formatter = f end
function Widget:SetStatusBarColor(r, g, b) self.barColor = { r, g, b } end
function Widget:SetTimerDuration(d, interpolation, direction) self.timer = { d, direction } end
function Widget:SetDesaturated(on) self.grey = on and true or nil end
function Widget:SetReverse(on) self.reverse = on and true or nil end
function Widget:SetDrawSwipe(on) self.swipe = on end
function Widget:SetText(text) self.text = text; hit('SetText') end
function Widget:SetTexture(path) self.texture = path; hit('SetTexture') end
function Widget:GetEffectiveScale() return 1 end
function Widget:GetFrameLevel() return 1 end
function Widget:SetDontSavePosition(on) self.dontSave = on end
function Widget:SetDrawLayer(layer) self.layer = layer end
function Widget:CreateTexture(name, layer)
    local t = newWidget('Texture', name, self)
    t.layer = layer
    self.textures = self.textures or {}
    self.textures[#self.textures + 1] = t
    return t
end

-- Keys (ClassicAPI's left and right reads).
shift, ctrl = false, false
function IsLeftShiftKeyDown() return shift and 1 or nil end
function IsRightShiftKeyDown() return nil end
function IsLeftControlKeyDown() return ctrl and 1 or nil end
function IsRightControlKeyDown() return nil end
function press(s, c) shift, ctrl = s, c; fire('MODIFIER_STATE_CHANGED', 'LSHIFT', s and 1 or 0) end

-- Units: token -> unit.
units = {}
function unit(token, name, class, t)
    t = t or {}
    t.name, t.class, t.guid = name, class, t.guid or ('0x' .. name)
    t.hp, t.max = t.hp or 3000, t.max or 3000
    t.mana, t.maxMana, t.power = t.mana or 100, t.maxMana or 100, t.power or 3
    if t.player == nil then t.player = true end
    units[token] = t
    return t
end
local function u(token) return units[token] end
function UnitExists(x) return u(x) and 1 or nil end
function UnitName(x) return u(x) and u(x).name end
function GetUnitName(x) return UnitName(x) end
function UnitGUID(x) return u(x) and u(x).guid end
function UnitClass(x) if u(x) then return u(x).class, u(x).class end end
function UnitIsPlayer(x) return u(x) and u(x).player and 1 or nil end
function UnitHealth(x) return u(x) and u(x).hp or 0 end
function UnitHealthMax(x) return u(x) and u(x).max or 0 end
function UnitMana(x) return u(x) and u(x).mana or 0 end
function UnitManaMax(x) return u(x) and u(x).maxMana or 0 end
function UnitPowerType(x) return u(x) and u(x).power or 0 end
function UnitIsDeadOrGhost(x) return u(x) and u(x).dead and 1 or nil end
function UnitIsConnected(x) return u(x) and 1 or nil end
function UnitIsUnit(a, b) return u(a) and u(a) == u(b) and 1 or nil end
party = 0
function GetNumPartyMembers() return party end
function GetNumRaidMembers() return 0 end
RAID_CLASS_COLORS = {}
for i, c in ipairs({ 'WARRIOR', 'PRIEST', 'MAGE', 'ROGUE', 'DRUID', 'HUNTER', 'WARLOCK', 'SHAMAN', 'PALADIN' }) do
    RAID_CLASS_COLORS[c] = { r = i / 10, g = 0.5, b = 0.5 }
end
function AbbreviateNumbers(n) if n >= 1000 then return string.format('%.1fK', math.floor(n / 100) / 10) end; return tostring(n) end

-- ClassicAPI's types.
Enum = { NumericRuleFormatRounding = { Up = 1 }, StatusBarInterpolation = { Immediate = 0 },
    StatusBarTimerDirection = { ElapsedTime = 0, RemainingTime = 1 } }
C_StringUtil = { CreateNumericRuleFormatter = function() return { SetBreakpoints = function(self, b) self.breakpoints = b end } end }
C_DurationUtil = { CreateDuration = function() return { SetTimeSpan = function(self, a, b) self.span = { a, b } end } end }

-- Spells: spells[id or name] = { name, icon, id }; book[id] = slot; cooldowns[slot] = { start, duration };
-- base[id] = the spell's own cooldown in ms (GetSpellBaseCooldown; 0 for the global one only).
spells, book, cooldowns, base = {}, {}, {}, {}
function spell(id, name, icon) local s = { name = name, icon = icon, id = id }; spells[id] = s; spells[name] = s; return s end
function GetSpellInfo(x)
    hit('GetSpellInfo')
    local s = spells[x]
    if s then return s.name, '', s.icon, 0, false, 0, 0, 0, 0, s.id end
end
function FindSpellBookSlotByID(id) if book[id] then return book[id], 'spell' end end
function GetSpellBaseCooldown(id) return base[id] or (spells[id] and 0 or nil) end
function GetSpellCooldown(slot) hit('GetSpellCooldown'); local c = cooldowns[slot]; if c then return c[1], c[2], 1 end; return 0, 0, 1 end
casts = {}
C_Spell = {
    UnitCastingInfo = function(x) local c = casts[x]; if c and not c.channel then
        return c.name, c.name, c.icon, c.start, c.finish, false, 1, c.locked end end,
    UnitChannelInfo = function(x) local c = casts[x]; if c and c.channel then
        return c.name, c.name, c.icon, c.start, c.finish, false, c.locked end end,
    CancelSpellByID = function(id) hit('cancel:' .. id) end,
}

-- Auras: auras[token] = { HELPFUL = { ... }, HARMFUL = { ... } } in the game's order.
auras = {}
local function list(x, f) auras[x] = auras[x] or { HELPFUL = {}, HARMFUL = {} }; return auras[x][f] end
local instances = 0
function aura(x, f, t)
    local l = list(x, f); l[#l + 1] = t
    instances = instances + 1; t.instance = instances
    return t
end
C_UnitAuras = {
    GetAuraSlots = function(x, f, max, token, out)
        hit('GetAuraSlots')
        local l = list(x, f)
        for i = 1, #l do out[i] = (f == 'HARMFUL' and 1000 or 0) + i end
        for i = #l + 1, #out do out[i] = nil end
        return nil, #l
    end,
    UnitAuraBySlot = function(x, slot)
        local a = list(x, slot > 1000 and 'HARMFUL' or 'HELPFUL')[slot % 1000]
        if a then return a.name, a.icon, a.stacks or 1, a.dispel, a.duration or 0, a.expires or 0, a.source,
            false, false, a.id end
    end,
    GetAuraDataByAuraInstanceID = function(x, id, buf)
        for _, f in ipairs({ 'HELPFUL', 'HARMFUL' }) do
            for _, a in ipairs(list(x, f)) do
                if a.instance == id then
                    buf.name, buf.spellId, buf.isHelpful, buf.applications = a.name, a.id, f == 'HELPFUL', a.stacks or 1
                    buf.duration, buf.expirationTime, buf.sourceUnit = a.duration or 0, a.expires or 0, a.source
                    buf.sourceGUID = a.source and UnitGUID(a.source)
                    return buf
                end
            end
        end
    end,
    GetAuraDispelTypeColor = function(name) return { r = name == 'Magic' and 0.2 or 0.8, g = 0, b = 0, a = 1 } end,
}
function delta(x, info) fire('UNIT_AURA_DELTA', x, info) end

-- The player's own buffs, as the stock BuffFrame reads them: buffs[filter][i].
playerBuffs = { HELPFUL = {}, HARMFUL = {} }
local function pb(index) return playerBuffs[index >= 100 and 'HARMFUL' or 'HELPFUL'][index % 100 + 1] end
function GetPlayerBuff(id, filter)
    local b = playerBuffs[filter == 'HARMFUL' and 'HARMFUL' or 'HELPFUL'][id + 1]
    if not b then return -1, nil end
    return (filter == 'HARMFUL' and 100 or 0) + id, b.permanent and 1 or nil
end
function GetPlayerBuffTexture(i) hit('GetPlayerBuffTexture'); return pb(i).icon end
function GetPlayerBuffApplications(i) return pb(i).stacks or 0 end
function GetPlayerBuffDispelType(i) return i >= 0 and pb(i) and pb(i).dispel end
function GetPlayerBuffTimeLeft(i) return pb(i).ends and pb(i).ends - now or 0 end
function GetPlayerBuffID(i) return pb(i).id end

-- Weapons: enchant[16|17] = { id, ends }; bags[bag][slot] = { itemName, iconFileID }.
enchant, bags, quality = {}, {}, {}
local function ms(e) return e and (e.ends - now) * 1000 end
function GetWeaponEnchantInfo()
    local m, o = enchant[16], enchant[17]
    return m ~= nil, ms(m), 0, o ~= nil, ms(o), 0
end
C_Item = {
    GetWeaponEnchantInfo = function()
        local m, o = enchant[16], enchant[17]
        return m ~= nil, ms(m), 0, m and m.id or 0, o ~= nil, ms(o), 0, o and o.id or 0
    end,
    GetEnchantInfo = function(id) return { enchantID = id, name = id == 323 and 'Instant Poison' or 'Deadly Poison', spellID = 1 } end,
}
C_Container = {
    GetContainerNumSlots = function(b) return bags[b] and #bags[b] or 0 end,
    GetContainerItemInfo = function(b, s) hit('GetContainerItemInfo'); return bags[b][s] end,
}
function GetInventoryItemTexture(_, slot) return 'weapon' .. slot end
function GetInventoryItemQuality(_, slot) return quality[slot] end
function GetItemQualityColor(q) return q / 10, 0, 0 end

GameTooltip = CreateFrame('GameTooltip', 'GameTooltip')
function GameTooltip:SetOwner(owner) self.owner = owner end
function GameTooltip:IsOwned(f) return self.owner == f and 1 or nil end
function GameTooltip:Hide() self.owner = nil end
function GameTooltip:SetUnitAura(x, i, f) self.aura = { x, i, f } end

-- The stock frames (FrameXML).
local function frame(kind, name, parent) return CreateFrame(kind, name, parent) end
PlayerFrame = frame('Frame', 'PlayerFrame', UIParent)
TargetFrame = frame('Frame', 'TargetFrame', UIParent); TargetFrame:Hide()
TargetFrame:RegisterEvent('UNIT_AURA') -- TargetFrame.lua:28; it only draws the stock auras
TargetFrameNameBackground = TargetFrame:CreateTexture('TargetFrameNameBackground')
TargetPortrait = TargetFrame:CreateTexture('TargetPortrait')
TargetRaidTargetIcon = TargetFrame:CreateTexture('TargetRaidTargetIcon')
TargetHPText = TargetFrame:CreateFontString('TargetHPText')
TargetHPPercText = TargetFrame:CreateFontString('TargetHPPercText')
for i = 1, 4 do
    frame('Frame', 'PartyMemberFrame' .. i, UIParent)
    _G['PartyMemberFrame' .. i .. 'Name'] = CreateFrame('FontString')
end
local function bar(name, parent, text)
    local b = frame('StatusBar', name, parent)
    if text then b.TextString = b:CreateFontString(name .. 'Text') end
    b.lockShow = 0
    _G[name] = b
    return b
end
bar('PlayerFrameHealthBar', PlayerFrame, true); bar('PlayerFrameManaBar', PlayerFrame, true)
bar('TargetFrameHealthBar', TargetFrame); bar('TargetFrameManaBar', TargetFrame)
PetFrame = frame('Frame', 'PetFrame', UIParent)
bar('PetFrameHealthBar', PetFrame, true); bar('PetFrameManaBar', PetFrame, true)
PlayerFrameManaBar.width, PlayerFrameManaBar.height = 120, 10
function TextStatusBar_UpdateTextString(b)
    b = b or this
    local fs = b.TextString
    if fs then local lo, hi = b:GetMinMaxValues(); fs:SetText(b:GetValue() .. ' / ' .. hi) end
end
function TargetFrame_CheckDead() end
function TargetFrame_CheckFaction() end
function PlayerFrame_Update() end
function PartyMemberFrame_UpdateMember() end
function TargetFrame_UpdateRaidTargetIcon() hit('TargetFrame_UpdateRaidTargetIcon') end
function SetRaidTarget() end
function UIParent_ManageFramePositions() CastingBarFrame:ClearAllPoints(); CastingBarFrame:SetPoint('BOTTOM', UIParent, 'BOTTOM', 0, 60) end

TargetofTargetFrame = frame('Button', 'TargetofTargetFrame', TargetFrame); TargetofTargetFrame:Hide()
TargetofTargetFrame.unit = 'targettarget'
TargetofTargetFrame.portrait = TargetofTargetFrame:CreateTexture()
TargetofTargetFrame.name = TargetofTargetFrame:CreateFontString()
TargetofTargetFrame.healthbar, TargetofTargetFrame.manabar = frame('StatusBar'), frame('StatusBar')
TargetofTargetFrame:SetScript('OnUpdate', function() hit('TargetofTarget_OnUpdate') end)
function TargetofTarget_Update()
    hit('TargetofTarget_Update')
    if UnitExists('target') and UnitExists('targettarget') and UnitHealth('target') > 0 then
        TargetofTargetFrame:Show()
    else
        TargetofTargetFrame:Hide()
    end
end
function SetPortraitTexture(t, x) hit('SetPortraitTexture') end
function UnitFrameHealthBar_Update() hit('UnitFrameHealthBar_Update') end
function UnitFrameManaBar_Update() hit('UnitFrameManaBar_Update') end
function TargetofTarget_CheckDead() end
function RefreshBuffs() hit('RefreshBuffs') end
for i = 1, 5 do frame('Button', 'TargetFrameBuff' .. i, TargetFrame) end
for i = 1, 16 do frame('Button', 'TargetFrameDebuff' .. i, TargetFrame) end
function TargetDebuffButton_Update()
    for i = 1, 5 do _G['TargetFrameBuff' .. i]:Show() end
    for i = 1, 16 do _G['TargetFrameDebuff' .. i]:Show() end
end

CastingBarFrame = frame('StatusBar', 'CastingBarFrame', UIParent); CastingBarFrame:Hide()
CastingBarFrame:SetPoint('BOTTOM', UIParent, 'BOTTOM', 0, 60) -- CastingBarFrame.xml

-- BuffFrame.xml / BuffFrame.lua.
BuffFrame = frame('Frame', 'BuffFrame', UIParent)
BuffFrame:SetScript('OnUpdate', function() hit('BuffFrame_OnUpdate') end)
TemporaryEnchantFrame = frame('Frame', 'TemporaryEnchantFrame', UIParent)
TemporaryEnchantFrame:SetScript('OnUpdate', function() hit('BuffFrame_Enchant_OnUpdate:clock'); BuffFrame_Enchant_OnUpdate(0) end)
local function buffButton(name, id, filter)
    local b = frame('Button', name, BuffFrame)
    b:SetID(id); b.buffFilter = filter
    for _, part in ipairs({ 'Icon', 'Duration', 'Count', 'Border' }) do
        _G[name .. part] = part == 'Icon' and b:CreateTexture(name .. part) or b:CreateFontString(name .. part)
    end
    _G[name .. 'Icon'].layer, _G[name .. 'Count'].layer = 'BACKGROUND', 'BACKGROUND' -- BuffFrame.xml:9-18
    return b
end
for i = 0, 39 do
    local b = buffButton('BuffButton' .. i, i < 24 and i or i - 24, i < 24 and 'HELPFUL' or 'HARMFUL')
    b:SetScript('OnUpdate', function() hit('BuffButton_OnUpdate') end)
end
for i = 1, 2 do
    local b = buffButton('TempEnchant' .. i, 0)
    b:SetScript('OnUpdate', function() hit('BuffFrame_EnchantButton_OnUpdate') end)
end
function BuffButton_Update()
    local buffIndex, untilCancelled = GetPlayerBuff(this:GetID(), this.buffFilter)
    this.buffIndex, this.untilCancelled = buffIndex, untilCancelled
    if buffIndex < 0 then this:Hide(); return end
    this:SetAlpha(1.0); this:Show()
    _G[this:GetName() .. 'Icon']:SetTexture(pb(buffIndex).icon) -- GetPlayerBuffTexture, not counted as ours
end
function BuffButtons_UpdatePositions() end
function BuffFrame_Enchant_OnUpdate()
    local hasMain, _, _, hasOff = GetWeaponEnchantInfo()
    local n = 0
    if hasOff then n = n + 1; TempEnchant1:SetID(17); TempEnchant1:Show() end
    if hasMain then n = n + 1; local b = _G['TempEnchant' .. n]; b:SetID(16); b:Show() end
    for i = n + 1, 2 do _G['TempEnchant' .. i]:Hide() end
end
function playerAuras() local was = this
    for i = 0, 39 do this = _G['BuffButton' .. i]; BuffButton_Update() end
    this = was
end

-- Reading back.
function shownIcons(rowName)
    local row, out = _G['FostercareFrames' .. rowName], {}
    for _, b in ipairs(row.buttons) do if b:IsShown() then out[#out + 1] = b.icon.texture end end
    return table.concat(out, ' ')
end
function topShown(filter)
    local out = {}
    for i = 0, 39 do
        local b = _G['BuffButton' .. i]
        if b.buffFilter == filter and b:IsShown() then out[#out + 1] = GetPlayerBuffTexture(b.buffIndex) end
    end
    return table.concat(out, ' ')
end
function listening(w)
    local out = {}
    for e in pairs(w.events) do out[#out + 1] = e end
    table.sort(out)
    return table.concat(out, ',')
end
-- The frame that listens to `e`; a frame's Ctrl+Shift handle; the energy line.
function listener(e) for _, w in ipairs(widgets) do if w.events[e] then return w end end end
function handleOf(f) for _, w in ipairs(widgets) do if w.parent == f and w.scripts.OnMouseDown then return w end end end
function tickLine() for _, w in ipairs(widgets) do if w.parent == PlayerFrameManaBar and w.kind == 'Frame' then return w end end end
-- The class fill a frame's addon texture on BORDER shows: its red, or "hidden".
function fill(f)
    for _, t in ipairs(f.textures or {}) do
        if t.layer == 'BORDER' then return t:IsShown() and tostring(t.color[1]) or 'hidden' end
    end
end
function watchIcon(x, name) return _G['FostercareFramesWatch_' .. x .. '_' .. string.gsub(name, '[^%w]', '')] end
F = nil
'''

GLOBALS = ("FostercareFramesDB", "SLASH_FOSTERCAREFRAMES1", "FostercareFramesTargetCast",
           "FostercareFramesPlayerBuffs", "FostercareFramesPlayerDebuffs", "FostercareFramesTargetBuffs",
           "FostercareFramesTargetDebuffs", "FostercareFramesTopBuffs", "FostercareFramesTopDebuffs",
           "FostercareFramesEnchants", "FostercareFramesWatchList", "FostercareFramesWatchName")


def load(saved="", setup="", world=True):
    """The addon over `saved` (Lua that sets FostercareFramesDB), as the rogue
    Claude logs in with no target; with `world`, the login events have fired."""
    lua = wowkit.runtime()
    lua.execute(MOCK)
    lua.execute("unit('player', 'Claude', 'ROGUE')")
    lua.execute(setup)
    wowkit.load_addon(lua, ROOT, "FostercareFrames", saved=saved or None)
    lua.execute("F = __addon_ns")
    if world:
        lua.execute('fire("VARIABLES_LOADED") fire("PLAYER_ENTERING_WORLD") runTimers()')
    return lua


def target(lua, name="Mob", cls="WARRIOR", **kw):
    """Claude targets `name`; the game's target frame shows."""
    extra = ", ".join(f"{k} = {v!r}" if not isinstance(v, bool) else f"{k} = {str(v).lower()}" for k, v in kw.items())
    lua.execute(f"unit('target', {name!r}, {cls!r}, {{ {extra} }}); TargetFrame:Show(); fire('PLAYER_TARGET_CHANGED'); runTimers()")
