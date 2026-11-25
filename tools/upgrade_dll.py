#!/usr/bin/env python3
"""Take a new DLL release in one command.

    python -B tools/upgrade_dll.py [component] [--pin | --next]

Without --pin it only reports, for the component (default classicapi):
the pinned and the latest release, the commit subjects in between, the doc
headings that were added, removed or renamed, the replacement-rule leads
in every maintained addon, and the gaps: every `-- GAP:` in the maintained
addons (the jobs we do because no DLL did them), the ones whose text names an
API the release adds first, and the planned gaps of the rebuild's wishlist
(.private/rebuild/WISHLIST.md) the same way. A release that covers a gap
means its function is deleted (VANILLAFORGE.md section 8 rule 4). The full
doc diff goes to .private/upgrade-<component>-<old>-<new>.diff for reading on
demand.

--next reads the default branch instead of the latest release: what the next
release will bring, so a spec is not built on a gap that is about to close
(C_AddOnProfiler was on master a day before !ErrorLog's build, 2026-11-25).
It never pins: the client runs releases.

With --pin it also writes the new release into UPSTREAM_VERSIONS.json, the
only file that names a DLL version. Addons never name one (they check that
the DLL is loaded), so nothing else needs a version edit. What remains is the
real work: the release-notes section in the reference, new rules in
tools/replacements.json and the refactors the leads point to.

Maintained addons are the installed addons that have a regression suite in
regressions/, so addons we only keep a
copy of, such as BigWigs, are left out. The AddOns folder comes from --addons
or from .private/workspace.json ({"addons": "<client>/Interface/AddOns"}).

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
REGRESSIONS = ROOT / "regressions"


def maintained(addons_dir, regressions=REGRESSIONS):
    """Installed folders of the addons that have a regression suite."""
    suites = {p.name.lower() for p in regressions.iterdir() if p.is_dir() and any(p.glob("test_*.py"))}
    return sorted(d for d in Path(addons_dir).iterdir() if d.is_dir() and d.name.lstrip("!").lower() in suites)


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
    if data.get("encoding") != "base64":
        # Over 1 MB the contents API sends no content (encoding "none"); the
        # blob API serves files up to 100 MB. docs/API.md is past 1 MB.
        data = github_api(f"/repos/{repo}/git/blobs/{data['sha']}", tok)
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


# An API-shaped name: a C_ namespace, CamelCase with an inner capital, a
# lowerCamel cvar, an EVENT_NAME. Plain words ("Until", "Frame") are left out.
API_NAME = re.compile(r"\b(?:C_[A-Za-z]\w*|[A-Z][a-z0-9]+(?:[A-Z][A-Za-z0-9]*)+|[a-z]+[A-Z][A-Za-z0-9]*"
                      r"|[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+)\b")


def api_names(text: str) -> set[str]:
    return set(API_NAME.findall(text))


def wishlist_gaps(path: Path = PRIVATE / "rebuild" / "WISHLIST.md") -> list[dict]:
    """The wishlist's table rows (planned gaps too), when the file is there."""
    if not path.is_file():
        return []
    return [{"where": f"{path.name}:{number}", "text": line.strip()}
            for number, line in enumerate(path.read_text("utf-8").splitlines(), 1)
            if line.startswith("| ") and not re.match(r"^\|[\s|:-]+\|$", line.strip())]


def code_gaps(addons: list[Path]) -> list[dict]:
    from find_holes import Addon, gaps
    found = []
    for folder in addons:
        try:
            found += [dict(gap, where=f"{folder.name} {gap['where']}") for gap in gaps(Addon(folder))]
        except OSError as error:
            found.append({"where": folder.name, "text": f"unreadable: {error}"})
    return found


def gap_hits(gaps: list[dict], added: set[str]) -> list[dict]:
    """The gaps whose text names something the release adds."""
    hits = []
    for gap in gaps:
        names = sorted(api_names(gap["text"]) & added)
        if names:
            hits.append(dict(gap, names=names))
    return hits


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
    parser.add_argument("--next", action="store_true", help="Read the default branch's unreleased work; never pins")
    parser.add_argument("--addons", type=Path, help="The client's Interface/AddOns folder")
    args = parser.parse_args(argv)
    if args.pin and args.next:
        parser.error("--next never pins: the client runs releases")

    config = json.loads(CONFIG.read_text("utf-8"))
    entry = config.get(args.component)
    if not entry:
        print(f"unknown component {args.component}; known: {', '.join(config)}", file=sys.stderr)
        return 1
    repo, tok = entry["repository"], token()
    new_names: set[str] = set()      # API names the newer docs have and the pinned ones lack
    try:
        old = entry["reference_version"]
        if args.next:
            branch = entry.get("branch") or github_api(f"/repos/{repo}", tok)["default_branch"]
            release, new_tag, new = None, branch, branch
            print(f"{args.component}: pinned {old}; reading {branch}, unreleased")
        else:
            release = github_api(f"/repos/{repo}/releases/latest", tok)
            new_tag = release["tag_name"]
            new = new_tag.lstrip("v")
            print(f"{args.component}: pinned {old}, latest {new}")
        # The pinned commit, not its tag: a maintainer can delete and renumber tags
        # (ClassicAPI's v1.24.x became v1.23.x on 2026-11-24).
        old_tag = (entry.get("reference_commit") or entry.get("release_provenance", {}).get("tag")
                   or ("v" + old))
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
                new_names |= api_names(after) - api_names(before)
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
    folders = maintained(addons)
    leads = lead_scan(folders)
    print(f"\nReplacement leads in {len(folders)} maintained addons ({len(leads)} rules hit):")
    for rule, hits in sorted(leads.items()):
        print(f"  {rule}")
        for hit in hits:
            print(f"    {hit}")
    if new_names:
        report_gaps(code_gaps(folders), wishlist_gaps(), new_names)
    return 0


def report_gaps(gaps: list[dict], planned: list[dict], added: set[str]) -> None:
    """The gaps against what the newer docs add: the ones that name an added API
    first, then every gap in the code, to read beside the new headings."""
    hits = gap_hits(gaps + planned, added)
    print(f"\nGaps that name an API the newer docs add ({len(hits)}; read these first):")
    for hit in hits:
        print(f"  {hit['where']}: {', '.join(hit['names'])}")
    print(f"\nEvery gap in the maintained addons ({len(gaps)}; does the release do one of them?):")
    for gap in gaps:
        text = gap["text"] if len(gap["text"]) <= 110 else gap["text"][:107] + "..."
        print(f"  {gap['where']}: {text}")


if __name__ == "__main__":
    raise SystemExit(main())
