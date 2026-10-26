"""GearRack audit of 2026-10-26: reproductions that fail on the audited code.

Each test runs the addon's own functions, cut from the source files, under
Lua 5.1 with small mocks. Lua 5.1, like the client's Lua 5.0, drops the
backslash of an unknown escape such as "\\I", so the tests check the texture
path the code really produces. Whether the client draws the art stays an
in-game check.
"""
from pathlib import Path
import os
import unittest
from lupa.lua51 import LuaRuntime

ROOT = Path(os.environ["VANILLAFORGE_ADDON_ROOT"])
EQUIPMENT = (ROOT / "src/Equipment.lua").read_text("utf-8")
CORE = (ROOT / "src/Core.lua").read_text("utf-8")
QUEUES = (ROOT / "src/TrinketQueues.lua").read_text("utf-8")

# Python strings with single backslashes: the paths the client must receive.
SLOW_POISON = "Interface\\Icons\\Spell_Nature_SlowPoison"
CORROSIVE = "Interface\\Icons\\INV_Corrosive_01"
QUESTION_MARK = "Interface\\Icons\\INV_Misc_QuestionMark"
SPELL_ICON = "Interface\\Icons\\Ability_Rogue_DualWeild"


def between(text, start, end):
    return text[text.index(start):text.index(end)]


def runtime():
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(r'''
        GearRack = { enabled = true }
        table.wipe = function(t) for k in pairs(t) do t[k] = nil end return t end
        calls, textures = {}, {}
    ''')
    return lua


class EnchantIconPathTests(unittest.TestCase):
    """Equipment.lua wrote enchant icons with single backslashes ("Interface\\Icons\\...").
    Lua drops "\\I", so the poison and fallback icons named a texture that does not exist."""

    def texture_for(self, info):
        lua = runtime()
        # The function is local to the cut chunk; call it in the same chunk.
        chunk = between(EQUIPMENT, "local function get_enchant_texture(info)", "-- Resolved icon art")
        return lua.execute(r'''
            C_Spell = { GetSpellTexture = function() return "Interface\\Icons\\Ability_Rogue_DualWeild" end }
        ''' + chunk + " return get_enchant_texture(...)", lua.table_from(info) if info is not None else None)

    def test_dissolvent_poison_icon_keeps_its_path(self):
        self.assertEqual(self.texture_for({"name": "Dissolvent Poison II"}), SLOW_POISON)

    def test_corrosive_poison_icon_keeps_its_path(self):
        self.assertEqual(self.texture_for({"name": "Corrosive Poison"}), CORROSIVE)

    def test_enchant_without_a_spell_shows_the_question_mark(self):
        # Sharpening stones and weightstones carry no spellID (API.md, C_Item.GetEnchantInfo).
        self.assertEqual(self.texture_for({"name": "Sharpened +8"}), QUESTION_MARK)

    def test_control_spell_enchant_uses_the_spell_icon(self):
        self.assertEqual(self.texture_for({"name": "Instant Poison VI", "spellID": 11340}), SPELL_ICON)

    def test_question_mark_is_not_cached_so_late_data_recovers(self):
        """The cache skips the placeholder so a cold enchant record can recover.
        With the broken path the comparison never matched and the blank icon stuck."""
        lua = runtime()
        chunk = between(EQUIPMENT, "local function format_enchant_duration(", "local equippedEnchantLocations")
        lua.execute(r'''
            C_Spell = { GetSpellTexture = function() return "Interface\\Icons\\Ability_Rogue_DualWeild" end }
            ENCHANT = { name = "Unknown" }
            C_Item = {
                GetItemTempEnchantInfo = function() return true, 600000, 0, 4321 end,
                GetEnchantInfo = function() return ENCHANT end,
            }
            function GetWeaponEnchantInfo() return 1, 600000, 0, nil, 0, 0 end
            function SecondsToTimeAbbrev(s) return string.format("%d m", math.ceil(s / 60)) end
            local function region() return { SetTexture = function(_, t) table.insert(textures, t) end,
                SetText = function() end, SetTextColor = function() end, Show = function() end } end
            BUTTON = { enchantOverlay = { icon = region(), duration = region(), iconFrame = region(),
                Hide = function() end, Show = function() end, IsShown = function() return true end } }
        ''' + chunk + r'''
            local location = { equipmentSlotIndex = 16 }
            update_enchant(BUTTON, location)
            ENCHANT = { name = "Deadly Poison V", spellID = 11358 }
            update_enchant(BUTTON, location)
        ''')
        seen = list(lua.eval("textures").values())
        self.assertEqual(seen, [QUESTION_MARK, SPELL_ICON])


