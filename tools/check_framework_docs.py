#!/usr/bin/env python3
"""Check startup budgets, local links and supported baselines without network access.

Only the two mandatory entry documents have size limits. Technical references
remain uncapped. Links in fenced/inline code and external URLs are ignored.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
WORD_LIMITS = {"AGENTS.md": 300, "VANILLAFORGE_SYSTEM_PROMPT.md": 1100}
EXCLUDED = {"ChatGPT", "__pycache__", "node_modules", ".git", ".venv"}
FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
HEADING = re.compile(r"^ {0,3}#{1,6}(?:[ \t]+|$)(.*?)\s*$")
SETEXT = re.compile(r"^ {0,3}(?:=+|-+)\s*$")
INLINE_CODE = re.compile(r"(`+)(?!`)(.*?)\1(?!`)")
# Markdown destinations may use angle brackets for spaces or one balanced
# parenthesis pair. Optional titles are ignored; reference definitions count.
DESTINATION = r"(?:<([^>\n]+)>|((?:\\.|[^\s()]|\([^()\n]*\))+))"
INLINE_LINK = re.compile(r"(?<!\\)\]\(\s*" + DESTINATION + r"(?:\s+[\"'][^\n]*?[\"'])?\s*\)")
REFERENCE = re.compile(r"^ {0,3}\[[^]\n]+\]:\s*" + DESTINATION)
COMPONENTS = {
    "classicapi": "ClassicAPI",
    "superwow": "SuperWoW",
    "nampower": "NamPower",
    "unitxp_sp3": "UnitXP SP3",
}


def check_baselines(root: Path) -> list[str]:
    """Compare current support declarations, not dated audits or reference builds."""
    config = json.loads((root / "UPSTREAM_VERSIONS.json").read_text(encoding="utf-8"))
    if not isinstance(config, dict):
        return ["UPSTREAM_VERSIONS.json: expected a component object"]
    errors: list[str] = []
    documents = {}
    for name in ("README.md", "VANILLAFORGE_SYSTEM_PROMPT.md", "ENGINE_REFERENCE.md"):
        path = root / name
        if not path.is_file():
            errors.append(f"{name}: missing supported baseline document")
        else:
            documents[name] = path.read_text(encoding="utf-8")
    for key, label in COMPONENTS.items():
        entry = config.get(key)
        minimum = entry.get("minimum_version") if isinstance(entry, dict) else None
        if not isinstance(minimum, str) or not re.fullmatch(r"\d+(?:\.\d+)*", minimum):
            errors.append(f"UPSTREAM_VERSIONS.json: {key}.minimum_version must be a numeric version string")
            continue
        for name, text in documents.items():
            # Inspect only the canonical Target/header, excluding later evidence.
            if name == "README.md":
                section = text.split("## Target\n", 1)[-1].split("\n## ", 1)[0]
                pattern = rf"\[{re.escape(label)}\]\([^\n)]*\)\s*\|\s*v(\d+(?:\.\d+)*)\+"
            elif name == "VANILLAFORGE_SYSTEM_PROMPT.md":
                section = text.split("## Target\n", 1)[-1].split("\n## ", 1)[0]
                pattern = rf"{re.escape(label)}\s+v(\d+(?:\.\d+)*)\+"
            else:
                section = text.split("\n---", 1)[0]
                pattern = rf"{re.escape(label)}\s+v(\d+(?:\.\d+)*)\+"
            versions = re.findall(pattern, section)
            if versions != [minimum]:
                errors.append(f"{name}: {label} supported baseline {versions!r}; expected exactly one v{minimum}+")
        # UnitXP's detailed section repeats support separately from its source pin.
        if key == "unitxp_sp3" and "ENGINE_REFERENCE.md" in documents:
            section = documents["ENGINE_REFERENCE.md"].split("## 7. UnitXP SP3\n", 1)[-1].split("\n### ", 1)[0]
            versions = re.findall(r"\*\*Baseline:\*\*\s*v(\d+(?:\.\d+)*)\+", section)
            if versions != [minimum]:
                errors.append(f"ENGINE_REFERENCE.md: UnitXP section baseline {versions!r}; expected exactly one v{minimum}+")
    return errors


def visible_lines(text: str):
    """Keep line numbers while omitting fenced examples."""
    marker = ""
    length = 0
    for number, line in enumerate(text.splitlines(), 1):
        fence = FENCE.match(line)
        if marker:
            if fence and fence[1][0] == marker and len(fence[1]) >= length and not fence[2].strip():
                marker = ""
            continue
        if fence:
            marker, length = fence[1][0], len(fence[1])
            continue
        yield number, line


def heading_ids(text: str) -> set[str]:
    """Common GitHub heading slugs, including duplicate suffixes and Setext."""
    used: set[str] = set()
    previous = ""
    for _, line in visible_lines(text):
        heading = HEADING.match(line)
        title = heading[1] if heading else previous if SETEXT.match(line) and previous.strip() else None
        previous = line
        if title is None:
            continue
        title = re.sub(r"\s+#+\s*$", "", title)
        title = re.sub(r"\[([^]]+)\]\([^)]*\)", r"\1", title)
        title = re.sub(r"<[^>]*>", "", title)
        title = re.sub(r"(?<!\w)(_{1,3})(.*?)\1(?!\w)", r"\2", title)
        title = html.unescape(title).lower().strip()
        slug = re.sub(r"[^\w\-\s]", "", title)
        slug = re.sub(r"\s", "-", slug)
        candidate, suffix = slug, 0
        while candidate in used:
            suffix += 1
            candidate = f"{slug}-{suffix}"
        used.add(candidate)
    return used


def link_destinations(text: str):
    for number, line in visible_lines(text):
        line = INLINE_CODE.sub(lambda match: " " * len(match[0]), line)
        for match in INLINE_LINK.finditer(line):
            yield number, match[1] or match[2]
        reference = REFERENCE.match(line)
        if reference:
            yield number, reference[1] or reference[2]


def check(root: Path) -> list[str]:
    root = root.resolve()
    errors: list[str] = []
    documents = {}
    for path in sorted(root.rglob("*.md")):
        relative = path.relative_to(root)
        if any(part in EXCLUDED or part.startswith(".") for part in relative.parts):
            continue
        documents[path] = path.read_text(encoding="utf-8")
    for name, limit in WORD_LIMITS.items():
        text = documents.get(root / name)
        if text is None:
            errors.append(f"{name}: missing mandatory entry document")
        elif len(text.split()) > limit:
            errors.append(f"{name}: {len(text.split())} words exceeds startup budget of {limit}")

    anchors = {path: heading_ids(text) for path, text in documents.items()}
    for path, text in documents.items():
        relative = path.relative_to(root).as_posix()
        for number, destination in link_destinations(text):
            url = urlsplit(destination)
            if url.scheme or url.netloc or url.path.startswith(("/", "\\")):
                continue
            target = (path.parent / unquote(url.path).replace("\\", "/")).resolve() if url.path else path
            label = f"{relative}:{number}: [{destination}]"
            if not target.is_relative_to(root):
                errors.append(f"{label} points outside the repository")
            elif not target.exists():
                errors.append(f"{label} has no local target")
            elif target.suffix.lower() == ".md" and url.fragment:
                ids = anchors.get(target)
                if ids is None:
                    ids = heading_ids(target.read_text(encoding="utf-8"))
                if unquote(url.fragment) not in ids:
                    errors.append(f"{label} has no heading anchor")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT, help="VanillaForge repository root")
    args = parser.parse_args(argv)
    errors = []
    try:
        errors.extend(check(args.root))
        errors.extend(check_baselines(args.root))
    except (OSError, UnicodeError, ValueError) as exc:
        errors.append(str(exc))
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("Framework startup budgets, local Markdown links and supported baselines verified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
