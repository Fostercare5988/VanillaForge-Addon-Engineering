"""Self-contained Lua model of MSBT for regression tests.

Loads every TOC Lua file, including the ForgeUI settings window, into lupa with
mocked ClassicAPI globals and a small stateful widget model (checked state,
text, values, clicks, show/hide scripts). It needs no client MPQs. Lua 5.0
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

CORE_SKIP = set()


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
CLASSIC_API_VERSION=11707;  -- ClassicAPI only: no SuperWoW or NamPower globals
now=1; event=nil; this=nil; cvars={}; calls={}; frames={};
local function count(name) calls[name]=(calls[name] or 0)+1 end

-- Minimal widget model: every unknown method is a no-op; event registration is recorded.
local Widget={}
local function Run(w,script,...) local f=w.scripts[script]; if f then local old=this; this=w; f(w,...); this=old end end
function Widget:RegisterEvent(e) self.events[e]=true end
function Widget:UnregisterEvent(e) self.events[e]=nil end
function Widget:UnregisterAllEvents() for k in pairs(self.events) do self.events[k]=nil end end
function Widget:SetScript(k,f) self.scripts[k]=f end
function Widget:GetScript(k) return self.scripts[k] end
function Widget:GetName() return self.name end
function Widget:GetParent() return self.parent end
function Widget:SetParent(p) self.parent=p end
function Widget:IsVisible() return self.shown end
function Widget:IsShown() return self.shown end
function Widget:Show() if not self.shown then self.shown=true; Run(self,"OnShow") end end
function Widget:Hide() if self.shown then self.shown=false; Run(self,"OnHide") end end
function Widget:CreateTexture(name) local t=NewWidget(name,"Texture",self); t.shown=true; return t end
function Widget:CreateFontString(name) local t=NewWidget(name,"FontString",self); t.shown=true; return t end
function Widget:SetFontString(fs) self.fontString=fs end
function Widget:GetFontString() return self.fontString end
function Widget:SetText(t) self.text=t; if self.fontString then self.fontString:SetText(t) end; if self.kind=="EditBox" then Run(self,"OnTextChanged") end end
function Widget:GetText() return self.text or "" end
function Widget:SetTextColor(r,g,b) self.color={r,g,b} end
function Widget:SetChecked(v) self.checked=(v and v~=0) and 1 or nil end
function Widget:GetChecked() return self.checked end
function Widget:SetMinMaxValues(a,b) self.min,self.max=a,b end
function Widget:SetValue(v) self.value=v; Run(self,"OnValueChanged") end
function Widget:GetValue() return self.value or 0 end
function Widget:Enable() self.disabled=nil end
function Widget:Disable() self.disabled=true end
function Widget:IsEnabled() return not self.disabled and 1 or nil end
function Widget:SetWidth(v) self.width=v end
function Widget:SetHeight(v) self.height=v end
function Widget:GetWidth() return self.width or 0 end
function Widget:GetHeight() return self.height or 0 end
function Widget:GetFrameLevel() return 1 end
function Widget:SetFocus() self.focus=true end
function Widget:ClearFocus() if self.focus then self.focus=nil; Run(self,"OnEditFocusLost") end end
-- A player click: a checkbutton toggles before OnClick, as natively.
function Widget:Click()
  if self.disabled then return end
  if self.kind=="CheckButton" then self:SetChecked(not self.checked) end
  Run(self,"OnClick")
end
function Widget:PressEnter() Run(self,"OnEnterPressed") end
function Widget:PressEscape() Run(self,"OnEscapePressed") end
-- Unknown methods (capitalised keys) are no-ops; unknown fields stay nil.
local function NoOp() end
local WidgetMeta={__index=function(t,k) return Widget[k] or (type(k)=="string" and string.find(k,"^%u") and NoOp) or nil end}
function NewWidget(name,kind,parent)
  local w=setmetatable({name=name,kind=kind,parent=parent,events={},scripts={},shown=false},WidgetMeta)
  table.insert(frames,w)
  if name then _G[name]=w end
  return w
end
function CreateFrame(kind,name,parent) local w=NewWidget(name,kind,parent); w.shown=true; return w end
UIParent=NewWidget("UIParent"); UIParent.shown=true
GameTooltip=NewWidget("GameTooltip")
function ShowUIPanel(f) f:Show() end
function HideUIPanel(f) f:Hide() end
-- ColorPickerFrame as the 1.12 FrameXML drives it: selecting a color calls func;
-- Okay calls func and hides; Cancel calls cancelFunc(previousValues) and hides.
ColorPickerFrame=NewWidget("ColorPickerFrame")
function ColorPickerFrame:SetColorRGB(r,g,b) self.r,self.g,self.b=r,g,b; if self.func then self.func() end end
function ColorPickerFrame:GetColorRGB() return self.r,self.g,self.b end
function PickerOkay() if ColorPickerFrame.func then ColorPickerFrame.func() end; HideUIPanel(ColorPickerFrame) end
function PickerCancel() if ColorPickerFrame.cancelFunc then ColorPickerFrame.cancelFunc(ColorPickerFrame.previousValues) end; HideUIPanel(ColorPickerFrame) end
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
function CombatLogGetCurrentEventInfo() count("CombatLogGetCurrentEventInfo"); return unpack(cleu,1,cleu.n) end
-- One combat log event: subevent, source GUID/name, dest GUID/name, then the
-- subevent's own values (position 12 on), as ClassicAPI documents them.
function CL(sub, src, srcName, dst, dstName, ...)
  local a={n=select("#",...),...}
  local flags = (dst=="0xPLAYER" or dst=="0xPET") and 0x511 or 0x548
  Fire("COMBAT_LOG_EVENT_UNFILTERED", 1, sub, false, src, srcName, 0x511, 0, dst, dstName, flags, 0, unpack(a,1,a.n))
end

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
spellNamesMock={}
function GetSpellInfo(id) return spellNamesMock[id] or "Spell"..id,"Rank 1","Interface\\Icons\\Spell"..id end
function GetSpellIdForName(n) count("GetSpellIdForName") return 0 end
function GetItemInfo(n) count("GetItemInfo") end
function GetFactionInfoByID(id) return "Faction"..id end
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
    """Boot the core files like the client: TOC files, XML OnLoad, ADDON_LOADED, PEW.

    saved: optional Lua source that sets MikSBT_Save before ADDON_LOADED.
    """
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(BOOT)
    lua.execute("MCEHEventFrame=NewWidget('MCEHEventFrame'); MSBTEventFrame=NewWidget('MSBTEventFrame')")
    # Each file runs like the client loads it: (addonName, shared namespace).
    load_file = lua.eval('''function(source, name)
      ADDON_NS = ADDON_NS or {}
      local chunk = assert(loadstring(source, "@" .. name))
      chunk("MikScrollingBattleText", ADDON_NS)
    end''')
    for name in toc_lua_files():
        load_file(lua50((ROOT / name).read_text("utf-8-sig")), name)
    lua.execute('''
    MCEHEventFrame:SetScript("OnEvent", function() MikCEH.OnEvent() end)
    MSBTEventFrame:SetScript("OnEvent", function() MikSBT.OnEvent() end)
    this=MCEHEventFrame; MikCEH.OnLoad()
    this=MSBTEventFrame; MikSBT.OnLoad()
    ''')
    if saved is not None:
        lua.execute(saved)
    lua.execute('''
    Fire("ADDON_LOADED","MikScrollingBattleText")
    Fire("PLAYER_ENTERING_WORLD")
    -- Record what reaches the display layer; keep the real handler reachable.
    sent={}; RealCombatEventsHandler=MikSBT.CombatEventsHandler
    MikSBT.CombatEventsHandler=function(e) local c={} for k,v in pairs(e) do c[k]=v end table.insert(sent,c) end
    calls={}
    ''')
    return lua
