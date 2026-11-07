"""The GearRack regressions on the shared game model (wowkit).

Loads selected files of the addon at VANILLAFORGE_ADDON_ROOT with widget mocks.
Every frame the addon's XML names (template children included) exists as a mock
widget, so Lua that styles or drives XML frames runs as it would after load.
ClassicAPI's file varargs are supplied: each file gets ("GearRack", ns).

The mocks record colors, parents and frame levels. They do not prove how the
client draws a texture, which font a button uses or how a window looks.
"""
from pathlib import Path
import os
import wowkit

ROOT = Path(os.environ["VANILLAFORGE_ADDON_ROOT"])
SRC = ROOT / "src"

MOCK = r'''
messages = chat
CLASSIC_API_VERSION, SUPERWOW_VERSION = 11805, "2.2"
function GetNampowerVersion() return 4, 6, 2 end
function GetCastInfo() end
function GetSpellIdCooldown() end

-- Frame levels follow the parent; heights start at 20; colours are kept apart.
local make = newWidget
function newWidget(kind, name, parent)
    local w = make(kind, name, parent)
    w.height, w.level, w.calls = 20, parent and (parent.level + 1) or 1, {}
    return w
end
UIParent.level = 1
function Widget:SetParent(p) self.parent = p; self.level = p.level + 1 end
function Widget:SetFrameLevel(l) self.level = l end
function Widget:GetFrameLevel() return self.level end
function Widget:SetHitRectInsets(l, r, t, b) self.hitInsets = { l, r, t, b } end
function Widget:SetTextColor(r, g, b) self.textColor = { r, g, b } end
function Widget:SetHighlightTextColor(r, g, b) self.highlightColor = { r, g, b } end
function Widget:SetDisabledTextColor(r, g, b) self.disabledColor = { r, g, b } end
function Widget:CreateTexture(name, layer) local t = newWidget("Texture", name, self); t.layer = layer; return t end
function Widget:CreateFontString(name, layer) local f = newWidget("FontString", name, self); f.layer = layer; return f end
function Widget:SetInventoryItem(...) table.insert(self.calls, "SetInventoryItem") end
'''


# Children of the client templates GearRack inherits.
CLIENT_TEMPLATES = {
    "UICheckButtonTemplate": ["$parentText"],
    "ActionButtonTemplate": ["$parentIcon", "$parentCount", "$parentHotKey", "$parentName",
                             "$parentCooldown", "$parentBorder", "$parentNormalTexture", "$parentFlash"],
    "FauxScrollFrameTemplate": ["$parentScrollBar", "$parentScrollChildFrame"],
    "UIPanelScrollFrameTemplate": ["$parentScrollBar"],
}


class Env:
    def __init__(self, files):
        self.lua = wowkit.runtime()
        self.lua.execute(MOCK)
        make = self.lua.globals().newWidget
        for name, kind in wowkit.xml_frames(sorted(SRC.glob("*.xml")), CLIENT_TEMPLATES):
            if self.lua.globals()[name] is None:
                make(kind, name)
        self.ns = self.lua.table()
        loader = self.lua.eval('function(src, name, ns) local f = assert(loadstring(src, name)); return f("GearRack", ns) end')
        for f in files:
            loader((SRC / f).read_text(encoding="utf-8"), f, self.ns)

    def run(self, code):
        return self.lua.execute(code)

    def eval(self, code):
        return self.lua.eval(code)


def text(name):
    return (SRC / name).read_text(encoding="utf-8")
