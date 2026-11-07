"""The shared game model for the regression suites: widgets, events, time and
the addon loader, written once on top of wowlua.

A suite builds its world with `wowkit.runtime()` and then adds only what is its
own: the API its addon calls, the data, and any widget method it records in its
own way (redefine `Widget:Method` after the kit; the kit's are the defaults).

What the kit models, and the evidence:

* Widgets (`CreateFrame`, `newWidget`): every method exists (unknown
  capitalised names are no-ops); state that tests read is kept: shown, parent,
  text, anchors, size, alpha, scale, checked, enabled, value, colour, scripts
  and events. Frames start shown, like the client's. `GetChecked` and
  `IsEnabled` return 1 or nil (FrameXML compares them with 1); `IsShown` and
  `IsVisible` follow the same 1.12 convention (UNVERIFIED: test in game,
  `/run print(UIParent:IsShown(), UIParent:IsEnabled())`). `IsVisible` also
  needs every parent shown. Show and Hide run OnShow and OnHide when the
  frame's own state changes.
* Events (`fire(event, ...)`): every frame registered for the event, in
  registration order, gets OnEvent with `this`, `event` and `arg1`...`arg9`
  set and `(self, event, ...)` passed (ClassicAPI's modern script arguments).
  `RegisterUnitEvent` follows ClassicAPI's API.md: the frame gets the event
  only when the first argument is a string naming one of its units (case
  ignored); a non-string first argument always gets through; a registration
  keeps its kind until it is unregistered; `IsEventRegistered` returns the
  units after the boolean.
* Time (`now`, `GetTime`, `step(dt)`): `step` moves the clock, runs the
  C_Timer callbacks that are due (After, NewTimer, NewTicker; Cancel and
  IsCancelled), then OnUpdate on every visible frame with the elapsed time as
  `arg1` and the second argument, the way the client does once per frame.
* Chat (`chat`, `DEFAULT_CHAT_FRAME`), `SlashCmdList`, `UISpecialFrames`,
  `UIParent`, and `categories` (InterfaceOptions_AddCategory, in order).
* Loading (`load_files`, `toc_files`, `xml_scripts`, and `xml_frames` for the
  frames an addon's XML makes): each file runs as the
  client loads it, `(addonName, namespace)` passed to the chunk and the file
  name in error messages. Lua 5.0's `for k, v in t do` table loop, which the
  client still runs, is rewritten to `pairs(t)` for lupa (`lua50`).

Not modelled: drawing, layout, input, frame strata and levels, XML templates
(a suite builds the frames its XML would make), and the engine's own events.
These stay in-game checks.
"""
import re
from pathlib import Path

from wowlua import LuaRuntime

