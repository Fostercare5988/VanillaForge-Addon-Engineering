"""Client evidence must distinguish observed files, reference identity and loading."""
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location(
    'client_manifest', Path(__file__).resolve().parents[1] / 'tools/octowow_client_manifest.py')
MANIFEST = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MANIFEST)


class ClientManifestTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.client = self.root / 'client'
        self.client.mkdir()

    def test_unknown_binaries_never_inherit_target_versions(self):
        for name in ('ClassicAPI.dll', 'SuperWoWhook.dll', 'nampower.dll', 'UnitXP_SP3.dll'):
            path = self.client / name
            path.write_bytes(bytes(128))
        report = MANIFEST.generate_manifest(self.client)
        for info in report['nativeExtensions'].values():
            self.assertIsNone(info['declaredVersion'])
            self.assertFalse(info['referenceHashMatches'])
            self.assertNotIn('declaredBuild', info)
            self.assertNotIn('engineGlobal', info)

    def test_reference_match_is_file_identity_not_a_version_declaration(self):
        path = self.client / 'nampower.dll'
        path.write_bytes(b'reference fixture')
        with patch.dict(MANIFEST.NATIVE_REFERENCES,
                        {'nampower.dll': ('4.6.2', hashlib.sha256(path.read_bytes()).hexdigest())}):
            info = MANIFEST.native_extension_info(path, ['NAMPOWER.DLL'])
        self.assertTrue(info['referenceHashMatches'])
        self.assertEqual(info['referenceVersion'], '4.6.2')
        self.assertIsNone(info['declaredVersion'])
        self.assertTrue(info['listedInDllsTxt'])
        self.assertNotIn('loadedInDllsTxt', info)

    def test_actual_pe_resource_wins_over_reference_target(self):
        path = self.client / 'ClassicAPI.dll'
        path.write_bytes('FileVersion\0'.encode('utf-16le') + '1.15.12.0\0'.encode('utf-16le'))
        info = MANIFEST.native_extension_info(path, [])
        self.assertEqual(info['declaredVersion'], '1.15.12.0')
        self.assertFalse(info['sha256MatchesUpstreamRelease'])

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

    def test_loader_comments_d3d9_and_unreadable_archives_are_recorded(self):
        (self.client / 'dlls.txt').write_text('# disabled.dll\n; another.dll\nD3D9.DLL\nmissing.dll\n')
        (self.client / 'd3d9.dll').write_bytes(b'graphics fixture')
        data = self.client / 'Data'
        data.mkdir()
        (data / 'patch-5.mpq').write_bytes(b'invalid archive')
        report = MANIFEST.generate_manifest(self.client)
        self.assertEqual(report['loaderConfiguration']['dlls_txt']['entries'], ['D3D9.DLL', 'missing.dll'])
        self.assertTrue(report['nativeExtensions']['d3d9.dll']['listedInDllsTxt'])
        self.assertEqual(report['frameXMLReadErrors'][0]['archive'], 'patch-5.mpq')

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

    def test_reports_cannot_be_written_inside_game(self):
        output = self.client / 'report.json'
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(MANIFEST.main(['--client', str(self.client), '--output', str(output)]), 1)
        self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()
