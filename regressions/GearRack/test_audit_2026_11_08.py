"""GearRack audit of 2026-11-08: reproductions that fail on the audited code
(5467148), and tests for the paths the fixes moved.

The whole addon logs in (gr_env.logged_in) with the client stubbed: a Rogue,
empty bags, every other client global inert. The tests prove what GearRack's
Lua asks for and how often, not what the client draws or how the server answers.
"""
import unittest
import gr_env


class RelicsEquipFromTheFlyout(unittest.TestCase):
    """The flyout (GearRackUI.Indexes) offers relics in the ranged slot; the engine's
    own slot table (GearRackEngine.SlotInfo) had no INVTYPE_RELIC, so picking one
    said "That item cannot be equipped in this slot." Two tables held one fact."""

    def test_every_type_the_flyout_offers_the_engine_accepts(self):
        e = gr_env.logged_in()
        refused = e.eval('''(function()
            local out = {}
            for slot, info in pairs(GearRackUI.Indexes) do
                for key in pairs(info) do
                    if string.find(key, "^INVTYPE_") and not GearRackEngine.SlotInfo[slot][key] then
                        out[#out + 1] = slot .. ":" .. key
                    end
                end
            end
            return table.concat(out, ",")
        end)()''')
        self.assertEqual(refused, "")

    def test_a_relic_picked_for_the_ranged_slot_is_requested(self):
        e = gr_env.logged_in('''
            function GetItemInfo(id)
                if tostring(id) == "22401" then
                    return "Test Relic", nil, 2, 1, "Armor", "Relic", 1, "INVTYPE_RELIC", "Interface\\\\Icons\\\\Test"
                end
            end
        ''')
        # Not carried in this world, so the request then ends with "no longer carried".
        e.run('chat = {}; GearRack.RequestItem(18, { id = "22401:0:0", name = "Test Relic" })')
        self.assertNotIn("GearRack: That item cannot be equipped in this slot.", list(e.eval("chat").values()))
        self.assertIn("GearRack: The queued item is no longer carried.", list(e.eval("chat").values()))


class TimerErrorsReachTheErrorHandler(unittest.TestCase):
    """Every GearRack timer ran in pcall and printed its error to chat: !ErrorLog (the
    error handler) never saw it, nor its stack. GearRack.CooldownUpdate caught and
    re-raised, which cut the stack at Core.lua."""

    def test_a_failing_timer_goes_to_the_error_handler_and_stops(self):
        e = gr_env.logged_in()
        e.run('''errors = {}
            GearRackEngine.CreateTimer("Probe", function() error("probe broke") end, 1, 1)
            GearRackEngine.StartTimer("Probe")
            step(1)''')
        self.assertEqual(len(e.eval("errors")), 1)
        self.assertIn("probe broke", e.eval("errors[1]"))
        self.assertFalse(e.eval('GearRackEngine.TimerEnabled("Probe")'))

    def test_a_failing_cooldown_view_reports_and_the_cache_closes(self):
        e = gr_env.logged_in()
        e.run('''errors = {}
            GearRackUI_CooldownUpdate_OnUpdate = function() error("view broke") end
            GearRack.CooldownUpdate()''')
        self.assertEqual(len(e.eval("errors")), 1)
        self.assertIn("view broke", e.eval("errors[1]"))
        self.assertIsNone(e.eval("GearRack.CooldownRead"))


class BankScansOncePerFrame(unittest.TestCase):
    """Each bank BAG_UPDATE, PLAYERBANKSLOTS_CHANGED and GET_ITEM_INFO_RECEIVED for a
    bank item rescanned every bank slot at once. A sort, a stack split or a cold bank
    sends dozens in one frame; one scan per frame is enough."""

    CLIENT = '''
        scans = 0
        function GetContainerNumSlots(bag)
            if bag == -1 then scans = scans + 1; return 1 end
            return 0
        end
        C_Container.GetContainerItemID = function(bag, slot) if bag == -1 and slot == 1 then return 1234 end end
    '''

    def test_a_burst_of_bank_events_scans_the_bank_once(self):
        e = gr_env.logged_in(self.CLIENT)
        e.run('fire("BANKFRAME_OPENED"); step(0.1); scans = 0')
        e.run('''for i = 1, 3 do fire("BAG_UPDATE", 5) end
            fire("BAG_UPDATE", -1)
            fire("PLAYERBANKSLOTS_CHANGED", 1); fire("PLAYERBANKSLOTS_CHANGED", 2)
            for i = 1, 3 do fire("GET_ITEM_INFO_RECEIVED", 1234, true) end
            step(0); step(0.1)''')
        self.assertEqual(e.eval("scans"), 1)

    def test_opening_the_bank_still_reads_it_at_once(self):
        e = gr_env.logged_in(self.CLIENT)
        e.run('fire("BANKFRAME_OPENED")')
        self.assertTrue(e.eval("GearRackUI.BankItemIDs[1234]"))

    def test_a_closed_bank_is_not_scanned(self):
        e = gr_env.logged_in(self.CLIENT)
        e.run('fire("BANKFRAME_OPENED"); fire("BAG_UPDATE", 5); fire("BANKFRAME_CLOSED"); scans = 0; step(0); step(0.1)')
        self.assertEqual(e.eval("scans"), 0)