KIT = r'''
widgets, chat, categories = {}, {}, {}
SlashCmdList, UISpecialFrames = {}, {}
DEFAULT_CHAT_FRAME = { AddMessage = function(_, message) chat[#chat + 1] = message end }
function InterfaceOptions_AddCategory(panel) categories[#categories + 1] = panel end
function hooksecurefunc() end

local function flag(v) if v then return 1 end end

Widget = {}
-- One shared no-op: a fresh function per unknown method would be the kit's garbage.
local NOOP = function() end
local WidgetMeta = { __index = function(_, key)
    local method = Widget[key]
    if method then return method end
    if type(key) == "string" and string.find(key, "^%u") then return NOOP end
end }

function newWidget(kind, name, parent)
    local w = setmetatable({ kind = kind or "Frame", name = name, parent = parent, shown = true,
        enabled = true, scripts = {}, events = {}, units = {}, points = {} }, WidgetMeta)
    if name then rawset(_G, name, w) end
    widgets[#widgets + 1] = w
    return w
end
function CreateFrame(kind, name, parent) return newWidget(kind, name, parent) end

-- this, event and arg1... as the client sets them; (self, ...) as ClassicAPI passes them.
-- The kit calls its own functions through locals: a suite may reuse the global names.
local function runScript(w, script, ...)
    local f = w.scripts[script]
    if not f then return end
    local oldThis = this
    this = w
    arg1, arg2, arg3, arg4, arg5, arg6, arg7, arg8, arg9 = ...
    f(w, ...)
    this = oldThis
end
run = runScript

function Widget:GetName() return self.name end
function Widget:GetObjectType() return self.kind end
function Widget:IsObjectType(kind) return flag(self.kind == kind) end
function Widget:GetParent() return self.parent end
function Widget:SetParent(p) self.parent = p end
function Widget:GetID() return self.id or 0 end
function Widget:SetID(id) self.id = id end

function Widget:SetScript(script, f) self.scripts[script] = f end
function Widget:GetScript(script) return self.scripts[script] end
function Widget:HookScript(script, f)
    local old = self.scripts[script]
    self.scripts[script] = old and function(...) old(...); f(...) end or f
end

function Widget:Show() if not self.shown then self.shown = true; runScript(self, "OnShow") end end
function Widget:Hide() if self.shown then self.shown = false; runScript(self, "OnHide") end end
function Widget:SetShown(on) if on then self:Show() else self:Hide() end end
function Widget:IsShown() return flag(self.shown) end
function Widget:IsVisible()
    local w = self
    while w do
        if not w.shown then return nil end
        w = w.parent
    end
    return 1
end

function Widget:Enable() self.enabled = true end
function Widget:Disable() self.enabled = false end
function Widget:IsEnabled() return flag(self.enabled) end
function Widget:SetChecked(on) self.checked = on and true or nil end
function Widget:GetChecked() return flag(self.checked) end
function Widget:SetValue(v) self.value = v end
function Widget:GetValue() return self.value or 0 end
function Widget:SetMinMaxValues(lo, hi) self.min, self.max = lo, hi end
function Widget:GetMinMaxValues() return self.min or 0, self.max or 0 end

function Widget:SetText(text)
    self.text = text
    if self.fontString then self.fontString:SetText(text) end
end
function Widget:GetText() return self.text end
function Widget:SetFontString(fs) self.fontString = fs end
function Widget:GetFontString() return self.fontString end
function Widget:CreateFontString(name) return newWidget("FontString", name, self) end
function Widget:CreateTexture(name) return newWidget("Texture", name, self) end
function Widget:SetTexture(path) self.texture = path end
function Widget:GetTexture() return self.texture end
function Widget:SetVertexColor(r, g, b, a) self.color = { r, g, b, a } end
function Widget:SetTextColor(r, g, b, a) self.color = { r, g, b, a } end

function Widget:SetPoint(...) self.points[#self.points + 1] = { ... } end
function Widget:ClearAllPoints() self.points = {} end
function Widget:GetNumPoints() return #self.points end
function Widget:GetPoint(i) local p = self.points[i or 1]; if p then return unpack(p) end end
function Widget:SetWidth(w) self.width = w end
function Widget:GetWidth() return self.width or 0 end
function Widget:SetHeight(h) self.height = h end
function Widget:GetHeight() return self.height or 0 end
function Widget:SetSize(w, h) self.width, self.height = w, h end
function Widget:SetAlpha(a) self.alpha = a end
function Widget:GetAlpha() return self.alpha or 1 end
function Widget:SetScale(s) self.scale = s end
function Widget:GetScale() return self.scale or 1 end

-- Events: registration order, unit filters as ClassicAPI documents them.
local order = 0
function Widget:RegisterEvent(e)
    if not self.events[e] then order = order + 1; self.events[e] = order end
    return 1
end
function Widget:RegisterUnitEvent(e, ...)
    local units = {}
    for i = 1, select("#", ...) do
        local u = select(i, ...)
        if type(u) == "string" then units[#units + 1] = string.lower(u) end
    end
    if #units == 0 then return self:RegisterEvent(e) end
    if self.events[e] and not self.units[e] then return 1 end
    self:RegisterEvent(e)
    self.units[e] = units
    return 1
end
function Widget:UnregisterEvent(e) self.events[e], self.units[e] = nil, nil end
function Widget:UnregisterAllEvents() self.events, self.units = {}, {} end
function Widget:IsEventRegistered(e)
    if not self.events[e] then return nil end
    if self.units[e] then return 1, unpack(self.units[e]) end
    return 1
end

local function wants(w, e, first)
    local units = w.units[e]
    if not units or type(first) ~= "string" then return true end
    first = string.lower(first)
    for _, u in ipairs(units) do if u == first then return true end end
    return false
end
-- Whether the frame would get `e` for `unit`: ask this, not the registration tables.
function receives(w, e, unit) return w.events[e] ~= nil and wants(w, e, unit) end
-- The kit builds no garbage per call (a suite may measure the addon's): one
-- buffer per nesting depth, an insertion sort, no closures.
local buffers, depth = {}, 0
function fire(e, ...)
    local first = ...
    depth = depth + 1
    local due = buffers[depth] or {}
    buffers[depth] = due
    local n = 0
    for _, w in ipairs(widgets) do
        if w.events[e] and w.scripts.OnEvent and wants(w, e, first) then
            n = n + 1
            due[n] = w
            local i = n
            while i > 1 and due[i - 1].events[e] > w.events[e] do due[i], due[i - 1] = due[i - 1], w; i = i - 1 end
        end
    end
    for i = 1, n do
        local w = due[i]
        due[i] = nil
        local f = w.events[e] and w.scripts.OnEvent
        if f then
            local oldThis = this
            this, event = w, e
            arg1, arg2, arg3, arg4, arg5, arg6, arg7, arg8, arg9 = ...
            f(w, e, ...)
            this = oldThis
        end
    end
    depth = depth - 1
end

-- Time.
now, timers = 100, {}
function GetTime() return now end
local seq = 0
local function schedule(seconds, fn, iterations)
    seq = seq + 1
    local t = { at = now + seconds, seq = seq, seconds = seconds, fn = fn, left = iterations }
    function t:Cancel() self.cancelled = true end
    function t:IsCancelled() return self.cancelled and true or false end
    timers[#timers + 1] = t
    return t
end
C_Timer = {
    After = function(seconds, fn) schedule(seconds, fn, 1) end,
    NewTimer = function(seconds, fn) return schedule(seconds, fn, 1) end,
    NewTicker = function(seconds, fn, iterations) return schedule(seconds, fn, iterations) end,
}
-- The earliest due timer runs first; ties in the order they were scheduled.
local function dueTimers()
    while true do
        local best, at
        for i = #timers, 1, -1 do
            local t = timers[i]
            if t.cancelled then
                table.remove(timers, i)
                if best then best = best - 1 end
            elseif t.at <= now and (not best or t.at < timers[best].at
                    or (t.at == timers[best].at and t.seq < timers[best].seq)) then
                best = i
            end
        end
        if not best then return end
        local t = timers[best]
        if t.left then t.left = t.left - 1 end
        if t.left == 0 then
            table.remove(timers, best)
        else
            seq = seq + 1
            t.at, t.seq = t.at + t.seconds, seq
        end
        t.fn(t)
    end
end
runTimers = dueTimers
function step(dt)
    dt = dt or 0
    now = now + dt
    dueTimers()
    for _, w in ipairs(widgets) do
        if w.scripts.OnUpdate and w:IsVisible() then runScript(w, "OnUpdate", dt) end
    end
end

-- ClassicAPI's GetCoinTextureString: coin icons in the real client, plain letters here.
function GetCoinTextureString(copper)
    local g, s, c = math.floor(copper / 10000), math.floor(copper % 10000 / 100), copper % 100
    local t = {}
    if g > 0 then t[#t + 1] = g .. "g" end
    if s > 0 then t[#t + 1] = s .. "s" end
    if c > 0 or #t == 0 then t[#t + 1] = c .. "c" end
    return table.concat(t, " ")
end

UIParent = newWidget("Frame", "UIParent")
'''

