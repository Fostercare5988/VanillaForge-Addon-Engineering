"""ClassicAPI's engine-side countdowns, as API.md describes them, for the timer tests.

C_DurationUtil.CreateDuration and CreateDurationTextBinding, and
C_StringUtil.CreateNumericRuleFormatter (breakpoints chosen before rounding;
step, rounding, div and mod as documented). The engine writes an enabled
binding's text on every drawn frame; here `__frame()` is that frame: it writes
every enabled binding and runs the C_Timer timers that are due. Append CLOCK to
a BASE after its C_Timer and GetTime; GetTime is read when the clock runs.
"""

CLOCK = r'''
Enum = Enum or {}
Enum.NumericRuleFormatRounding = { Nearest = 0, Up = 1, Down = 2 }
Enum.DurationTextBindingProperty = { RemainingDuration = 0, RemainingPercent = 1, ElapsedDuration = 2,
    ElapsedPercent = 3, TotalDuration = 4, StartTime = 5, EndTime = 6 }

local function Round(n, step, rounding)
    if not step or step <= 0 then return n end
    local q = n / step
    if rounding == 1 then q = math.ceil(q) elseif rounding == 2 then q = math.floor(q) else q = math.floor(q + 0.5) end
    return q * step
end

local Formatter = {}
Formatter.__index = Formatter
function Formatter:SetBreakpoints(points) self.points = points end
function Formatter:FormatNumber(n)
    local best
    for _, p in ipairs(self.points or {}) do
        if p.threshold <= n and (not best or p.threshold > best.threshold) then best = p end
    end
    if not best then return tostring(n) end
    n = Round(n, best.step, best.rounding)
    if best.min and n < best.min then n = best.min end
    if best.max and n > best.max then n = best.max end
    if not best.components or #best.components == 0 then return string.format(best.format, n) end
    local values = {}
    for i, c in ipairs(best.components) do
        local v = n
        if c.div and c.div ~= 0 then v = v / c.div end
        if c.mod and c.mod ~= 0 then v = math.fmod(v, c.mod) end
        values[i] = Round(v, c.step, c.rounding)
    end
    return string.format(best.format, unpack(values))
end
C_StringUtil = { CreateNumericRuleFormatter = function() return setmetatable({}, Formatter) end }

local Duration = {}
Duration.__index = Duration
function Duration:SetTimeSpan(s, e) self.startTime, self.endTime = s, math.max(s, e) end
function Duration:GetRemainingDuration() return math.max(0, (self.endTime or 0) - math.max(GetTime(), self.startTime or 0)) end
function Duration:GetElapsedDuration()
    local total = (self.endTime or 0) - (self.startTime or 0)
    return math.min(total, math.max(0, GetTime() - (self.startTime or 0)))
end

local bindings = {}
local Binding = {}
Binding.__index = Binding
function Binding:SetFontString(fs) self.fs = fs end
function Binding:SetDuration(d) self.duration = d end
function Binding:SetFormatter(f) self.formatter, self.textFormat = f, nil end
function Binding:SetTextFormat(text, components) self.textFormat, self.components, self.formatter = text, components, nil end
function Binding:GetFormattedText()
    local d = self.duration
    if not d then return "" end
    if self.formatter then return self.formatter:FormatNumber(d:GetRemainingDuration()) end
    if self.textFormat then
        local i = 0
        return (string.gsub(self.textFormat, "{}", function()
            i = i + 1
            local c = self.components[i]
            local value = c.property == Enum.DurationTextBindingProperty.ElapsedDuration and d:GetElapsedDuration() or d:GetRemainingDuration()
            return c.formatter:FormatNumber(value)
        end))
    end
    return ""
end
function Binding:UpdateFontString()
    if not self.fs then return end
    local text = self:GetFormattedText()
    if self.fs.text ~= text then self.fs:SetText(text) end
end
function Binding:SetEnabled(on)
    self.enabled = on and true or false
    if self.enabled then self:UpdateFontString() end
end
function Binding:IsEnabled() return self.enabled end

C_DurationUtil = C_DurationUtil or {}
C_DurationUtil.CreateDuration = function() return setmetatable({ startTime = 0, endTime = 0 }, Duration) end
C_DurationUtil.CreateDurationTextBinding = function()
    local b = setmetatable({}, Binding)
    table.insert(bindings, b)
    return b
end

-- C_Timer.NewTimer timers run when __frame() finds them due.
local due = {}
C_Timer = C_Timer or {}
C_Timer.NewTimer = function(seconds, fn)
    local t = { at = GetTime() + seconds, fn = fn }
    t.Cancel = function(self) self.cancelled = true end
    table.insert(due, t)
    return t
end
function __frame()
    local now = GetTime()
    local run = {}
    for i = #due, 1, -1 do
        local t = due[i]
        if t.cancelled then table.remove(due, i)
        elseif t.at <= now then table.remove(due, i); table.insert(run, 1, t) end
    end
    for _, t in ipairs(run) do t.fn() end
    for _, b in ipairs(bindings) do if b.enabled then b:UpdateFontString() end end
end
'''
