#!/usr/bin/env python3
"""Take a new DLL release in one command.

    python -B tools/upgrade_dll.py [component] [--pin]

Without --pin it only reports, for the component (default classicapi):
the pinned and the latest release, the commit subjects in between, the doc
headings that were added, removed or renamed, and the replacement-rule leads
in every maintained addon. The full doc diff goes to
.private/upgrade-<component>-<old>-<new>.diff for reading on demand.

With --pin it also writes the new release into UPSTREAM_VERSIONS.json, the
only file that names a DLL version. Addons never name one (they check that
the DLL is loaded), so nothing else needs a version edit. What remains is the
real work: the release-notes section in the reference, new rules in
tools/replacements.json and the refactors the leads point to.

Maintained addons are the folders in the AddOns folder that are git clones of
the owner's repositories. The AddOns folder comes from --addons or from
.private/workspace.json ({"addons": "<client>/Interface/AddOns", "owner": "<GitHub user>"}).

Environment: GITHUB_TOKEN (or a logged-in `gh`) avoids GitHub's anonymous
rate limit.
"""
from __future__ import annotations

import argparse
import base64
import difflib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from check_upstream import CheckError, github_api  # noqa: E402

CONFIG = ROOT / "UPSTREAM_VERSIONS.json"
PRIVATE = ROOT / ".private"


def token() -> str | None:
    if os.environ.get("GITHUB_TOKEN"):
        return os.environ["GITHUB_TOKEN"]
    try:
        out = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, timeout=10)
        return out.stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        return None


def doc_at(repo: str, path: str, ref: str, tok: str | None) -> str:
    data = github_api(f"/repos/{repo}/contents/{path}?ref={ref}", tok)
    return base64.b64decode(data["content"]).decode("utf-8", errors="replace")


def headings(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if re.match(r"#{2,4} ", line)]


def release_identity(repo: str, release: dict, tok: str | None) -> dict:
    tag = release["tag_name"]
    ref = github_api(f"/repos/{repo}/git/ref/tags/{tag}", tok)["object"]
    tag_object = None
    commit = ref["sha"]
    if ref["type"] == "tag":
        tag_object = ref["sha"]
        commit = github_api(f"/repos/{repo}/git/tags/{tag_object}", tok)["object"]["sha"]
    ident = {"tag": tag}
    if tag_object:
        ident["tag_object"] = tag_object
    ident.update({"commit": commit, "published_at": release["published_at"]})
    dll = next((a for a in release.get("assets", []) if a["name"].lower().endswith(".dll")), None)
    if dll:
        ident.update({"dll_asset_id": dll["id"], "dll_size_bytes": dll["size"]})
        if (dll.get("digest") or "").startswith("sha256:"):
            ident["dll_sha256"] = dll["digest"][7:]
    return ident


def maintained_addons(addons: Path, owner: str | None) -> list[Path]:
    found = []
    for folder in sorted(addons.iterdir()):
        if not (folder / ".git").exists():
            continue
        if owner:
            url = subprocess.run(["git", "-C", str(folder), "remote", "get-url", "origin"],
                                 capture_output=True, text=True).stdout
            if owner.lower() not in url.lower():
                continue
        found.append(folder)
    return found


def lead_scan(addons: list[Path]) -> dict[str, list[str]]:
    from find_holes import Addon, replacements
    leads: dict[str, list[str]] = {}
    for folder in addons:
        try:
            hits = replacements(Addon(folder))
        except OSError as error:
            leads.setdefault("unreadable", []).append(f"{folder.name}: {error}")
            continue
        for hit in hits:
            leads.setdefault(hit["id"], []).append(f"{folder.name} ({hit['hits']}: {', '.join(hit['where'])})")
    return leads


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("component", nargs="?", default="classicapi")
    parser.add_argument("--pin", action="store_true", help="Write the latest release into UPSTREAM_VERSIONS.json")
    parser.add_argument("--addons", type=Path, help="The client's Interface/AddOns folder")
    args = parser.parse_args(argv)

    config = json.loads(CONFIG.read_text("utf-8"))
    entry = config.get(args.component)
    if not entry:
        print(f"unknown component {args.component}; known: {', '.join(config)}", file=sys.stderr)
        return 1
    repo, tok = entry["repository"], token()
    try:
        release = github_api(f"/repos/{repo}/releases/latest", tok)
        new_tag, old = release["tag_name"], entry["reference_version"]
        new = new_tag.lstrip("v")
        old_tag = entry.get("release_provenance", {}).get("tag") or ("v" + old)
        print(f"{args.component}: pinned {old}, latest {new}")
        if new != old:
            compare = github_api(f"/repos/{repo}/compare/{old_tag}...{new_tag}", tok)
            print(f"\n{len(compare['commits'])} commits:")
            for c in compare["commits"]:
                print("  " + c["sha"][:7] + " " + c["commit"]["message"].splitlines()[0])
            PRIVATE.mkdir(exist_ok=True)
            diff_path = PRIVATE / f"upgrade-{args.component}-{old}-{new}.diff"
            chunks = []
            for path in entry.get("file_shas", {}):
                before, after = doc_at(repo, path, old_tag, tok), doc_at(repo, path, new_tag, tok)
                chunks += difflib.unified_diff(before.splitlines(), after.splitlines(),
                                               f"{path}@{old_tag}", f"{path}@{new_tag}", lineterm="")
                hb, ha = headings(before), headings(after)
                added = [h for h in ha if h not in hb]
                removed = [h for h in hb if h not in ha]
                print(f"\n{path}: {len(added)} headings added or changed, {len(removed)} removed or changed")
                for h in added:
                    print("  + " + h)
                for h in removed:
                    print("  - " + h)
            diff_path.write_text("\n".join(chunks) + "\n", "utf-8")
            print(f"\nFull doc diff: {diff_path}")
        if args.pin and new != old:
            ident = release_identity(repo, release, tok)
            entry["reference_version"] = entry["minimum_version"] = new
            entry["reference_commit"] = ident["commit"]
            entry["file_shas"] = {p: github_api(f"/repos/{repo}/contents/{p}?ref={ident['commit']}", tok)["sha"]
                                  for p in entry.get("file_shas", {})}
            entry["release_provenance"] = ident
            for key in ("minimum_version_scope", "reference_commit_scope"):
                entry.pop(key, None)
            CONFIG.write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n", "utf-8")
            print(f"\nPinned {args.component} {new} in {CONFIG.name}. Next: run "
                  "python -B tools/fetch_upstream_docs.py, write the release notes section, add rules.")
    except CheckError as error:
        print(f"upgrade_dll: {error}", file=sys.stderr)
        return 1

    workspace = PRIVATE / "workspace.json"
    settings = json.loads(workspace.read_text("utf-8")) if workspace.exists() else {}
    addons = args.addons or (Path(settings["addons"]) if settings.get("addons") else None)
    if not addons or not addons.is_dir():
        print("\nNo AddOns folder (pass --addons or set it in .private/workspace.json); skipped the lead scan.")
        return 0
    folders = maintained_addons(addons, settings.get("owner"))
    leads = lead_scan(folders)
    print(f"\nReplacement leads in {len(folders)} maintained addons ({len(leads)} rules hit):")
    for rule, hits in sorted(leads.items()):
        print(f"  {rule}")
        for hit in hits:
            print(f"    {hit}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
