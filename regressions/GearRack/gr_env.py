"""Shared Lua 5.1 environment for the GearRack regressions.

Loads selected files of the addon at VANILLAFORGE_ADDON_ROOT with widget mocks.
Every frame the addon's XML names (template children included) exists as a mock
widget, so Lua that styles or drives XML frames runs as it would after load.
ClassicAPI's file varargs are supplied: each file gets ("GearRack", ns).

The mocks record colors, parents and frame levels. They do not prove how the
client draws a texture, which font a button uses or how a window looks.
"""
from pathlib import Path
import os
import re
from lxml import etree
from lupa.lua51 import LuaRuntime

ROOT = Path(os.environ["VANILLAFORGE_ADDON_ROOT"])
SRC = ROOT / "src"

MOCK = r'''
table.wipe = function(t) for k in pairs(t) do t[k] = nil end return t end
getglobal = function(n) return _G[n] end
messages = {}
DEFAULT_CHAT_FRAME = { AddMessage = function(_, m) table.insert(messages, m) end }
UISpecialFrames, SlashCmdList = {}, {}
CLASSIC_API_VERSION, SUPERWOW_VERSION = 11600, "2.2"
function GetNampowerVersion() return 4, 6, 2 end
function GetCastInfo() end
function GetSpellIdCooldown() end
function GetTime() return 100 end

local Widget = {}
local mt = { __index = function(_, k)
    local m = Widget[k]; if m then return m end
    if type(k) == "string" and string.find(k, "^[A-Z]") then return function() end end
end }
function newWidget(kind, name, parent)
    local w = setmetatable({ kind = kind, name = name, parent = parent, shown = true, height = 20,
        level = parent and (parent.level + 1) or 1, calls = {} }, mt)
    if name then _G[name] = w end
    return w
end
function Widget:GetName() return self.name end
function Widget:SetParent(p) self.parent = p; self.level = p.level + 1 end
function Widget:GetParent() return self.parent end
function Widget:SetFrameLevel(l) self.level = l end
function Widget:GetFrameLevel() return self.level end
function Widget:SetHeight(h) self.height = h end
function Widget:GetHeight() return self.height end
function Widget:Show() self.shown = true end
function Widget:Hide() self.shown = false end
function Widget:IsShown() return self.shown end
function Widget:IsVisible() return self.shown end
function Widget:Enable() self.disabled = false end
function Widget:Disable() self.disabled = true end
function Widget:SetAlpha(a) self.alpha = a end
function Widget:SetHitRectInsets(l, r, t, b) self.hitInsets = { l, r, t, b } end
function Widget:SetVertexColor(r, g, b, a) self.color = { r, g, b, a } end
function Widget:SetTextColor(r, g, b) self.textColor = { r, g, b } end
function Widget:SetHighlightTextColor(r, g, b) self.highlightColor = { r, g, b } end
function Widget:SetDisabledTextColor(r, g, b) self.disabledColor = { r, g, b } end
function Widget:SetText(t) self.text = t end
function Widget:GetText() return self.text end
function Widget:CreateTexture(name, layer) local t = newWidget("Texture", name, self); t.layer = layer; return t end
function Widget:CreateFontString(name, layer) local f = newWidget("FontString", name, self); f.layer = layer; return f end
function Widget:SetFontString(f) self.font = f end
function Widget:GetFontString() return self.font end
function Widget:SetInventoryItem(...) table.insert(self.calls, "SetInventoryItem") end
function CreateFrame(kind, name, parent) return newWidget(kind, name, parent) end
UIParent = newWidget("Frame", "UIParent")
'''


def xml_names():
    """Every frame/region name the addon's XML creates, with template children."""
    files = sorted(SRC.glob("*.xml"))
    nodes, templates, names = {}, {}, []
    for f in files:
        for el in etree.parse(str(f)).getroot().iter():
            if isinstance(el.tag, str) and el.get("virtual") == "true":
                nodes[el.get("name")] = el

    def children(template):
        """Named descendants of a template, through nested templates, as $parent... names."""
        if template not in templates:
            found = []

            def scan(el, prefix):
                for ch in el:
                    if not isinstance(ch.tag, str):
                        continue
                    name = ch.get("name")
                    own = name.replace("$parent", prefix) if name else prefix
                    if name:
                        found.append(own)
                    if ch.get("inherits") in nodes:
                        found.extend(n.replace("$parent", own) for n in children(ch.get("inherits")))
                    scan(ch, own)

            root = nodes[template]
            if root.get("inherits") in nodes or root.get("inherits") in templates:
                found.extend(children(root.get("inherits")))
            scan(root, "$parent")
            templates[template] = found
        return templates[template]

    # Children of the client templates the addon inherits.
    templates.update({
        "UICheckButtonTemplate": ["$parentText"],
        "ActionButtonTemplate": ["$parentIcon", "$parentCount", "$parentHotKey", "$parentName",
                                 "$parentCooldown", "$parentBorder", "$parentNormalTexture", "$parentFlash"],
        "FauxScrollFrameTemplate": ["$parentScrollBar", "$parentScrollChildFrame"],
        "UIPanelScrollFrameTemplate": ["$parentScrollBar"],
    })
    for name in nodes:
        children(name)

    def walk(el, parent, inside_template):
        name = el.get("name")
        virtual = inside_template or el.get("virtual") == "true"
        full = name.replace("$parent", parent or "") if name else None
        # An unnamed frame declared with parent="X" (the queue insets) expands $parent from X.
        base = full or el.get("parent") or parent
        if not virtual:
            if full:
                names.append((full, el.tag))
            for child in templates.get(el.get("inherits"), []):
                names.append((child.replace("$parent", base or ""), "Region"))
        for ch in el:
            if isinstance(ch.tag, str):
                walk(ch, base, virtual)

    for f in files:
        walk(etree.parse(str(f)).getroot(), None, False)
    return names


class Env:
    def __init__(self, files):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute(MOCK)
        make = self.lua.globals().newWidget
        for name, kind in xml_names():
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
