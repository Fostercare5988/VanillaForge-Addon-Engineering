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
* Positions (`layoutCache`, `GetLeft`...): a frame with no anchor has no
  position (GetLeft, GetTop, GetRight, GetBottom and GetCenter return nil), as
  in the client. An anchored frame is at `left` and `top` (fields a test sets;
  100 and 200 by default), UIParent 1024 x 768. `StartMoving` makes a frame
  placed by hand (`IsUserPlaced`). A named frame in `layoutCache` (name ->
  { x, y }, a block of layout-cache.txt) is placed by hand from its creation
  but has no position until the first `step()`, when the client puts it back
  at TOPLEFT x, y: at a first login the client lays the frames out after
  PLAYER_ENTERING_WORLD (FostercareBars Bars.lua:69, 2026-11-17).
* Events (`fire(event, ...)`): every frame registered for the event, in
  registration order, gets OnEvent with `this`, `event` and `arg1`...`arg9`
  set and `(self, event, ...)` passed (ClassicAPI's modern script arguments).
  `RegisterUnitEvent` follows ClassicAPI's API.md: the frame gets the event
  only when the first argument is a string naming one of its units (case
  ignored); a non-string first argument always gets through; a registration
  keeps its kind until it is unregistered; `IsEventRegistered` returns the
  units after the boolean. `RegisterGUIDEvent` (ClassicAPI) is a registration of
  its own: `fireGUID(event, guid, ...)` reaches it with the GUID first, `fire`
  never does, `IsEventRegistered` does not see it and `UnregisterAllEvents`
  removes it.
* Time (`now`, `GetTime`, `step(dt)`): `step` moves the clock, runs the
  C_Timer callbacks that are due (After, NewTimer, NewTicker; Cancel and
  IsCancelled; a timer or ticker callback gets its handle, After's gets
  nothing), then OnUpdate on every visible frame with the elapsed time as
  `arg1` and the second argument, the way the client does once per frame.
* Chat (`chat`, `DEFAULT_CHAT_FRAME`), `SlashCmdList`, `UISpecialFrames`,
  `UIParent`, and `categories` (InterfaceOptions_AddCategory, in order).
* The Settings window (`Settings`, `SettingsRegistrar`, `C_SettingsUtil`, the
  row makers), as ClassicAPI's Lua for it behaves
  (`.private/upstream/classicapi/src/embed/AddOns/!!!ClassicAPI/Settings/`):
  registrants run when VARIABLES_LOADED and PLAYER_ENTERING_WORLD have both
  been fired, then SETTINGS_LOADED fires; an addon setting writes its default
  into the saved table when the key is nil; a write of the wrong type and a
  variable registered twice are errors; every write calls the change
  callbacks, Defaults included. Nothing is drawn. A test uses a page through
  `settingsWindow`: `find(name)`, `row(category, name)`, `use(variable,
  value)` (the player uses the control), `defaults([category])` (the Defaults
  button), `enabled(row)`, `visible(row)`, `choices(row)`, `click(row)`, and
  `opened` (the category the window was last opened to).
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

local layoutRead -- the client has read layout-cache.txt (Positions, below)
function newWidget(kind, name, parent)
    local w = setmetatable({ kind = kind or "Frame", name = name, parent = parent, shown = true,
        enabled = true, scripts = {}, events = {}, units = {}, points = {} }, WidgetMeta)
    if name then rawset(_G, name, w) end
    widgets[#widgets + 1] = w
    if name and layoutCache[name] and not layoutRead then w.userPlaced = true; restoring[#restoring + 1] = w end
    return w
end

-- Positions: none without an anchor; the client's saved places at the first frame.
-- It reads them when the addons have loaded (VARIABLES_LOADED): a frame made after
-- that has no saved place and is never saved (AutoBG's queue bars, 2026-11-23).
layoutCache, restoring = {}, {}
function Widget:GetLeft() if #self.points > 0 then return self.left or 100 end end
function Widget:GetTop() if #self.points > 0 then return self.top or 200 end end
function Widget:GetRight() local l = self:GetLeft(); return l and l + self:GetWidth() end
function Widget:GetBottom() local t = self:GetTop(); return t and t - self:GetHeight() end
function Widget:GetCenter()
    local l, t = self:GetLeft(), self:GetTop()
    if l then return l + self:GetWidth() / 2, t - self:GetHeight() / 2 end
end
function Widget:IsUserPlaced() return self.userPlaced and 1 or nil end
function Widget:SetUserPlaced(on) self.userPlaced = on and true or nil end
function Widget:StartMoving() self.moving = true; self.userPlaced = true end
function Widget:StopMovingOrSizing() self.moving = nil end
local function restore()
    for i = 1, #restoring do
        local w, at = restoring[i], layoutCache[restoring[i].name]
        restoring[i] = nil
        w:ClearAllPoints()
        w:SetPoint("TOPLEFT", UIParent, "TOPLEFT", at[1], at[2])
        w.left, w.top = at[1], 768 + at[2]
    end
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

-- The client refuses text on a font string made without a template before its
-- SetFont or SetFontObject ("<unnamed>:SetText(): Font not set", Nameplates 2026-11-22).
function Widget:SetText(text)
    if self.noFont then error((self.name or "<unnamed>") .. ":SetText(): Font not set") end
    self.text = text
    if self.fontString then self.fontString:SetText(text) end
end
function Widget:GetText() return self.text end
function Widget:SetFontString(fs) self.fontString = fs end
function Widget:GetFontString() return self.fontString end
function Widget:CreateFontString(name, layer, template)
    local w = newWidget("FontString", name, self)
    w.layer, w.noFont = layer, not template or nil
    return w
end
function Widget:SetFont(path, size, flags) self.font, self.fontSize, self.fontFlags, self.noFont = path, size, flags, nil end
function Widget:GetFont() return self.font, self.fontSize, self.fontFlags end
function Widget:SetFontObject(object) self.fontObject, self.noFont = object, nil end
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
function Widget:UnregisterAllEvents() self.events, self.units, self.guids = {}, {}, nil end
-- GUID registrations (ClassicAPI ### frame:RegisterGUIDEvent): apart from the
-- others, each call replaces the list, a string that is no GUID is skipped and
-- none at all is a usage error; only fireGUID reaches them.
function Widget:RegisterGUIDEvent(e, ...)
    local list = {}
    for i = 1, select("#", ...) do
        local g = select(i, ...)
        if type(g) ~= "string" then break end
        if string.find(g, "^0x%x+$") then list[#list + 1] = g end
    end
    if #list == 0 then error("Usage: frame:RegisterGUIDEvent(event, guid [, guid ...])", 2) end
    self.guids = self.guids or {}
    local old = self.guids[e]
    if old and #old == #list then
        local same = true
        for i = 1, #list do if old[i] ~= list[i] then same = false end end
        if same then return false end
    end
    self.guids[e] = list
    return true
end
function Widget:UnregisterGUIDEvent(e) if self.guids then self.guids[e] = nil end end
function Widget:IsGUIDEventRegistered(e)
    local list = self.guids and self.guids[e]
    if not list then return false, nil end
    return true, unpack(list)
end
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
local settingsEvent
function fire(e, ...)
    local first = ...
    if e == "VARIABLES_LOADED" then layoutRead = true end
    settingsEvent(e)
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
-- A unit event of the unit with this GUID, as the engine gives it to GUID
-- registrations: the GUID first, once per frame that lists it, in creation order.
function fireGUID(e, guid, ...)
    depth = depth + 1
    local due = buffers[depth] or {}
    buffers[depth] = due
    local n = 0
    for _, w in ipairs(widgets) do
        local list = w.guids and w.guids[e]
        if list and w.scripts.OnEvent then
            for i = 1, #list do
                if list[i] == guid then n = n + 1; due[n] = w; break end
            end
        end
    end
    for i = 1, n do
        local w = due[i]
        due[i] = nil
        local f = w.guids and w.guids[e] and w.scripts.OnEvent
        if f then
            local oldThis = this
            this, event = w, e
            arg1, arg2, arg3, arg4, arg5, arg6, arg7, arg8, arg9 = guid, ...
            f(w, e, guid, ...)
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
    t.arg = t
    function t:Cancel() self.cancelled = true end
    function t:IsCancelled() return self.cancelled and true or false end
    timers[#timers + 1] = t
    return t
end
C_Timer = {
    After = function(seconds, fn) schedule(seconds, fn, 1).arg = nil end,
    NewTimer = function(seconds, fn) return schedule(seconds, fn, 1) end,
    NewTicker = function(seconds, fn, iterations) return schedule(seconds, fn, iterations) end,
}
-- The engine's timer list is not addon Lua: removing from it must not depend
-- on Lua 5.0's stored table size (wowlua's table.remove does).
local function drop(list, i)
    for j = i, #list do list[j] = list[j + 1] end
end
-- The earliest due timer runs first; ties in the order they were scheduled.
local function dueTimers()
    while true do
        local best, at
        for i = #timers, 1, -1 do
            local t = timers[i]
            if t.cancelled then
                drop(timers, i)
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
            drop(timers, best)
        else
            seq = seq + 1
            t.at, t.seq = t.at + t.seconds, seq
        end
        t.fn(t.arg)
    end
end
runTimers = dueTimers
function step(dt)
    dt = dt or 0
    now = now + dt
    restore()
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

-- The Settings window. Vertical layouts and canvases, the three kinds of
-- setting, the rows, Defaults and opening; nothing is drawn.
settingsWindow = { categories = {}, settings = {} }
local window, callbacks, lastID, lastOwner = settingsWindow, {}, 0, 0

local Row = {}
Row.__index = Row
function Row:SetParentInitializer(parent, predicate)
    assert(parent and parent ~= self)
    self.parent = parent
    if predicate then self:AddModifyPredicate(predicate) end
end
function Row:GetParentInitializer() return self.parent end
function Row:AddModifyPredicate(fn) self.modify[#self.modify + 1] = fn end
function Row:AddShownPredicate(fn) self.shown[#self.shown + 1] = fn end
function Row:AddSearchTags(...)
    for i = 1, select("#", ...) do self.tags[#self.tags + 1] = (select(i, ...)) end
end
function Row:GetData() return self.data end
function Row:GetName() return self.data.name end
function Row:GetTooltip() return self.data.tooltip end
function Row:GetOptions() return self.data.options end
function Row:GetSetting() return self.data.setting end
local function newRow(template, data)
    return setmetatable({ template = template, data = data, modify = {}, shown = {}, tags = {} }, Row)
end

local Layout = {}
Layout.__index = Layout
function Layout:AddInitializer(row) self.rows[#self.rows + 1] = row end
function Layout:GetInitializers() return self.rows end
function Layout:GetFrame() return self.frame end

local Category = {}
Category.__index = Category
function Category:GetID() return self.ID end
function Category:GetName() return self.name end
function Category:GetParentCategory() return self.parent end
function Category:GetSubcategories() return self.subcategories end
local function newCategory(name, parent, frame)
    lastID = lastID + 1
    local c = setmetatable({ name = name, ID = lastID, parent = parent, subcategories = {},
        layout = setmetatable({ rows = {}, frame = frame }, Layout) }, Category)
    if parent then parent.subcategories[#parent.subcategories + 1] = c end
    return c, c.layout
end
local function findCategory(list, id)
    for _, c in ipairs(list) do
        if c.ID == id then return c end
        local sub = findCategory(c.subcategories, id)
        if sub then return sub end
    end
end

local function resolve(v) if type(v) == "function" then return v() end return v end
local Setting = {}
Setting.__index = Setting
function Setting:GetName() return resolve(self.name) end
function Setting:GetVariable() return self.variable end
function Setting:GetVariableType() return self.variableType end
function Setting:GetValue() return self.get() end
function Setting:GetDefaultValue() return resolve(self.default) end
function Setting:TriggerValueChanged(value)
    local list = callbacks[self.variable]
    if list then
        for i = 1, #list do
            local cb = list[i]
            if cb and not cb.gone then cb.fn(cb.owner, self, value) end
        end
    end
end
function Setting:SetValue(value)
    if self.locked then return end
    if self.get() ~= value then
        if type(value) ~= self.variableType then
            error(string.format("SetValue '%s' requires '%s' type, not '%s' type.",
                tostring(self.name), self.variableType, type(value)))
        end
        self.locked = true
        self.set(value)
        self.locked = false
    end
    self:TriggerValueChanged(value)
end
function Setting:SetValueToDefault()
    local default = self:GetDefaultValue()
    if default == nil then return false end
    self:SetValue(default)
    return true
end
function Setting:NotifyUpdate() self:TriggerValueChanged(self.get()) end
function Setting:SetValueChangedCallback(fn)
    Settings.SetOnValueChangedCallback(self.variable, function(_, setting, value) fn(setting, value) end)
end
local function register(category, setting)
    for _, other in ipairs(window.settings) do
        if other.variable == setting.variable then
            error(string.format("Setting variable '%s' was previously registered.", setting.variable))
        end
    end
    setting.category = category
    window.settings[#window.settings + 1] = setmetatable(setting, Setting)
    return setting
end
local function checked(name, variable, variableType, default)
    if variableType == nil then
        assert(default ~= nil)
        variableType = type(resolve(default))
    end
    if type(resolve(name)) ~= "string" then
        error(string.format("'name' for variable '%s' requires string type or a function that returns a string.", tostring(variable)))
    end
    if type(variable) ~= "string" then error(string.format("'variable' for '%s' requires string type.", resolve(name))) end
    if default ~= nil and type(resolve(default)) ~= variableType then
        error(string.format("'defaultValue' argument for '%s', '%s' variable type '%s' doesn't match default value type '%s'.",
            resolve(name), variable, variableType, type(resolve(default))))
    end
    return variableType
end

Settings = {
    VarType = { Boolean = "boolean", String = "string", Number = "number" },
    Default = { True = true, False = false },
}
function Settings.RegisterAddOnSetting(category, variable, key, tbl, variableType, name, default)
    for _, v in ipairs({ variable, key, variableType, name, default }) do
        if type(v) == "function" then error("Function values are not allowed for settings APIs") end
    end
    variableType = checked(name, variable, variableType, default)
    assert(type(tbl) == "table", "'variableTbl' argument must be a table.")
    if tbl[key] == nil then tbl[key] = default end
    return register(category, { name = name, variable = variable, variableType = variableType, default = default,
        get = function() return tbl[key] end, set = function(v) tbl[key] = v end })
end
function Settings.RegisterProxySetting(category, variable, variableType, name, default, getValue, setValue)
    variableType = checked(name, variable, variableType, default)
    return register(category, { name = name, variable = variable, variableType = variableType, default = default,
        get = getValue, set = setValue })
end
-- A cvar as the window reads it: "1" and "0" for a boolean, a number by tonumber.
function Settings.RegisterCVarSetting(category, cvar, variableType, name)
    variableType = checked(name, cvar, variableType)
    local function read(text)
        if text == nil then return nil end
        if variableType == "boolean" then return text == "1" end
        if variableType == "number" then return tonumber(text) end
        return text
    end
    return register(category, { name = name, variable = cvar, variableType = variableType,
        default = function() return read(GetCVarDefault and GetCVarDefault(cvar)) end,
        get = function() return read(GetCVar(cvar)) end,
        set = function(v) SetCVar(cvar, variableType == "boolean" and (v and "1" or "0") or tostring(v)) end })
end
function Settings.GetSetting(variable)
    for _, setting in ipairs(window.settings) do
        if setting.variable == variable then return setting end
    end
end
function Settings.GetValue(variable)
    local setting = Settings.GetSetting(variable)
    if setting then return setting:GetValue() end
end
function Settings.SetValue(variable, value)
    local setting = Settings.GetSetting(variable)
    if not setting then error(string.format("Setting for variable '%s' did not exist.", tostring(variable))) end
    setting:SetValue(value)
end
function Settings.NotifyUpdate(variable)
    local setting = Settings.GetSetting(variable)
    if setting then setting:NotifyUpdate() end
end
function Settings.SetOnValueChangedCallback(variable, fn, owner)
    if owner == nil then lastOwner = lastOwner + 1; owner = lastOwner end
    local cb = { fn = fn, owner = owner }
    callbacks[variable] = callbacks[variable] or {}
    table.insert(callbacks[variable], cb)
    return { Unregister = function() cb.gone = true end }
end

function Settings.RegisterVerticalLayoutCategory(name) return newCategory(name) end
function Settings.RegisterVerticalLayoutSubcategory(parent, name) return newCategory(name, parent) end
function Settings.RegisterCanvasLayoutCategory(frame, name) return newCategory(name, nil, frame) end
function Settings.RegisterCanvasLayoutSubcategory(parent, frame, name) return newCategory(name, parent, frame) end
function Settings.RegisterAddOnCategory(category)
    category.addon = true
    window.categories[#window.categories + 1] = category
end
function Settings.RegisterCategory(category) window.categories[#window.categories + 1] = category end
function Settings.GetCategory(id) return findCategory(window.categories, id) end
function Settings.OpenToCategory(id, scrollToElementName) C_SettingsUtil.OpenSettingsPanel(id, scrollToElementName) end
C_SettingsUtil = {
    OpenSettingsPanel = function(id, scrollToElementName)
        fire("SETTINGS_PANEL_OPEN", id, scrollToElementName)
        window.shown, window.opened = true, Settings.GetCategory(id)
    end,
    NotifySettingsLoaded = function() fire("SETTINGS_LOADED") end,
}
-- The older API makes a canvas page whose category ID is the panel's name.
function InterfaceOptions_AddCategory(panel)
    categories[#categories + 1] = panel
    local parent
    for _, c in ipairs(window.categories) do
        if panel.parent and c.ID == panel.parent then parent = c end
    end
    local category = newCategory(panel.name, parent, panel)
    category.ID, category.addon = panel.name, true
    if not parent then window.categories[#window.categories + 1] = category end
end

local function control(template, category, setting, options, tooltip)
    local row = Settings.CreateControlInitializer(template, setting, options, tooltip)
    category.layout:AddInitializer(row)
    return row
end
function Settings.CreateElementInitializer(template, data) return newRow(template, data) end
function Settings.CreateControlInitializer(template, setting, options, tooltip)
    local row = newRow(template, { setting = setting, name = setting:GetName(), options = options or {}, tooltip = tooltip })
    row:AddSearchTags(setting:GetName())
    return row
end
function Settings.CreateCheckbox(category, setting, tooltip)
    assert(setting:GetVariableType() == "boolean")
    return control("SettingsCheckboxControlTemplate", category, setting, nil, tooltip)
end
function Settings.CreateSlider(category, setting, options, tooltip)
    assert(setting:GetVariableType() == "number" and options ~= nil)
    return control("SettingsSliderControlTemplate", category, setting, options, tooltip)
end
function Settings.CreateDropdown(category, setting, options, tooltip)
    assert(options ~= nil)
    return control("SettingsDropdownControlTemplate", category, setting, options, tooltip)
end
function Settings.CreateColorSwatch(category, setting, tooltip, options)
    return control("SettingsColorSwatchControlTemplate", category, setting, options, tooltip)
end
function Settings.CreateSliderOptions(minValue, maxValue, rate)
    local options = { minValue = minValue or 0, maxValue = maxValue or 1, formatters = {} }
    options.steps = rate and (maxValue - minValue) / rate or 100
    function options:SetLabelFormatter(labelType, format) self.formatters[labelType] = format or true end
    return options
end
function Settings.CreateControlTextContainer()
    local container = { data = {} }
    function container:Add(value, label, tooltip)
        local entry = { text = label, label = label, tooltip = tooltip, value = value }
        self.data[#self.data + 1] = entry
        return entry
    end
    function container:GetData() return self.data end
    return container
end
MinimalSliderWithSteppersMixin = { Label = { Left = 1, Right = 2, Top = 3, Min = 4, Max = 5 } }

function CreateSettingsListSectionHeaderInitializer(name, tooltip)
    return newRow("SettingsListSectionHeaderTemplate", { name = name, tooltip = tooltip })
end
function CreateSettingsButtonInitializer(name, buttonText, buttonClick, tooltip, addSearchTags)
    assert(addSearchTags ~= nil)
    local row = newRow("SettingButtonControlTemplate",
        { name = name, buttonText = buttonText, buttonClick = buttonClick, tooltip = tooltip })
    if addSearchTags then row:AddSearchTags(name, buttonText) end
    return row
end
function CreateSettingsCheckboxWithButtonInitializer(setting, buttonText, buttonClick, evaluateState, clickRequiresSet, tooltip)
    local row = Settings.CreateControlInitializer("SettingsCheckboxWithButtonControlTemplate", setting, nil, tooltip)
    row.data.buttonText, row.data.buttonClick = buttonText, buttonClick
    row.data.OnEvaluateState, row.data.clickRequiresSet = evaluateState, clickRequiresSet
    return row
end
function CreateSettingsCheckboxSliderInitializer(cbSetting, cbLabel, cbTooltip, sliderSetting, sliderOptions, sliderLabel, sliderTooltip)
    local row = newRow("SettingsCheckboxSliderControlTemplate", { name = cbLabel, tooltip = cbTooltip,
        cbSetting = cbSetting, cbLabel = cbLabel, cbTooltip = cbTooltip, sliderSetting = sliderSetting,
        sliderOptions = sliderOptions, sliderLabel = sliderLabel, sliderTooltip = sliderTooltip })
    row:AddSearchTags(cbLabel, sliderLabel)
    return row
end
function CreateSettingsCheckboxDropdownInitializer(cbSetting, cbLabel, cbTooltip, dropdownSetting, dropdownOptions, dropDownLabel, dropDownTooltip)
    return newRow("SettingsCheckboxDropdownControlTemplate", { name = cbLabel, tooltip = cbTooltip,
        cbSetting = cbSetting, cbLabel = cbLabel, cbTooltip = cbTooltip, dropdownSetting = dropdownSetting,
        dropdownOptions = dropdownOptions, dropDownLabel = dropDownLabel, dropDownTooltip = dropDownTooltip })
end

-- Registrants wait for the saved variables and the world, as the window's do.
SettingsRegistrar = { registrants = {} }
function SettingsRegistrar:AddRegistrant(fn)
    if self.ready then fn() else self.registrants[#self.registrants + 1] = fn end
end
local seen = {}
settingsEvent = function(e)
    if SettingsRegistrar.ready or (e ~= "VARIABLES_LOADED" and e ~= "PLAYER_ENTERING_WORLD") then return end
    seen[e] = true
    if seen.VARIABLES_LOADED and seen.PLAYER_ENTERING_WORLD then
        SettingsRegistrar.ready = true
        for _, fn in ipairs(SettingsRegistrar.registrants) do fn() end
        C_SettingsUtil.NotifySettingsLoaded()
    end
end

-- What a test does with a page.
function window.find(name)
    local function search(list)
        for _, c in ipairs(list) do
            if c.name == name then return c end
            local sub = search(c.subcategories)
            if sub then return sub end
        end
    end
    return search(window.categories)
end
function window.row(category, name)
    for _, row in ipairs(category.layout.rows) do
        if row.data.name == name then return row end
    end
end
local function all(list)
    for _, fn in ipairs(list) do
        if not fn() then return false end
    end
    return true
end
function window.enabled(row) return all(row.modify) end
function window.visible(row) return all(row.shown) end
function window.choices(row) return resolve(row.data.options) end
function window.click(row) return row.data.buttonClick() end
function window.use(variable, value) Settings.SetValue(variable, value) end
-- The Defaults button: These Settings for a category, All Settings without one.
function window.defaults(category)
    for _, setting in ipairs(window.settings) do
        if not category or setting.category == category then setting:SetValueToDefault() end
    end
    for _, c in ipairs(window.categories) do
        local frame = c.layout.frame
        if frame and (not category or c == category) then
            -- rawget: a widget answers every capitalised name with a no-op.
            local default = rawget(frame, "OnDefault") or rawget(frame, "default")
            if default then default(frame) end
        end
    end
end

UIParent = newWidget("Frame", "UIParent")
UIParent:SetPoint("TOPLEFT")
UIParent.left, UIParent.top, UIParent.width, UIParent.height = 0, 768, 1024, 768
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
