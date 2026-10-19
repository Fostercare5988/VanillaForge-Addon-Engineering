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

# These hashes identify the dated reference files; they do not prove runtime
# loading or compatibility. Only ClassicAPI has upstream asset provenance here.
NATIVE_REFERENCES = {
    'ClassicAPI.dll': ('1.16.0', 'ae88fc0461b58eff37171e10015ddaf8c27b1f428794c4ff927429389fc2535b'),
    'SuperWoWhook.dll': ('2.2', 'bd214b32c878649e94ce654835946bd05e0ce7710e8f01bae10d8ab50a89351d'),
    'nampower.dll': ('4.6.2', '96af1722ee6b1a76cbb11e59e452fe54a83f54a3da80ae24f9c7571a0a6392fe'),
    'UnitXP_SP3.dll': ('90', '74a0a80aef02be28187fd67e9ec3945d54828ef3302a827754b4c40b69cdaed8'),
    'd3d9.dll': ('3.1.1', '265888c31ca78dffa290c39cb7e50bfb02762590e41927906e46fb32f01497fa'),
}

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


def get_git_info(repo_path: Path, verify_remote: bool = False) -> dict:
    if not (repo_path / '.git').exists():
        return {'status': 'not_a_repo'}
    try:
        def git(*args):
            return subprocess.check_output(
                ['git', '-C', str(repo_path), *args], stderr=subprocess.DEVNULL,
                timeout=20, encoding='utf-8', errors='replace').strip()

        head = git('rev-parse', 'HEAD')
        status_out = git('status', '--short')
        branch = git('rev-parse', '--abbrev-ref', 'HEAD')
        result = {
            'head': head,
            'branch': branch,
            'clean': len(status_out) == 0,
            'status': status_out if status_out else 'clean',
            'remoteVerification': 'not_requested',
        }
        try:
            result['origin'] = git('remote', 'get-url', 'origin')
        except subprocess.CalledProcessError:
            result['origin'] = None
        try:
            result['upstream'] = git('rev-parse', '--abbrev-ref', '@{u}')
            ahead, behind = git('rev-list', '--left-right', '--count', 'HEAD...@{u}').split()
            result.update(ahead=int(ahead), behind=int(behind), trackingEvidence='local refs; fetch may be stale')
        except subprocess.CalledProcessError:
            result['upstream'] = None
        if verify_remote:
            if not result['origin'] or branch == 'HEAD':
                result['remoteVerification'] = 'unavailable'
            else:
                try:
                    remote = git('ls-remote', '--heads', 'origin', 'refs/heads/' + branch)
                    remote_head = remote.split()[0] if remote else None
                    result.update(remoteHead=remote_head, remoteMatchesHead=remote_head == head,
                                  remoteVerification='verified' if remote_head else 'branch_missing')
                except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
                    result.update(remoteVerification='failed', remoteError=str(error))
        return result
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


def inspect_addons(client_root: Path, verify_remotes: bool = False) -> dict:
    """Discover installed Git checkouts without a second maintained-name list."""
    addons_dir = client_root / 'Interface' / 'AddOns'
    result = {'deployedAddons': {}, 'unmanagedAddons': []}
    if addons_dir.is_dir():
        for addon in sorted(addons_dir.iterdir(), key=lambda p: p.name.casefold()):
            if not addon.is_dir():
                continue
            if not (addon / '.git').exists():
                result['unmanagedAddons'].append(addon.name)
                continue
            toc = addon / (addon.name + '.toc')
            result['deployedAddons'][addon.name] = {
                'path': str(addon), 'git': get_git_info(addon, verify_remotes),
                'toc': parse_toc_metadata(toc), 'runtimeTocExists': toc.is_file(),
            }
    return result


