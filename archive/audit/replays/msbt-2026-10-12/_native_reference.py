"""Extract the selected client's native UI references into temporary storage.

No Blizzard source is vendored in the repository. MPQs and addon files are read
only; the temporary reference tree is removed when this Python process exits.
"""
from pathlib import Path
import hashlib
import json
import os
import sys
import tempfile

WORKSPACE = Path(__file__).resolve().parents[3]
selection = os.environ.get("VANILLAFORGE_ADDON_ROOT") or os.environ.get("MSBT_AUDIT_SOURCE")
if not selection:
    raise RuntimeError("Set VANILLAFORGE_ADDON_ROOT to the selected MikScrollingBattleText checkout")
ROOT = Path(selection).resolve()
if not (ROOT / "MikScrollingBattleText.toc").is_file():
    raise RuntimeError(f"Selected MSBT TOC does not exist: {ROOT}")
CLIENT = ROOT.parents[2]
sys.path.insert(0, str(WORKSPACE / "tools"))
from octowow_client_manifest import MPQArchive

_storage = tempfile.TemporaryDirectory(prefix="vanillaforge-msbt-native-")
NATIVE = Path(_storage.name)
GLOBAL_STRINGS = []
PROVENANCE = {}
targets = ["UIDropDownMenu.lua", "ColorPickerFrame.xml", "UIParent.lua",
           "UIPanelTemplates.xml", "OptionsFrameTemplates.xml", "UIDropDownMenu.xml"]
order = ["base.MPQ", "dbc.MPQ", "fonts.MPQ", "interface.MPQ", "misc.MPQ",
         "model.MPQ", "sound.MPQ", "speech.MPQ", "terrain.MPQ", "texture.MPQ", "wmo.MPQ",
         "patch.MPQ", "patch-1.mpq", "patch-2.mpq", "patch-3.mpq", "patch-4.mpq",
         "patch-5.mpq", "patch-O.mpq", "patch-Y.MPQ"]
for archive_name in order:
    path = CLIENT / "Data" / archive_name
    if not path.is_file():
        continue
    archive = MPQArchive(path)
    try:
        for name in targets + ["GlobalStrings.lua"]:
            blob = archive.read_file("Interface\\FrameXML\\" + name)
            if blob is None:
                continue
            filename = name
            if name == "GlobalStrings.lua":
                filename = f"globals-{len(GLOBAL_STRINGS):02d}-{archive_name.rsplit('.', 1)[0]}.lua"
                GLOBAL_STRINGS.append(NATIVE / filename)
            (NATIVE / filename).write_bytes(blob)
            PROVENANCE[filename] = {"archive": archive_name, "bytes": len(blob),
                                    "sha256": hashlib.sha256(blob).hexdigest()}
    finally:
        archive.close()
missing = [name for name in targets if not (NATIVE / name).is_file()]
if missing or not GLOBAL_STRINGS:
    raise RuntimeError(f"Required deployed FrameXML references are missing: {missing}; globals={len(GLOBAL_STRINGS)}")


def output_directory():
    output = Path(os.environ.get("MSBT_AUDIT_OUTPUT", str(WORKSPACE / ".private/msbt-audit-current"))).resolve()
    if output == CLIENT or CLIENT in output.parents:
        raise ValueError("Audit output must remain outside the selected game directory")
    output.mkdir(parents=True, exist_ok=True)
    return output


if __name__ == "__main__":
    print(json.dumps(PROVENANCE, indent=2))
