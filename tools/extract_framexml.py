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
import bz2
import json
import struct
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Data archive load order; a later archive overrides an earlier one.
MPQ_ORDER = [
    'base.MPQ', 'dbc.MPQ', 'fonts.MPQ', 'interface.MPQ', 'misc.MPQ',
    'model.MPQ', 'sound.MPQ', 'speech.MPQ', 'terrain.MPQ', 'texture.MPQ', 'wmo.MPQ',
    'patch.MPQ', 'patch-1.mpq', 'patch-2.mpq', 'patch-3.mpq', 'patch-4.mpq',
    'patch-5.mpq', 'patch-O.mpq', 'patch-Y.MPQ'
]

class MPQArchive:
    """Self-contained standard-library MPQ reader for WoW 1.12.1 archives."""

    def __init__(self, path: Path | str) -> None:
        self.file = open(path, "rb")
        try:
            self.header = self._read_header()
            self.hash_table = self._read_table("hash")
            self.block_table = self._read_table("block")
        except Exception:
            self.file.close()
            raise
        self.index = {}
        for entry in self.hash_table:
            block_idx, locale = entry[4], entry[2]
            if block_idx < len(self.block_table) and locale in (0, 1033):
                key = (entry[0], entry[1])
                if key not in self.index or locale == 0:
                    self.index[key] = entry

    def close(self) -> None:
        self.file.close()

    @staticmethod
    def _prepare_crypt_table() -> dict[int, int]:
        table = {}
        seed = 0x00100001
        for i in range(256):
            idx = i
            for _ in range(5):
                seed = (seed * 125 + 3) % 0x2AAAAB
                t1 = (seed & 0xFFFF) << 0x10
                seed = (seed * 125 + 3) % 0x2AAAAB
                t2 = (seed & 0xFFFF)
                table[idx] = t1 | t2
                idx += 0x100
        return table

    _CRYPT_TABLE = _prepare_crypt_table()

    @classmethod
    def _hash(cls, string: str, hash_type: str) -> int:
        types = {"TABLE_OFFSET": 0, "HASH_A": 1, "HASH_B": 2, "TABLE": 3}
        seed1 = 0x7FED7FED
        seed2 = 0xEEEEEEEE
        for ch in string.upper():
            c = ord(ch) if isinstance(ch, str) else ch
            val = cls._CRYPT_TABLE[(types[hash_type] << 8) + c]
            seed1 = (val ^ (seed1 + seed2)) & 0xFFFFFFFF
            seed2 = (c + seed1 + seed2 + (seed2 << 5) + 3) & 0xFFFFFFFF
        return seed1

    @classmethod
    def _decrypt(cls, data: bytes, key: int) -> bytes:
        seed1 = key & 0xFFFFFFFF
        seed2 = 0xEEEEEEEE
        count = len(data) // 4
        words = list(struct.unpack(f"<{count}I", data[:count * 4]))
        for i in range(count):
            seed2 = (seed2 + cls._CRYPT_TABLE[0x400 + (seed1 & 0xFF)]) & 0xFFFFFFFF
            val = (words[i] ^ (seed1 + seed2)) & 0xFFFFFFFF
            seed1 = (((~seed1 << 0x15) + 0x11111111) | (seed1 >> 0x0B)) & 0xFFFFFFFF
            seed2 = (val + seed2 + (seed2 << 5) + 3) & 0xFFFFFFFF
            words[i] = val
        res = struct.pack(f"<{count}I", *words)
        return res + data[count * 4:]

    def _read_header(self) -> dict:
        magic = self.file.read(4)
        if magic == b"MPQ\x1a":
            self.file.seek(0)
            data = self.file.read(32)
            fields = struct.unpack("<4s2I2H4I", data)
            return {
                "offset": 0,
                "header_size": fields[1],
                "archive_size": fields[2],
                "format_version": fields[3],
                "sector_size_shift": fields[4],
                "hash_table_offset": fields[5],
                "block_table_offset": fields[6],
                "hash_table_entries": fields[7],
                "block_table_entries": fields[8],
            }
        elif magic == b"MPQ\x1b":
            self.file.seek(0)
            ud_data = self.file.read(16)
            ud = struct.unpack("<4s3I", ud_data)
            header_offset = ud[2]
            self.file.seek(header_offset)
            data = self.file.read(32)
            fields = struct.unpack("<4s2I2H4I", data)
            return {
                "offset": header_offset,
                "header_size": fields[1],
                "archive_size": fields[2],
                "format_version": fields[3],
                "sector_size_shift": fields[4],
                "hash_table_offset": fields[5],
                "block_table_offset": fields[6],
                "hash_table_entries": fields[7],
                "block_table_entries": fields[8],
            }
        raise ValueError("Invalid MPQ magic")

    def _read_table(self, table_type: str) -> list:
        offset = self.header[f"{table_type}_table_offset"] + self.header["offset"]
        count = self.header[f"{table_type}_table_entries"]
        key = self._hash(f"({table_type} table)", "TABLE")
        self.file.seek(offset)
        raw = self.file.read(count * 16)
        dec = self._decrypt(raw, key)
        if table_type == "hash":
            return [struct.unpack("<2I2HI", dec[i*16:(i+1)*16]) for i in range(count)]
        else:
            return [struct.unpack("<4I", dec[i*16:(i+1)*16]) for i in range(count)]

    @staticmethod
    def _unpack_sector(data: bytes, expected: int, flags: int) -> bytes:
        if len(data) == expected:
            return data
        if not data:
            raise ValueError("Empty sector")
        mask = data[0]
        if mask == 2:
            decomp = zlib.decompress(data[1:])
        elif mask == 16:
            decomp = bz2.decompress(data[1:])
        else:
            raise ValueError(f"Unsupported compression mask: {mask}")
        return decomp

    def read_file(self, filename: str) -> bytes | None:
        ha = self._hash(filename, "HASH_A")
        hb = self._hash(filename, "HASH_B")
        entry = self.index.get((ha, hb))
        if entry is None:
            return None
        block = self.block_table[entry[4]]
        offset, arch_size, size, flags = block[0], block[1], block[2], block[3]
        if not (flags & 0x80000000) or (flags & 0x02000000):
            return None
        if size == 0 or arch_size == 0:
            return b""
        self.file.seek(offset + self.header["offset"])
        data = self.file.read(arch_size)
        if len(data) != arch_size:
            return None

        key = self._hash(filename.replace("/", "\\").split("\\")[-1], "TABLE")
        if flags & 0x00020000:
            key = ((key + offset) ^ size) & 0xFFFFFFFF
        encrypted = bool(flags & 0x00010000)

        if flags & 0x01000000:
            if encrypted:
                data = self._decrypt(data, key)
            return self._unpack_sector(data, size, flags)

        sector_size = 512 << self.header["sector_size_shift"]
        num_sectors = (size + sector_size - 1) // sector_size
        compressed = bool(flags & 0x00000200)

        if compressed:
            crc = bool(flags & 0x04000000)
            table_size = 4 * (num_sectors + 1 + (1 if crc else 0))
            pos_data = data[:table_size]
            if encrypted:
                pos_data = self._decrypt(pos_data, key - 1)
            positions = struct.unpack(f"<{len(pos_data)//4}I", pos_data)
        else:
            positions = tuple(range(0, size, sector_size)) + (size,)

        buf = bytearray()
        for idx in range(num_sectors):
            sec_data = data[positions[idx]:positions[idx+1]]
            if encrypted:
                sec_data = self._decrypt(sec_data, key + idx)
            expected = min(sector_size, size - len(buf))
            buf.extend(self._unpack_sector(sec_data, expected, flags))

        return bytes(buf)


def client_file(root: Path, filename: str) -> Path:
    """Match Windows file identity on case-sensitive fixture hosts as well."""
    expected = root / filename
    if expected.is_file() or not root.is_dir():
        return expected
    return next((path for path in root.iterdir() if path.name.casefold() == filename.casefold()), expected)


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
