"""RaidFrames 1.0 (a rebuild: the grid of the old Tweaks) on the
shared game model (wowkit).

The addon lives outside AddOns while the old Tweaks plays
(`Interface/Rebuild/RaidFrames`); point VANILLAFORGE_ADDON_ROOT at it
(tools/audit_addon.py does when given that folder).

The game is modelled as ClassicAPI documents it (docs/API.md): unit events
reach a frame only for the units it registered (### frame:RegisterUnitEvent);
UNIT_IN_RANGE_UPDATE carries the new range; C_UnitAuras.GetAuraSlots fills a
table and UnitAuraBySlot gives the classic positional values, own auras first
as the game orders them; GetAuraDataByAuraInstanceID fills the given buffer;
C_Spell.GetSpellEffectInfo gives three effects with their aura codes. The
client's group grid follows FrameXML Turtle_GroupUI.lua: GroupFrame listens
to PLAYER_ENTERING_WORLD, its member frames to nine unit events, and
GroupFrame_Toggle registers its events and shows it when GROUP_ENABLED is
"1". The mocks do not prove drawing, the client's saved positions, or when
the client sends events.
"""
from pathlib import Path
import os
import wowkit

ROOT = Path(os.environ["VANILLAFORGE_ADDON_ROOT"])

MOCK = r'''
CLASSIC_API_VERSION = 12100
UNKNOWNOBJECT, STANDARD_TEXT_FONT = 'Unknown', 'Fonts\\FRIZQT__.TTF'
calls = {}
function count(name) return calls[name] or 0 end
local function hit(name) calls[name] = (calls[name] or 0) + 1 end

function Widget:SetAttribute(k, v) self.attrs = self.attrs or {}; self.attrs[k] = v end
function Widget:GetAttribute(k) return self.attrs and self.attrs[k] end
function Widget:GetFrameLevel() return 1 end
function Widget:SetText(text) self.text = text; hit('SetText') end
function Widget:SetCooldown(start, duration) self.cooldown = { start, duration } end
function Widget:Clear() self.cooldown = nil end
function Widget:SetHideCountdownNumbers(hide) self.hideNumbers = hide end
function Widget:GetCountdownFontString() self.numbers = self.numbers or CreateFrame('FontString'); return self.numbers end
-- Positions, dragging and the client's saved places: the kit's (wowkit.py, "Positions").
-- The merged reads lag MODIFIER_STATE_CHANGED; the left and right ones do not
-- (CLASSICAPI_MASTER_REFERENCE, "Modifier event state ordering").
local was
function IsShiftKeyDown() if was then return was.shift end return shift end
function IsControlKeyDown() if was then return was.ctrl end return ctrl end
function IsLeftShiftKeyDown() return shift end
function IsRightShiftKeyDown() return nil end
function IsLeftControlKeyDown() return ctrl end
function IsRightControlKeyDown() return nil end
function press(s, c)
    was = { shift = shift, ctrl = ctrl }
    shift, ctrl = s, c
    fire('MODIFIER_STATE_CHANGED', s and 'LSHIFT' or 'LCTRL', s and 1 or 0)
    was = nil
end

-- Units: token -> member. `who` resolves a token to a member's name.
members = {}
function member(token, name, class, t)
    t = t or {}
    t.name, t.class = name, class
    t.hp, t.max = t.hp or 3000, t.max or 3000
    t.mana, t.maxMana, t.power = t.mana or 1000, t.maxMana or 1000, t.power or 0
    if t.online == nil then t.online = true end
    members[token] = t
    return t
end
local function m(unit) return members[unit] end
function UnitName(u) return m(u) and m(u).name end
function UnitClass(u) local x = m(u); if x and x.class then return x.class, x.class end end
function UnitHealth(u) return m(u) and m(u).hp or 0 end
function UnitHealthMax(u) hit('UnitHealthMax'); return m(u) and m(u).max or 0 end
function UnitHealthMissing(u) local x = m(u); return x and x.max - x.hp or 0 end
function UnitMana(u) return m(u) and m(u).mana or 0 end
function UnitManaMax(u) return m(u) and m(u).maxMana or 0 end
function UnitPowerType(u) return m(u) and m(u).power or 0 end
function UnitIsConnected(u) return m(u) and m(u).online and 1 or nil end
function UnitIsDead(u) return m(u) and m(u).dead and 1 or nil end
function UnitIsGhost(u) return m(u) and m(u).ghost and 1 or nil end
function UnitExists(u) return m(u) and 1 or nil end
function UnitIsUnit(a, b) return m(a) and m(a) == m(b) and 1 or nil end
function UnitCanAttack(a, b) return m(b) and m(b).enemy and 1 or nil end
function UnitIsPartyLeader(u) return m(u) and m(u).leader and 1 or nil end
inRange = {}
function UnitInRange(u) hit('UnitInRange'); return inRange[u] and true or false, true end
marks = {}
function GetRaidTargetIndex(u) return marks[u] end
function SetRaidTargetIconTexture(tex, i) tex.markIndex = i end
function AbbreviateNumbers(n) hit('AbbreviateNumbers'); if n >= 1000 then return string.format('%.1fK', math.floor(n / 100) / 10) end; return tostring(n) end

-- Party and raid.
party, raid = {}, {}
function GetNumPartyMembers() return #party end
function GetNumRaidMembers() return #raid end
function GetRaidRosterInfo(i)
    local r = raid[i]; local x = members['raid' .. i]
    return x.name, r.rank or 0, r.group, 60, x.class, x.class, 'Zone', x.online and 1 or nil
end
function joinParty(...)
    party = { ... }
    for i, name in ipairs(party) do member('party' .. i, name, 'PRIEST') end
    fire('PARTY_MEMBERS_CHANGED'); runTimers()
end

-- Auras: auras[token] = { HELPFUL = { ... }, HARMFUL = { ... } } in the game's order.
auras = {}
local function list(u, f) auras[u] = auras[u] or { HELPFUL = {}, HARMFUL = {} }; return auras[u][f] end
function aura(u, f, t) local l = list(u, f); l[#l + 1] = t; t.instance = t.instance or (#l + (f == 'HARMFUL' and 100 or 0)); return t end
C_UnitAuras = {
    GetAuraSlots = function(u, f, max, token, out)
        hit('GetAuraSlots')
        local l = list(u, f or 'HELPFUL')
        for i = 1, #l do out[i] = (f == 'HARMFUL' and 1000 or 0) + i end
        for i = #l + 1, #out do out[i] = nil end
        out.n = #l
        return nil, #l
    end,
    UnitAuraBySlot = function(u, slot)
        local a = list(u, slot > 1000 and 'HARMFUL' or 'HELPFUL')[slot % 1000]
        if not a then return end
        return 'Aura', a.icon, a.stacks or 1, a.dispel, a.duration or 0, a.expires or 0, a.source, false, false, a.id
    end,
    GetAuraDataByAuraInstanceID = function(u, id, buf)
        for _, f in ipairs({ 'HELPFUL', 'HARMFUL' }) do
            for _, a in ipairs(list(u, f)) do
                if a.instance == id then
                    buf.spellId, buf.isHelpful, buf.applications = a.id, f == 'HELPFUL', a.stacks or 1
                    buf.duration, buf.expirationTime, buf.sourceUnit = a.duration or 0, a.expires or 0, a.source
                    return buf
                end
            end
        end
    end,
}
spellFx = {}
C_Spell = { GetSpellEffectInfo = function(id)
    hit('GetSpellEffectInfo')
    local codes = spellFx[id]; if not codes then return end
    return { { auraName = codes[1] or 0 }, { auraName = codes[2] or 0 }, { auraName = 0 } }
end }
function delta(u, info) fire('UNIT_AURA_DELTA', u, info) end

-- Colours (### C_ClassColor.GetClassColor returns RAID_CLASS_COLORS' own table).
RAID_CLASS_COLORS = {}
for _, c in ipairs({ 'WARRIOR', 'PRIEST', 'MAGE', 'ROGUE', 'DRUID', 'HUNTER', 'WARLOCK', 'SHAMAN', 'PALADIN' }) do
    RAID_CLASS_COLORS[c] = { r = 0.5, g = 0.5, b = 0.5, name = c }
end
C_ClassColor = { GetClassColor = function(c) return RAID_CLASS_COLORS[c] end }
known = {}
C_PlayerCache = { GetPlayerInfoByName = function(name) local c = known[name]; if c then return c, c end end }
ManaBarColor = { [0] = { r = 0, g = 0, b = 1 }, [1] = { r = 1, g = 0, b = 0 }, [3] = { r = 1, g = 1, b = 0 } }
DebuffTypeColor = { none = { r = 0.8, g = 0, b = 0 }, Magic = { r = 0.2, g = 0.6, b = 1 } }
GameTooltip = CreateFrame('GameTooltip', 'GameTooltip')
function GameTooltip:SetUnit(u) self.unit = u end
function GameTooltip_SetDefaultAnchor() end

-- The stock party frames (FrameXML PartyMemberFrame.lua).
for i = 1, 4 do CreateFrame('Frame', 'PartyMemberFrame' .. i):Hide() end
function HidePartyFrame() for i = 1, 4 do _G['PartyMemberFrame' .. i]:Hide() end end
function ShowPartyFrame() for i = 1, #party do _G['PartyMemberFrame' .. i]:Show() end end

-- The client's group grid (FrameXML Turtle_GroupUI.lua).
GROUP_ENABLED = '1'
local GROUP_EVENTS = { 'CHAT_MSG_ADDON', 'PLAYER_TARGET_CHANGED', 'PARTY_MEMBERS_CHANGED', 'RAID_ROSTER_UPDATE' }
local MEMBER_EVENTS = { 'UNIT_AURA', 'UNIT_HEALTH', 'UNIT_DISPLAYPOWER', 'UNIT_ENERGY', 'UNIT_MAXENERGY',
    'UNIT_MANA', 'UNIT_MAXMANA', 'UNIT_RAGE', 'UNIT_MAXRAGE' }
GroupFrame = CreateFrame('Frame', 'GroupFrame'); GroupFrame:Hide()
GroupFrame:RegisterEvent('PLAYER_ENTERING_WORLD')
GroupPetsClusterFrame = CreateFrame('Frame', 'GroupPetsClusterFrame')
function GroupMemberFrame_OnLoad() for _, e in ipairs(MEMBER_EVENTS) do this:RegisterEvent(e) end end
function GroupMemberFrame_OnUpdate() hit('nativeRange') end
for g = 1, 8 do
    CreateFrame('Frame', 'GroupClusterFrame' .. g)
    for k = 1, 5 do
        local f = CreateFrame('Button', 'GroupClusterFrame' .. g .. 'MemberFrame' .. k)
        this = f; GroupMemberFrame_OnLoad(); this = nil
        f:SetScript('OnEvent', function() hit('nativeMember') end)
        f:SetScript('OnUpdate', GroupMemberFrame_OnUpdate)
    end
end
local pet = CreateFrame('Button', 'GroupPetsClusterFramePet1'); pet:RegisterEvent('UNIT_HEALTH')
function GroupFrame_Update() hit('GroupFrame_Update'); for g = 1, 8 do _G['GroupClusterFrame' .. g]:Show() end end
function GroupFrame_UpdateLayout() hit('GroupFrame_UpdateLayout') end
function GroupFrame_Toggle()
    hit('GroupFrame_Toggle')
    if GROUP_ENABLED == '1' then
        for _, e in ipairs(GROUP_EVENTS) do GroupFrame:RegisterEvent(e) end
        GroupFrame:Show(); GroupFrame_Update()
    else
        GroupFrame:UnregisterAllEvents(); GroupFrame:Hide(); ShowPartyFrame()
    end
end
function GroupFrame_OnEvent() hit('GroupFrame:' .. event); if event == 'PLAYER_ENTERING_WORLD' then GroupFrame_Toggle() end end
GroupFrame:SetScript('OnEvent', function() GroupFrame_OnEvent() end)

-- Reading back.
function btn(g, k) return _G['RaidFramesG' .. g .. 'M' .. k] end
function shown(g, k) local b = btn(g, k); return b and b:IsShown() and b.nameText.text or nil end
function grid() return RaidFramesMain end
function unitsOf(e) local u = grid().units[e]; return u and table.concat(u, ',') or (grid().events[e] and 'all') end
function iconsOf(b)
    local out = {}
    for _, icon in ipairs(b.icons) do if icon:IsShown() then out[#out + 1] = icon.path .. '@' .. icon.size end end
    return table.concat(out, ' ')
end
function listening(w)
    local out = {}
    for e in pairs(w.events) do out[#out + 1] = e end
    table.sort(out)
    return table.concat(out, ',')
end
R = nil
'''

