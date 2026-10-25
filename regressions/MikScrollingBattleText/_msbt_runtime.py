"""Self-contained Lua model of MSBT's core files for regression tests.

Loads the addon's TOC Lua files (options UI excluded) into lupa with mocked
ClassicAPI / SuperWoW / NamPower globals. It needs no client MPQs. Lua 5.0
generic `for k,v in t do` loops are adapted to `pairs`. Not in-game proof.

Requires VANILLAFORGE_ADDON_ROOT=<AddOns>/MikScrollingBattleText and lupa.
"""
from pathlib import Path
import os
import re

from lupa.lua51 import LuaRuntime

ROOT = Path(os.environ.get("VANILLAFORGE_ADDON_ROOT", "")).resolve()
if not (ROOT / "MikScrollingBattleText.toc").is_file():
    raise RuntimeError("Set VANILLAFORGE_ADDON_ROOT to the MikScrollingBattleText folder")

CORE_SKIP = {"MSBTOptions.lua"}


def lua50(source):
    return re.sub(r'for ([\w_, ]+) in ([\w.\[\]"\']+) do', r'for \1 in pairs(\2) do', source)


def toc_lua_files():
    files = []
    for line in (ROOT / "MikScrollingBattleText.toc").read_text("utf-8-sig").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and line.endswith(".lua") and line not in CORE_SKIP:
            files.append(line)
    return files


