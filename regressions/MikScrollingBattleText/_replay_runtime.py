"""Private regression/integration evidence. Lua 5.1 runner adapts native 5.0 table iteration only.
Native widget types expose explicit methods; unsupported methods fail.
Source selection: VANILLAFORGE_ADDON_ROOT; run audit_replays.py beside this module.
"""
import re
from lupa.lua51 import LuaRuntime

from _replay_native import ROOT, NATIVE, GLOBAL_STRINGS

def lua50(s):
    return re.sub(r'for ([\w_, ]+) in ([\w.\[\]"\']+) do', r'for \1 in pairs(\2) do', s)

BOOT = r'''
CLASSIC_API_VERSION=11707; SUPERWOW_VERSION="2.2";
now=1; timers={}; scheduled=0; tickers=0; sent={}; messages={}; sounds=0;
units={player={guid="0xPLAYER",name="Hero",health=1000,max=1000,mana=100,maxmana=100,class="PRIEST"},
 pet={guid="0xPET",name="Wolf",health=500,max=500,class="WARRIOR"},
 target={guid="0xENEMY",name="Twin",health=1000,max=1000,class="MAGE"},
 other={guid="0xOTHER",name="Twin",health=500,max=1000,class="ROGUE"}}
function Resolve(u) if units[u] then return units[u] end; for _,v in pairs(units) do if v.guid==u then return v end end end
function UnitGUID(u) local v=Resolve(u); return v and v.guid end
function UnitExists(u) local v=Resolve(u); if v then return 1,v.guid end end
function UnitName(u) local v=Resolve(u); return v and v.name end
function UnitClass(u) local v=Resolve(u); return v and v.class,v and v.class end
function UnitIsPlayer(u) return u~="pet" and 1 or nil end
function UnitIsFriend(a,b) if b=="target" then return friendly end;return b=="player" and 1 or nil end
function UnitIsUnit(a,b) local x,y=Resolve(a),Resolve(b); return x and y and x.guid==y.guid and 1 or nil end
healthReads=0; nameReads=0; unitReads=0;
function UnitHealth(u) healthReads=healthReads+1; local v=Resolve(u); return v and v.health or 0 end
function UnitHealthMax(u) healthReads=healthReads+1; local v=Resolve(u); return v and v.max or 0 end
function UnitMana(u) return Resolve(u).mana or 0 end
function UnitManaMax(u) return Resolve(u).maxmana or 0 end
function UnitPowerType() return 0 end
function GetComboPoints() return 0 end
function GetTime() return now end
function GetLocale() return "enUS" end
function GetNampowerVersion() return 4,6,2 end
function SpellInfo(id) return "Spell"..id,"Rank1","Interface\\Icons\\Spell"..id end
function GetSpellInfo(id) return "Spell"..id,"Rank1","Interface\\Icons\\Spell"..id end
function GetSpellRecField(id,field) if field=="name" then return "Spell"..id end; return 1 end
function GetShapeshiftFormInfo() return "", "", 1 end
function GetAddOnMetadata(a,k) return "1.0.0" end
function GetCVar() return "0" end
function SetCVar() end
function PlaySoundFile() sounds=sounds+1 end
function PlaySound() end
function getglobal(n) return _G[n] end
strlower=string.lower; string.gfind=string.gmatch;
table.wipe=function(t) for k in pairs(t) do t[k]=nil end end
table.setn=function() end
bit={band=function(a,b) local r,p=0,1; while a>0 and b>0 do if a%2==1 and b%2==1 then r=r+p end; a=math.floor(a/2);b=math.floor(b/2);p=p*2 end; return r end}
SlashCmdList={}; UISpecialFrames={};
DEFAULT_CHAT_FRAME={AddMessage=function(self,m) table.insert(messages,m) end};
C_Timer={}
function C_Timer.NewTimer(delay,fn)
 scheduled=scheduled+1; local t={fn=fn,at=now+delay,cancelled=false};
 function t:Cancel() self.cancelled=true end
 table.insert(timers,t); return t;
end
function C_Timer.After(delay,fn) C_Timer.NewTimer(delay,fn) end
function C_Timer.NewTicker(delay,fn) tickers=tickers+1; return {fn=fn,Cancel=function(self) self.cancelled=true end} end
function Drain()
 local rounds=0;
 while #timers>0 do
  local pending=timers;timers={};rounds=rounds+1;assert(rounds<50,"timer loop");
  for _,t in ipairs(pending) do now=math.max(now,t.at); if not t.cancelled then t.fn() end end
 end
end
local Region={}
function Region:GetObjectType() return self.kind end
function Region:GetName() return self.name end
function Region:GetParent() return self.parent end
function Region:SetPoint(...) self.point={...} end
function Region:ClearAllPoints() self.point=nil end
function Region:Show() local was=self.shown;self.shown=true; if not was and self.scripts and self.scripts.OnShow then local old=this;this=self;self.scripts.OnShow();this=old end end
function Region:Hide() local was=self.shown;self.shown=false; if was and self.scripts and self.scripts.OnHide then local old=this;this=self; self.scripts.OnHide();this=old end end
function Region:IsShown() return self.shown and 1 or nil end
function Region:IsVisible() return self:IsShown() end
function Region:SetWidth(v) self.width=v end
function Region:SetHeight(v) self.height=v end
function Region:GetWidth() return self.width or 640 end
function Region:GetHeight() return self.height or 440 end
function Region:SetAlpha(v) self.alpha=v end
local Font={};setmetatable(Font,{__index=Region})
function Font:SetFont(...) self.font={...} end
function Font:GetFont() return self.font and unpack(self.font) end
function Font:SetText(t) self.text=t end
function Font:GetText() return self.text end
function Font:SetTextHeight(v) self.textheight=v end
function Font:SetTextColor(...) self.color={...} end
function Font:GetTextWidth() return #(self.text or "")*6 end
local Texture={};setmetatable(Texture,{__index=Region})
function Texture:SetTexture(t) self.texture=t end
function Texture:SetTexCoord(...) self.coord={...} end
function Texture:SetVertexColor(...) self.color={...} end
function Texture:SetDrawLayer(l) assert(l=="ARTWORK" or l=="OVERLAY");self.layer=l end
local Frame={};setmetatable(Frame,{__index=Region})
function Frame:RegisterEvent(e) self.events[e]=true end
function Frame:UnregisterEvent(e) self.events[e]=nil end
function Frame:UnregisterAllEvents() table.wipe(self.events) end
function Frame:SetScript(e,fn) self.scripts[e]=fn end
function Frame:GetRegions() return unpack(self.regions) end
function Frame:GetChildren() return unpack(self.children) end
function Frame:SetScale(v) self.scale=v end
function Frame:GetScale() return self.scale or 1 end
function Frame:SetClampedToScreen(v) self.clamped=v end
function Frame:SetBackdrop(v) self.backdrop=v end
function Frame:SetBackdropColor(...) self.bg={...} end
function Frame:SetBackdropBorderColor(...) self.border={...} end
function Frame:EnableMouse(v) self.mouse=v end
function Frame:EnableMouseWheel(v) self.mousewheel=v end
function Frame:StopMovingOrSizing() self.moving=false end
function Frame:Raise() end
function Frame:GetID() return self.id end
local Button={};setmetatable(Button,{__index=Frame})
function Button:Enable() self.enabled=true end
function Button:Disable() self.enabled=false end
function Button:SetText(v) self.text=v end
function Button:GetTextWidth() return #(self.text or "")*6 end
local Check={};setmetatable(Check,{__index=Button})
function Check:SetChecked(v) self.checked=(v and v~=0) and 1 or nil end
function Check:GetChecked() return self.checked end
function Check:GetCheckedTexture() return nil end
local Slider={};setmetatable(Slider,{__index=Frame})
function Slider:SetMinMaxValues(a,b) self.min,self.max=a,b end
function Slider:SetValueStep(v) self.step=v end
function Slider:SetValue(v) self.value=math.max(self.min or v,math.min(self.max or v,v)); local old=this;this=self;if self.scripts.OnValueChanged then self.scripts.OnValueChanged() elseif self.associatedVarPath then MikSBTOpt.SliderOnValueChanged() end;this=old end
function Slider:GetValue() return self.value end
local Edit={};setmetatable(Edit,{__index=Frame})
function Edit:SetText(v) self.text=tostring(v);local old=this;this=self;MikSBTOpt.EditboxOnTextChanged();this=old end
function Edit:GetText() return self.text end
function Edit:SetFocus() self.focus=true end
function Edit:ClearFocus() self.focus=false end
function CreateFrame(kind,name,parent)
 local methods=({Frame=Frame,Button=Button,CheckButton=Check,Slider=Slider,EditBox=Edit,ScrollFrame=Frame,FontString=Font,Texture=Texture})[kind];assert(methods,kind);
 local f=setmetatable({kind=kind,name=name,parent=parent,shown=true,events={},scripts={},regions={},children={}}, {__index=methods});
 if name then _G[name]=f end
 if parent then table.insert((kind=="FontString" or kind=="Texture") and parent.regions or parent.children,f) end
 return f;
end
function Frame:CreateTexture(name,layer) local f=CreateFrame("Texture",name);f.parent=self;table.insert(self.regions,f);return f end
UIParent=CreateFrame("Frame","UIParent");UIParent.width=1024;UIParent.height=768;
MCEHEventFrame=CreateFrame("Frame","MCEHEventFrame");MSBTEventFrame=CreateFrame("Frame","MSBTEventFrame");
for _,area in ipairs({"Incoming","Outgoing","Notification"}) do
 local f=CreateFrame("Frame","MSBTFrame"..area,UIParent);
 for i=1,20 do CreateFrame("FontString",f.name.."Text"..i,f) end
end
function Emit(name,...)
 event=name;arg1,arg2,arg3,arg4,arg5,arg6,arg7,arg8,arg9=unpack(arg or {...});
 -- Lua 5.1 test arguments; native 1.12 globals and callbacks are retained.
 arg1,arg2,arg3,arg4,arg5,arg6,arg7,arg8,arg9=...;
 MikCEH.OnNampowerEvent();
end
function UIDropDownMenu_GetSelectedValue(f) return f.selectedValue end
function UIDropDownMenu_SetSelectedValue(f,v) f.selectedValue=v end
function UIDropDownMenu_SetText(v,f) f.text=v end
function CloseDropDownMenus() end
function FauxScrollFrame_GetOffset(f) return f.offset or 0 end
function FauxScrollFrame_Update(f,total,page,height) end
'''

def toc_lua_files():
    lines=(ROOT/'MikScrollingBattleText.toc').read_text('utf-8-sig').splitlines()
    return [x.strip() for x in lines if x.strip().endswith('.lua') and not x.startswith('#')]

def runtime(core=True, options=False, capture=True):
    l=LuaRuntime(unpack_returned_tuples=True)
    l.execute(BOOT)
    for path in GLOBAL_STRINGS:
        l.execute(path.read_text('utf-8-sig'))
    files=toc_lua_files()
    for name in files[:files.index('MikCombatEventHelper.lua')+1]:
        l.execute(lua50((ROOT/name).read_text('utf-8-sig')))
    l.execute('MikCEH.OnLoad();MikCEH.Init();')
    if core:
        for name in files[files.index('MikCombatEventHelper.lua')+1:files.index('MSBTOptions.lua')]:
            l.execute(lua50((ROOT/name).read_text('utf-8-sig')))
        l.execute('MikSBT.Init();')
    if options:
        l.execute(lua50((ROOT/'MSBTOptions.lua').read_text('utf-8-sig')))
    if capture:
        l.execute('function MikCEH.SendEvent(e) local copy={};for k,v in pairs(e) do copy[k]=v end;table.insert(sent,copy) end')
    return l
