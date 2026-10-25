"""Desired-behavior regressions for the six MSBT audit findings (F1-F6, 12 Oct 2026).

Eight tests fail against MSBT 92bb79b2 (plus the ClassicAPI 1.16.0 floor edits)
and pass on MSBT 1.0.1; two are positive controls that pass on both.
Requires VANILLAFORGE_ADDON_ROOT=<AddOns>/MikScrollingBattleText and lupa. Same Lua-model
harness as the audit replays: mocked DLL APIs, deployed picker callbacks; no native
widget, pointer or rendering proof.
"""
import unittest

# Replay helpers: deployed picker callbacks, BigWigs caller, native references
# read from the selected client's MPQs.
import _replay as a


class AuraStackChanges(unittest.TestCase):  # F1
    def test_stack_decrease_is_not_a_fade(self):
        import _msbt_runtime as m
        l = m.runtime()
        l.execute('''
        sent={}; CL("SPELL_AURA_REMOVED_DOSE","0xENEMY","Twin","0xPLAYER","Hero",123,"Spell123",1,"BUFF",2); assert(#sent==0, "stack decrease faded");
        sent={}; CL("SPELL_AURA_REMOVED","0xENEMY","Twin","0xPLAYER","Hero",123,"Spell123",1,"BUFF");
        assert(#sent==1 and sent[1].NotificationType==MikCEH.NOTIFICATIONTYPE_BUFF_FADE, "removal lost");
        sent={}; CL("SPELL_AURA_REMOVED","0xENEMY","Twin","0xOTHER","Ally",123,"Spell123",1,"BUFF"); assert(#sent==0, "foreign unit");
        sent={}; CL("SPELL_AURA_APPLIED_DOSE","0xENEMY","Twin","0xPLAYER","Hero",123,"Spell123",1,"BUFF",3); assert(#sent==1); -- gains unchanged
        ''')


class NotificationFontOwner(unittest.TestCase):  # F2
    def test_notification_rows_edit_notification_fonts(self):
        l = a.settings_runtime()
        l.execute('''
        local d=MikSBT.CurrentProfile.DisplaySettings;
        d.Incoming.FontSettings.Normal.FontSize=22;d.Outgoing.FontSettings.Normal.FontSize=20;d.Notification.FontSettings.Normal.FontSize=34;
        local expect={[2]=22,[3]=20,[4]=34};
        for tab=2,4 do MikSBTOpt.TabOnClick(tab);
          local row=getglobal("MSBTFrameOptionsTab"..tab.."FrameEvent1");
          this=getglobal(row:GetName().."EditFontSettingsButton");msbtButtonClick();
          assert(MSBTFontSettingsFrame.InheritedFontSize==expect[tab], "tab "..tab.." inherited "..tostring(MSBTFontSettingsFrame.InheritedFontSize));
        end
        assert(MSBTFrameOptionsTab4FrameEvent1.EventArea=="Notification");
        local eventType=MSBTFrameOptionsTab4FrameEvent1.EventType;
        this=MSBTFontSettingsFrameInheritFontSizeCheckbox;this:SetChecked(false);msbtCheckClick();
        assert(MikSBT.CurrentProfile.EventSettings[eventType].FontSettings.Normal.FontSize==34);
        ''')


class DisabledGameDamage(unittest.TestCase):  # F3
    def test_disabled_msbt_keeps_native_damage_visible(self):
        l = a.settings_runtime()
        l.execute('''
        cvars={};function SetCVar(k,v) cvars[k]=tostring(v) end;
        MikSBT.CurrentProfile.ShowGameDamage=false;MikSBT.SetOptionUserDisabled(true);assert(cvars.CombatDamage=="1");
        this=MSBTFrameOptions;MikSBTOpt.OnShow();assert(cvars.CombatDamage=="1","options refresh hid native damage");
        MikSBTOpt.PopulateProfileOptions();assert(cvars.CombatDamage=="1");
        assert(MikSBT.CurrentProfile.ShowGameDamage==false, "saved preference changed");
        MikSBT.SetOptionUserDisabled(false);assert(cvars.CombatDamage=="0");
        MikSBT.SetOptionShowGameDamage(true);assert(cvars.CombatDamage=="1");
        MikSBT.SetOptionShowGameDamage(false);assert(cvars.CombatDamage=="0");
        MikSBT.SetOptionUserDisabled(true);MikSBT.SetOptionShowGameDamage(false);assert(cvars.CombatDamage=="1");
        ''')


