"""A swap is not re-issued before the server can have answered, 2026-11-01.

Equips are confirmed by the server. GearRack re-issued a swap 0.3 s after the
last attempt when the slot did not match yet; on a slow connection (a VPN) the
first answer was still on its way, so the repeat swapped the items back. The
wait is now the larger of 0.3 s and twice the latency plus 0.1 s, at most 3 s,
so a normal connection keeps 0.3 s. GetNetStats' third return is the latency in
ms. UNVERIFIED in game: confirm the swap no longer reverts over a slow link.
"""
import unittest
from test_audit_2026_10_22 import env, CORE


def reissues(latency_ms, elapsed, persistent=False):
    e = env(CORE)
    e.run("""
        function GetNetStats() return 0, 0, %d end
        function GetTime() return now end
        now = 100
        function CursorHasItem() return false end
        function UnitIsDeadOrGhost() return false end
        GearRackEngine.AnyLocked = function() return false end
        GearRackEngine.SwapMatches = function() return false end
        GearRackEngine.StartTimer = function() end
        reissued = 0
        GearRackEngine.IterateSwapQueue = function() reissued = reissued + 1 end
        GearRackEngine.SwapRequest = { setname = "PVE", items = {}, deferred = {} }
        GearRackEngine.SwapQueue[1].direction = "BAGTOINV"
        GearRackEngine.SwapQueue[1].started = true
        GearRackEngine.SwapQueue[1].deadline = 120
        GearRackEngine.SwapQueue[1].lastAttempt = 100
        GearRackEngine.SwapQueueOrder = { 1 }
        now = 100 + %s
        GearRackEngine.OnItemLockChanged()
    """ % (latency_ms, elapsed))
    return e.eval("reissued")


class SlowConnectionRetry(unittest.TestCase):
    def test_fast_connection_keeps_the_short_wait(self):
        self.assertEqual(reissues(40, 0.35), 1)
        self.assertEqual(reissues(40, 0.2), 0)

    def test_slow_connection_waits_for_the_server(self):
        # 800 ms latency: the wait is 1.7 s.
        self.assertEqual(reissues(800, 0.35), 0)
        self.assertEqual(reissues(800, 1.5), 0)
        self.assertEqual(reissues(800, 1.75), 1)

    def test_wait_is_capped(self):
        self.assertEqual(reissues(9000, 3.05), 1)


if __name__ == "__main__":
    unittest.main()
