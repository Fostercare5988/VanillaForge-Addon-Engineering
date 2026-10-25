"""Shared replay helpers for the 2026-10-12 regressions (options UI, native picker).

Reads the deployed FrameXML and GlobalStrings from the selected client's MPQs.
Requires VANILLAFORGE_ADDON_ROOT=<AddOns>/MikScrollingBattleText and lupa.
"""
import xml.etree.ElementTree as ET

from _replay_runtime import ROOT as SOURCE, runtime, lua50, NATIVE
from _replay_controls import controls


def settings_runtime():
    l = controls(runtime(options=True))
    root = ET.parse(SOURCE / "MSBTOptions.xml").getroot()
    ns = {"ui": "http://www.blizzard.com/wow/ui/"}
    for template, global_name in (("MSBTButtonTemplate", "msbtButtonClick"), ("MSBTCheckTemplate", "msbtCheckClick")):
        code = root.find(f"*[@name='{template}']/ui:Scripts/ui:OnClick", ns).text
        l.globals()[global_name] = l.eval("function() " + code + " end")
    l.execute("function GetNampowerVersion() return 4,6,2 end; this=MSBTFrameOptions; MikSBTOpt.Init(); MikSBTOpt.isInitialized=true;")
    return l


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
