"""Turn the author's saved settings into the defaults a new user gets.

    python -B tools/export_defaults.py --tweaks "<...>/SavedVariables/FostercareTweaks.lua" \
        [--addons "<AddOns folder>"]

Reads FostercareTweaks_Config from the author's SavedVariables file and writes
<AddOns>/FostercareTweaks/Defaults.lua. Run it again after changing settings in
game (and /reload, so the file is saved). AutoLazy keeps its defaults in
AutoLazy.lua (a handful of values); edit them there.

Left out on purpose: the chat history in FostercareTweaks_Cache (private), and
the spell and item lists of the extra action bars (they depend on the class).
Pixel positions are filtered at first run by FostercareTweaks (Core.lua), so a
smaller screen never gets a frame off screen.
"""
import argparse
import datetime
import re
from pathlib import Path

from lupa.lua51 import LuaRuntime

DEFAULT_ADDONS = Path(r"C:\Users\Fostercare\Desktop\client-2026-10-10\Interface\AddOns")


def load_config(path):
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(Path(path).read_text("utf-8-sig"))
    config = lua.globals().FostercareTweaks_Config
    if config is None:
        raise SystemExit("no FostercareTweaks_Config in " + str(path))
    return config


def to_python(value):
    if hasattr(value, "items"):
        return {k: to_python(v) for k, v in value.items()}
    return value


def clean(config):
    config.pop("Social Colors", None)
    bars = config.get("actionbars", {}).get("bars", {})
    for bar in bars.values():
        bar.pop("actions", None)
    # A bar with nothing left to say is not worth a line.
    for name in [n for n, bar in bars.items() if not bar]:
        del bars[name]
    return config


def number(value):
    if isinstance(value, float):
        text = ("%.2f" % value).rstrip("0").rstrip(".")
        return text if text not in ("", "-0") else "0"
    return str(value)


def lua_key(key):
    if isinstance(key, str) and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
        return key
    if isinstance(key, str):
        return '["%s"]' % key.replace("\\", "\\\\").replace('"', '\\"')
    return "[%s]" % number(key)


def lua_value(value, depth=0):
    pad = "    " * (depth + 1)
    if isinstance(value, dict):
        if not value:
            return "{}"
        rows = [pad + lua_key(k) + " = " + lua_value(v, depth + 1) + "," for k, v in sorted(value.items(), key=lambda kv: str(kv[0]))]
        return "{\n" + "\n".join(rows) + "\n" + "    " * depth + "}"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return '"%s"' % value.replace("\\", "\\\\").replace('"', '\\"')
    return number(value)


def render(config):
    stamp = datetime.date.today().isoformat()
    return (
        "-- FostercareTweaks: the settings a new character starts with.\n"
        "-- Generated %s from the author's own settings by VanillaForge/tools/export_defaults.py;\n"
        "-- do not edit by hand, run the tool again. Applied once, on a character that has no\n"
        "-- saved settings yet (Core.lua), never over existing ones. Chat history and the\n"
        "-- extra bars' spell and item lists are not included.\n"
        "FostercareTweaks_Defaults = %s\n" % (stamp, lua_value(config))
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--tweaks", required=True, help="the author's FostercareTweaks.lua SavedVariables file")
    parser.add_argument("--addons", default=str(DEFAULT_ADDONS), help="the AddOns folder")
    args = parser.parse_args()
    config = clean(to_python(load_config(args.tweaks)))
    out = Path(args.addons) / "FostercareTweaks" / "Defaults.lua"
    # The addon's files use CRLF.
    out.write_bytes(render(config).replace("\n", "\r\n").encode("utf-8"))
    print("wrote %s (%d settings)" % (out, len(config)))


if __name__ == "__main__":
    main()
