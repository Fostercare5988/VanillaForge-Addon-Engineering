"""Audit reproductions against unchanged installed MSBT, not a patch or FPS benchmark.

Assertions confirm the recorded existing defects and positive controls. A successful
run means the defects were reproduced; it does not mean they have been fixed.
The reused Lua 5.1 runner adapts only Lua 5.0 generic table iteration.
"""
from pathlib import Path
import hashlib
import json
import os
import sys
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
WORKSPACE = HERE.parents[2]
from _audit_runtime import ROOT as SOURCE, runtime, lua50, NATIVE
from _controls import controls
from _native_reference import output_directory, PROVENANCE


def tree_hashes():
    return {p.relative_to(SOURCE).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in SOURCE.rglob("*") if p.is_file() and ".git" not in p.relative_to(SOURCE).parts}


def table(value):
    if hasattr(value, "items"):
        return {str(k): table(v) for k, v in value.items()}
    return value


def settings_runtime():
    l = controls(runtime(options=True))
    root = ET.parse(SOURCE / "MSBTOptions.xml").getroot()
    ns = {"ui": "http://www.blizzard.com/wow/ui/"}
    for template, global_name in (("MSBTButtonTemplate", "msbtButtonClick"), ("MSBTCheckTemplate", "msbtCheckClick")):
        code = root.find(f"*[@name='{template}']/ui:Scripts/ui:OnClick", ns).text
        l.globals()[global_name] = l.eval("function() " + code + " end")
    l.execute("function GetNampowerVersion() return 4,6,2 end; this=MSBTFrameOptions; MikSBTOpt.Init(); MikSBTOpt.isInitialized=true;")
    return l


def aura_reduction():
    l = runtime()
    l.execute('''
    auraResults={};
    for _,eventName in ipairs({"BUFF_REMOVED_SELF","DEBUFF_REMOVED_SELF"}) do
      sent={}; Emit(eventName,"0xPLAYER",1,123,2,60,0,2);
      assert(#sent==1 and sent[1].NotificationType==MikCEH.NOTIFICATIONTYPE_BUFF_FADE);
      auraResults[eventName]={remainingStacks=2,state=2,expectedFadeEvents=0,observedFadeEvents=#sent};
      sent={}; Emit(eventName,"0xPLAYER",1,123,0,60,0,1);
      assert(#sent==1 and sent[1].NotificationType==MikCEH.NOTIFICATIONTYPE_BUFF_FADE);
      auraResults[eventName].trueRemovalControl=#sent;
    end
    ''')
    # Also exercise the complete notification/display pipeline, without capture SendEvent.
    full = runtime(capture=False)
    full.execute('''
    displayed={};function MikSBT.AddAnimation(e) table.insert(displayed,{EventType=e.EventType,EffectName=e.EffectName}) end;
    Emit("BUFF_REMOVED_SELF","0xPLAYER",1,123,2,60,0,2);
    assert(#displayed==1 and displayed[1].EventType=="MSBT_EVENTTYPE_NOTIFICATION_BUFF_FADE");
    ''')
    return {"cases": table(l.globals().auraResults), "completePipelineFalseFade": len(full.globals().displayed)}


def notification_font_owner():
    l = settings_runtime()
    l.execute('''
    MikSBT.CurrentProfile.DisplaySettings.Incoming.FontSettings.Normal.FontSize=22;
    MikSBT.CurrentProfile.DisplaySettings.Outgoing.FontSettings.Normal.FontSize=20;
    MikSBT.CurrentProfile.DisplaySettings.Notification.FontSettings.Normal.FontSize=34;
    fontResults={};
    for tab=2,4 do
      MikSBTOpt.TabOnClick(tab);
      local row=getglobal("MSBTFrameOptionsTab"..tab.."FrameEvent1");
      this=getglobal(row:GetName().."EditFontSettingsButton");msbtButtonClick();
      fontResults[tostring(tab)]={eventType=row.EventType,recordedArea=row.EventArea,inheritedSize=MSBTFontSettingsFrame.InheritedFontSize};
    end
    assert(fontResults["2"].inheritedSize==22 and fontResults["3"].inheritedSize==20);
    assert(fontResults["4"].recordedArea=="Outgoing" and fontResults["4"].inheritedSize==20);
    local eventType=MSBTFrameOptionsTab4FrameEvent1.EventType;
    this=MSBTFontSettingsFrameInheritFontSizeCheckbox;this:SetChecked(false);msbtCheckClick();
    fontResults["4"].persistedOverride=MikSBT.CurrentProfile.EventSettings[eventType].FontSettings.Normal.FontSize;
    fontResults["4"].expectedInheritedSize=34;
    assert(fontResults["4"].persistedOverride==20);
    ''')
    return table(l.globals().fontResults)


