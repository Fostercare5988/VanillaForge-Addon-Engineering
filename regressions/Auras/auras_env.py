"""Auras 1.0 (watched auras, split out of FostercareFrames 2026-11-18) on the
shared game model (wowkit) and FostercareFrames' mocks of the stock frames
(ff_env.MOCK).

The game loads Auras before FostercareFrames (alphabetical): `load` does the same,
each with its own namespace (A and F), so FostercareFrames' rows and top right
ask the real Auras.Hidden. `frames=False` leaves FostercareFrames out. The
FostercareFrames folder is the one beside the Auras folder.
"""
from pathlib import Path
import os
import sys
import wowkit

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "FostercareFrames"))
import ff_env  # noqa: E402

ROOT = Path(os.environ["VANILLAFORGE_ADDON_ROOT"])
FRAMES = ROOT.parent / "FostercareFrames"
MOCK = ff_env.MOCK
target = ff_env.target
GLOBALS = ("AurasDB", "Auras", "SLASH_AURAS1", "AurasList", "AurasListName")


def load(saved="", setup="", world=True, frames=True):
    """Auras over `saved` (Lua that sets AurasDB), then FostercareFrames, as the
    rogue Claude logs in with no target; with `world`, the login events fired."""
    lua = wowkit.runtime()
    lua.execute(MOCK)
    lua.execute("unit('player', 'Claude', 'ROGUE')")
    lua.execute(setup)
    wowkit.load_addon(lua, ROOT, "Auras", saved=saved or None)
    lua.execute("A = __addon_ns; __addon_ns = nil")
    if frames:
        wowkit.load_addon(lua, FRAMES, "FostercareFrames")
        lua.execute("F = __addon_ns")
    if world:
        lua.execute('fire("VARIABLES_LOADED") fire("PLAYER_ENTERING_WORLD") runTimers()')
    return lua
