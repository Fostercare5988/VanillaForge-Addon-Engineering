"""Regressions for the six MSBT audit findings (F1-F6, 12 Oct 2026).

Since MSBT 1.2.0 the settings window is ForgeUI; the tests drive it through the
_fbt_runtime widget model (clicks, checked state, text). The color picker mock
follows the 1.12 FrameXML contract: selecting calls func, Okay calls func and
hides, Cancel calls cancelFunc(previousValues). Not in-game proof.
Requires VANILLAFORGE_ADDON_ROOT=<AddOns>/MikScrollingBattleText and lupa.
"""
import unittest

import _fbt_runtime as m


class AuraStackChanges(unittest.TestCase):  # F1
    def test_stack_decrease_is_not_a_fade(self):
        l = m.runtime()
        l.execute('''
        sent={}; CL("SPELL_AURA_REMOVED_DOSE","0xENEMY","Twin","0xPLAYER","Hero",123,"Spell123",1,"BUFF",2); assert(#sent==0, "stack decrease faded");
        sent={}; CL("SPELL_AURA_REMOVED","0xENEMY","Twin","0xPLAYER","Hero",123,"Spell123",1,"BUFF");
        assert(#sent==1 and sent[1].NotificationType==FBT.Combat.NOTIFICATIONTYPE_BUFF_FADE, "removal lost");
        sent={}; CL("SPELL_AURA_REMOVED","0xENEMY","Twin","0xOTHER","Ally",123,"Spell123",1,"BUFF"); assert(#sent==0, "foreign unit");
        sent={}; CL("SPELL_AURA_APPLIED_DOSE","0xENEMY","Twin","0xPLAYER","Hero",123,"Spell123",1,"BUFF",3); assert(#sent==1); -- gains unchanged
        ''')


class NotificationFontOwner(unittest.TestCase):  # F2
    def test_event_font_editor_inherits_from_its_own_area(self):
        l = m.runtime()
        l.execute('''
        local d=FBT.CurrentProfile.DisplaySettings
        d.Incoming.FontSettings.Normal.FontSize=22; d.Outgoing.FontSettings.Normal.FontSize=20; d.Notification.FontSettings.Normal.FontSize=34
        local rows={[3]="Incoming",[4]="Outgoing",[5]="Notification"}
        local expect={[3]=22,[4]=20,[5]=34}
        for tab=3,5 do
          FBT.Options.ShowTab(tab); getglobal("FBT_"..rows[tab].."Row1Font"):Click()
          assert(FBT_FontNormalSize:GetValue()==expect[tab], "tab "..tab.." size "..tostring(FBT_FontNormalSize:GetValue()))
        end
        -- Stop inheriting on the Notices row: the event keeps the Notification size.
        assert(FBT_FontNormalInheritSize:GetChecked())
        FBT_FontNormalInheritSize:Click()
        assert(FBT.CurrentProfile.EventSettings.MSBT_EVENTTYPE_NOTIFICATION_DEBUFF.FontSettings.Normal.FontSize==34)
        ''')


class DisabledGameDamage(unittest.TestCase):  # F3
    def test_disabled_msbt_keeps_native_damage_visible(self):
        l = m.runtime()
        l.execute('''
        cvars={}
        FBT.CurrentProfile.ShowGameDamage=false; FBT.SetOptionUserDisabled(true); assert(cvars.CombatDamage=="1")
        for tab=1,8 do FBT.Options.ShowTab(tab) end
        FBT.Options.Toggle(); FBT.Options.Toggle()
        assert(cvars.CombatDamage=="1", "opening settings hid native damage")
        assert(FBT.CurrentProfile.ShowGameDamage==false, "saved preference changed")
        FBT.Options.ShowTab(1); FBT_Enabled:Click(); assert(not FostercareBattleTextDB.UserDisabled and cvars.CombatDamage=="0")
        FBT_ShowGameDamage:Click(); assert(cvars.CombatDamage=="1")
        FBT_ShowGameDamage:Click(); assert(cvars.CombatDamage=="0")
        FBT_Enabled:Click(); assert(FostercareBattleTextDB.UserDisabled and cvars.CombatDamage=="1")
        ''')


