"""UNIT_TARGET for a token that has no "target" child must not error, 2026-11-01.

Seen in Warsong Gulch (!ErrorLog): AutoBG_Targets.lua:1806 "Unknown unit name:
npctarget". The gossip NPC token "npc" also sends UNIT_TARGET, and the handler
appended "target" to every token. Fails on the old handler.
"""
import unittest

from test_targets_guid_events import runtime, fire


class UnitTargetTokens(unittest.TestCase):
    def test_the_gossip_npc_token_is_ignored(self):
        lua = runtime()
        lua.execute('''
            local exists = UnitExists
            function UnitExists(u)
                if u == "npctarget" then error("Unknown unit name: npctarget") end
                return exists(u)
            end
        ''')
        fire(lua, "UNIT_TARGET", "npc")

    def test_a_group_members_target_is_still_observed(self):
        lua = runtime()
        lua.execute('''
            asked = {}
            local exists = UnitExists
            function UnitExists(u) asked[#asked + 1] = u; return exists(u) end
        ''')
        fire(lua, "UNIT_TARGET", "raid3")
        self.assertEqual(lua.eval("asked[1]"), "raid3target")


if __name__ == "__main__":
    unittest.main()
