#!/usr/bin/env python3
"""Extract the native FrameXML files that regressions need into .private.

FrameXML is Blizzard's code: it is written only under the repository's ignored
.private directory (or another folder outside the repository and the client),
never committed. Only Data/*.MPQ archives are read. DLLs and executables are
never opened, and no client file is hashed.
"""
from __future__ import annotations

import sys
sys.dont_write_bytecode = True
import argparse
import json
from pathlib import Path

from octowow_client_manifest import MPQ_ORDER, MPQArchive, client_file

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / ".private" / "framexml"
# Files read by the installed-addon regressions (see regressions/README.md).
REQUIRED = [
    "Interface\\FrameXML\\UnitFrame.lua",
    "Interface\\FrameXML\\PlayerFrame.lua",
    "Interface\\FrameXML\\PlayerFrame.xml",
    "Interface\\FrameXML\\TargetFrame.lua",
    "Interface\\FrameXML\\TargetFrame.xml",
    "Interface\\FrameXML\\ComboFrame.lua",
    "Interface\\FrameXML\\ComboFrame.xml",
]


def inside(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def checked_output(output: Path, client: Path) -> Path:
    output = output.resolve()
    if inside(output, client.resolve()):
        raise ValueError("Output must be outside the client directory")
    if inside(output, ROOT) and not inside(output, (ROOT / ".private").resolve()):
        raise ValueError("Blizzard FrameXML may only be written under .private, never into the repository")
    return output


def extract(client: Path, names: list[str], output: Path) -> dict:
    """Read each name from the archives in load order; the last archive wins."""
    data_dir = client / "Data"
    found: dict[str, tuple[str, bytes]] = {}
    errors = []
    for archive_name in MPQ_ORDER:
        path = client_file(data_dir, archive_name)
        if not path.is_file():
            continue
        archive = None
        try:
            archive = MPQArchive(path)
            for name in names:
                blob = archive.read_file(name)
                if blob is not None:
                    found[name] = (path.name, blob)
        except Exception as error:  # A damaged archive must not hide the others.
            errors.append({"archive": path.name, "error": str(error)})
        finally:
            if archive is not None:
                archive.close()
    files = {}
    for name, (archive_name, blob) in sorted(found.items()):
        destination = output / Path(*name.split("\\"))
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(blob)
        files[name] = {"archive": archive_name, "bytes": len(blob)}
    record = {"client": str(client.resolve()), "files": files,
              "missing": sorted(set(names) - set(found)), "archive_errors": errors,
              "note": "Blizzard code for local tests only; never commit these files."}
    output.mkdir(parents=True, exist_ok=True)
    (output / "sources.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return record


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--client", type=Path, required=True, help="Client root containing Data/*.MPQ")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Destination; default .private/framexml")
    parser.add_argument("--file", action="append", default=[], metavar="NAME",
                        help="Extra archive path, e.g. Interface\\FrameXML\\BuffFrame.lua (repeatable)")
    args = parser.parse_args(argv)
    try:
        if not (args.client / "Data").is_dir():
            raise ValueError(f"No Data directory under {args.client}")
        output = checked_output(args.output, args.client)
        names = list(dict.fromkeys(REQUIRED + [name.replace("/", "\\") for name in args.file]))
        record = extract(args.client, names, output)
    except (OSError, ValueError) as error:
        print(f"FrameXML extraction failed: {error}", file=sys.stderr)
        return 2
    print(f"FrameXML: {len(record['files'])} extracted, {len(record['missing'])} missing, "
          f"{len(record['archive_errors'])} archive errors -> {output}")
    return int(bool(record["missing"] or record["archive_errors"]))


if __name__ == "__main__":
    raise SystemExit(main())