def disabled_damage_owner():
    l = settings_runtime()
    l.execute('''
    cvars={};writes={};function SetCVar(k,v) cvars[k]=tostring(v);table.insert(writes,{k=k,v=tostring(v)}) end;
    MikSBT.CurrentProfile.ShowGameDamage=false;MikSBT.SetOptionUserDisabled(true);
    assert(cvars.CombatDamage=="1");
    damageResult={afterDisable=cvars.CombatDamage,showGameDamage=MikSBT.CurrentProfile.ShowGameDamage};
    -- This is the actual OnShow refresh path after options have initialized.
    this=MSBTFrameOptions;MikSBTOpt.OnShow();
    damageResult.afterOptionsShown=cvars.CombatDamage;damageResult.userDisabled=MikSBT_Save.UserDisabled;
    assert(MikSBT_Save.UserDisabled and cvars.CombatDamage=="0");
    MikSBT.SetOptionUserDisabled(false);MikSBTOpt.PopulateProfileOptions();
    damageResult.enabledFalseControl=cvars.CombatDamage;assert(cvars.CombatDamage=="0");
    MikSBT.SetOptionShowGameDamage(true);MikSBTOpt.PopulateProfileOptions();
    damageResult.enabledTrueControl=cvars.CombatDamage;assert(cvars.CombatDamage=="1");
    ''')
    return table(l.globals().damageResult)


def native_picker(l):
    """Execute deployed open/select/cancel callbacks with explicit widget methods."""
    source = (NATIVE / "UIDropDownMenu.lua").read_text("utf-8-sig")
    start = source.index("function UIDropDownMenuButton_OpenColorPicker(")
    end = source.index("\nfunction ", start + 10)
    l.execute(lua50(source[start:end]))
    root = ET.parse(NATIVE / "ColorPickerFrame.xml").getroot()
    ns = {"ui": "http://www.blizzard.com/wow/ui/"}
    select = root.find("ui:ColorSelect", ns)
    onselect = select.find("ui:Scripts/ui:OnColorSelect", ns).text
    cancel = select.find("ui:Frames/ui:Button[@name='ColorPickerCancelButton']/ui:Scripts/ui:OnClick", ns).text
    okay = select.find("ui:Frames/ui:Button[@name='ColorPickerOkayButton']/ui:Scripts/ui:OnClick", ns).text
    l.globals().nativeColorSelect = l.eval("function() " + onselect + " end")
    l.globals().nativeCancelClick = l.eval("function() " + cancel + " end")
    l.globals().nativeOkayClick = l.eval("function() " + okay + " end")
    l.execute('''
    ColorPickerFrame=CreateFrame("Frame","ColorPickerFrame",UIParent);ColorPickerFrame:Hide();
    ColorSwatch=CreateFrame("Texture","ColorSwatch",ColorPickerFrame);
    ColorPickerCancelButton=CreateFrame("Button","ColorPickerCancelButton",ColorPickerFrame);
    ColorPickerOkayButton=CreateFrame("Button","ColorPickerOkayButton",ColorPickerFrame);
    function CloseMenus() end;
    -- Deployed ShowUIPanel directly shows frames without a UIPanelWindows area.
    function ShowUIPanel(frame) frame:Show() end;function HideUIPanel(frame) frame:Hide() end;
    function ColorPickerFrame:GetColorRGB() return self.r,self.g,self.b end;
    function ColorPickerFrame:SetColorRGB(r,g,b)
      self.r,self.g,self.b=r,g,b;local old=this;this=self;arg1,arg2,arg3=r,g,b;nativeColorSelect();this=old;
    end;
    ''')