class TrinketSortTooltipTests(unittest.TestCase):
    """The trinket order list read trinketOptions.ShowTooltips, a key Core clears at
    every login. Hovering a loaded trinket said "Item details not loaded yet."."""

    def hover(self, show_tooltips):
        lua = runtime()
        lua.execute(r'''
            GearRackUI = { DefaultSettings = { ShowTooltips = "ON" } }
            -- Saved data from before the trinket window shared the tooltip setting.
            GearRackDB = { settings = { ShowTooltips = "''' + show_tooltips + r'''" },
                trinketOptions = { ShowTooltips = "ON", TooltipFollow = "OFF" } }
            GearRackCharDB = { queues = { Sort = { [0] = { "11810", 0 } } } }
        ''' + between(CORE, "function GearRack.NormalizeSavedData()", "-- Narrow public queries") + r'''
            GearRack.NormalizeSavedData()
            GearRackTrinkets = { CurrentlySorting = 0 }
            function FauxScrollFrame_GetOffset() return 0 end
            function GetItemInfo(id)
                if tostring(id) == "11810" then return "Force of Will", "|cffa335ee|Hitem:11810:0:0:0|h[Force of Will]|h|r" end
            end
            GameTooltip = { SetHyperlink = function(_, l) table.insert(calls, "link:" .. l) end,
                Show = function() table.insert(calls, "show") end }
            function GearRackTrinkets.AnchorTooltip() end
            function GearRackTrinkets.OnTooltip(a, b)
                if GearRackDB.settings.ShowTooltips == "ON" then table.insert(calls, "text:" .. a .. ": " .. b) end
            end
            this = { GetID = function() return 1 end }
        ''' + between(QUEUES, "function GearRackTrinkets.SortTooltip()", "function GearRackTrinkets.SortOnClick()")
          + " GearRackTrinkets.SortTooltip()")
        return list(lua.eval("calls").values())

    def test_loaded_trinket_shows_its_item_tooltip(self):
        shown = self.hover("ON")
        self.assertTrue(any(c.startswith("link:") for c in shown), shown)
        self.assertFalse(any("not loaded" in c for c in shown), shown)

    def test_control_tooltips_off_shows_nothing(self):
        self.assertEqual(self.hover("OFF"), [])


TIMER_MOCK = r'''
    NOW, made, fired = 0, 0, {}
    function GetTime() return NOW end
    local pending = {}
    local function handle(delay, cb, period)
        made = made + 1
        local h = { at = NOW + delay, cb = cb, period = period }
        function h.Cancel(self) self.cancelled = true end
        table.insert(pending, h)
        return h
    end
    C_Timer = { NewTimer = function(d, cb) return handle(d, cb) end,
        NewTicker = function(d, cb) return handle(d, cb, d) end }
    -- Advance the clock in small steps; a cancelled handle never fires (API.md).
    function Advance(seconds)
        for _ = 1, math.floor(seconds * 20 + .5) do
            NOW = NOW + .05
            for _, h in ipairs(pending) do
                if not h.cancelled and h.at <= NOW + 1e-9 then
                    if h.period then h.at = h.at + h.period else h.cancelled = true end
                    h.cb()
                end
            end
        end
    end
    GearRackEngine = { TimerPool = {} }
    GearRackEngineFrame = { Show = function() end, Hide = function() end }
    DEFAULT_CHAT_FRAME = { AddMessage = function() end }
'''


