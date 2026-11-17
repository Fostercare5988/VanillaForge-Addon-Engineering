"""AutoLazy 1.0 (written new, 2026-11-18) on the shared game model (wowkit).

The game is modelled as ClassicAPI documents it (docs/API.md) and as the
client's FrameXML runs it: the roll strings are GlobalStrings.lua's; a chat
event reaches each chat window through ChatFrame_OnEvent with
GetCurrentChatEvent() giving its text; C_GossipInfo lists the quests of a
gossip and a greeting window alike; GetQuestReward is the global QuestFrame.lua
calls. The mocks do not prove drawing, anchoring or when the server answers.
"""
from pathlib import Path
import os
import wowkit

ROOT = Path(os.environ["VANILLAFORGE_ADDON_ROOT"])

MOCK = r'''
CLASSIC_API_VERSION = 12101
calls = {}
local function record(name, value) calls[name] = calls[name] or {}; table.insert(calls[name], value) end
function count(name) return calls[name] and #calls[name] or 0 end
function last(name) local list = calls[name]; return list and list[#list] end
function forget() calls = {} end

-- hooksecurefunc(name, fn) and hooksecurefunc(table, name, fn), as the client runs them.
function hooksecurefunc(a, b, c)
    local t, name, hook = _G, a, b
    if type(a) == 'table' then t, name, hook = a, b, c end
    local stock = t[name]
    t[name] = function(...) local r = { stock(...) }; hook(...); return unpack(r) end
end

-- Widgets: what the addon reads back.
function Widget:SetMovable(on) self.movable = on end
function Widget:IsMovable() return self.movable and 1 or nil end
function Widget:IsMouseOver() return self.hovered and true or false end
function Widget:SetFrameStrata(s) self.strata = s end
function Widget:GetFrameStrata() return self.strata or 'MEDIUM' end
function Widget:GetChildren()
    local out = {}
    for _, w in ipairs(widgets) do
        if w.parent == self and w.kind ~= 'Texture' and w.kind ~= 'FontString' then out[#out + 1] = w end
    end
    return unpack(out)
end
function click(frame, button) run(frame, 'OnClick', button or 'LeftButton') end

-- Loot (### GetInstanceInfo(), GetLootRollItemID in the ID-companion table).
instance, rollItems = 'Kalimdor', {}
function GetInstanceInfo() return instance, 'raid', 1, 'Normal', 40, 0, false, 1, 40 end
function GetLootRollItemID(id) return rollItems[id] end
function RollOnLoot(id, kind) record('RollOnLoot', id .. ':' .. kind) end
function ConfirmLootRoll(id, kind) record('ConfirmLootRoll', id .. ':' .. kind) end
function LootSlot(slot) record('LootSlot', slot) end
function StaticPopup_Hide(which, data) record('StaticPopup_Hide', which .. ':' .. tostring(data)) end

-- Chat: GlobalStrings.lua's roll lines; each window runs ChatFrame_OnEvent.
LOOT_ROLL_ALL_PASSED = "Everyone passed on: %s|Hitem:%d:%d:%d:%d|h[%s]|h%s"
LOOT_ROLL_GREED = "%s has selected Greed for: %s|Hitem:%d:%d:%d:%d|h[%s]|h%s"
LOOT_ROLL_GREED_SELF = "You have selected Greed for: %s|Hitem:%d:%d:%d:%d|h[%s]|h%s"
LOOT_ROLL_NEED = "%s has selected Need for: %s|Hitem:%d:%d:%d:%d|h[%s]|h%s"
LOOT_ROLL_NEED_SELF = "You have selected Need for: %s|Hitem:%d:%d:%d:%d|h[%s]|h%s"
LOOT_ROLL_PASSED = "%s passed on: %s|Hitem:%d:%d:%d:%d|h[%s]|h%s"
LOOT_ROLL_PASSED_SELF = "You passed on: %s|Hitem:%d:%d:%d:%d|h[%s]|h%s"
LOOT_ROLL_ROLLED = "%s rolls a %d on: %s|Hitem:%d:%d:%d:%d|h[%s]|h%s"
LOOT_ROLL_ROLLED_GREED = "Greed Roll - %d for %s|Hitem:%d:%d:%d:%d|h[%s]|h%s by %s"
LOOT_ROLL_ROLLED_GREED_SELF = "You roll a %d (Greed) on: %s|Hitem:%d:%d:%d:%d|h[%s]|h%s"
LOOT_ROLL_ROLLED_NEED = "Need Roll - %d for %s|Hitem:%d:%d:%d:%d|h[%s]|h%s by %s"
LOOT_ROLL_ROLLED_NEED_SELF = "You roll a %d (Need) on: %s|Hitem:%d:%d:%d:%d|h[%s]|h%s"
LOOT_ROLL_ROLLED_SELF = "You roll a %d on: %s|Hitem:%d:%d:%d:%d|h[%s]|h%s"
LOOT_ROLL_START = "Rolling started on: %s|Hitem:%d:%d:%d:%d|h[%s]|h%s"
LOOT_ROLL_WON = "%s won: %s|Hitem:%d:%d:%d:%d|h[%s]|h%s"
LOOT_ROLL_YOU_WON = "You won: %s|Hitem:%d:%d:%d:%d|h[%s]|h%s"
function ChatFrame_OnEvent(e) record('shown', this:GetName() .. '|' .. arg1) end
for i = 1, 3 do CreateFrame('ScrollingMessageFrame', 'ChatFrame' .. i) end
local current
function GetCurrentChatEvent() if current then return current, arg1 end end
-- One chat event, as each window gets it; a hook before ours changed arg1 on the way.
function chatLine(e, text)
    current = e
    for i = 1, 3 do this, event, arg1 = _G['ChatFrame' .. i], e, text; ChatFrame_OnEvent(e) end
    current = nil
end

-- Quests: the quest giver, its lists, the bags and the quest cache.
shift, guids = false, { npc = 'Creature-1' }
function IsLeftShiftKeyDown() return shift and 1 or nil end
function IsRightShiftKeyDown() return nil end
function UnitGUID(unit) return guids[unit] end
GossipFrame = CreateFrame('Frame', 'GossipFrame'); GossipFrame:Hide()
QuestFrameGreetingPanel = CreateFrame('Frame', 'QuestFrameGreetingPanel'); QuestFrameGreetingPanel:Hide()
active, available, details, bags = {}, {}, {}, {}
local function copy(list)
    local out = {}
    for i, q in ipairs(list) do out[i] = { questID = q[1], isComplete = q[2], title = 'Quest ' .. q[1] } end
    return out
end
C_GossipInfo = {
    GetActiveQuests = function() return copy(active) end,
    GetAvailableQuests = function() return copy(available) end,
    SelectActiveQuest = function(id) record('pick', 'active:' .. id) end,
    SelectAvailableQuest = function(id) record('pick', 'offered:' .. id) end,
}
function SelectActiveQuest(i) record('pick', 'active#' .. i) end
function SelectAvailableQuest(i) record('pick', 'offered#' .. i) end
C_QuestLog = {
    GetQuestDetails = function(id) return details[id] end,
    RequestLoadQuestByID = function(id) record('load', id) end,
}
C_Item = { GetItemCount = function(id) return bags[id] or 0 end }
-- { { 'item', id, count }, ... } as GetQuestDetails' requirements.
function quest(id, ...)
    local req = {}
    for _, r in ipairs({ ... }) do req[#req + 1] = { kind = r[1], id = r[2], count = r[3], text = '' } end
    details[id] = { questID = id, requirements = req }
end
completable, choices = true, {}
function IsQuestCompletable() return completable and 1 or nil end
function CompleteQuest() record('CompleteQuest', true) end
function GetNumQuestChoices() return #choices end
function GetQuestItemID(kind, i) if kind == 'choice' then return choices[i] end end
function GetQuestReward(i) record('GetQuestReward', i) end
function gossip(a, o) active, available = a or {}, o or {}; GossipFrame:Show(); fire('GOSSIP_SHOW') end
function greeting(a, o) active, available = a or {}, o or {}; QuestFrameGreetingPanel:Show(); fire('QUEST_GREETING') end
function closeAll() GossipFrame:Hide(); QuestFrameGreetingPanel:Hide() end

-- The minimap and what the installed addons put on it.
Minimap = CreateFrame('Minimap', 'Minimap')
function minimapButton(name, kind, how)
    local b = CreateFrame(kind or 'Button', name, Minimap)
    b:SetPoint('TOPLEFT', Minimap, 'TOPLEFT', 10, -10)
    b:SetFrameStrata('LOW')
    if how == 'movable' then b:SetMovable(true) elseif how == 'drag' then b:SetScript('OnDragStart', function() end) end
    return b
end

-- Which frames listen to what, and every OnUpdate.
function listening()
    local out = {}
    for _, w in ipairs(widgets) do
        for e in pairs(w.events) do out[#out + 1] = e end
        if w.scripts.OnUpdate then out[#out + 1] = 'OnUpdate' end
    end
    table.sort(out)
    return table.concat(out, ',')
end
function liveTimers() local n = 0; for _, t in ipairs(timers) do if not t.cancelled then n = n + 1 end end; return n end
'''

# Buttons on the minimap before login, as the installed addons make them.
BEFORE = '''
minimapButton('AtlasLootMinimapButton', 'Button', 'movable')
minimapButton('LibDBIcon10_UnitXP', 'Button', 'drag')
minimapButton('GearRackMinimapButton', 'Button', 'movable')
minimapButton('EBC_Minimap', 'Button')
minimapButton('LFTMinimapButton', 'Button')
minimapButton('MinimapZoomIn', 'Button', 'movable')
minimapButton('MinimapClock', 'Frame', 'movable')
minimapButton(nil, 'Button', 'movable')
minimapButton('MapPin1', 'Button')
'''


def load(saved="", setup="", world=True, buttons=BEFORE):
    """The addon loaded over `saved` (Lua that sets AutoLazyDB); with `world`,
    the login events have fired, so the page exists and the tray is filled."""
    lua = wowkit.runtime()
    lua.execute(MOCK)
    lua.execute(buttons)
    lua.execute(setup)
    wowkit.load_addon(lua, ROOT, "AutoLazy", saved=saved or None)
    if world:
        lua.execute('fire("VARIABLES_LOADED") fire("PLAYER_LOGIN") fire("PLAYER_ENTERING_WORLD") step()')
    return lua