def picker_profile_owner():
    results = {}
    for operation in ("accept", "cancel"):
        l = settings_runtime()
        native_picker(l)
        l.execute('''
        MikSBT.CreateProfile("Second");
        colorPath="EventSettings.MSBT_EVENTTYPE_INCOMING_DAMAGE.FontSettings.Color";
        local first=MikSBT.CurrentProfile.EventSettings.MSBT_EVENTTYPE_INCOMING_DAMAGE.FontSettings.Color;
        first.r,first.g,first.b=0.1,0.2,0.3;
        local second=MikSBT_Save.Profiles.Second.EventSettings.MSBT_EVENTTYPE_INCOMING_DAMAGE.FontSettings.Color;
        second.r,second.g,second.b=0.7,0.8,0.9;
        MikSBTOpt.TabOnClick(2);this=MSBTFrameOptionsTab2FrameEvent1ColorSwatch;this.scripts.OnClick();
        ColorPickerFrame:SetColorRGB(0.4,0.5,0.6);
        assert(first.r==0.4 and second.r==0.7); -- same-owner positive control
        -- Actual General page and Load Profile button, while the native picker remains open.
        MikSBTOpt.TabOnClick(1);MSBTFrameOptionsTab1FrameProfileDropdown.selectedValue="Second";
        this=MSBTFrameOptionsTab1FrameLoadProfileButton;msbtButtonClick();
        assert(MikSBT_Save.CurrentProfile=="Second" and ColorPickerFrame:IsShown());
        firstColor=first;secondColor=second;
        ''')
        if operation == "accept":
            l.execute('''this=ColorPickerOkayButton;nativeOkayClick();assert(secondColor.r==0.4);''')
        else:
            l.execute('''this=ColorPickerCancelButton;nativeCancelClick();assert(secondColor.r==0.1);''')
        results[operation] = {
            "expectedSecondProfile": {"r": 0.7, "g": 0.8, "b": 0.9},
            "observedSecondProfile": table(l.globals().secondColor),
            "firstProfileAfter": table(l.globals().firstColor),
        }
    return results


def external_color_units():
    l = runtime(capture=False)
    bigwigs = SOURCE.parent / "BigWigs/Plugins/Messages.lua"
    source = bigwigs.read_text("utf-8-sig")
    start = source.index("function BigWigsMessages:BigWigs_Message(")
    end = source.index("\nfunction ", start + 10)
    l.execute('''
    L=setmetatable({}, {__index=function(t,k) return k end});
    BigWigsMessages={db={profile={display="Mik's Scrolling Battle Text"}}};
    ''')
    l.execute(lua50(source[start:end]))
    l.execute('''
    BigWigsMessages:BigWigs_Message("audit-colored-warning",{r=0.2,g=0.5,b=0.8});
    observedColor=nil;
    for i=1,20 do local font=getglobal("MSBTFrameNotificationText"..i);
      if font.text=="audit-colored-warning" then observedColor=font.color end;
    end;
    assert(observedColor and observedColor[1]==51 and observedColor[2]==127.5 and observedColor[3]==204);
    ''')
    return {"caller": str(bigwigs), "callerSha256": hashlib.sha256(bigwigs.read_bytes()).hexdigest(),
            "expectedSetTextColor": [0.2, 0.5, 0.8], "observedSetTextColor": list(l.globals().observedColor.values()),
            "nativeClampingOrAppearanceMeasured": False}


def mana_enable_baseline():
    results = []
    for initial, while_off in ((100, 20), (20, 70)):
        l = settings_runtime()
        l.globals().initialMana, l.globals().offMana = initial, while_off
        l.execute('''
        for _,trigger in pairs(MikSBT.CurrentProfile.Triggers) do
          if trigger.TriggerSettings.TriggerType==MikCEH.TRIGGERTYPE_SELF_MANA then trigger.EventSettings.Show=false end;
        end;
        units.player.mana=initialMana;MikSBT.RegisterTriggers();
        function ManaEvent() now=now+1;event="UNIT_MANA";arg1="player";MikCEH.OnEvent() end;
        units.player.mana=offMana;ManaEvent();
        this=MSBTFrameOptionsTab1FrameShowAllManaGainsCheckbox;this:SetChecked(true);msbtCheckClick();
        sent={};units.player.mana=offMana+5;ManaEvent();
        firstGains={};for _,e in ipairs(sent) do if e.NotificationType==MikCEH.NOTIFICATIONTYPE_POWER_GAIN then table.insert(firstGains,e.Amount) end end;
        sent={};units.player.mana=offMana+7;ManaEvent();
        assert(#sent==1 and sent[1].Amount=="2 "..MANA); -- subsequent gains work
        ''')
        observed = list(l.globals().firstGains.values())
        assert observed == ([] if initial == 100 else ["55 Mana"]), observed
        results.append({"previousBaseline": initial, "manaWhenEnabled": while_off,
                        "firstObservedIncrease": 5, "expectedFirstGain": "5 Mana",
                        "observedFirstGainMessages": observed, "subsequentTwoManaGainControl": True})
    return results