BOOT = r'''
CLASSIC_API_VERSION=11707; SUPERWOW_VERSION="2.2";
now=1; event=nil; this=nil; cvars={}; calls={}; frames={};
local function count(name) calls[name]=(calls[name] or 0)+1 end

-- Minimal widget model: every unknown method is a no-op; event registration is recorded.
local Widget={}
function Widget:RegisterEvent(e) self.events[e]=true end
function Widget:UnregisterEvent(e) self.events[e]=nil end
function Widget:UnregisterAllEvents() for k in pairs(self.events) do self.events[k]=nil end end
function Widget:SetScript(k,f) self.scripts[k]=f end
function Widget:GetScript(k) return self.scripts[k] end
function Widget:GetName() return self.name end
function Widget:IsVisible() return self.shown end
function Widget:IsShown() return self.shown end
function Widget:Show() self.shown=true end
function Widget:Hide() self.shown=false end
function Widget:CreateTexture() return NewWidget() end
local WidgetMeta={__index=function(t,k) return Widget[k] or function() end end}
function NewWidget(name)
  local w=setmetatable({name=name,events={},scripts={},shown=false},WidgetMeta)
  table.insert(frames,w)
  if name then _G[name]=w end
  return w
end
function CreateFrame(kind,name) return NewWidget(name) end
function getglobal(name) return rawget(_G,name) or NewWidget(name) end
setglobal=function(k,v) _G[k]=v end

-- Fire an event at every frame registered for it, the way the client does.
function Fire(e,...)
  local a={n=select("#",...),...}
  event=e
  for i=1,24 do _G["arg"..i]=a[i] end
  cleu=a
  for _,f in ipairs(frames) do
    local h=f.scripts.OnEvent
    if f.events[e] and h then this=f; h(f,e,unpack(a,1,a.n)) end
  end
end
function CombatLogGetCurrentEventInfo() return unpack(cleu,1,cleu.n) end

-- Bit library (ClassicAPI ships one; lupa's 5.1 has none).
bit={}
function bit.band(a,b) local r,p=0,1 while a>0 and b>0 do if math.mod(a,2)==1 and math.mod(b,2)==1 then r=r+p end; a=math.floor(a/2); b=math.floor(b/2); p=p*2 end; return r end
math.mod=math.mod or math.fmod
string.gfind=string.gmatch
function table.wipe(t) for k in pairs(t) do t[k]=nil end return t end

-- Instrument string.lower before the addon caches it.
local lower=string.lower
string.lower=function(s) count("string.lower"); return lower(s) end
strlower=string.lower

units={player={guid="0xPLAYER",name="Hero",health=1000,max=1000,mana=100,maxmana=100,class="PRIEST"},
 pet={guid="0xPET",name="Wolf",health=500,max=500,class="WARRIOR"},
 target={guid="0xENEMY",name="Twin",health=1000,max=1000,class="MAGE",player=true}}
function Resolve(u) if units[u] then return units[u] end; for _,v in pairs(units) do if v.guid==u then return v end end end
function UnitExists(u) count("UnitExists"); local v=Resolve(u); if v then return 1,v.guid end end
function UnitGUID(u) local v=Resolve(u); return v and v.guid end
function UnitName(u) local v=Resolve(u); return v and v.name end
function UnitClass(u) local v=Resolve(u); return v and v.class,v and v.class end
function UnitIsPlayer(u) local v=Resolve(u); return v and (u=="player" or v.player) and 1 or nil end
function UnitIsFriend(a,b) return b=="player" and 1 or nil end
function UnitIsUnit(a,b) local x,y=Resolve(a),Resolve(b); return x and y and x.guid==y.guid and 1 or nil end
function UnitHealth(u) local v=Resolve(u); return v and v.health or 0 end
function UnitHealthMax(u) local v=Resolve(u); return v and v.max or 0 end
function UnitMana(u) local v=Resolve(u); return v and v.mana or 0 end
function UnitManaMax(u) local v=Resolve(u); return v and v.maxmana or 0 end
function UnitPowerType() return 0 end
function GetComboPoints() return 0 end
function GetTime() return now end
function GetNampowerVersion() return 4,6,2 end
function SpellInfo(id) return "Spell"..id,"Rank 1","Interface\\Icons\\Spell"..id end
function GetSpellInfo(id) return "Spell"..id,"Rank 1","Interface\\Icons\\Spell"..id end
function GetSpellRecField(id,field) if field=="name" then return "Spell"..id end return 1 end
function GetSpellIdForName(n) count("GetSpellIdForName") return 0 end
function GetItemInfo(n) count("GetItemInfo") end
function GetShapeshiftFormInfo() return "","",1 end
function GetAddOnMetadata() return "1.0.1" end
function SetCVar(k,v) cvars[k]=tostring(v) end
function GetCVar(k) return cvars[k] end
function PlaySoundFile() count("PlaySoundFile") end
function PlaySound() end
DEFAULT_CHAT_FRAME={AddMessage=function(self,m) table.insert(chat,m) end}; chat={}
SlashCmdList={}; UISpecialFrames={}
timers={}
C_Timer={}
function C_Timer.NewTimer(d,f) local t={f=f,Cancel=function(self) self.cancelled=true end}; table.insert(timers,t); return t end
function C_Timer.After(d,f) C_Timer.NewTimer(d,f) end
function RunTimers() local list=timers; timers={}; for _,t in ipairs(list) do if not t.cancelled then t.f() end end end

-- 1.12 GlobalStrings the core files read (English client).
MANA="Mana"; RAGE="Rage"; ENERGY="Energy"; HONOR="Honor"; UNKNOWN="Unknown"; ALL="All"
MISS="Miss"; DODGE="Dodge"; PARRY="Parry"; BLOCK="Block"; ABSORB="Absorb"; IMMUNE="Immune"
EVADE="Evade"; RESIST="Resist"; REFLECT="Reflect"; TUTORIAL_TITLE16="Reputation"
SPELL_SCHOOL0_CAP="Physical"; SPELL_SCHOOL1_CAP="Holy"; SPELL_SCHOOL2_CAP="Fire"; SPELL_SCHOOL3_CAP="Nature"
SPELL_SCHOOL4_CAP="Frost"; SPELL_SCHOOL5_CAP="Shadow"; SPELL_SCHOOL6_CAP="Arcane"
ABSORB_TRAILER=" (%d absorbed)"; BLOCK_TRAILER=" (%d blocked)"; RESIST_TRAILER=" (%d resisted)"
CRUSHING_TRAILER=" (crushing)"; GLANCING_TRAILER=" (glancing)"
AURAADDEDSELFHELPFUL="You gain %s."
SELFKILLOTHER="You have slain %s!"
COMBATLOG_HONORGAIN="%s dies, honorable kill Rank: %s (Estimated Honor Points: %d)"
COMBATLOG_HONORAWARD="You have been awarded %d honor points."
FACTION_STANDING_INCREASED="Your %s reputation has increased by %d."
FACTION_STANDING_DECREASED="Your %s reputation has decreased by %d."
SKILL_RANK_UP="Your skill in %s has increased to %d."
COMBATLOG_XPGAIN_FIRSTPERSON="%s dies, you gain %d experience."
VSPARRYOTHERSELF="%s attacks. You parry."; SPELLPARRIEDOTHERSELF="%s's %s was parried."
VSDODGEOTHERSELF="%s attacks. You dodge."; SPELLDODGEDOTHERSELF="%s's %s was dodged."
VSDODGESELFOTHER="You attack. %s dodges."; SPELLDODGEDSELFOTHER="Your %s was dodged by %s."
COMBATLOG_OBJECT_AFFILIATION_MINE=0x1; COMBATLOG_OBJECT_AFFILIATION_OUTSIDER=0x8
COMBATLOG_OBJECT_REACTION_HOSTILE=0x40; COMBATLOG_OBJECT_CONTROL_PLAYER=0x100; COMBATLOG_OBJECT_CONTROL_NPC=0x200
COMBATLOG_OBJECT_TYPE_PLAYER=0x400; COMBATLOG_OBJECT_TYPE_NPC=0x800; COMBATLOG_OBJECT_TYPE_MASK=0xFC00
'''


def runtime(saved=None):
    """Boot the core files like the client: TOC files, XML OnLoad, ADDON_LOADED, PEW."""
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(BOOT)
    lua.execute("MCEHEventFrame=NewWidget('MCEHEventFrame'); MSBTEventFrame=NewWidget('MSBTEventFrame')")
    for name in toc_lua_files():
        lua.execute(lua50((ROOT / name).read_text("utf-8-sig")))
    lua.execute('''
    MCEHEventFrame:SetScript("OnEvent", function() MikCEH.OnEvent() end)
    MSBTEventFrame:SetScript("OnEvent", function() MikSBT.OnEvent() end)
    this=MCEHEventFrame; MikCEH.OnLoad()
    this=MSBTEventFrame; MikSBT.OnLoad()
    ''')
    if saved is not None:
        lua.globals().MikSBT_Save = saved
    lua.execute('''
    Fire("ADDON_LOADED","MikScrollingBattleText")
    Fire("PLAYER_ENTERING_WORLD")
    -- Record what reaches the display layer; keep the real handler reachable.
    sent={}; RealCombatEventsHandler=MikSBT.CombatEventsHandler
    MikSBT.CombatEventsHandler=function(e) local c={} for k,v in pairs(e) do c[k]=v end table.insert(sent,c) end
    calls={}
    ''')
    return lua
