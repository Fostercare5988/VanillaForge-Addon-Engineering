"""Exercise the complete slide watcher with explicit widget/state owners."""
from pathlib import Path
import os
import unittest
from lupa.lua51 import LuaRuntime

SOURCE = (Path(os.environ["VANILLAFORGE_ADDON_ROOT"]) /
          "Modules/FostercareGroup.lua").read_text("utf-8-sig")


def runtime():
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute('''
        FostercareGroup={_tmpSlideList={'first'},_slidingCount=1}
        frames={first={_daSliding=true}}
    ''')
    body = SOURCE[SOURCE.index('local function _SlideTick()'):
                  SOURCE.index('-- One-shot reflow runner')]
    lua.execute('''
        local _watch={}
        function _watch:SetScript(name,fn) assert(name=='OnUpdate'); self.callback=fn end
        local function _GetIconFrame(key) return frames[key] end
    ''' + body + '''
        _watch:SetScript('OnUpdate',_SlideTick)
        function tick() assert(_watch.callback); _watch.callback() end
        function ticking() return _watch.callback~=nil end
    ''')
    return lua


class GroupSlideTests(unittest.TestCase):
    def test_active_icon_keeps_watch_until_animation_finishes(self):
        runtime().execute('''
            tick(); assert(FostercareGroup._slidingCount==1 and ticking(),
                'active icon was removed from its slide watcher')
            frames.first._daSliding=false; tick()
            assert(FostercareGroup._slidingCount==0 and not ticking())
        ''')

    def test_unrelated_global_frame_cannot_keep_finished_icon_active(self):
        runtime().execute('''
            f={_daSliding=true}; frames.first._daSliding=false; tick()
            assert(FostercareGroup._slidingCount==0 and not ticking(),
                'foreign global frame owns the icon lifecycle')
        ''')

    def test_removed_frame_is_discarded_while_other_slide_survives_swap(self):
        runtime().execute('''
            frames.first=nil; frames.second={_daSliding=true}
            FostercareGroup._tmpSlideList={'first','second'}; FostercareGroup._slidingCount=2
            tick()
            assert(FostercareGroup._slidingCount==1 and ticking())
            assert(FostercareGroup._tmpSlideList[1]=='second' and FostercareGroup._tmpSlideList[2]==nil)
        ''')

    def test_pending_reflow_keeps_delivery_and_empty_watch_stops(self):
        runtime().execute('''
            frames.first._daSliding=false; FostercareGroup_NeedReflow=true
            tick(); assert(ticking())
            FostercareGroup_NeedReflow=nil; tick(); assert(not ticking())
        ''')


if __name__ == '__main__':
    unittest.main()
