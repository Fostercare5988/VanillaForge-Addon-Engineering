#!/usr/bin/env python3
"""Read-only inventory of maintained addon checkouts in a client's Interface/AddOns.

Standard library only. Reports each Git checkout's head, working-tree state and
TOC metadata, and compares with a previous inventory. It never opens the client
installation, its DLLs or archives (CORE). The target-profile validator below is
shared with the framework documentation checker.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
TARGET_PROFILE = ROOT / 'TARGET_ENVIRONMENT.json'
UPSTREAM_CONFIG = ROOT / 'UPSTREAM_VERSIONS.json'

def numeric_version(value: str) -> tuple[int, ...] | None:
    if not isinstance(value, str) or re.fullmatch(r'\d+(?:\.\d+)*', value) is None:
        return None
    parts = [int(part) for part in value.split('.')]
    while len(parts) > 1 and parts[-1] == 0:
        parts.pop()
    return tuple(parts)


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


def compare_manifests(curr: dict, prev: dict) -> list[str]:
    deltas = []
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
    parser.add_argument('--output', type=Path, help='Private JSON destination outside the client; default stdout')
    parser.add_argument('--compare', type=Path, default=None,
                        help='Previous manifest JSON file to compare against')
    parser.add_argument('--addons-only', action='store_true',
                        help='Accepted for existing commands; addon inventory is the only mode')
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

    print(f"Inventorying addons in: {args.client}", file=sys.stderr)
    manifest = dict(generatedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    authoritativeClientRoot=str(args.client.resolve()), scope='addon Git/TOC inventory',
                    **inspect_addons(args.client.resolve(), args.verify_remotes))

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
        prev_manifest = {'deployedAddons': prev_manifest.get('deployedAddons', {})}
        deltas = compare_manifests(manifest, prev_manifest)
        if not deltas:
            print("No material engineering deltas detected.", file=sys.stderr)
        else:
            print(f"Detected {len(deltas)} material delta(s):", file=sys.stderr)
            for d in deltas:
                print(f"  {d}", file=sys.stderr)

    remote_failed = args.verify_remotes and any(
        addon['git'].get('remoteVerification') != 'verified' or not addon['git'].get('remoteMatchesHead')
        for addon in manifest['deployedAddons'].values())
    return int(remote_failed)


if __name__ == '__main__':
    sys.exit(main())