class PickerProfileOwner(unittest.TestCase):  # F4
    def setup_picker(self):
        l = a.settings_runtime()
        a.native_picker(l)
        l.execute('''
        MikSBT.CreateProfile("Second");
        first=MikSBT.CurrentProfile.EventSettings.MSBT_EVENTTYPE_INCOMING_DAMAGE.FontSettings.Color;first.r,first.g,first.b=0.1,0.2,0.3;
        second=MikSBT_Save.Profiles.Second.EventSettings.MSBT_EVENTTYPE_INCOMING_DAMAGE.FontSettings.Color;second.r,second.g,second.b=0.7,0.8,0.9;
        MikSBTOpt.TabOnClick(2);this=MSBTFrameOptionsTab2FrameEvent1ColorSwatch;this.scripts.OnClick();
        ColorPickerFrame:SetColorRGB(0.4,0.5,0.6);assert(first.r==0.4 and second.r==0.7);
        ''')
        return l

    def load_second(self, l):
        l.execute('''
        MikSBTOpt.TabOnClick(1);MSBTFrameOptionsTab1FrameProfileDropdown.selectedValue="Second";
        this=MSBTFrameOptionsTab1FrameLoadProfileButton;msbtButtonClick();assert(MikSBT_Save.CurrentProfile=="Second");
        ''')

    def test_profile_load_retires_picker_and_restores_owner(self):
        l = self.setup_picker(); self.load_second(l)
        l.execute('''
        assert(not ColorPickerFrame:IsShown(),"picker left open");
        assert(second.r==0.7 and second.g==0.8 and second.b==0.9,"second profile changed");
        assert(first.r==0.1 and first.g==0.2 and first.b==0.3,"first profile not restored");
        ''')

    def test_stale_ok_and_cancel_do_not_cross_profiles(self):
        for button in ("nativeOkayClick", "nativeCancelClick"):
            l = self.setup_picker(); self.load_second(l)
            l.execute('ColorPickerFrame:Show();this=ColorPickerOkayButton;' + button + '();'
                      'assert(second.r==0.7 and second.g==0.8 and second.b==0.9,"' + button + ' wrote second")')

    def test_same_profile_ok_and_cancel(self):
        l = self.setup_picker()
        l.execute('this=ColorPickerOkayButton;nativeOkayClick();assert(first.r==0.4 and second.r==0.7)')
        l = self.setup_picker()
        l.execute('this=ColorPickerCancelButton;nativeCancelClick();assert(first.r==0.1 and first.b==0.3 and second.r==0.7)')

    def test_closing_options_keeps_choice(self):
        l = self.setup_picker()
        l.execute('this=MSBTFrameOptions;MikSBTOpt.OnHide();assert(not ColorPickerFrame:IsShown() and first.r==0.4)')

    def test_foreign_picker_untouched(self):
        l = self.setup_picker()
        l.execute('''
        this=ColorPickerOkayButton;nativeOkayClick();
        foreign=0;ColorPickerFrame.func=function() foreign=foreign+1 end;ColorPickerFrame.cancelFunc=nil;ColorPickerFrame:Show();
        MikSBTOpt.TabOnClick(1);this=MSBTFrameOptionsTab1FrameResetProfileButton;msbtButtonClick();
        assert(ColorPickerFrame:IsShown(),"another addon's picker was closed");
        ''')


class ExternalColorUnits(unittest.TestCase):  # F5
    def test_bigwigs_intermediate_colors_are_normalized(self):
        l = a.runtime(capture=False)
        src = (a.SOURCE.parent / "BigWigs/Plugins/Messages.lua").read_text("utf-8-sig")
        s = src.index("function BigWigsMessages:BigWigs_Message("); e = src.index("\nfunction ", s + 10)
        l.execute('L=setmetatable({}, {__index=function(t,k) return k end});BigWigsMessages={db={profile={display="Mik\'s Scrolling Battle Text"}}};')
        l.execute(a.lua50(src[s:e]))
        l.execute('''
        local function find(t) for i=1,20 do local f=getglobal("MSBTFrameNotificationText"..i); if f.text==t then return f.color end end end
        BigWigsMessages:BigWigs_Message("mid",{r=0.2,g=0.5,b=0.8});local c=find("mid");
        assert(c and math.abs(c[1]-0.2)<1e-9 and math.abs(c[2]-0.5)<1e-9 and math.abs(c[3]-0.8)<1e-9,"wrong units");
        MikSBT.DisplayMessage("default",MikSBT.DISPLAYTYPE_NOTIFICATION,false);c=find("default");
        assert(c[1]==1 and c[2]==1 and c[3]==1,"default white");
        MikSBT.DisplayMessage("bad",MikSBT.DISPLAYTYPE_NOTIFICATION,false,300,-1,128);c=find("bad");
        assert(c[1]==1 and c[2]==1 and math.abs(c[3]-128/255)<1e-9);
        ''')


class ManaEnableBaseline(unittest.TestCase):  # F6
    def test_first_gain_after_enable(self):
        for initial, off in ((100, 20), (20, 70)):
            l = a.settings_runtime()
            l.globals().initialMana, l.globals().offMana = initial, off
            l.execute('''
            for _,t in pairs(MikSBT.CurrentProfile.Triggers) do
              if t.TriggerSettings.TriggerType==MikCEH.TRIGGERTYPE_SELF_MANA then t.EventSettings.Show=false end end;
            units.player.mana=initialMana;MikSBT.RegisterTriggers();
            function ManaEvent() now=now+1;event="UNIT_MANA";arg1="player";MikCEH.OnEvent() end;
            units.player.mana=offMana;ManaEvent();
            this=MSBTFrameOptionsTab1FrameShowAllManaGainsCheckbox;this:SetChecked(true);msbtCheckClick();
            local function gains() local g={};for _,e in ipairs(sent) do if e.NotificationType==MikCEH.NOTIFICATIONTYPE_POWER_GAIN then table.insert(g,e.Amount) end end;return g end
            sent={};units.player.mana=offMana+5;ManaEvent();local g=gains();assert(#g==1 and g[1]=="5 "..MANA,"first gain "..tostring(g[1]));
            sent={};units.player.mana=offMana+7;ManaEvent();g=gains();assert(#g==1 and g[1]=="2 "..MANA);
            this:SetChecked(false);msbtCheckClick();sent={};units.player.mana=offMana+9;ManaEvent();assert(#gains()==0);
            ''')


if __name__ == "__main__":
    unittest.main(verbosity=2)
