#!/usr/bin/env python3
"""Deterministic, read-only client manifest generator and update diff tool for OctoWoW.

Standard library only. No process interaction, no binary mutation, no private/WTF data.
Tracks authoritative client binaries, native extensions, loader configuration,
Data MPQs, effective FrameXML files, and maintained addon working tree state.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import sys
import zlib
import bz2

class MPQArchive:
    """Self-contained standard-library MPQ reader for WoW 1.12.1 archives."""

    def __init__(self, path: Path | str) -> None:
        self.file = open(path, "rb")
        self.header = self._read_header()
        self.hash_table = self._read_table("hash")
        self.block_table = self._read_table("block")
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



def sha256_file(path: Path) -> str:
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def get_pe_version_strings(path: Path) -> dict[str, str]:
    try:
        data = path.read_bytes()
    except Exception:
        return {}
    res = {}
    for key in [b'FileVersion', b'ProductVersion', b'ProductName', b'LegalCopyright']:
        k_u16 = key.decode('ascii').encode('utf-16le')
        idx = data.find(k_u16)
        if idx != -1:
            start = idx + len(k_u16)
            while start + 2 <= len(data) and data[start:start+2] == b'\x00\x00':
                start += 2
            end = start
            while end + 2 <= len(data) and data[end:end+2] != b'\x00\x00':
                end += 2
            val = data[start:end].decode('utf-16le', errors='ignore').strip()
            if val:
                res[key.decode('ascii')] = val
    return res


def get_git_info(repo_path: Path) -> dict[str, str]:
    if not (repo_path / '.git').exists():
        return {'status': 'not_a_repo'}
    try:
        head = subprocess.check_output(
            ['git', '-C', str(repo_path), 'rev-parse', 'HEAD'],
            stderr=subprocess.DEVNULL
        ).decode().strip()
        status_out = subprocess.check_output(
            ['git', '-C', str(repo_path), 'status', '--short'],
            stderr=subprocess.DEVNULL
        ).decode().strip()
        branch = subprocess.check_output(
            ['git', '-C', str(repo_path), 'rev-parse', '--abbrev-ref', 'HEAD'],
            stderr=subprocess.DEVNULL
        ).decode().strip()
        return {
            'head': head,
            'branch': branch,
            'clean': len(status_out) == 0,
            'status': status_out if status_out else 'clean'
        }
    except Exception as e:
        return {'error': str(e)}


def parse_toc_metadata(toc_path: Path) -> dict[str, str]:
    if not toc_path.is_file():
        return {}
    res = {}
    try:
        for line in toc_path.read_text(encoding='latin1').splitlines():
            line = line.strip()
            if line.startswith('##'):
                parts = line[2:].strip().split(':', 1)
                if len(parts) == 2:
                    k, v = parts[0].strip(), parts[1].strip()
                    res[k] = v
    except Exception:
        pass
    return res


def generate_manifest(client_root: Path, historical_root: Path | None = None) -> dict:
    client_root = client_root.resolve()
    manifest: dict = {
        'generatedAt': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'authoritativeClientRoot': str(client_root),
        'historicalClientRoot': str(historical_root.resolve()) if historical_root else None,
        'clientExecutable': 'WoW.exe',
        'clientBuild': 5875,
        'interfaceVersion': 11200,
        'realm': None,
        'loaderConfiguration': {},
        'nativeExtensions': {},
        'dataArchives': {},
        'frameXML': {},
        'deployedAddons': {}
    }

    # Realm
    realm_file = client_root / 'realmlist.wtf'
    if realm_file.is_file():
        m = re.search(r'set\s+realmlist\s+"([^"]+)"', realm_file.read_text(errors='ignore'))
        if m:
            manifest['realm'] = m.group(1)

    # Executable
    wow_exe = client_root / 'WoW.exe'
    if wow_exe.is_file():
        manifest['clientExecutableInfo'] = {
            'filename': 'WoW.exe',
            'bytes': wow_exe.stat().st_size,
            'sha256': sha256_file(wow_exe),
            'versionInfo': get_pe_version_strings(wow_exe)
        }

    # Loader config
    dlls_txt = client_root / 'dlls.txt'
    loader_entries = []
    if dlls_txt.is_file():
        loader_entries = [l.strip() for l in dlls_txt.read_text(errors='ignore').splitlines() if l.strip()]
        manifest['loaderConfiguration']['dlls_txt'] = {
            'path': str(dlls_txt),
            'sha256': sha256_file(dlls_txt),
            'entries': loader_entries
        }

    dlls_cache = client_root / 'dlls.txt.cache'
    if dlls_cache.is_file():
        manifest['loaderConfiguration']['dlls_txt_cache'] = {
            'path': str(dlls_cache),
            'sha256': sha256_file(dlls_cache),
            'cached_dlls': [l.strip() for l in dlls_cache.read_text(errors='ignore').splitlines() if l.strip()]
        }

    # Native extensions
    ext_files = [
        'ClassicAPI.dll', 'SuperWoWhook.dll', 'nampower.dll', 'UnitXP_SP3.dll',
        'AuctionQueryThrottle.dll', 'transmogfix.dll', 'dxgi.dll',
        'VanillaFixes.exe', 'VanillaHelpers.dll', 'VanillaMultiMonitorFix.dll', 'VfPatcher.dll'
    ]
    for ext_name in ext_files:
        p = client_root / ext_name
        if not p.is_file():
            continue
        data = p.read_bytes()
        info: dict = {
            'filename': ext_name,
            'bytes': len(data),
            'sha256': hashlib.sha256(data).hexdigest(),
            'loadedInDllsTxt': ext_name in loader_entries,
            'versionStrings': get_pe_version_strings(p)
        }

        # Specific known versions from logs/strings
        if ext_name == 'ClassicAPI.dll':
            info['declaredVersion'] = info['versionStrings'].get('FileVersion', '1.15.16.0')
            info['knownUpstreamTag'] = 'v1.15.16'
            info['sha256MatchesUpstreamRelease'] = (info['sha256'] == 'e34886fb9725b9059375a5c37bff81ce220633c4e2c39719ef3223a6b8fc703d')
        elif ext_name == 'SuperWoWhook.dll':
            info['declaredVersion'] = '2.2'
            info['engineGlobal'] = 'SUPERWOW_VERSION="2.2"'
        elif ext_name == 'nampower.dll':
            info['declaredVersion'] = '4.6.2'
            info['logSignature'] = 'Loading nampower v4.6.2'
            info['luaGlobal'] = 'GetNampowerVersion'
        elif ext_name == 'UnitXP_SP3.dll':
            info['declaredBuild'] = 90
            pe_off = struct.unpack_from('<I', data, 0x3C)[0]
            ts = struct.unpack_from('<I', data, pe_off + 8)[0]
            info['peTimeDateStamp'] = ts
            info['luaGlobal'] = 'UnitXP'

        manifest['nativeExtensions'][ext_name] = info

    # Data MPQ inventory
    data_dir = client_root / 'Data'
    mpq_order = [
        'base.MPQ', 'dbc.MPQ', 'fonts.MPQ', 'interface.MPQ', 'misc.MPQ',
        'model.MPQ', 'sound.MPQ', 'speech.MPQ', 'terrain.MPQ', 'texture.MPQ', 'wmo.MPQ',
        'patch.MPQ', 'patch-1.mpq', 'patch-2.mpq', 'patch-3.mpq', 'patch-4.mpq',
        'patch-5.mpq', 'patch-O.mpq', 'patch-Y.MPQ'
    ]
    if data_dir.is_dir():
        for mpq_name in sorted(os.listdir(data_dir)):
            if mpq_name.lower().endswith('.mpq'):
                mp = data_dir / mpq_name
                manifest['dataArchives'][mpq_name] = {
                    'bytes': mp.stat().st_size,
                    'sha256': sha256_file(mp)
                }

    # Effective FrameXML inspection
    framexml_targets = [
        'Interface\\FrameXML\\ChatFrame.lua',
        'Interface\\FrameXML\\ChatFrame.xml',
        'Interface\\FrameXML\\GlobalStrings.lua',
        'Interface\\FrameXML\\QuestFrame.lua',
        'Interface\\FrameXML\\QuestFrame.xml',
        'Interface\\FrameXML\\GossipFrame.lua',
        'Interface\\FrameXML\\GossipFrame.xml',
        'Interface\\FrameXML\\LootFrame.lua',
        'Interface\\FrameXML\\LootFrame.xml',
        'Interface\\FrameXML\\UIParent.lua',
        'Interface\\FrameXML\\UIParent.xml',
        'Interface\\FrameXML\\FrameXML.toc',
        'Interface\\FrameXML\\QuestLogFrame.lua',
    ]
    effective_files: dict = {}
    for mpq_name in mpq_order:
        p = data_dir / mpq_name
        if not p.is_file():
            continue
        try:
            arc = MPQArchive(p)
            for t in framexml_targets:
                blob = arc.read_file(t)
                if blob is not None:
                    effective_files[t] = {
                        'sourceArchive': mpq_name,
                        'bytes': len(blob),
                        'sha256': hashlib.sha256(blob).hexdigest()
                    }
            arc.close()
        except Exception:
            pass

    manifest['frameXML'] = effective_files

    # Maintained addons in Interface\AddOns
    addons_dir = client_root / 'Interface' / 'AddOns'
    maintained = [
        'FostercareTweaks', 'ItemRack', 'AutoBG', 'Bagnon',
        'AutoLazy', 'TrinketMenu', 'MikScrollingBattleText', 'TWThreat'
    ]
    if addons_dir.is_dir():
        for a in maintained:
            ap = addons_dir / a
            if ap.is_dir():
                toc_path = ap / f"{a}.toc"
                manifest['deployedAddons'][a] = {
                    'path': str(ap),
                    'git': get_git_info(ap),
                    'toc': parse_toc_metadata(toc_path)
                }

    return manifest


def compare_manifests(curr: dict, prev: dict) -> list[str]:
    deltas = []
    # Realmlist
    if curr.get('realm') != prev.get('realm'):
        deltas.append(f"REALM: changed from {prev.get('realm')} to {curr.get('realm')}")

    # Executable
    ce = curr.get('clientExecutableInfo', {})
    pe = prev.get('clientExecutableInfo', {})
    if ce.get('sha256') != pe.get('sha256'):
        deltas.append(f"EXE: WoW.exe hash changed ({pe.get('sha256', '')[:12]} -> {ce.get('sha256', '')[:12]})")

    # Native extensions
    cext = curr.get('nativeExtensions', {})
    pext = prev.get('nativeExtensions', {})
    for k in sorted(set(cext.keys()) | set(pext.keys())):
        if k not in pext:
            deltas.append(f"NATIVE: + added extension {k}")
        elif k not in cext:
            deltas.append(f"NATIVE: - removed extension {k}")
        elif cext[k]['sha256'] != pext[k]['sha256']:
            deltas.append(f"NATIVE: ~ changed extension {k} (hash {pext[k]['sha256'][:10]}... -> {cext[k]['sha256'][:10]}...)")

    # MPQ archives
    cmpq = curr.get('dataArchives', {})
    pmpq = prev.get('dataArchives', {})
    for k in sorted(set(cmpq.keys()) | set(pmpq.keys())):
        if k not in pmpq:
            deltas.append(f"MPQ: + added {k} ({cmpq[k]['bytes']} bytes)")
        elif k not in cmpq:
            deltas.append(f"MPQ: - removed {k}")
        elif cmpq[k]['sha256'] != pmpq[k]['sha256']:
            deltas.append(f"MPQ: ~ changed {k} (size {pmpq[k]['bytes']} -> {cmpq[k]['bytes']})")

    # FrameXML
    cfx = curr.get('frameXML', {})
    pfx = prev.get('frameXML', {})
    for k in sorted(set(cfx.keys()) | set(pfx.keys())):
        if k not in pfx:
            deltas.append(f"FRAMEXML: + added {k}")
        elif k not in cfx:
            deltas.append(f"FRAMEXML: - removed {k}")
        elif cfx[k]['sha256'] != pfx[k]['sha256']:
            deltas.append(f"FRAMEXML: ~ changed {k} (source: {cfx[k]['sourceArchive']})")

    # Addons
    cad = curr.get('deployedAddons', {})
    pad = prev.get('deployedAddons', {})
    for k in sorted(set(cad.keys()) | set(pad.keys())):
        if k not in pad:
            deltas.append(f"ADDON: + added maintained addon {k}")
        elif k not in cad:
            deltas.append(f"ADDON: - removed maintained addon {k}")
        else:
            cg = cad[k].get('git', {}).get('head')
            pg = pad[k].get('git', {}).get('head')
            if cg != pg:
                deltas.append(f"ADDON: ~ {k} git commit updated ({pg[:8] if pg else 'none'} -> {cg[:8] if cg else 'none'})")

    return deltas


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--client', type=Path, default=Path(r'C:\Users\Fostercare\Desktop\client'),
                        help='Authoritative deployed client directory')
    parser.add_argument('--historical', type=Path, default=Path(r'C:\Users\Fostercare\Desktop\Niko2'),
                        help='Historical comparison client directory (optional)')
    parser.add_argument('--output', type=Path,
                        default=Path(r'C:\Users\Fostercare\Documents\VanillaForge\audit\octowow-client-manifest.json'),
                        help='Output path for JSON manifest')
    parser.add_argument('--compare', type=Path, default=None,
                        help='Previous manifest JSON file to compare against')
    args = parser.parse_args(argv)

    if not args.client.is_dir():
        print(f"ERROR: Authoritative client directory not found: {args.client}", file=sys.stderr)
        return 1

    print(f"Auditing deployed client: {args.client}")
    manifest = generate_manifest(args.client, args.historical if args.historical.is_dir() else None)

    prev_manifest = None
    if args.compare and args.compare.is_file():
        try:
            prev_manifest = json.loads(args.compare.read_text(encoding='utf-8'))
        except Exception as e:
            print(f"Warning: could not read comparison file: {e}", file=sys.stderr)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print(f"Manifest written to: {args.output}")

    if prev_manifest is not None:
        print(f"\nComparing with baseline manifest: {args.compare}")
        deltas = compare_manifests(manifest, prev_manifest)
        if not deltas:
            print("No material engineering deltas detected.")
        else:
            print(f"Detected {len(deltas)} material delta(s):")
            for d in deltas:
                print(f"  {d}")

    return 0


if __name__ == '__main__':
    sys.exit(main())