def merge_cardinality():
    results = []
    for count in (1, 10, 50, 200):
        for distinct in (False, True):
            l = runtime()
            l.globals().sampleCount = count
            l.globals().distinct = distinct
            l.execute('''
            local pending={};local merged={};mergeData={UnmergedEvents=pending,MergedEvents=merged};
            for i=1,sampleCount do pending[i]={EventType="MSBT_EVENTTYPE_OUTGOING_SPELL_DAMAGE",EffectName="Spell",SpellId=distinct and i or 123,Amount=1} end;
            local originalIpairs=ipairs;iteratorVisits=0;
            function ipairs(t)
              local nextFn,state,index=originalIpairs(t);
              if t~=merged then return nextFn,state,index end;
              return function(s,k) local a,b=nextFn(s,k);if a then iteratorVisits=iteratorVisits+1 end;return a,b end,state,index;
            end;
            MikSBT.MergeEvents(mergeData,pending,sampleCount);ipairs=originalIpairs;
            outputCount=#merged;comparisons=iteratorVisits-outputCount;total=0;
            for _,e in ipairs(merged) do total=total+e.Amount end;assert(total==sampleCount);
            ''')
            comparisons = l.globals().comparisons
            assert comparisons == (count * (count - 1) // 2 if distinct else max(0, count - 1))
            results.append({"inputs": count, "distinctSpellIds": distinct, "mergeCandidateVisits": comparisons,
                            "outputs": l.globals().outputCount, "amountConserved": l.globals().total})
    return results


def sticky_ui_writes():
    l = runtime()
    l.execute('''
    uiWrites={};local function count(method) return function() uiWrites[method]=(uiWrites[method] or 0)+1 end end;
    local font={SetPoint=count("font.SetPoint"),SetAlpha=count("font.SetAlpha"),SetTextHeight=count("font.SetTextHeight")};
    local texture={SetAlpha=count("icon.SetAlpha"),SetWidth=count("icon.SetWidth"),SetHeight=count("icon.SetHeight")};
    local info={FontObject=font,Texture=texture,IsSticky=true,IsCrit=false,LastUpdated=0,FontSize=26,
      AnchorPoint="BOTTOM",PositionX=0,PositionY=0,IsActive=true};
    -- 100 frames entirely inside the unchanged hold phase, after the entry animation.
    for i=1,100 do now=0.5+i/100;MikSBT.DoAnimation(info,{}) end;
    for _,n in pairs(uiWrites) do assert(n==100) end;
    ''')
    values = table(l.globals().uiWrites)
    return {"frames": 100, "unchangedNonCriticalStickyWithIcon": values,
            "totalWidgetWrites": sum(values.values()), "nativeMillisecondsMeasured": False}


def main():
    before = tree_hashes()
    findings = {
        "F1_aura_stack_decrease": aura_reduction(),
        "F2_notification_font_owner": notification_font_owner(),
        "F3_disabled_damage_owner": disabled_damage_owner(),
        "F4_picker_profile_owner": picker_profile_owner(),
        "F5_external_color_units": external_color_units(),
        "F6_mana_enable_baseline": mana_enable_baseline(),
    }
    operations = {"merge": merge_cardinality(), "sticky": sticky_ui_writes()}
    assert tree_hashes() == before, "Installed source changed during read-only replays"
    report = {"source": str(SOURCE), "sourceFiles": len(before), "sourceUnchanged": True,
              "meaning": "Six existing defect reproductions confirmed; no fixes applied.",
              "findings": findings, "operationCounts": operations, "sourceHashes": before}
    report["nativeReferenceProvenance"] = PROVENANCE
    (output_directory() / "replay-results.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "sourceHashes"}, indent=2))


if __name__ == "__main__":
    main()