class TimerOwnerTests(unittest.TestCase):
    """Repeating timers re-armed with a new C_Timer handle every tick, and each start
    built a new closure: the only steady garbage GearRack made."""

    def lua(self):
        lua = runtime()
        lua.execute(TIMER_MOCK + between(EQUIPMENT, "--[[ Timer maintenance", "--[[ old OnUpdates"))
        return lua

    def test_repeating_timer_ticks_on_one_handle(self):
        lua = self.lua()
        lua.execute('''
            GearRackEngine.CreateTimer("Tick", function() table.insert(fired, NOW) end, 1, 1)
            GearRackEngine.StartTimer("Tick")
            Advance(60)
        ''')
        self.assertEqual(len(lua.eval("fired")), 60)
        self.assertEqual(lua.eval("made"), 1)

    def test_short_first_wait_then_one_ticker(self):
        lua = self.lua()
        lua.execute('''
            GearRackEngine.CreateTimer("Tick", function() table.insert(fired, NOW) end, 1, 1)
            GearRackEngine.StartTimer("Tick", 0)
            Advance(10.5)
        ''')
        self.assertEqual(len(lua.eval("fired")), 11)
        self.assertEqual(lua.eval("made"), 2)

    def test_stopped_timer_never_fires_again(self):
        lua = self.lua()
        lua.execute('''
            GearRackEngine.CreateTimer("Once", function() table.insert(fired, "once") end, 1)
            GearRackEngine.CreateTimer("Tick", function() table.insert(fired, "tick") end, 1, 1)
            GearRackEngine.StartTimer("Once"); GearRackEngine.StartTimer("Tick")
            Advance(.5)
            GearRackEngine.StopTimer("Once"); GearRackEngine.StopTimer("Tick")
            Advance(5)
        ''')
        self.assertEqual(len(lua.eval("fired")), 0)
        self.assertIsNone(lua.eval('GearRackEngine.TimerEnabled("Tick")'))

    def test_timer_restarting_itself_runs_on_the_new_wait(self):
        lua = self.lua()
        lua.execute('''
            local n = 0
            GearRackEngine.CreateTimer("Self", function()
                n = n + 1; table.insert(fired, NOW)
                if n == 1 then GearRackEngine.StartTimer("Self", 3) end
            end, 1, 1)
            GearRackEngine.StartTimer("Self")
            Advance(4.5)
        ''')
        # 1 s, then the 3 s wait it chose (4 s), not the old ticker at 2 s and 3 s.
        self.assertEqual([round(t, 2) for t in lua.eval("fired").values()], [1.0, 4.0])

    def test_one_shot_reports_errors_and_stops(self):
        lua = self.lua()
        lua.execute('''
            GearRackEngine.CreateTimer("Bad", function() table.insert(fired, NOW); error("x") end, 1, 1)
            GearRackEngine.StartTimer("Bad")
            Advance(5)
        ''')
        self.assertEqual(len(lua.eval("fired")), 1)

    def test_control_frame_check_stops_on_an_unlocked_bar(self):
        lua = self.lua()
        lua.execute('''
            local user = "Me"
            GearRackDB = { bars = { Me = { Locked = "OFF" } } }
            function IsAltKeyDown() end
            GearRackUI_ControlFrame = { Hide = function() table.insert(fired, "hide") end }
        ''' + between(EQUIPMENT, "function GearRackEngine.ControlFrame()", "-- Only the current source") + '''
            GearRackEngine.CreateTimer("ControlFrame", GearRackEngine.ControlFrame, .75, 1)
            GearRackEngine.StartTimer("ControlFrame")
            Advance(10)
        ''')
        self.assertIsNone(lua.eval('GearRackEngine.TimerEnabled("ControlFrame")'))
        self.assertEqual(len(lua.eval("fired")), 0)


TRINKETS = (ROOT / "src/Trinkets.lua").read_text("utf-8")


