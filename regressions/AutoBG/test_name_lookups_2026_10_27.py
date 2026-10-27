"""Name lookups, 2026-10-27: ClassicAPI finds players by name, so AutoBG no
longer walks the raid and party itself.

- AutoBG_FindPlayerClass (the flag carrier's class color) asks
  C_PlayerCache.GetPlayerInfoByName first: you, your group in range or not,
  players near you and everyone met this session. Only an enemy never seen
  near you comes from the scoreboard.
- A base message that names a player ("Grom has assaulted the Stables!") is
  the player's side when ClassicAPI finds them with UnitTokenFromName; a player
  it cannot find is taken for an enemy, as before. The old name patterns never
  matched "X claims" or "X has assaulted", so this fallback did not work at all.
"""
import unittest
from lupa.lua51 import LuaRuntime

import test_player_state as tps
import test_timer_bars as ttb


class FindPlayerClassTests(unittest.TestCase):
    def runtime(self):
        lua = tps.runtime()
        lua.execute('''
            function UnitName(u) if u == "player" then return "Tester" end end
            function UnitClass() return "Priest", "PRIEST" end
            cacheCalls = 0
            C_PlayerCache = { GetPlayerInfoByName = function(name)
                cacheCalls = cacheCalls + 1
                if name == "Ally" then return "Mage", "MAGE" end
            end }
            function GetNumBattlefieldScores() return 1 end
            function GetBattlefieldScore(i) return "Farenemy", 0, 0, 0, 0, 0, 0, "Orc", "Warrior", "WARRIOR" end
            function GetNumRaidMembers() error("the raid is not walked any more") end
        ''')
        return lua

    def test_known_player_comes_from_the_player_cache(self):
        lua = self.runtime()
        self.assertEqual(lua.eval('AutoBG_FindPlayerClass("Ally")'), "MAGE")

    def test_enemy_never_seen_comes_from_the_scoreboard(self):
        lua = self.runtime()
        self.assertEqual(lua.eval('AutoBG_FindPlayerClass("Farenemy-Realm")'), "WARRIOR")
        self.assertIsNone(lua.eval('AutoBG_FindPlayerClass("Nobody")'))


class MessageFactionTests(unittest.TestCase):
    def runtime(self, prelude):
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute(ttb.BASE + r'''
            AutoBG_Settings.TestAllTimers = false
            function GetRealZoneText() return "Arathi Basin" end
            function IsInInstance() return 1, "pvp" end
            function UnitName(u) if u == "player" then return "Tester" end end
            function GetNumRaidMembers() error("the raid is not walked any more") end
        ''' + prelude)
        lua.execute(ttb.TIMERS)
        lua.execute('local f = AutoBG_TimersEventFrame; f.scripts.OnEvent(f, "PLAYER_ENTERING_WORLD")')
        lua.execute('local f = AutoBG_TimersEventFrame; f.scripts.OnEvent(f, "CHAT_MSG_BG_SYSTEM_NEUTRAL", "Grom has assaulted the Stables!")')
        lua.execute('AutoBG_Timers_UpdateVisibility()')
        return lua.eval('AutoBG_NodeFrame.rows[1].icon.texture')

    def test_group_member_named_in_the_message_is_your_side(self):
        icon = self.runtime('function UnitTokenFromName(n) if n == "Grom" then return "raid3" end end\n'
                            'function UnitFactionGroup(u) return "Alliance" end')
        self.assertTrue(icon.endswith("Stables_Alliance"), icon)

    def test_player_not_found_is_an_enemy(self):
        icon = self.runtime('function UnitTokenFromName() return nil end')
        self.assertTrue(icon.endswith("Stables_Horde"), icon)


if __name__ == "__main__":
    unittest.main()
