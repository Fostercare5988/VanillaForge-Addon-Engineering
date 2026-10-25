"""XML-derived control tree and extracted deployed FrameXML callback integration."""
import copy
import xml.etree.ElementTree as ET
from _replay_runtime import ROOT, NATIVE

def controls(lua):
    namespace={'ui':'http://www.blizzard.com/wow/ui/'}
    templates={}
    for path in [NATIVE/'UIPanelTemplates.xml',NATIVE/'OptionsFrameTemplates.xml',NATIVE/'UIDropDownMenu.xml',ROOT/'MSBTOptions.xml']:
        for e in ET.parse(path).getroot():
            if e.get('virtual')=='true':templates[e.get('name')]=e
    def tag(e):return e.tag.split('}')[-1]
    def make(element,parent=None,name_override=None,active=()):
        name=name_override or element.get('name')
        if name and '$parent' in name:
            name=name.replace('$parent', parent.name if parent else '')
        kind=tag(element)
        frame=lua.globals().CreateFrame(kind,name,parent)
        def apply(e,chain=()):
            for inherited in (e.get('inherits') or '').split(','):
                if inherited in templates and inherited not in chain:
                    apply(templates[inherited],chain+(inherited,))
            for child in e:
                t=tag(child)
                if t=='Size':
                    d=next(iter(child));frame.width=float(d.get('x',640));frame.height=float(d.get('y',440))
                elif t=='Frames':
                    for item in child:make(item,frame)
                elif t=='Layers':
                    for layer in child:
                        for item in layer:make(item,frame)
                elif t in ('NormalTexture','PushedTexture','DisabledTexture','HighlightTexture','CheckedTexture','ThumbTexture'):
                    region=copy.deepcopy(child);region.tag=region.tag.replace(t,'Texture');make(region,frame)
                elif t=='Scripts':
                    for script in child:
                        code=(script.text or '').strip()
                        # Native input helpers run in their own focused source integration below.
                        if code.startswith(('MikSBTOpt.','this:ClearFocus')):
                            frame.scripts[tag(script)]=lua.eval('function() '+code+' end')
            if e.get('hidden')=='true':frame.shown=False
            if e.get('id'):frame.id=int(e.get('id'))
        apply(element)
        return frame
    # Actual native inherited templates build child names, including check labels and slider text.
    for e in ET.parse(ROOT/'MSBTOptions.xml').getroot():
        if not e.get('virtual') and tag(e) in ('Frame','Button','ScrollFrame','Slider','EditBox','CheckButton'):
            make(e,lua.globals().UIParent)
    lua.execute('''
    function UIDropDownMenu_Initialize(frame,fn) frame.initialize=fn end
    function UIDropDownMenu_SetWidth(w,frame) frame.width=w end
    function UIDropDownMenu_AddButton(info) end
    function PanelTemplates_SetNumTabs(frame,n) frame.numTabs=n end
    function PanelTemplates_SetTab(frame,n) frame.selectedTab=n end
    function PanelTemplates_TabResize(pad,frame) end
    ''')
    return lua
