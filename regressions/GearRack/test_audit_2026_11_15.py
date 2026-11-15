"""GearRack regressions for the 2026-11-15 audit.

Events that wait for an item to be ready hear it when the item is ready; the
chat alert's "Notify at 30 sec" choice moves only the alert. Equipped-item
changes come from ClassicAPI's PLAYER_EQUIPMENT_CHANGED (one slot), so the
frequent UNIT_INVENTORY_CHANGED (charges, durability, ammo) reads nothing.

The world is the model of test_audit_2026_11_13. It does not prove the client's
timing.
"""
import unittest
import gr_env
from test_audit_2026_11_13 import world, settle, TIMED

USER = "Claude of Y'Shaarj"

# An enabled GEARRACK_NOTIFY event with a set; its script counts its runs.
NOTIFY_EVENT = r'''
GearRackDB.settings.EnableEvents = "ON"
GearRackDB.sets["%s"].Sets.PvP = { icon = "x" }
GearRackDB.events.Probe = { trigger = "GEARRACK_NOTIFY", delay = 0, script = "runs = (runs or 0) + 1; ranAt = now" }
GearRackDB.bars["%s"].Events.Probe = { enabled = 1, setname = "PvP" }
GearRackUI_SetsFrame:Hide() -- an open Gear sets window pauses events
GearRackUI_EnableAllEvents()
''' % (USER, USER)


class ReadyEvent(unittest.TestCase):
    """With "Notify at 30 sec" on (the default) the GEARRACK_NOTIFY event ran
    30 seconds before the item was ready: the "Insignia" template, which equips
    a set "when the Insignia finishes cooldown", fired early."""

    def used(self, thirty):
        env = world(TIMED + "worn[13] = item(100, '0xT')")
        env.run(NOTIFY_EVENT + "GearRackDB.settings.NotifyThirty = '%s'" % thirty)
        env.run("cooldowns[13] = { now, 120 }; usedAt = now; GearRackUI.OnUseInventoryItem(13)")
        return env

    def test_the_event_waits_for_ready_with_the_early_alert_on(self):
        env = self.used("ON")
        settle(env, 100)
        self.assertIsNone(env.eval("runs"), "nothing at 30 seconds left")
        self.assertIn("ready soon", env.eval("chat[#chat]"))
        settle(env, 25)
        self.assertEqual(env.eval("runs"), 1)
        self.assertGreaterEqual(env.eval("ranAt - usedAt"), 120)

    def test_the_event_runs_once_at_ready_with_the_early_alert_off(self):
        env = self.used("OFF")
        settle(env, 125)
        self.assertEqual(env.eval("runs"), 1)
        self.assertIn("ready!", env.eval("chat[#chat]"))


class AltControls(unittest.TestCase):
    """A locked bar's controls stayed up to 0.75 s after Alt was let go: a ticker
    looked at the key. They now go on ClassicAPI's MODIFIER_STATE_CHANGED."""

    ALT = "alt = 1; function IsAltKeyDown() return alt end; function IsLeftAltKeyDown() return alt end; function IsRightAltKeyDown() end"

    def test_controls_go_when_alt_is_let_go(self):
        env = world(self.ALT)
        env.run("GearRackUI_SlashHandler('lock'); this = GearRackUIInv16; GearRackUI_Inv_OnEnter()")
        self.assertTrue(env.eval("GearRackUI_ControlFrame:IsShown()"))
        env.run("alt = nil; fire('MODIFIER_STATE_CHANGED', 'LALT', 0)")
        self.assertFalse(env.eval("GearRackUI_ControlFrame:IsShown()"))
        self.assertIsNone(env.eval("GearRackEngine.TimerPool.ControlFrame"), "nothing polls the key")

    def test_an_unlocked_bar_keeps_its_controls(self):
        env = world(self.ALT)
        env.run("GearRackUI_SlashHandler('unlock'); alt = nil; fire('MODIFIER_STATE_CHANGED', 'LALT', 0)")
        self.assertTrue(env.eval("GearRackUI_ControlFrame:IsShown()"))


class SavedSweep(unittest.TestCase):
    """Retired keys were cleared one line each, and the schema number nothing read
    was written back every login (KNOWN_PATTERNS KP-64)."""

    def test_keys_nothing_owns_are_cleared_and_the_rest_kept(self):
        env = world("")
        env.run('''GearRackDB.schema, GearRackCharDB.schema = 1, 1
            GearRackDB.settings.BigCooldown, GearRackDB.trinketOptions.TinyTooltips = "ON", "OFF"
            GearRackCharDB.trinkets.ItemsUsed, GearRackDB.Old, GearRackDB.settings.ShowTooltips = {}, {}, "ON"
            GearRack.NormalizeSavedData()''')
        for key in ("GearRackDB.schema", "GearRackCharDB.schema", "GearRackDB.settings.BigCooldown",
                    "GearRackDB.trinketOptions.TinyTooltips", "GearRackCharDB.trinkets.ItemsUsed", "GearRackDB.Old",
                    "GearRackDB.settings.ShowTooltips"):
            self.assertIsNone(env.eval(key), key)
        for key in ("GearRackDB.settings.Notify", "GearRackDB.trinketOptions.KeepOpen", "GearRackCharDB.trinkets.XPos",
                    "GearRackDB.eventsInitialized", "GearRackCharDB.KeepManualTrinkets"):
            self.assertIsNotNone(env.eval(key), key)


class MountTemplates(unittest.TestCase):
    """"Mount(Not ZG/AQ)" ran its script on every aura change; both mount templates
    wake on ClassicAPI's PLAYER_MOUNT_DISPLAY_CHANGED, once per mount or dismount."""

    def test_mount_templates_wake_on_mounting(self):
        env = world("")
        for name in ("Mount", "Mount(Not ZG/AQ)"):
            self.assertEqual(env.eval('GearRackUI_DefaultEvents["%s"].trigger' % name), "PLAYER_MOUNT_DISPLAY_CHANGED", name)


if __name__ == "__main__":
    unittest.main()