class PickerProfileOwner(unittest.TestCase):  # F4
    def setup_picker(self):
        l = m.runtime()
        l.execute('''
        FBT.CreateProfile("Second")
        first=FBT.CurrentProfile.EventSettings.MSBT_EVENTTYPE_INCOMING_DAMAGE.FontSettings.Color; first.r,first.g,first.b=0.1,0.2,0.3
        second=FostercareBattleTextDB.Profiles.Second.EventSettings.MSBT_EVENTTYPE_INCOMING_DAMAGE.FontSettings.Color; second.r,second.g,second.b=0.7,0.8,0.9
        FBT.Options.ShowTab(3); FBT_IncomingRow1Color:Click()
        assert(ColorPickerFrame:IsShown())
        ColorPickerFrame:SetColorRGB(0.4,0.5,0.6); assert(first.r==0.4 and second.r==0.7)
        ''')
        return l

    def load_second(self, l):
        l.execute('''
        FBT.Options.ShowTab(8)
        for i=1,10 do local row=getglobal("FBT_ProfileRow"..i); if row.name=="Second" then getglobal("FBT_ProfileRow"..i.."Use"):Click() end end
        assert(FostercareBattleTextCharDB.CurrentProfile=="Second")
        ''')

    def test_profile_load_retires_picker_and_restores_owner(self):
        l = self.setup_picker(); self.load_second(l)
        l.execute('''
        assert(not ColorPickerFrame:IsShown(), "picker left open")
        assert(second.r==0.7 and second.g==0.8 and second.b==0.9, "second profile changed")
        assert(first.r==0.1 and first.g==0.2 and first.b==0.3, "first profile not restored")
        ''')

    def test_stale_ok_and_cancel_do_not_cross_profiles(self):
        for button in ("PickerOkay", "PickerCancel"):
            l = self.setup_picker(); self.load_second(l)
            l.execute('ColorPickerFrame:Show(); ' + button + '(); '
                      'assert(second.r==0.7 and second.g==0.8 and second.b==0.9, "' + button + ' wrote second")')

    def test_same_profile_ok_and_cancel(self):
        l = self.setup_picker()
        l.execute('PickerOkay(); assert(first.r==0.4 and second.r==0.7)')
        l = self.setup_picker()
        l.execute('PickerCancel(); assert(first.r==0.1 and first.b==0.3 and second.r==0.7)')

    def test_closing_options_keeps_choice(self):
        l = self.setup_picker()
        l.execute('FBT.Options.Toggle(); assert(not ColorPickerFrame:IsShown() and first.r==0.4)')

    def test_foreign_picker_untouched(self):
        l = self.setup_picker()
        l.execute('''
        PickerOkay()
        foreign=0; ColorPickerFrame.func=function() foreign=foreign+1 end; ColorPickerFrame.cancelFunc=nil; ColorPickerFrame:Show()
        FBT.Options.ShowTab(8); FBT_ProfileReset:Click()
        assert(ColorPickerFrame:IsShown(), "another addon's picker was closed")
        ''')


class ExternalColorUnits(unittest.TestCase):  # F5
    def test_public_display_takes_0_255_colors(self):
        # FostercareBattleText.DisplayMessage, the public call, takes 0-255 channels.
        l = m.runtime()
        l.execute('''
        local function find(t) for i=1,20 do local f=FBT.scrollAreas.Notification.Slots[i].FontObject; if f.text==t then return f.color end end end
        FostercareBattleText.DisplayMessage("mid",FBT.DISPLAYTYPE_NOTIFICATION,false,0.2*255,0.5*255,0.8*255); local c=find("mid")
        assert(c and math.abs(c[1]-0.2)<1e-9 and math.abs(c[2]-0.5)<1e-9 and math.abs(c[3]-0.8)<1e-9, "wrong units")
        FBT.DisplayMessage("default",FBT.DISPLAYTYPE_NOTIFICATION,false); c=find("default")
        assert(c[1]==1 and c[2]==1 and c[3]==1, "default white")
        FBT.DisplayMessage("bad",FBT.DISPLAYTYPE_NOTIFICATION,false,300,-1,128); c=find("bad")
        assert(c[1]==1 and c[2]==1 and math.abs(c[3]-128/255)<1e-9)
        ''')


class ManaEnableBaseline(unittest.TestCase):  # F6
    def test_first_gain_after_enable(self):
        for initial, off in ((100, 20), (20, 70)):
            l = m.runtime()
            l.globals().initialMana, l.globals().offMana = initial, off
            l.execute('''
            for _,t in pairs(FBT.CurrentProfile.Triggers) do
              if t.TriggerSettings.TriggerType==FBT.Combat.TRIGGERTYPE_SELF_MANA then t.EventSettings.Show=false end end
            units.player.mana=initialMana; FBT.RegisterTriggers()
            local function ManaEvent() now=now+1; Fire("UNIT_POWER_UPDATE","player","MANA") end
            local function gains() local g={} for _,e in ipairs(sent) do if e.NotificationType==FBT.Combat.NOTIFICATIONTYPE_POWER_GAIN then table.insert(g,e.Amount) end end return g end
            units.player.mana=offMana; ManaEvent()
            FBT.Options.ShowTab(1); FBT_ShowAllManaGains:Click()
            sent={}; units.player.mana=offMana+5; ManaEvent(); local g=gains(); assert(#g==1 and g[1]==5, "first gain "..tostring(g[1]))
            sent={}; units.player.mana=offMana+7; ManaEvent(); g=gains(); assert(#g==1 and g[1]==2)
            FBT_ShowAllManaGains:Click(); sent={}; units.player.mana=offMana+9; ManaEvent(); assert(#gains()==0)
            ''')


if __name__ == "__main__":
    unittest.main(verbosity=2)
