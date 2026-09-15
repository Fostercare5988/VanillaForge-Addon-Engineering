#!/usr/bin/env python3
"""
VanillaForge upstream dependency checker.

Reads UPSTREAM_VERSIONS.json and compares the stored upstream snapshot against
GitHub without modifying repository files.

Designed for:
  - local manual checks
  - GitHub Actions scheduled checks
  - machine-readable GitHub Actions outputs

Exit codes:
  0 = no upstream change detected
  1 = configuration/network/API error
  2 = upstream change detected

Environment:
  GITHUB_TOKEN  Optional locally; automatically supplied by GitHub Actions.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

DEFAULT_CONFIG = "UPSTREAM_VERSIONS.json"
USER_AGENT = "VanillaForge-Upstream-Checker/1.0"
TIMEOUT = 20

# Files whose blob SHAs are especially useful for ClassicAPI API/reference drift.
TRACKED_FILES = {
    "classicapi": ("docs/API.md", "README.md"),
    "superwow": ("README.md",),
    "nampower": ("README.md", "SCRIPTS.md", "EVENTS.md", "DBC_FIELDS.md", "UNIT_FIELDS.md"),
}


class CheckError(RuntimeError):
    pass


def github_api(path: str, token: str | None) -> Any:
    url = "https://api.github.com" + path
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": USER_AGENT,
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise CheckError(f"GitHub API HTTP {exc.code} for {url}: {detail[:500]}") from exc
    except urllib.error.URLError as exc:
        raise CheckError(f"Unable to reach GitHub API: {exc.reason}") from exc


def parse_repo(value: str) -> tuple[str, str]:
    value = value.strip().strip("/")
    if value.startswith("https://github.com/"):
        value = value[len("https://github.com/"):]
    if value.endswith(".git"):
        value = value[:-4]
    parts = value.split("/")
    if len(parts) != 2 or not all(parts):
        raise CheckError(f"Invalid GitHub repository value: {value!r}")
    return parts[0], parts[1]


def load_config(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise CheckError(f"Configuration file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise CheckError(f"Invalid JSON in {path}: {exc}") from exc

    if not isinstance(data, dict):
        raise CheckError("UPSTREAM_VERSIONS.json must contain a JSON object.")
    return data


def normalize_version(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text.lstrip("vV") or None


def version_key(value: str | None) -> tuple[int, ...] | None:
    """Best-effort numeric comparison for ordinary X.Y.Z-style versions."""
    if not value:
        return None
    match = re.match(r"^(\d+(?:\.\d+)*)", normalize_version(value) or "")
    if not match:
        return None
    return tuple(int(part) for part in match.group(1).split("."))


def latest_release(owner: str, repo: str, token: str | None) -> dict[str, Any] | None:
    try:
        return github_api(f"/repos/{owner}/{repo}/releases/latest", token)
    except CheckError as exc:
        # A project may legitimately use tags rather than GitHub Releases.
        if "HTTP 404" not in str(exc):
            raise
        return None


def latest_tag(owner: str, repo: str, token: str | None) -> str | None:
    tags = github_api(f"/repos/{owner}/{repo}/tags?per_page=1", token)
    if isinstance(tags, list) and tags:
        return tags[0].get("name")
    return None


def default_branch(owner: str, repo: str, token: str | None) -> str:
    info = github_api(f"/repos/{owner}/{repo}", token)
    return info.get("default_branch") or "master"


def commit_sha(owner: str, repo: str, ref: str, token: str | None) -> str:
    encoded = urllib.parse.quote(ref, safe="")
    commit = github_api(f"/repos/{owner}/{repo}/commits/{encoded}", token)
    sha = commit.get("sha")
    if not sha:
        raise CheckError(f"GitHub returned no commit SHA for {owner}/{repo}@{ref}")
    return sha


def file_sha(owner: str, repo: str, path: str, ref: str, token: str | None) -> str | None:
    encoded_path = "/".join(urllib.parse.quote(part, safe="") for part in path.split("/"))
    encoded_ref = urllib.parse.quote(ref, safe="")
    try:
        data = github_api(
            f"/repos/{owner}/{repo}/contents/{encoded_path}?ref={encoded_ref}", token
        )
    except CheckError as exc:
        if "HTTP 404" in str(exc):
            return None
        raise
    return data.get("sha") if isinstance(data, dict) else None


def write_github_output(values: dict[str, str]) -> None:
    output_path = os.environ.get("GITHUB_OUTPUT")
    if not output_path:
        return
    with open(output_path, "a", encoding="utf-8") as handle:
        for key, value in values.items():
            safe = str(value).replace("\n", " ")
            handle.write(f"{key}={safe}\n")


def check_component(
    name: str,
    cfg: dict[str, Any],
    token: str | None,
    verbose: bool,
) -> dict[str, Any]:
    repo_value = cfg.get("repository")
    if not repo_value:
        return {
            "name": name,
            "status": "SKIPPED",
            "reason": "No repository configured",
            "changed": False,
        }

    owner, repo = parse_repo(str(repo_value))
    branch = str(cfg.get("branch") or default_branch(owner, repo, token))

    release = latest_release(owner, repo, token)
    upstream_version = None
    release_url = None
    if release:
        upstream_version = release.get("tag_name")
        release_url = release.get("html_url")
    if not upstream_version:
        upstream_version = latest_tag(owner, repo, token)

    reference_version = normalize_version(
        cfg.get("reference_version") or cfg.get("minimum_version")
    )
    upstream_normalized = normalize_version(upstream_version)

    current_commit = commit_sha(owner, repo, branch, token)
    stored_commit = str(
        cfg.get("reference_commit") or cfg.get("reference_sha") or ""
    ).strip() or None

    tracked_paths = cfg.get("tracked_files")
    if tracked_paths is None:
        tracked_paths = TRACKED_FILES.get(name.lower(), ())
    if isinstance(tracked_paths, str):
        tracked_paths = [tracked_paths]

    current_files: dict[str, str | None] = {}
    for path in tracked_paths or ():
        current_files[str(path)] = file_sha(owner, repo, str(path), branch, token)

    stored_files = cfg.get("file_shas") or {}
    if not isinstance(stored_files, dict):
        stored_files = {}

    reasons: list[str] = []

    # Version drift is meaningful when both versions can be determined.
    ref_key = version_key(reference_version)
    upstream_key = version_key(upstream_normalized)
    if ref_key is not None and upstream_key is not None and upstream_key > ref_key:
        reasons.append(
            f"version {reference_version} -> {upstream_normalized}"
        )
    elif (
        reference_version
        and upstream_normalized
        and upstream_normalized != reference_version
        and ref_key is None
    ):
        reasons.append(
            f"tag/version changed {reference_version} -> {upstream_normalized}"
        )

    if stored_commit and current_commit != stored_commit:
        reasons.append(
            f"default-branch commit {stored_commit[:12]} -> {current_commit[:12]}"
        )

    for path, current_sha in current_files.items():
        stored_sha = stored_files.get(path)
        if stored_sha and current_sha and stored_sha != current_sha:
            reasons.append(
                f"{path} blob {str(stored_sha)[:12]} -> {current_sha[:12]}"
            )

    # Missing snapshot data is informational, not an upstream change. This lets the
    # first run show what should be recorded without opening a false-positive issue.
    snapshot_missing = not stored_commit and not stored_files

    return {
        "name": name,
        "repository": f"{owner}/{repo}",
        "branch": branch,
        "reference_version": reference_version,
        "upstream_version": upstream_normalized,
        "reference_commit": stored_commit,
        "upstream_commit": current_commit,
        "release_url": release_url,
        "file_shas": current_files,
        "snapshot_missing": snapshot_missing,
        "changed": bool(reasons),
        "reasons": reasons,
        "status": "CHANGED" if reasons else "CURRENT",
    }


def print_report(results: list[dict[str, Any]], verbose: bool) -> None:
    print("VanillaForge upstream check")
    print("=" * 72)

    for result in results:
        print(f"\n[{result['status']}] {result['name']}")
        if result["status"] == "SKIPPED":
            print(f"  {result['reason']}")
            continue

        print(f"  Repository: {result['repository']}")
        print(f"  Branch:     {result['branch']}")
        print(f"  Reference:  {result.get('reference_version') or 'not recorded'}")
        print(f"  Upstream:   {result.get('upstream_version') or 'no release/tag found'}")

        if result.get("reference_commit"):
            print(f"  Stored SHA: {result['reference_commit']}")
        print(f"  Current SHA:{result['upstream_commit']}")

        if result.get("snapshot_missing"):
            print("  NOTE: No reference_commit/file_shas recorded yet.")
            print("        Record the reviewed snapshot after your first manual review.")

        for reason in result.get("reasons", []):
            print(f"  CHANGE: {reason}")

        if verbose:
            for path, sha in result.get("file_shas", {}).items():
                print(f"  {path}: {sha or 'not found'}")

    changed = [r for r in results if r.get("changed")]
    print("\n" + "=" * 72)
    if changed:
        print("REVIEW REQUIRED")
        print("Upstream changed. Review the actual diff before updating VanillaForge.")
    else:
        print("CURRENT")
        print("No tracked upstream change was detected.")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check VanillaForge upstream dependencies for version/API drift."
    )
    parser.add_argument(
        "--config",
        default=DEFAULT_CONFIG,
        help=f"Path to configuration JSON (default: {DEFAULT_CONFIG})",
    )
    parser.add_argument(
        "--component",
        action="append",
        default=[],
        help="Check only this component; may be supplied more than once.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show tracked upstream file blob SHAs.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Print machine-readable JSON instead of the human report.",
    )
    parser.add_argument(
        "--no-fail-on-change",
        action="store_true",
        help="Return exit code 0 even when upstream changes are detected.",
    )
    args = parser.parse_args()

    try:
        config = load_config(Path(args.config))
        selected = {name.lower() for name in args.component}
        token = os.environ.get("GITHUB_TOKEN")

        results: list[dict[str, Any]] = []
        for name, cfg in config.items():
            if selected and name.lower() not in selected:
                continue
            if not isinstance(cfg, dict):
                raise CheckError(f"Configuration for {name!r} must be an object.")
            results.append(check_component(name, cfg, token, args.verbose))

        if selected and not results:
            raise CheckError(
                "None of the requested components exist in UPSTREAM_VERSIONS.json."
            )

        changed = [r for r in results if r.get("changed")]
        changed_names = ",".join(r["name"] for r in changed)

        write_github_output(
            {
                "changed": "true" if changed else "false",
                "changed_components": changed_names,
                "changed_count": str(len(changed)),
            }
        )

        if args.json_output:
            print(json.dumps({"changed": bool(changed), "results": results}, indent=2))
        else:
            print_report(results, args.verbose)

        if changed and not args.no_fail_on_change:
            return 2
        return 0

    except CheckError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        write_github_output({"changed": "error", "changed_components": "", "changed_count": "0"})
        return 1


if __name__ == "__main__":
    sys.exit(main())
