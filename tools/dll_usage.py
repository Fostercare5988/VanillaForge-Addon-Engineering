"""Which DLL functions and events each addon calls (text matches, not proof).

    python -B tools/dll_usage.py [addon ...] [--addons <AddOns folder>] [--json out.json]

Reads the AddOns folder from .private/workspace.json when --addons is not given.
Use it to keep .private/dll-overview-*.md true: after a cleanup, the counts show who still
calls SuperWoW's SpellInfo, UNIT_CASTEVENT, UnitXP and so on. Third-party libs are skipped.
"""
import argparse
import collections
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAMPOWER = (r"\b(GetBagItems?|GetCastInfo|GetEquippedItems?|GetItemIdCooldown|GetItemStatsField|GetItemStats|GetRaidTargets"
            r"|GetSpellIdCooldown|GetSpellModifiers|GetSpellRecField|GetSpellRec|GetTrinkets|GetUnitData|GetUnitField"
            r"|SetLocalRaidTargetIndex|NP_\w+|SPELL_(?:START|GO|CAST|HEAL|ENERGIZE|MISS|FAILED|CHANNEL|DELAYED|QUEUE)\w*"
            r"|AURA_CAST_\w+|AUTO_ATTACK_\w+|BUFF_(?:ADDED|REMOVED)\w*|DEBUFF_(?:ADDED|REMOVED)\w*|UNIT_DIED)\b")
SUPERWOW = (r"\b(SpellInfo|UnitPosition|TrackUnit|UntrackUnit|SetMouseoverUnit|CombatLogAdd|GetPlayerBuffID|UNIT_CASTEVENT"
            r"|RAW_COMBATLOG|GetWeaponEnchantID|UnitNameplate|CursorPosition|Clickthrough|SetAutoloot|ImportFile|ExportFile"
            r"|IsSwimming|GetSpeed|FocusUnit|CanLootUnit|GetQuestIDForLogIndex|GetQuestLinkForID|GetWorldLocMapPosition"
            r"|GetMapPositionWorldLoc|GetMapBoundaries|GetActionText|PingLocation|CREATE_CHATBUBBLE)\b")
UNITXP = r"UnitXP\s*[,(]\s*[\"'](\w+)[\"'](?:\s*,\s*[\"'](\w+)[\"'])?"
CLASSICAPI = r"\b(C_[A-Za-z]+)\.([A-Za-z]+)"
GROUPS = (("nampower", NAMPOWER), ("superwow", SUPERWOW), ("unitxp", UNITXP), ("classicapi", CLASSICAPI))


def census(folder):
    found = {name: collections.Counter() for name, _ in GROUPS}
    for path in folder.rglob("*.lua"):
        if any(part.lower() in ("libs", "lib", ".git") for part in path.parts):
            continue
        text = path.read_text("utf-8", "replace")
        for name, pattern in GROUPS:
            for m in re.finditer(pattern, text):
                found[name][".".join(g for g in m.groups() if g)] += 1
    return found


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("addons", nargs="*")
    parser.add_argument("--addons-dir", "--addons", dest="folder", type=Path)
    parser.add_argument("--json", type=Path)
    args = parser.parse_args(argv)
    folder = args.folder or Path(json.loads((ROOT / ".private" / "workspace.json").read_text("utf-8"))["addons"])
    names = args.addons or sorted(p.name for p in folder.iterdir() if p.is_dir() and (p / (p.name + ".toc")).exists())
    result = {}
    for name in names:
        result[name] = census(folder / name)
        row = ["%s %d" % (g, sum(c.values())) for g, c in result[name].items() if c]
        print("%-26s %s" % (name, ", ".join(row) or "no DLL calls found"))
        for group in ("nampower", "superwow", "unitxp"):
            if result[name][group]:
                print("    %-9s %s" % (group, ", ".join("%s %d" % kv for kv in result[name][group].most_common(8))))
    if args.json:
        args.json.write_text(json.dumps({n: {g: dict(c) for g, c in d.items()} for n, d in result.items()}, indent=2) + "\n", "utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