class InventoryEventTests(unittest.TestCase):
    """UNIT_INVENTORY_CHANGED also fires for durability, charges and ammo. Every one
    rebuilt the trinket view and the whole bar, even when no worn item changed."""

    def lua(self):
        lua = runtime()
        lua.execute(r'''
            GearRack.initialized = true
            GearRack.EquippedItemIDs, GearRack.BagContainerIDs = {}, {}
            WORN = { [13] = 11810, [16] = 12783 }
            function GetInventoryItemID(_, s) return WORN[s] end
            function GearRack.EquippedGUID(s) return WORN[s] and ("0x4" .. s .. WORN[s]) end
            local equippedGUID = GearRack.EquippedGUID
            function GearRack.InvalidateBag() table.insert(calls, "bags") end
            function GearRack.Wake() end
            GearRackTrinkets = { UpdateWornTrinkets = function() table.insert(calls, "trinkets") end }
            GearRackEngine = {}
        ''' + between(CORE, "local equippedSlotIDs,equippedGUIDs", "-- Global cache notifications")
          + between(CORE, "function GearRack.UIEvent(", "-- Measured in play"))
        return lua

    def test_unchanged_equipment_skips_the_views(self):
        lua = self.lua()
        first = lua.eval('GearRack.UIEvent("UNIT_INVENTORY_CHANGED", "player")')
        lua.execute("calls = {}")
        second = lua.eval('GearRack.UIEvent("UNIT_INVENTORY_CHANGED", "player")')
        self.assertTrue(first)
        self.assertFalse(second)
        self.assertEqual(list(lua.eval("calls").values()), [])

    def test_a_new_item_refreshes_the_views(self):
        lua = self.lua()
        lua.eval('GearRack.UIEvent("UNIT_INVENTORY_CHANGED", "player")')
        lua.execute("calls = {}; WORN[13] = 19406")
        self.assertTrue(lua.eval('GearRack.UIEvent("UNIT_INVENTORY_CHANGED", "player")'))
        self.assertEqual(list(lua.eval("calls").values()), ["bags", "trinkets"])

    def test_worn_trinket_spirals_redraw_only_on_change(self):
        lua = runtime()
        lua.execute(r'''
            CD = { [13] = { 900, 180, 1 }, [14] = { 0, 0, 1 } }
            function GearRack.GetInventoryCooldown(s) return CD[s][1], CD[s][2], CD[s][3] end
            function CooldownFrame_SetTimer(f) table.insert(calls, f.name) end
            GearRackTrinkets_Trinket0Cooldown, GearRackTrinkets_Trinket1Cooldown = { name = "top" }, { name = "bottom" }
            GearRackTrinkets = {}
        ''' + between(TRINKETS, "-- Every global cooldown asks again", "function GearRackTrinkets.UpdateMenuCooldowns()") + r'''
            for i = 1, 5 do GearRackTrinkets.UpdateWornCooldowns(1) end
            CD[14] = { 950, 120, 1 }
            GearRackTrinkets.UpdateWornCooldowns(1)
        ''')
        self.assertEqual(list(lua.eval("calls").values()), ["top", "bottom", "bottom"])