class TrinketQueueMacros(unittest.TestCase):
    """GearRack.SetTrinketQueue / GearRackTrinkets.SetQueue read Lua 5.0's implicit
    `arg` table; they now take `...`. The macro behaviour stays."""

    def test_on_off_and_a_profile_by_name(self):
        e = gr_env.logged_in()
        e.run('''GearRackCharDB.queues.Profiles = { { "PvP", "123", "456", 0 } }
            GearRack.SetTrinketQueue(0, "SORT", "PvP")
            GearRack.SetTrinketQueue(1, "ON")''')
        self.assertEqual(list(e.eval("GearRackCharDB.queues.Sort[0]").values()), ["123", "456", 0])
        self.assertEqual(e.eval("GearRackCharDB.queues.Enabled[1]"), 1)
        e.run('GearRack.SetTrinketQueue(1, "OFF")')
        self.assertIsNone(e.eval("GearRackCharDB.queues.Enabled[1]"))

    def test_no_action_is_explained_not_an_error(self):
        e = gr_env.logged_in()
        e.run('chat = {}; GearRack.SetTrinketQueue(0)')
        self.assertIn("Second parameter", e.eval("chat[1]"))


class EventScripts(unittest.TestCase):
    """The event-script runner lost its environment probes; what it promises stays:
    a saved script compiles once, an edit recompiles, arg1/arg2 and the event's set
    are seen inside and restored after, errors are named in chat."""

    def setUp(self):
        self.e = gr_env.logged_in()
        self.e.run('''compiles = 0
            local real = loadstring
            loadstring = function(...) compiles = compiles + 1 return real(...) end
            GearRackDB.events.Probe = { trigger = "X", delay = 0, script = "seen = (seen or 0) + 1; got = arg1 .. GearRackUI.EventSetName" }''')

    def test_a_saved_script_compiles_once(self):
        self.e.run('''arg1 = "outer"
            GearRackUI.RunEventScript(GearRackDB.events.Probe.script, "Probe", "Set", "a", "b")
            GearRackUI.RunEventScript(GearRackDB.events.Probe.script, "Probe", "Set", "c", "d")''')
        self.assertEqual(self.e.eval("compiles"), 1)
        self.assertEqual(self.e.eval("seen"), 2)
        self.assertEqual(self.e.eval("got"), "cSet")
        self.assertEqual(self.e.eval("arg1"), "outer")
        self.assertIsNone(self.e.eval("GearRackUI.EventSetName"))

    def test_an_edit_recompiles(self):
        self.e.run('''GearRackUI.RunEventScript(GearRackDB.events.Probe.script, "Probe", "Set", "a")
            GearRackDB.events.Probe.script = "edited = true"
            GearRackUI.RunEventScript(GearRackDB.events.Probe.script, "Probe", "Set", "a")''')
        self.assertEqual(self.e.eval("compiles"), 2)
        self.assertTrue(self.e.eval("edited"))

    def test_a_script_may_run_an_event_inside_itself(self):
        self.e.run('''GearRackDB.events.Outer = { trigger = "X", delay = 0,
                script = "GearRackUI.RunEventScript(GearRackDB.events.Probe.script, 'Probe', 'Inner', 'i') outerSet = GearRackUI.EventSetName" }
            GearRackUI.RunEventScript(GearRackDB.events.Outer.script, "Outer", "Outer", "o")''')
        self.assertEqual(self.e.eval("got"), "iInner")
        self.assertEqual(self.e.eval("outerSet"), "Outer")

    def test_errors_are_named_in_chat(self):
        self.e.run('chat = {}; GearRackUI.RunEventScript("error(\\"bad\\")", "Broken", nil)')
        self.assertIn('GearRack event "Broken"', self.e.eval("chat[1]"))
        self.e.run('chat = {}; GearRackUI.RunEventScript("if then", "Syntax", nil)')
        self.assertIn('GearRack event "Syntax"', self.e.eval("chat[1]"))


if __name__ == "__main__":
    unittest.main()