GLOBALS = ("RaidFramesDB", "RaidFramesMain", "SLASH_RAIDFRAMES1",
           "GroupFrame_Toggle", "GroupFrame_Update", "GroupFrame_UpdateLayout")


def load(saved="", setup="", world=True):
    """The addon over `saved` (Lua that sets RaidFramesDB), as the player
    Claude logs in solo; with `world`, the login events have fired and their
    roster pass has run."""
    lua = wowkit.runtime()
    lua.execute(MOCK)
    lua.execute("member('player', 'Claude', 'ROGUE')")
    lua.execute(setup)
    wowkit.load_addon(lua, ROOT, "RaidFrames", saved=saved or None)
    lua.execute("R = __addon_ns")
    if world:
        lua.execute('fire("VARIABLES_LOADED") fire("PLAYER_ENTERING_WORLD") runTimers()')
    return lua


def in_party(saved="", setup=""):
    """Claude with Ann and Bob in a party, all in range."""
    lua = load(saved, setup)
    lua.execute("inRange.party1, inRange.party2 = true, true; joinParty('Ann', 'Bob')")
    return lua


def in_raid(lua, groups):
    """A raid: `groups` is a list of (name, class, group); member i is raid<i>."""
    rows = ", ".join("{%r, %r, %d}" % g for g in groups)
    lua.execute("""
        raid = {}
        for i, r in ipairs({ %s }) do
            member('raid' .. i, r[1], r[2]); raid[i] = { group = r[3] }; inRange['raid' .. i] = true
        end
        members.raid1 = members.player; members.player.name = 'Claude'
        fire('RAID_ROSTER_UPDATE'); runTimers()
    """ % rows)
    return lua
