"""Actual event, snapshot and delivery bodies; no native rendering claim."""
from pathlib import Path
import os
import re
import unittest
from lupa.lua51 import LuaRuntime

ADDON = Path(os.environ["VANILLAFORGE_ADDON_ROOT"])
SOURCE = (ADDON / "Modules/FostercareConditions.lua").read_text("utf-8-sig")


def runtime():
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(r'''
        now, clockReads, equippedReads, bagReads = 100, 0, 0, 0
        bagContents = 'first'
        function GetTime() clockReads = clockReads + 1; return now end
        function UnitExists(unit) return unit == 'player' and 1 or nil end
        function GetEquippedItem(unit, slot) equippedReads = equippedReads + 1; return {itemId=slot} end
        function GetBagItems() bagReads = bagReads + 1; return bagContents end
        function GetAmmo() return 0, 0 end
        function CreateFrame(kind, name)
            assert(kind == 'Frame' and name == 'FostercareConditionsEventFrame')
            local frame = {events={}, scripts={}}
            function frame:RegisterEvent(ev) self.events[ev] = true end
            function frame:SetScript(script, fn) self.scripts[script] = fn end
            eventFrame = frame; return frame
        end
        function fire(ev, first, second)
            assert(eventFrame.events[ev]); this,event,arg1,arg2=eventFrame,ev,first,second
            eventFrame.scripts.OnEvent()
        end
        FostercareConditions = {_hasAnyItemLogic=true, _daItemSnapshotDirty=false}
        FostercareConditions_SlideMgr = {active={}}
        function FostercareConditions:ProcessPendingAuraScans() end
        function FostercareConditions_WarriorProcTick() end
        function FostercareConditions_UpdateTimeText() end
        abilityPasses, auraPasses, customPasses = 0, 0, 0
        function FostercareConditions:EvaluateAbilities(logic, time)
            abilityPasses = abilityPasses + 1
            if onAbility then onAbility() end
        end
        function FostercareConditions:EvaluateAuras()
            auraPasses = auraPasses + 1
            if onAura then onAura() end
        end
        function FostercareConditions:EvaluateCustom()
            customPasses = customPasses + 1
            if onCustom then onCustom() end
            return true
        end
        _acc,_textAccum,_timeEvalAccum,_distAccum,_teFastAccum=0,0,0,0,0
        _teFastActive=false
    ''')
    slots = '\n'.join(re.findall(r'local INV_SLOT_\w+ = \d+', SOURCE))
    helpers = SOURCE[SOURCE.index('local _TrinketFirstMemory = {}'):SOURCE.index('local function _ScanPlayerItemInstances(data)')]
    request = SOURCE[SOURCE.index('function FostercareConditions_RequestEvaluate()'):SOURCE.index('function FostercareConditions:EvaluateAbilities(')]
    tick = SOURCE[SOURCE.index('function FostercareConditions_OnUpdate(dt)'):SOURCE.index('-- Drive the update loop')]
    events = SOURCE[SOURCE.index('local eventFrame = CreateFrame("Frame", "FostercareConditionsEventFrame")'):]
    lua.execute('''
        local dirty_ability,dirty_aura,dirty_target,dirty_power,dirty_ability_time=false,false,false,false,false
        local _hasAnyAbilityTimeLogic,_hasAnyAuraTimeLogic,_hasAnyTargetMods_Ability,_hasAnyTargetMods_Aura=false,false,false,false
        local _hasAnyCustomLogic=false
    ''' + slots + '\n' + helpers + '\n' + request + '\n' + tick + '\n' + events + r'''
        function snapshot() return _GetPlayerItemSnapshot().bags end
        function enableCustom() _hasAnyCustomLogic=true end
        function resetFlags()
            dirty_ability,dirty_aura,dirty_target,dirty_power,dirty_ability_time=false,false,false,false,false
        end
    ''')
    return lua


class ConditionDeliveryTests(unittest.TestCase):
    def test_bag_change_after_snapshot_within_fifty_milliseconds_is_not_lost(self):
        runtime().execute('''
            fire('BAG_UPDATE',0); assert(snapshot()=='first')
            now=100.02; bagContents='second'; fire('BAG_UPDATE',1)
            assert(snapshot()=='second','bag notification after a delivered snapshot was discarded')
            assert(bagReads==2)
        ''')

    def test_equipment_then_bag_change_keeps_both_snapshots_current(self):
        runtime().execute('''
            fire('UNIT_INVENTORY_CHANGED_GUID','0xPLAYER',1); assert(snapshot()=='first')
            now=100.01; bagContents='second'; fire('BAG_UPDATE',0)
            assert(snapshot()=='second','equipment notification suppressed a later bag change')
        ''')

    def test_bag_burst_coalesces_without_clock_reads_or_eager_scans(self):
        runtime().execute('''
            for i=1,200 do fire('BAG_UPDATE',i%5) end
            assert(clockReads==0,'bag invalidation reads a clock despite sharing one pending snapshot')
            assert(bagReads==0 and equippedReads==0)
            assert(snapshot()=='first'); assert(bagReads==1 and equippedReads==19)
            assert(snapshot()=='first'); assert(bagReads==1 and equippedReads==19)
        ''')

    def test_ability_callback_can_request_a_subsequent_pass(self):
        runtime().execute('''
            fire('UNIT_HEALTH','player')
            onAbility=function() onAbility=nil; FostercareConditions_RequestEvaluate() end
            FostercareConditions_OnUpdate(.1); FostercareConditions_OnUpdate(.1)
            assert(abilityPasses==2,'ability evaluation erased reentrant invalidation')
            FostercareConditions_OnUpdate(.1); assert(abilityPasses==2)
        ''')

    def test_aura_callback_can_request_a_subsequent_pass(self):
        runtime().execute('''
            fire('UNIT_HEALTH','player')
            onAura=function() onAura=nil; FostercareConditions_RequestEvaluate() end
            FostercareConditions_OnUpdate(.1); FostercareConditions_OnUpdate(.1)
            assert(auraPasses==2,'aura evaluation erased reentrant invalidation')
        ''')

    def test_custom_callback_can_invalidate_an_otherwise_idle_pass(self):
        runtime().execute('''
            enableCustom()
            onCustom=function() onCustom=nil; FostercareConditions_RequestEvaluate() end
            FostercareConditions_OnUpdate(.1); FostercareConditions_OnUpdate(.1)
            assert(abilityPasses==1 and auraPasses==1,'custom evaluation erased new work')
        ''')

    def test_sliding_keeps_ability_updates_and_stops_when_slide_finishes(self):
        runtime().execute('''
            FostercareConditions_SlideMgr.active.icon=true
            fire('UNIT_HEALTH','player'); FostercareConditions_OnUpdate(.03)
            FostercareConditions_OnUpdate(.03); assert(abilityPasses==2)
            FostercareConditions_SlideMgr.active.icon=nil
            FostercareConditions_OnUpdate(.1); FostercareConditions_OnUpdate(.1)
            assert(abilityPasses==3)
        ''')


if __name__ == '__main__':
    unittest.main()
