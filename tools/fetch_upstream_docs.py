#!/usr/bin/env python3
"""Download the DLL maintainers' documentation at the commits pinned in UPSTREAM_VERSIONS.json.

Writes .private/upstream/<name>/<path> and .private/upstream/sources.json.
Only documentation is fetched, never binaries. Files listed in an entry's
file_shas must match their recorded Git blob SHA. UnitXP SP3 publishes no prose
docs, so its command dispatcher source stands in for them. SuperWoW documents
its API in the GitHub wiki, which has no pinned commit: the wiki is copied at its
current head, and that commit is recorded as unpinned.

Exit codes: 0 = all docs written, 1 = configuration, network or integrity error.
Environment: GITHUB_TOKEN (optional) raises the GitHub API rate limit.
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
USER_AGENT = "VanillaForge-Upstream-Docs/1.0"
TIMEOUT = 30

# Repository paths that hold each component's documentation. "*" does not cross "/".
DOC_PATTERNS = {
    "classicapi": ["README.md", "docs/*.md"],
    "superwow": ["README.md"],
    "nampower": ["*.md"],
    "unitxp_sp3": ["README.md", "dllmain.cpp"],
}
DEFAULT_PATTERNS = ["*.md"]
WIKIS = {"superwow"}


class FetchError(RuntimeError):
    pass


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def matches(path: str, pattern: str) -> bool:
    return path.count("/") == pattern.count("/") and fnmatch.fnmatchcase(path, pattern)


def select_docs(paths: list[str], patterns: list[str]) -> list[str]:
    return sorted(p for p in paths if any(matches(p, pattern) for pattern in patterns))


def safe_relative(path: str) -> PurePosixPath:
    relative = PurePosixPath(path)
    if relative.is_absolute() or not relative.parts or ".." in relative.parts:
        raise FetchError(f"unsafe repository path: {path}")
    return relative


def http_get(url: str) -> bytes:
    headers = {"User-Agent": USER_AGENT}
    token = os.environ.get("GITHUB_TOKEN")
    if token and url.startswith("https://api.github.com/"):
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            return response.read()
    except OSError as error:
        raise FetchError(f"{url}: {error}") from error


def list_tree(repository: str, commit: str) -> list[str]:
    data = json.loads(http_get(f"https://api.github.com/repos/{repository}/git/trees/{commit}?recursive=1"))
    if data.get("truncated"):
        raise FetchError(f"{repository}@{commit}: tree listing truncated")
    return [item["path"] for item in data.get("tree", []) if item.get("type") == "blob"]


def read_file(repository: str, commit: str, path: str) -> bytes:
    return http_get(f"https://raw.githubusercontent.com/{repository}/{commit}/{path}")


def clone_wiki(repository: str, destination: Path) -> tuple[str, list[str]]:
    """Copy the wiki's Markdown pages; return the wiki commit and page paths."""
    with tempfile.TemporaryDirectory() as temporary:
        checkout = Path(temporary) / "wiki"
        command = ["git", "clone", "--quiet", "--depth", "1",
                   f"https://github.com/{repository}.wiki.git", str(checkout)]
        try:
            subprocess.run(command, check=True, capture_output=True, timeout=120)
            commit = subprocess.run(["git", "-C", str(checkout), "rev-parse", "HEAD"], check=True,
                                    capture_output=True, text=True, timeout=30).stdout.strip()
        except (OSError, subprocess.SubprocessError) as error:
            raise FetchError(f"{repository} wiki: {error}") from error
        pages = []
        for page in sorted(checkout.rglob("*.md")):
            relative = page.relative_to(checkout).as_posix()
            target = destination / "wiki" / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(page, target)
            pages.append("wiki/" + relative)
        return commit, pages


def fetch_entry(name: str, entry: dict, output: Path, *, tree=list_tree, read=read_file,
                wiki=clone_wiki, include_wiki: bool = True) -> dict:
    repository, commit = entry.get("repository"), entry.get("reference_commit")
    if not repository or not commit:
        raise FetchError(f"{name}: repository and reference_commit are required")
    pinned_shas = entry.get("file_shas") or {}
    docs = select_docs(tree(repository, commit), DOC_PATTERNS.get(name, DEFAULT_PATTERNS))
    if not docs:
        raise FetchError(f"{name}: no documentation found at {repository}@{commit}")

    destination = output / name
    if destination.exists():
        shutil.rmtree(destination)
    files = []
    for path in docs:
        data = read(repository, commit, path)
        sha = git_blob_sha(data)
        if path in pinned_shas and pinned_shas[path] != sha:
            raise FetchError(f"{name}: {path} is {sha}, UPSTREAM_VERSIONS.json pins {pinned_shas[path]}")
        target = destination.joinpath(*safe_relative(path).parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        files.append({"path": path, "sha": sha, "bytes": len(data), "pinned": path in pinned_shas})

    record = {"repository": repository, "commit": commit, "files": files}
    if include_wiki and name in WIKIS:
        wiki_commit, pages = wiki(repository, destination)
        record["wiki"] = {"commit": wiki_commit, "pinned": False, "pages": pages}
    return record


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--config", default=str(ROOT / "UPSTREAM_VERSIONS.json"))
    parser.add_argument("--output", default=str(ROOT / ".private" / "upstream"))
    parser.add_argument("--only", action="append", help="Fetch only this entry (repeatable)")
    parser.add_argument("--no-wiki", action="store_true", help="Skip unpinned wiki copies")
    args = parser.parse_args(argv)

    try:
        config = json.loads(Path(args.config).read_text(encoding="utf-8"))
        entries = {name: entry for name, entry in config.items()
                   if isinstance(entry, dict) and "repository" in entry}
        unknown = set(args.only or []) - set(entries)
        if unknown:
            raise FetchError("unknown entries: " + ", ".join(sorted(unknown)))
        output = Path(args.output)
        output.mkdir(parents=True, exist_ok=True)
        manifest_path = output / "sources.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
        for name in sorted(args.only or entries):
            manifest[name] = fetch_entry(name, entries[name], output, include_wiki=not args.no_wiki)
            record = manifest[name]
            wiki_note = f", wiki {record['wiki']['commit'][:7]} (unpinned)" if "wiki" in record else ""
            print(f"{name}: {len(record['files'])} files at {record['commit'][:7]}{wiki_note}")
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    except (FetchError, OSError, ValueError) as error:
        print(f"fetch_upstream_docs: {error}", file=sys.stderr)
        return 1
    print(f"Upstream docs -> {output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
