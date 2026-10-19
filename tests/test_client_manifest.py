"""Client inventory never opens DLLs and keeps addon evidence separate."""
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import struct
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location(
    'client_manifest', Path(__file__).resolve().parents[1] / 'tools/octowow_client_manifest.py')
MANIFEST = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MANIFEST)


def versioned_pe(version, *, pe32_plus=False):
    """Minimal PE/resource fixture; version evidence resides in RT_VERSION."""
    parts = [int(part) for part in version.split('.')]
    parts += [0] * (4 - len(parts))
    ms, ls = parts[0] << 16 | parts[1], parts[2] << 16 | parts[3]
    blob = bytearray(92)
    struct.pack_into('<3H', blob, 0, len(blob), 52, 0)
    key = 'VS_VERSION_INFO\0'.encode('utf-16le')
    blob[6:6 + len(key)] = key
    struct.pack_into('<13I', blob, 40, 0xFEEF04BD, 0x10000, ms, ls, ms, ls, *([0] * 7))
    resource = bytearray(88) + blob
    for offset in (0, 24, 48):
        struct.pack_into('<2H', resource, offset + 12, 0, 1)
    struct.pack_into('<2I', resource, 16, 16, 0x80000018)
    struct.pack_into('<2I', resource, 40, 1, 0x80000030)
    struct.pack_into('<2I', resource, 64, 1033, 72)
    struct.pack_into('<4I', resource, 72, 4096 + 88, len(blob), 0, 0)
    image = bytearray(1024)
    image[:2] = b'MZ'
    struct.pack_into('<I', image, 0x3C, 128)
    image[128:132] = b'PE\0\0'
    optional_size, directory = (240, 112) if pe32_plus else (224, 96)
    struct.pack_into('<HHIIIHH', image, 132, 0x8664 if pe32_plus else 0x14C, 1, 0, 0, 0, optional_size, 0x102)
    struct.pack_into('<H', image, 152, 0x20B if pe32_plus else 0x10B)
    struct.pack_into('<I', image, 152 + directory - 4, 16)
    struct.pack_into('<2I', image, 152 + directory + 16, 4096, len(resource))
    section = 152 + optional_size
    image[section:section + 8] = b'.rsrc\0\0\0'
    struct.pack_into('<4I', image, section + 8, len(resource), 4096, 512, 512)
    image[512:512 + len(resource)] = resource
    return bytes(image)


class ClientManifestTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.client = self.root / 'client'
        self.client.mkdir()

    def test_discovery_includes_new_git_addons_and_separates_unmanaged_folders(self):
        addons = self.client / 'Interface/AddOns'
        for name in ('NewAddon', 'OtherAddon', 'Blizzard_InspectUI'):
            addon = addons / name
            addon.mkdir(parents=True)
            (addon / (name + '.toc')).write_text('## Interface: 11200\n## Version: 1.0\n')
            if name != 'Blizzard_InspectUI':
                (addon / '.git').mkdir()
        with patch.object(MANIFEST, 'get_git_info', return_value={'clean': True}):
            report = MANIFEST.inspect_addons(self.client)
        self.assertEqual(set(report['deployedAddons']), {'NewAddon', 'OtherAddon'})
        self.assertEqual(report['unmanagedAddons'], ['Blizzard_InspectUI'])
        self.assertEqual(report['deployedAddons']['NewAddon']['toc']['Version'], '1.0')

    def test_remote_verification_is_explicit_and_independent_of_cached_tracking(self):
        (self.client / '.git').mkdir()
        calls = []

        def git(command, **kwargs):
            arguments = command[3:]
            calls.append(arguments)
            if arguments == ['rev-parse', 'HEAD']:
                return 'a' * 40
            if arguments == ['status', '--short']:
                return ''
            if arguments == ['rev-parse', '--abbrev-ref', 'HEAD']:
                return 'main'
            if arguments == ['remote', 'get-url', 'origin']:
                return 'https://github.com/example/addon.git'
            if arguments == ['rev-parse', '--abbrev-ref', '@{u}']:
                return 'origin/main'
            if arguments == ['rev-list', '--left-right', '--count', 'HEAD...@{u}']:
                return '0\t0'
            if arguments == ['ls-remote', '--heads', 'origin', 'refs/heads/main']:
                return 'b' * 40 + '\trefs/heads/main'
            raise AssertionError(arguments)

        with patch.object(subprocess, 'check_output', side_effect=git):
            local = MANIFEST.get_git_info(self.client)
            self.assertFalse(any(args[0] == 'ls-remote' for args in calls))
            remote = MANIFEST.get_git_info(self.client, True)
        self.assertEqual(local['remoteVerification'], 'not_requested')
        self.assertEqual(remote['ahead'], 0)
        self.assertEqual(remote['behind'], 0)
        self.assertFalse(remote['remoteMatchesHead'])
        self.assertEqual(remote['remoteVerification'], 'verified')

    def test_loader_comments_and_unreadable_archives_are_recorded(self):
        (self.client / 'dlls.txt').write_text('# disabled.dll\n; another.dll\nD3D9.DLL\nmissing.dll\n')
        data = self.client / 'Data'
        data.mkdir()
        (data / 'patch-5.mpq').write_bytes(b'invalid archive')
        report = MANIFEST.generate_manifest(self.client)
        self.assertEqual(report['loaderConfiguration']['dlls_txt']['entries'], ['D3D9.DLL', 'missing.dll'])
        self.assertNotIn('missingEntries', report['loaderConfiguration'])
        self.assertEqual(report['frameXMLReadErrors'][0]['archive'], 'patch-5.mpq')

    def test_dlls_are_never_opened_or_reported(self):
        # CORE: the DLL stack is assumed installed; no hashing or version reads.
        for name in ('ClassicAPI.dll', 'SuperWoWhook.dll', 'nampower.dll', 'UnitXP_SP3.dll', 'd3d9.dll'):
            (self.client / name).write_bytes(b'native fixture')
        opened = []
        original_open, original_bytes = Path.open, Path.read_bytes

        def watch_open(path, *args, **kwargs):
            opened.append(path.name.casefold())
            return original_open(path, *args, **kwargs)

        def watch_bytes(path):
            opened.append(path.name.casefold())
            return original_bytes(path)

        with patch.object(Path, 'open', watch_open), patch.object(Path, 'read_bytes', watch_bytes):
            report = MANIFEST.generate_manifest(self.client)
        self.assertFalse([name for name in opened if name.endswith('.dll')])
        self.assertNotIn('nativeExtensions', report)
        self.assertNotIn('environment', report)
        for removed in ('inspect_environment', 'native_extension_info', 'NATIVE_REFERENCES', 'pe_architecture'):
            self.assertFalse(hasattr(MANIFEST, removed), removed)

    def test_environment_check_option_is_gone(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as exit:
            MANIFEST.main(['--client', str(self.client), '--check-environment'])
        self.assertEqual(exit.exception.code, 2)

    def test_quick_inventory_does_not_hash_game_or_report_removed_native_files(self):
        output = self.root / 'inventory.json'
        previous = self.root / 'previous.json'
        previous.write_text(json.dumps({'clientExecutableInfo': {'sha256': 'old'},
                                       'nativeExtensions': {'old.dll': {'sha256': 'old'}}}))
        with patch.object(MANIFEST, 'generate_manifest', side_effect=AssertionError('must not inspect runtime')):
            with contextlib.redirect_stdout(io.StringIO()) as printed:
                result = MANIFEST.main(['--client', str(self.client), '--addons-only',
                                        '--output', str(output), '--compare', str(previous)])
        self.assertEqual(result, 0)
        self.assertEqual(json.loads(output.read_text())['scope'], 'addon Git/TOC inventory')
        self.assertNotIn('removed extension', printed.getvalue())
        self.assertNotIn('EXE:', printed.getvalue())

    def test_invalid_archive_closes_handle_when_constructor_fails(self):
        path = self.client / 'bad.mpq'
        path.write_bytes(b'not an MPQ')
        handle = path.open('rb')
        self.addCleanup(handle.close)
        with patch('builtins.open', return_value=handle):
            with self.assertRaises(ValueError):
                MANIFEST.MPQArchive(path)
        self.assertTrue(handle.closed)

    def test_unknown_patches_and_loose_framexml_stay_visible_as_scoped_evidence(self):
        data = self.client / 'Data'
        data.mkdir()
        (data / 'patch-custom.mpq').write_bytes(b'custom archive fixture')
        loose = self.client / 'Interface/FrameXML/ChatFrame.lua'
        loose.parent.mkdir(parents=True)
        loose.write_bytes(b'-- loose override candidate')
        report = MANIFEST.generate_manifest(self.client)
        scope = report['frameXMLInspection']
        self.assertEqual(scope['status'], 'scoped_inventory')
        self.assertEqual(scope['uninspectedArchives'], ['patch-custom.mpq'])
        self.assertEqual(scope['looseCandidates']['Interface\\FrameXML\\ChatFrame.lua']['sha256'],
                         hashlib.sha256(loose.read_bytes()).hexdigest())
        self.assertNotIn('Interface\\FrameXML\\ChatFrame.lua', report['frameXML'])
        previous = json.loads(json.dumps(report))
        loose.write_bytes(b'-- changed loose candidate')
        self.assertTrue(any('loose candidate evidence changed' in delta for delta in
                            MANIFEST.compare_manifests(MANIFEST.generate_manifest(self.client), previous)))

    def test_same_commit_does_not_hide_toc_or_working_tree_changes(self):
        previous = {'deployedAddons': {'Example': {'toc': {'Interface': '11200'},
                    'runtimeTocExists': True, 'git': {'head': 'a' * 40, 'clean': True, 'status': 'clean'}}}}
        current = json.loads(json.dumps(previous))
        self.assertEqual(MANIFEST.compare_manifests(current, previous), [])
        current['deployedAddons']['Example']['toc']['Interface'] = '30400'
        current['deployedAddons']['Example']['git'].update(clean=False, status=' M Core.lua')
        deltas = MANIFEST.compare_manifests(current, previous)
        self.assertTrue(any('TOC metadata' in delta for delta in deltas))
        self.assertTrue(any('working-tree' in delta for delta in deltas))
        self.assertFalse(any('git commit updated' in delta for delta in deltas))

    def test_version_resource_parser_handles_pe32_plus_and_rejects_bad_bounds(self):
        path = self.client / 'WoW.exe'
        path.write_bytes(versioned_pe('1.12.1.5875', pe32_plus=True))
        self.assertEqual(MANIFEST.get_pe_version_strings(path)['FileVersion'], '1.12.1.5875')
        for blob in (versioned_pe('2.2')[:550], b'MZ' + bytes(200),
                     b'FileVersion\0' + '999.0\0'.encode('utf-16le')):
            path.write_bytes(blob)
            self.assertEqual(MANIFEST.get_pe_version_strings(path), {})

    def test_reports_cannot_be_written_inside_game(self):
        output = self.client / 'report.json'
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(MANIFEST.main(['--client', str(self.client), '--output', str(output)]), 1)
        self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()
