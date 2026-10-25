"""Load AutoBG files the way the client does: each chunk gets ("AutoBG", ns).

ForgeUI.lua fills ns.UI, which the Spy and Options files read at load;
AutoBG_AlertCard.lua adds ns.CreateAlertCard for the Spy and flag alerts.
"""
from pathlib import Path
import os

ROOT = Path(os.environ["VANILLAFORGE_ADDON_ROOT"])
FORGEUI = (ROOT / "ForgeUI.lua").read_text("utf-8-sig")
ALERT_CARD = (ROOT / "AutoBG_AlertCard.lua").read_text("utf-8-sig")

LOADER = r'''
function __load_addon_file(source, name)
    __addon_ns = __addon_ns or {}
    local chunk = assert(loadstring(source, name))
    return chunk("AutoBG", __addon_ns)
end
'''


def load(lua, source, name):
    """Run one addon file with the shared namespace, loading the shared kits
    (ForgeUI and the alert card) first."""
    if not lua.eval('__load_addon_file ~= nil'):
        lua.execute(LOADER)
        lua.globals().__load_addon_file(FORGEUI, "ForgeUI.lua")
        lua.globals().__load_addon_file(ALERT_CARD, "AutoBG_AlertCard.lua")
    lua.globals().__load_addon_file(source, name)