class LeanDataTests(unittest.TestCase):
    """Retired settings, the saved combat-queue scratch set, the ClassicAPI 1.15.16
    enchant workaround and the English "Bag" subtype check."""

    def test_retired_saved_data_is_cleared_on_load(self):
        lua = runtime()
        lua.execute(r'''
            GearRackUI = { DefaultSettings = {} }
            GearRackDB = { settings = { BigCooldown = "ON", CooldownNumbers = "ON", QualityBorders = "ON",
                    TinyTooltip = "OFF", Minimap = {}, Notify = "ON" },
                trinketOptions = { CooldownCount = "ON", LargeCooldown = "ON", TinyTooltips = "OFF", KeepOpen = "OFF" },
                sets = { ["Me of R"] = { Sets = { ["GearRackEngine-CombatQueue"] = { [1] = {} }, Tank = { icon = "x" } } } } }
        ''' + between(CORE, "function GearRack.NormalizeSavedData()", "-- Narrow public queries")
          + " GearRack.NormalizeSavedData()")
        for key in ("BigCooldown", "CooldownNumbers", "QualityBorders", "TinyTooltip", "Minimap"):
            self.assertIsNone(lua.eval(f"GearRackDB.settings.{key}"), key)
        for key in ("CooldownCount", "LargeCooldown", "TinyTooltips"):
            self.assertIsNone(lua.eval(f"GearRackDB.trinketOptions.{key}"), key)
        self.assertIsNone(lua.eval('GearRackDB.sets["Me of R"].Sets["GearRackEngine-CombatQueue"]'))
        self.assertEqual(lua.eval('GearRackDB.settings.Notify'), "ON")
        self.assertEqual(lua.eval('GearRackDB.trinketOptions.KeepOpen'), "OFF")
        self.assertEqual(lua.eval('GearRackDB.sets["Me of R"].Sets.Tank.icon'), "x")

    def test_worn_enchant_time_comes_from_classicapi_alone(self):
        lua = runtime()
        lua.execute(r'''
            C_Spell = { GetSpellTexture = function() return "icon" end }
            C_Item = { GetItemTempEnchantInfo = function() return true, 1500000, 0, 2630 end,
                GetEnchantInfo = function() return { name = "Deadly Poison", spellID = 11355 } end }
            function GetWeaponEnchantInfo() table.insert(calls, "native"); return 1, 60000, 0 end
            function SecondsToTimeAbbrev(s) return string.format("%d m", math.ceil(s / 60)) end
            local function region(n) return { SetTexture = function() end, SetText = function(_, t) textures[n] = t end,
                SetTextColor = function() end, Show = function() end } end
            BUTTON = { enchantOverlay = { icon = region("icon"), duration = region("time"), iconFrame = region("f"),
                Hide = function() end, Show = function() end, IsShown = function() return true end } }
        ''' + between(EQUIPMENT, "local function format_enchant_duration(", "local equippedEnchantLocations")
          + " update_enchant(BUTTON, { equipmentSlotIndex = 17 })")
        self.assertEqual(lua.eval("textures.time"), "25m")
        self.assertEqual(list(lua.eval("calls").values()), [])

    def bank_bag(self, family):
        lua = runtime()
        lua.execute(r'''
            function GetInventoryItemLink() return "|Hitem:4500:0:0:0|h[Traveler's Backpack]|h" end
            function ContainerIDToInventoryID(b) return b + 63 end
            -- 1.12 order: name, link, quality, minLevel, type, subType.
            function GetItemInfo() return "Traveler's Backpack", nil, 1, 1, "Container", FAMILY == 0 and "Bag" or "Herb Bag" end
            C_Container = { GetContainerNumFreeSlots = function() return 0, 0 end }
            C_Item = { GetItemFamily = function() return FAMILY end }
            GearRackUIText = { INVTYPE_CONTAINER = "Bag" }
            GearRackEngine = {}
        ''' + between(EQUIPMENT, "function GearRackEngine.ValidBag(bagid)", "function GearRackEngine.FindSpaceInBag("))
        lua.execute(f"FAMILY = {family}")
        return lua.eval("GearRackEngine.ValidBag(6)")

    def test_general_bank_bag_takes_items(self):
        self.assertTrue(self.bank_bag(0))

    def test_specialty_bank_bag_is_skipped_by_family(self):
        # A herb bag: family 32, subtype "Herb Bag".
        self.assertFalse(self.bank_bag(32))


