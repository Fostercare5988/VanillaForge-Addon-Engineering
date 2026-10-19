#!/usr/bin/env python3
"""Deterministic, read-only client manifest generator and update diff tool for OctoWoW.

Standard library only. No process interaction, no binary mutation, no private/WTF data.
Tracks the client executable, loader configuration, Data MPQs, scoped FrameXML
candidates, and maintained addon working tree state. DLLs are never opened or
hashed (CORE): the required stack is assumed installed.
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

ROOT = Path(__file__).resolve().parents[1]
TARGET_PROFILE = ROOT / 'TARGET_ENVIRONMENT.json'
UPSTREAM_CONFIG = ROOT / 'UPSTREAM_VERSIONS.json'

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



def sha256_file(path: Path) -> str:
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def get_pe_version_strings(path: Path) -> dict[str, str]:
    """Read fixed version fields from a bounded PE RT_VERSION resource.

    An embedded text match is not a version resource. PE32 and PE32+ use the
    resource directory and VS_FIXEDFILEINFO layouts documented by Microsoft:
    https://learn.microsoft.com/windows/win32/debug/pe-format
    https://learn.microsoft.com/windows/win32/api/verrsrc/ns-verrsrc-vs_fixedfileinfo
    """
    try:
        data = path.read_bytes()
        if data[:2] != b'MZ':
            return {}

        def unpack(fmt, offset):
            if offset < 0 or offset + struct.calcsize(fmt) > len(data):
                raise ValueError('Truncated PE structure')
            return struct.unpack_from(fmt, data, offset)

        pe = unpack('<I', 0x3C)[0]
        if data[pe:pe + 4] != b'PE\0\0':
            return {}
        sections = unpack('<H', pe + 6)[0]
        optional_size = unpack('<H', pe + 20)[0]
        optional = pe + 24
        magic = unpack('<H', optional)[0]
        directory = {0x10B: 96, 0x20B: 112}.get(magic)
        if directory is None or optional_size < directory + 24 or not 0 < sections <= 96:
            return {}
        if unpack('<I', optional + directory - 4)[0] < 3:
            return {}
        resource_rva, resource_size = unpack('<2I', optional + directory + 16)
        section_table = optional + optional_size

        def rva_offset(rva, length):
            for index in range(sections):
                _, address, raw_size, raw_offset = unpack('<4I', section_table + index * 40 + 8)
                delta = rva - address
                if 0 <= delta and delta + length <= raw_size:
                    offset = raw_offset + delta
                    if offset + length <= len(data):
                        return offset
            raise ValueError('Resource RVA is outside section data')

        base = rva_offset(resource_rva, resource_size)

        def resource_unpack(fmt, relative):
            if relative < 0 or relative + struct.calcsize(fmt) > resource_size:
                raise ValueError('Resource directory exceeds its bounds')
            return unpack(fmt, base + relative)

        versions, visited = [], set()

        def walk(relative, depth):
            if depth > 2 or relative in visited or len(visited) >= 4096:
                raise ValueError('Unexpected version resource directory depth')
            visited.add(relative)
            named, ids = resource_unpack('<2H', relative + 12)
            count = named + ids
            if count > 4096:
                raise ValueError('Resource directory entry limit exceeded')
            for index in range(count):
                name, target = resource_unpack('<2I', relative + 16 + index * 8)
                if depth == 0 and name != 16:  # RT_VERSION
                    continue
                if target & 0x80000000:
                    walk(target & 0x7FFFFFFF, depth + 1)
                    continue
                if depth != 2:
                    raise ValueError('Unexpected version resource leaf')
                rva, size = resource_unpack('<2I', target)
                offset = rva_offset(rva, size)
                blob = data[offset:offset + size]
                if len(blob) < 6:
                    raise ValueError('Truncated version resource')
                length, value_length, value_type = struct.unpack_from('<3H', blob)
                key = 'VS_VERSION_INFO\0'.encode('utf-16le')
                fixed = (6 + len(key) + 3) & ~3
                if (blob[6:6 + len(key)] != key or length > len(blob)
                        or value_type != 0 or value_length != 52 or fixed + 52 > length):
                    raise ValueError('Invalid VS_VERSION_INFO')
                fields = struct.unpack_from('<13I', blob, fixed)
                if fields[:2] != (0xFEEF04BD, 0x00010000):
                    raise ValueError('Invalid VS_FIXEDFILEINFO')

                def version(ms, ls):
                    return '.'.join(str(part) for part in (ms >> 16, ms & 0xFFFF, ls >> 16, ls & 0xFFFF))

                versions.append({'FileVersion': version(fields[2], fields[3]),
                                 'ProductVersion': version(fields[4], fields[5])})

        walk(0, 0)
        if versions and all(version == versions[0] for version in versions):
            return versions[0]
    except (OSError, ValueError, struct.error):
        return {}
    return {}


def numeric_version(value: str) -> tuple[int, ...] | None:
    if not isinstance(value, str) or re.fullmatch(r'\d+(?:\.\d+)*', value) is None:
        return None
    parts = [int(part) for part in value.split('.')]
    while len(parts) > 1 and parts[-1] == 0:
        parts.pop()
    return tuple(parts)


def client_file(root: Path, filename: str) -> Path:
    """Match Windows file identity on case-sensitive fixture hosts as well."""
    expected = root / filename
    if expected.is_file() or not root.is_dir():
        return expected
    return next((path for path in root.iterdir() if path.name.casefold() == filename.casefold()), expected)


def read_loader_entries(path: Path) -> list[str]:
    if not path.is_file():
        return []
    return [line.strip().strip('"') for line in path.read_text(encoding='utf-8-sig').splitlines()
            if line.strip() and not line.lstrip().startswith(('#', ';'))]


def configured_realm(path: Path) -> str | None:
    if not path.is_file():
        return None
    values = re.findall(r'^\s*(?:set\s+)?realmlist\s+(?:"([^"]+)"|\'([^\']+)\'|([^\s#;]+))',
                        path.read_text(encoding='utf-8-sig'), re.I | re.M)
    return next((value for value in reversed(values[-1]) if value), None) if values else None


def load_environment_requirements(target_path: Path = TARGET_PROFILE,
                                  upstream_path: Path = UPSTREAM_CONFIG) -> tuple[dict, dict, dict]:
    """Validate the shared target profile and canonical dependency floors offline."""
    target_bytes, upstream_bytes = target_path.read_bytes(), upstream_path.read_bytes()
    target, upstream = json.loads(target_bytes), json.loads(upstream_bytes)
    if (not isinstance(target, dict) or type(target.get('schema_version')) is not int
            or target['schema_version'] != 1 or not isinstance(upstream, dict)):
        raise ValueError('Unsupported environment profile or upstream registry')
    client, server, extensions = target.get('client'), target.get('server'), target.get('required_extensions')
    if not isinstance(client, dict) or not isinstance(server, dict) or not isinstance(extensions, dict):
        raise ValueError('Environment profile sections must be objects')
    for key in ('distribution_revision', 'engine_version', 'executable', 'launcher'):
        if not isinstance(client.get(key), str) or not client[key]:
            raise ValueError(f'client.{key} must be a nonempty string')
    if numeric_version(client['engine_version']) != (1, 12, 1, 5875) or client.get('interface') != 11200:
        raise ValueError('Client target must declare WoW 1.12.1.5875 and Interface 11200')
    if not isinstance(server.get('realmlist'), str) or not server['realmlist']:
        raise ValueError('server.realmlist must be a nonempty string')
    expected = {'classicapi': 'ClassicAPI.dll', 'superwow': 'SuperWoWhook.dll',
                'nampower': 'nampower.dll', 'unitxp_sp3': 'UnitXP_SP3.dll'}
    if extensions != expected:
        raise ValueError('Profile must require the canonical ClassicAPI, SuperWoW, NamPower and UnitXP SP3 binaries')
    for filename in [client['executable'], client['launcher'], *extensions.values()]:
        if not isinstance(filename, str) or not filename or '/' in filename or '\\' in filename or ':' in filename or filename in {'.', '..'}:
            raise ValueError('Profile binary filenames must be root filenames')
    for component in extensions:
        config = upstream.get(component)
        if not isinstance(config, dict) or numeric_version(config.get('minimum_version')) is None:
            raise ValueError(f'{component}.minimum_version must be a numeric version string')
        provenance = config.get('release_provenance')
        if provenance is not None and not isinstance(provenance, dict):
            raise ValueError(f'{component}.release_provenance must be an object')
        supported = config.get('supported_release_provenance', [])
        if not isinstance(supported, list) or any(not isinstance(entry, dict) for entry in supported):
            raise ValueError(f'{component}.supported_release_provenance must be a list of objects')
        for entry in ([provenance] if provenance else []) + supported:
            if 'dll_sha256' in entry and (not isinstance(entry['dll_sha256'], str)
                    or re.fullmatch(r'[0-9a-f]{64}', entry['dll_sha256']) is None):
                raise ValueError(f'{component} release provenance requires a valid DLL SHA-256')
            if 'dll_sha256' in entry and numeric_version(
                    entry.get('version') or str(entry.get('tag', '')).lstrip('vV')) is None:
                raise ValueError(f'{component} DLL provenance requires a numeric release version')
    inputs = {'target_profile_sha256': hashlib.sha256(target_bytes).hexdigest(),
              'upstream_registry_sha256': hashlib.sha256(upstream_bytes).hexdigest()}
    return target, upstream, inputs


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


def generate_manifest(client_root: Path, historical_root: Path | None = None) -> dict:
    client_root = client_root.resolve()
    manifest: dict = {
        'generatedAt': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'authoritativeClientRoot': str(client_root),
        'historicalClientRoot': str(historical_root.resolve()) if historical_root else None,
        'clientExecutable': 'WoW.exe',
        'realm': None,
        'loaderConfiguration': {},
        'dataArchives': {},
        'frameXML': {},
        'frameXMLReadErrors': [],
        'deployedAddons': {}
    }

    # Realm
    realm_file = client_root / 'realmlist.wtf'
    if realm_file.is_file():
        manifest['realm'] = configured_realm(realm_file)

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
        loader_entries = read_loader_entries(dlls_txt)
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

    # Data MPQ inventory
    data_dir = client_root / 'Data'
    mpq_order = MPQ_ORDER
    if data_dir.is_dir():
        for mpq_name in sorted(os.listdir(data_dir)):
            if mpq_name.lower().endswith('.mpq'):
                mp = data_dir / mpq_name
                manifest['dataArchives'][mpq_name] = {
                    'bytes': mp.stat().st_size,
                    'sha256': sha256_file(mp)
                }

    # Scoped extraction order, not proof of the runtime's complete resolution.
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
    inspected_archives = []
    for mpq_name in mpq_order:
        p = client_file(data_dir, mpq_name)
        if not p.is_file():
            continue
        inspected_archives.append(p.name)
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
    manifest['frameXMLInspection'] = {
        'status': 'scoped_inventory',
        'archiveOrder': inspected_archives,
        'uninspectedArchives': sorted(name for name in manifest['dataArchives']
                                     if name.casefold() not in {item.casefold() for item in mpq_order}),
        'looseCandidates': {},
        'limitations': 'Selected paths extracted in the listed archive order; this does not establish complete archive coverage, active patch precedence or runtime UI behavior.',
    }
    for name in framexml_targets:
        path = client_root / name.replace('\\', '/')
        if path.is_file():
            manifest['frameXMLInspection']['looseCandidates'][name] = {
                'bytes': path.stat().st_size, 'sha256': sha256_file(path)}

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
    if curr.get('frameXMLInspection') != prev.get('frameXMLInspection'):
        deltas.append('FRAMEXML: scoped inspection or loose candidate evidence changed')
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
            if any(cad[k].get(field) != pad[k].get(field) for field in ('toc', 'runtimeTocExists')):
                deltas.append(f'ADDON: ~ {k} TOC metadata or manifest presence changed')
            if any(cad[k].get('git', {}).get(field) != pad[k].get('git', {}).get(field)
                   for field in ('clean', 'status')):
                deltas.append(f'ADDON: ~ {k} working-tree evidence changed')
            cg = cad[k].get('git', {}).get('head')
            pg = pad[k].get('git', {}).get('head')
            if cg != pg:
                deltas.append(f"ADDON: ~ {k} git commit updated ({pg[:8] if pg else 'none'} -> {cg[:8] if cg else 'none'})")

    return deltas


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--client', type=Path, required=True,
                        help='Explicitly selected deployed client directory')
    parser.add_argument('--historical', type=Path,
                        help='Historical comparison client directory (optional)')
    parser.add_argument('--output', type=Path, help='Private JSON destination outside the client; default stdout')
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
    if args.output and args.output.resolve().is_relative_to(args.client.resolve()):
        print('ERROR: Keep manifests outside the active game directory.', file=sys.stderr)
        return 1
    if args.output and args.compare and args.output.resolve() == args.compare.resolve():
        print('ERROR: Preserve comparison evidence; input and output must differ.', file=sys.stderr)
        return 1

    print(f"Auditing deployed client: {args.client}", file=sys.stderr)
    if args.addons_only:
        manifest = dict(generatedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                        authoritativeClientRoot=str(args.client.resolve()), scope='addon Git/TOC inventory',
                        **inspect_addons(args.client.resolve(), args.verify_remotes))
    else:
        manifest = generate_manifest(args.client, args.historical if args.historical and args.historical.is_dir() else None)
        if args.verify_remotes:
            manifest.update(inspect_addons(args.client.resolve(), True))

    prev_manifest = None
    if args.compare and args.compare.is_file():
        try:
            prev_manifest = json.loads(args.compare.read_text(encoding='utf-8'))
        except Exception as e:
            print(f"Warning: could not read comparison file: {e}", file=sys.stderr)

    output = json.dumps(manifest, indent=2) + '\n'
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output, encoding='utf-8')
        print(f"Manifest written to: {args.output}", file=sys.stderr)
    else:
        print(output, end='')
    for name, addon in manifest['deployedAddons'].items():
        git = addon['git']
        print(f"  {name}: {git.get('head', '?')[:8]} "
              f"{'clean' if git.get('clean') else 'CHANGED'}; origin {git.get('remoteVerification', 'unknown')}", file=sys.stderr)

    if prev_manifest is not None:
        print(f"\nComparing with baseline manifest: {args.compare}", file=sys.stderr)
        if args.addons_only:
            prev_manifest = {'deployedAddons': prev_manifest.get('deployedAddons', {})}
        deltas = compare_manifests(manifest, prev_manifest)
        if not deltas:
            print("No material engineering deltas detected.", file=sys.stderr)
        else:
            print(f"Detected {len(deltas)} material delta(s):", file=sys.stderr)
            for d in deltas:
                print(f"  {d}", file=sys.stderr)

    incomplete = bool(manifest.get('frameXMLReadErrors'))
    if incomplete:
        print('ERROR: FrameXML inspection was incomplete; see frameXMLReadErrors.', file=sys.stderr)
    remote_failed = args.verify_remotes and any(
        addon['git'].get('remoteVerification') != 'verified' or not addon['git'].get('remoteMatchesHead')
        for addon in manifest['deployedAddons'].values())
    return int(incomplete or remote_failed)


if __name__ == '__main__':
    sys.exit(main())
