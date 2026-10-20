"""Enemy detection uses DLL events, not English combat-log text (audit 2026-10-19b, P3-14).

NamPower BUFF_ADDED/REMOVED_OTHER and SuperWoW UNIT_CASTEVENT carry GUIDs and
spell IDs, so stealth, trinkets and melee keep the enemy's identity instead of
adding name-only rows. The behavior itself is covered by test_spy_nearby.py and
test_targets_guid_events.py.
"""
from pathlib import Path
import os
import re
import unittest

ROOT = Path(os.environ["VANILLAFORGE_ADDON_ROOT"])
COMBAT_LOG = re.compile(r'RegisterEvent\("CHAT_MSG_(SPELL|COMBAT)_')


class NoChatParsingTests(unittest.TestCase):
    def test_modules_do_not_register_combat_log_chat(self):
        for name in ("AutoBG_Targets.lua", "AutoBG_Spy.lua"):
            source = (ROOT / name).read_text("utf-8-sig")
            self.assertEqual(COMBAT_LOG.findall(source), [], name)

    def test_dll_events_stay_registered(self):
        for name in ("AutoBG_Targets.lua", "AutoBG_Spy.lua"):
            source = (ROOT / name).read_text("utf-8-sig")
            for event in ("UNIT_CASTEVENT", "BUFF_ADDED_OTHER", "BUFF_REMOVED_OTHER"):
                self.assertIn('RegisterEvent("%s")' % event, source, name)


if __name__ == '__main__':
    unittest.main()