class HookTests(unittest.TestCase):
    """Eleven old*/new* hook globals leaked; observers now post-hook."""

    def test_hooks_install_without_globals_and_keep_the_native_chain(self):
        lua = runtime()
        lua.execute(r'''
            hooked = {}
            function hooksecurefunc(name) table.insert(hooked, name) end
            function PaperDollItemSlotButton_OnClick(b) table.insert(calls, "native click " .. tostring(b)) end
            function CharacterModelFrame_OnMouseUp(b) table.insert(calls, "native model " .. tostring(b)) end
            function PaperDollItemSlotButton_OnEnter() end
            function GossipTitleButton_OnClick(a) table.insert(calls, "native gossip " .. tostring(a)) end
            function IsAltKeyDown() end
            GearRackUI = {}
            GearRackDB = { settings = { EnableEvents = "OFF" } }
            this = { RegisterEvent = function() end }
            local before = {}
            for k in pairs(_G) do before[k] = true end
            BEFORE = before
        ''' + between(EQUIPMENT, "-- Character sheet and gossip hooks", "--[[ Inv Movement ]]") + r'''
            GearRackUI_OnLoad()
            PaperDollItemSlotButton_OnClick("LeftButton")
            CharacterModelFrame_OnMouseUp("LeftButton")
            GossipTitleButton_OnClick("x")
            LEAKED = {}
            for k in pairs(_G) do
                if not BEFORE[k] and (string.find(k, "^old") or string.find(k, "^new") or string.find(k, "Original")) then
                    table.insert(LEAKED, k)
                end
            end
        ''')
        self.assertEqual(list(lua.eval("LEAKED").values()), [])
        self.assertEqual(list(lua.eval("calls").values()),
                         ["native click LeftButton", "native model LeftButton", "native gossip x"])
        self.assertEqual(sorted(lua.eval("hooked").values()),
                         ["PaperDollFrame_OnHide", "PaperDollFrame_OnShow", "PaperDollItemSlotButton_OnEnter",
                          "UseAction", "UseInventoryItem"])


class NotifyEventTests(unittest.TestCase):
    """An enabled GEARRACK_NOTIFY event switched "Notify when ready" back on (with a
    chat line) every time events re-enabled, even after the player turned it off."""

    def lua(self, notify):
        lua = runtime()
        lua.execute(r'''
            local user = "Me"
            GearRackUIText = { READY = "%s ready!", READYTHIRTY = "%s ready soon!" }
            GearRackDB = { settings = { Notify = "''' + notify + r'''", NotifyThirty = "OFF", EnableEvents = "ON" },
                events = { Insignia = { trigger = "GEARRACK_NOTIFY", delay = 0, script = "" } },
                bars = { Me = { Events = { Insignia = { enabled = 1, setname = "PvP" } } } } }
            GearRackUI = { Register = {} }
            messages = {}
            DEFAULT_CHAT_FRAME = { AddMessage = function(_, m) table.insert(messages, m) end }
            GearRackUI_SetsFrame = { IsShown = function() end }
            GearRackUIFrame = { RegisterEvent = function() end }
            GearRackUI_RegisterFrame = { RegisterEvent = function() end }
            function GearRackUI_DisableAllEvents() end
            function GearRack.Alert(t) table.insert(calls, "alert:" .. t) end
            function GearRackUI_RegisterFrame_OnEvent(ev, a) table.insert(calls, ev .. ":" .. a) end
        ''' + between(EQUIPMENT, "-- enables a specific eventname", "-- disables a sepcific eventname")
          + between(EQUIPMENT, "function GearRackUI_EnableAllEvents()", "-- Suspend event watching")
          + between(CORE, "-- Ready notices feed the alert", "function GearRack.GetInventoryCooldown(")
          + between(EQUIPMENT, "-- Ready alert for a used item", "-- Refresh only visible cooldown numbers") + r'''
            GearRackUI_EnableAllEvents()
            GearRack.ItemReady("Insignia of the Horde", false)
        ''')
        return lua

    def test_event_fires_without_turning_alerts_back_on(self):
        lua = self.lua("OFF")
        self.assertEqual(lua.eval("GearRackDB.settings.Notify"), "OFF")
        self.assertEqual(list(lua.eval("calls").values()), ["GEARRACK_NOTIFY:Insignia of the Horde"])
        self.assertEqual(list(lua.eval("messages").values()), [])

    def test_control_alerts_on_shows_the_alert_and_fires_the_event(self):
        lua = self.lua("ON")
        self.assertEqual(list(lua.eval("calls").values()),
                         ["alert:Insignia of the Horde ready!", "GEARRACK_NOTIFY:Insignia of the Horde"])


if __name__ == "__main__":
    unittest.main()