def native_extension_info(path: Path, loader_entries: list[str]) -> dict:
    data = path.read_bytes()
    info = {
        'filename': path.name, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(),
        'listedInDllsTxt': path.name.casefold() in {entry.casefold() for entry in loader_entries},
        'versionStrings': get_pe_version_strings(path),
    }
    # A missing version resource is unknown, never the framework's target.
    info['declaredVersion'] = info['versionStrings'].get('FileVersion')
    reference = NATIVE_REFERENCES.get(path.name)
    if reference:
        version, digest = reference
        info.update(referenceHashMatches=info['sha256'] == digest,
                    referenceVersion=version,
                    referenceEvidence='audit/OCTOWOW_NATIVE_STACK.md and OCTOWOW_CLIENT_BASELINE.md')
        if path.name == 'ClassicAPI.dll':
            info['sha256MatchesUpstreamRelease'] = info['sha256'] == digest
            info['knownUpstreamTag'] = 'v' + version
    return info


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
        'frameXMLReadErrors': [],
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
        loader_entries = [line.strip() for line in dlls_txt.read_text(errors='ignore').splitlines()
                          if line.strip() and not line.lstrip().startswith(('#', ';'))]
        manifest['loaderConfiguration']['dlls_txt'] = {
            'path': str(dlls_txt),
            'sha256': sha256_file(dlls_txt),
            'entries': loader_entries
        }
        manifest['loaderConfiguration']['missingEntries'] = [
            entry for entry in loader_entries if not (client_root / entry).is_file()]

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
        'AuctionQueryThrottle.dll', 'transmogfix.dll', 'd3d9.dll', 'dxgi.dll',
        'VanillaFixes.exe', 'VanillaHelpers.dll', 'VanillaMultiMonitorFix.dll', 'VfPatcher.dll'
    ]
    for ext_name in ext_files:
        p = client_root / ext_name
        if not p.is_file():
            continue
        manifest['nativeExtensions'][ext_name] = native_extension_info(p, loader_entries)

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
        arc = None
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
        except Exception as error:
            manifest['frameXMLReadErrors'].append({'archive': mpq_name, 'error': str(error)})
        finally:
            if arc is not None:
                arc.close()

    manifest['frameXML'] = effective_files

    manifest.update(inspect_addons(client_root))

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
    parser.add_argument('--client', type=Path, default=Path(r'C:\Users\Fostercare\Desktop\client-2026-10-10'),
                        help='Authoritative deployed client directory')
    parser.add_argument('--historical', type=Path, default=Path(r'C:\Users\Fostercare\Desktop\client-2026-10-06'),
                        help='Historical comparison client directory (optional)')
    parser.add_argument('--output', type=Path,
                        default=Path(r'C:\Users\Fostercare\Documents\VanillaForge\audit\octowow-client-manifest.json'),
                        help='Output path for JSON manifest')
    parser.add_argument('--compare', type=Path, default=None,
                        help='Previous manifest JSON file to compare against')
    parser.add_argument('--addons-only', action='store_true',
                        help='Quick portfolio status without hashing game archives')
    parser.add_argument('--verify-remotes', action='store_true',
                        help='Read origin branch heads over the network; no fetch or push')
    args = parser.parse_args(argv)

    if not args.client.is_dir():
        print(f"ERROR: Authoritative client directory not found: {args.client}", file=sys.stderr)
        return 1
    if args.output.resolve().is_relative_to(args.client.resolve()):
        print('ERROR: Keep manifests outside the active game directory.', file=sys.stderr)
        return 1

    print(f"Auditing deployed client: {args.client}")
    if args.addons_only:
        manifest = dict(generatedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                        authoritativeClientRoot=str(args.client.resolve()), scope='addon Git/TOC inventory',
                        **inspect_addons(args.client.resolve(), args.verify_remotes))
    else:
        manifest = generate_manifest(args.client, args.historical if args.historical.is_dir() else None)
        if args.verify_remotes:
            manifest.update(inspect_addons(args.client.resolve(), True))

    prev_manifest = None
    if args.compare and args.compare.is_file():
        try:
            prev_manifest = json.loads(args.compare.read_text(encoding='utf-8'))
        except Exception as e:
            print(f"Warning: could not read comparison file: {e}", file=sys.stderr)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print(f"Manifest written to: {args.output}")
    for name, addon in manifest['deployedAddons'].items():
        git = addon['git']
        print(f"  {name}: {git.get('head', '?')[:8]} "
              f"{'clean' if git.get('clean') else 'CHANGED'}; origin {git.get('remoteVerification', 'unknown')}")

    if prev_manifest is not None:
        print(f"\nComparing with baseline manifest: {args.compare}")
        if args.addons_only:
            prev_manifest = {'deployedAddons': prev_manifest.get('deployedAddons', {})}
        deltas = compare_manifests(manifest, prev_manifest)
        if not deltas:
            print("No material engineering deltas detected.")
        else:
            print(f"Detected {len(deltas)} material delta(s):")
            for d in deltas:
                print(f"  {d}")

    incomplete = bool(manifest.get('frameXMLReadErrors'))
    if incomplete:
        print('ERROR: FrameXML inspection was incomplete; see frameXMLReadErrors.', file=sys.stderr)
    remote_failed = args.verify_remotes and any(
        addon['git'].get('remoteVerification') != 'verified' or not addon['git'].get('remoteMatchesHead')
        for addon in manifest['deployedAddons'].values())
    return int(incomplete or remote_failed)


if __name__ == '__main__':
    sys.exit(main())