# A name, an indexed name or a table constructor; never a call (gmatch(...) is an iterator).
_LUA50_FOR = re.compile(r"\bfor ([\w, ]+) in ([A-Za-z_][\w.]*(?:\[[^\]\n]*\])*|\{[^\n]*\})\s+do\b")


def lua50(source):
    """Lua 5.0's `for k, v in t do` (a table, not an iterator) as `pairs(t)`."""
    return _LUA50_FOR.sub(r"for \1 in pairs(\2) do", source)


def runtime(**kwargs):
    """A game runtime with the kit loaded."""
    lua = LuaRuntime(**kwargs)
    lua.execute(KIT)
    return lua


def toc_files(root, toc=None):
    """The files a TOC lists, in order (Lua and XML)."""
    root = Path(root)
    toc = Path(toc) if toc else next(root.glob("*.toc"))
    if not toc.is_absolute():
        toc = root / toc
    names = []
    for line in toc.read_text("utf-8-sig").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            names.append(line.replace("\\", "/"))
    return names


def xml_scripts(root, xml):
    """The Lua files an XML file loads with <Script file=...>, in order."""
    root = Path(root)
    text = (root / xml).read_text("utf-8-sig")
    folder = Path(xml).parent
    return [str(folder / name.replace("\\", "/")).replace("\\", "/")
            for name in re.findall(r'<Script\s+file="([^"]+)"', text)]


def xml_frames(files, client_templates=None):
    """(name, tag) of every frame and region the XML files create, template
    children included, `$parent` expanded as the client does. Children of
    client templates the XML inherits come from `client_templates`
    ({template: ["$parentText", ...]}).
    """
    from lxml import etree
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

    templates.update(client_templates or {})
    for name in nodes:
        children(name)

    def walk(el, parent, inside_template):
        name = el.get("name")
        virtual = inside_template or el.get("virtual") == "true"
        # $parent is the frame named in parent="X" when there is one, as in the client.
        full = name.replace("$parent", el.get("parent") or parent or "") if name else None
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


def load_addon(lua, root, addon, saved=None, toc=None, rewrite=lua50):
    """Load an addon as the client does: its TOC files in order, its saved
    variables (`saved`, Lua source) restored after the files, or before them
    when the TOC declares `## LoadSavedVariablesFirst: 1` (ClassicAPI)."""
    root = Path(root)
    toc_path = root / (toc or f"{addon}.toc")
    first = re.search(r"^## LoadSavedVariablesFirst:\s*1\s*$", toc_path.read_text("utf-8-sig"), re.M)
    if saved and first:
        lua.execute(saved)
    load_files(lua, root, toc_files(root, toc_path), addon, rewrite)
    if saved and not first:
        lua.execute(saved)
    return lua


def load_files(lua, root, names, addon, rewrite=lua50):
    """Run each Lua file as the client does: chunk("addon", namespace)."""
    root = Path(root)
    loader = lua.eval('''function(source, name, addon)
        __addon_ns = __addon_ns or {}
        local chunk = assert(loadstring(source, "@" .. name))
        return chunk(addon, __addon_ns)
    end''')
    for name in names:
        if name.lower().endswith(".lua"):
            source = (root / name).read_text("utf-8-sig")
            loader(rewrite(source) if rewrite else source, name, addon)
    return lua
