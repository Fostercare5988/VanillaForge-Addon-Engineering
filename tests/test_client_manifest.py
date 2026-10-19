"""Client evidence must distinguish observed files, reference identity and loading."""
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

    def test_unknown_binaries_never_inherit_target_versions(self):
        for name in ('ClassicAPI.dll', 'SuperWoWhook.dll', 'nampower.dll', 'UnitXP_SP3.dll'):
            path = self.client / name
            path.write_bytes(bytes(128))
        report = MANIFEST.generate_manifest(self.client)
        self.assertNotIn('clientBuild', report)
        self.assertNotIn('interfaceVersion', report)
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
        path.write_bytes(versioned_pe('1.15.12.0'))
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

    def test_reports_cannot_be_written_inside_game(self):
        output = self.client / 'report.json'
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(MANIFEST.main(['--client', str(self.client), '--output', str(output)]), 1)
        self.assertFalse(output.exists())


class EnvironmentPreflightTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.client = self.root / 'client-2026-10-10'
        self.client.mkdir()
        self.profile = self.root / 'target.json'
        self.registry = self.root / 'upstream.json'
        self.target = json.loads(MANIFEST.TARGET_PROFILE.read_text(encoding='utf-8'))
        self.versions = {'classicapi': '1.16.0', 'superwow': '2.2', 'nampower': '4.6.3', 'unitxp_sp3': '90'}
        self.upstream = {key: {'minimum_version': version} for key, version in self.versions.items()}
        self.upstream['nampower']['minimum_version'] = '4.6.2'
        self.upstream['unitxp_sp3'].update(minimum_version='89', reference_version='90')
        self.save_requirements()
        (self.client / 'realmlist.wtf').write_text('set realmlist "play.octowow.st"\n')
        (self.client / 'WoW.exe').write_bytes(versioned_pe('1.12.1.5875'))
        (self.client / 'VanillaFixes.exe').write_bytes(b'launcher fixture')
        for component, filename in self.target['required_extensions'].items():
            (self.client / filename).write_bytes(versioned_pe(self.versions[component]))
        (self.client / 'dlls.txt').write_text('\n'.join(self.target['required_extensions'].values()))

    def save_requirements(self):
        self.profile.write_text(json.dumps(self.target), encoding='utf-8')
        self.registry.write_text(json.dumps(self.upstream), encoding='utf-8')

    def inspect(self):
        return MANIFEST.inspect_environment(self.client, target_path=self.profile, upstream_path=self.registry)

    def test_complete_files_pass_without_promoting_distribution_or_runtime_evidence(self):
        before = {path.name: path.read_bytes() for path in self.client.iterdir()}
        report = self.inspect()
        self.assertEqual(report['status'], 'checks_passed', report['errors'])
        self.assertEqual(report['runtime']['status'], 'pending')
        self.assertIsNone(report['distribution_revision']['observed'])
        self.assertEqual(report['distribution_revision']['status'], 'unverified')
        self.assertEqual(len(report['requirements']), 4)
        self.assertEqual(report['observed']['executable']['version'], '1.12.1.5875')
        self.assertEqual(before, {path.name: path.read_bytes() for path in self.client.iterdir()})

    def test_realm_quotes_case_and_loader_path_spelling_are_supported(self):
        (self.client / 'dlls.txt').write_text('# disabled.dll\n; ignored.dll\n' + '\n'.join(
            '.\\' + filename.upper() for filename in self.target['required_extensions'].values()))
        for realm in ('set realmlist play.octowow.st', 'SET REALMLIST "PLAY.OCTOWOW.ST"',
                      "set realmlist 'play.octowow.st'"):
            with self.subTest(realm=realm):
                (self.client / 'realmlist.wtf').write_text(realm)
                self.assertEqual(self.inspect()['status'], 'checks_passed')

    def test_every_required_dll_must_exist_and_be_configured(self):
        for filename in self.target['required_extensions'].values():
            with self.subTest(filename=filename):
                path = self.client / filename
                original = path.read_bytes()
                path.unlink()
                self.assertIn(f'Missing required extension: {filename}', self.inspect()['errors'])
                path.write_bytes(original)
                entries = [entry for entry in self.target['required_extensions'].values() if entry != filename]
                (self.client / 'dlls.txt').write_text('\n'.join(entries))
                self.assertIn(f'Required extension is not configured in dlls.txt: {filename}', self.inspect()['errors'])
                (self.client / 'dlls.txt').write_text('\n'.join(self.target['required_extensions'].values()))

    def test_wrong_server_engine_missing_launcher_and_loader_block(self):
        for filename, replacement, expected in (
                ('realmlist.wtf', b'set realmlist example.invalid', 'Configured realm'),
                ('WoW.exe', versioned_pe('1.12.1.6000'), 'Executable version'),
                ('VanillaFixes.exe', None, 'Missing launcher'),
                ('dlls.txt', None, 'Missing loader configuration')):
            with self.subTest(filename=filename):
                path = self.client / filename
                original = path.read_bytes()
                path.unlink() if replacement is None else path.write_bytes(replacement)
                report = self.inspect()
                self.assertEqual(report['status'], 'blocked')
                self.assertTrue(any(expected in error for error in report['errors']), report['errors'])
                path.write_bytes(original)

    def test_old_or_unverifiable_native_versions_block(self):
        path = self.client / 'nampower.dll'
        for blob, expected in ((versioned_pe('4.6.1'), 'below required 4.6.2'),
                               (b'unknown binary', 'Cannot establish'),
                               ('FileVersion\0'.encode('utf-16le') + '999.0\0'.encode('utf-16le'), 'Cannot establish')):
            with self.subTest(expected=expected):
                path.write_bytes(blob)
                report = self.inspect()
                self.assertEqual(report['status'], 'blocked')
                self.assertTrue(any(expected in error for error in report['errors']), report['errors'])

    def test_official_release_identity_overrides_older_embedded_nampower_version(self):
        path = self.client / 'nampower.dll'
        path.write_bytes(versioned_pe('4.6.2'))
        self.upstream['nampower']['release_provenance'] = {
            'tag': 'v4.6.3', 'dll_sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
        self.save_requirements()
        report = self.inspect()
        self.assertEqual(report['status'], 'checks_passed', report['errors'])
        native = report['requirements']['nampower']
        self.assertEqual(native['declared_version'], '4.6.2.0')
        self.assertEqual(native['version'], '4.6.3')
        self.assertEqual(native['version_evidence'], 'upstream release SHA-256')
        self.assertEqual(native['artifact_identity'], 'matched_release')

    def test_reference_90_does_not_raise_supported_unitxp_89_artifact_floor(self):
        path = self.client / 'UnitXP_SP3.dll'
        blob = bytearray(versioned_pe('89'))
        struct.pack_into('<2I', blob, 152 + 96 + 16, 0, 0)
        path.write_bytes(blob)
        self.upstream['unitxp_sp3']['release_provenance'] = {'tag': 'v90', 'dll_sha256': 'e' * 64}
        self.upstream['unitxp_sp3']['supported_release_provenance'] = [
            {'tag': 'v89', 'dll_sha256': hashlib.sha256(path.read_bytes()).hexdigest()}]
        self.save_requirements()
        report = self.inspect()
        self.assertEqual(report['status'], 'checks_passed', report['errors'])
        native = report['requirements']['unitxp_sp3']
        self.assertEqual(native['minimum_version'], '89')
        self.assertEqual(native['version'], '89')
        self.assertEqual(native['artifact_identity'], 'matched_release')

    def test_supported_nampower_and_unitxp_floors_are_not_raised_by_newer_references(self):
        self.upstream['nampower']['reference_version'] = '4.6.3'
        self.save_requirements()
        (self.client / 'nampower.dll').write_bytes(versioned_pe('4.6.2'))
        (self.client / 'UnitXP_SP3.dll').write_bytes(versioned_pe('89'))
        report = self.inspect()
        self.assertEqual(report['status'], 'checks_passed', report['errors'])
        self.assertEqual(report['requirements']['nampower']['version'], '4.6.2.0')
        self.assertEqual(report['requirements']['unitxp_sp3']['version'], '89.0.0.0')

    def test_dated_inventory_hash_does_not_authorize_a_release_version(self):
        path = self.client / 'UnitXP_SP3.dll'
        path.write_bytes(b'unknown old local build')
        with patch.dict(MANIFEST.NATIVE_REFERENCES,
                        {'UnitXP_SP3.dll': ('90', hashlib.sha256(path.read_bytes()).hexdigest())}):
            report = self.inspect()
        self.assertEqual(report['status'], 'blocked')
        self.assertIsNone(report['requirements']['unitxp_sp3']['version'])

    def test_invalid_profile_registry_and_missing_inputs_are_blocked_diagnostics(self):
        for value in ({}, [], {'schema_version': 2}, {'schema_version': 1, 'client': []}):
            with self.subTest(profile=value):
                self.profile.write_text(json.dumps(value))
                self.assertEqual(self.inspect()['status'], 'blocked')
        self.save_requirements()
        self.target['client']['engine_version'] = '2.0.0.0'
        self.save_requirements()
        self.assertIn('WoW 1.12.1.5875', self.inspect()['errors'][0])
        self.target['client']['engine_version'] = '1.12.1.5875'
        self.upstream['superwow']['minimum_version'] = 'latest'
        self.save_requirements()
        self.assertIn('superwow.minimum_version', self.inspect()['errors'][0])
        self.registry.unlink()
        self.assertEqual(self.inspect()['status'], 'blocked')

    def test_version_resource_parser_handles_pe32_plus_and_rejects_bad_bounds(self):
        path = self.client / 'test.dll'
        path.write_bytes(versioned_pe('2.2', pe32_plus=True))
        self.assertEqual(MANIFEST.get_pe_version_strings(path)['FileVersion'], '2.2.0.0')
        for blob in (versioned_pe('2.2')[:550], b'MZ' + bytes(200),
                     b'FileVersion\0' + '999.0\0'.encode('utf-16le')):
            path.write_bytes(blob)
            self.assertEqual(MANIFEST.get_pe_version_strings(path), {})

    def test_64_bit_dll_is_blocked_even_with_a_supported_declared_version(self):
        path = self.client / 'ClassicAPI.dll'
        path.write_bytes(versioned_pe('1.15.16', pe32_plus=True))
        report = self.inspect()
        self.assertEqual(report['status'], 'blocked')
        self.assertEqual(report['requirements']['classicapi']['architecture'], 'x64')
        self.assertIn('Required extension must be a valid x86 PE image: ClassicAPI.dll', report['errors'])

    def test_preflight_cli_skips_archives_and_emits_json_to_stdout(self):
        inspect = MANIFEST.inspect_environment
        with patch.object(MANIFEST, 'inspect_environment', side_effect=lambda root: inspect(
                root, target_path=self.profile, upstream_path=self.registry)), \
             patch.object(MANIFEST, 'generate_manifest', side_effect=AssertionError('MPQ scan')):
            with contextlib.redirect_stdout(io.StringIO()) as output, contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(MANIFEST.main(['--client', str(self.client), '--check-environment']), 0)
        report = json.loads(output.getvalue())
        self.assertEqual(report['environment']['status'], 'checks_passed')
        self.assertNotIn('dataArchives', report)

    def test_preflight_cli_writes_blocked_report_and_fails(self):
        output = self.root / 'blocked.json'
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(MANIFEST.main(['--client', str(self.client), '--check-environment',
                                            '--output', str(output)]), 0)
        (self.client / 'ClassicAPI.dll').write_bytes(b'unknown')
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(MANIFEST.main(['--client', str(self.client), '--check-environment',
                                            '--output', str(output)]), 1)
        self.assertEqual(json.loads(output.read_text())['environment']['status'], 'blocked')

    def test_preflight_comparison_preserves_input_and_limits_its_scope(self):
        previous = self.root / 'previous.json'
        previous.write_text(json.dumps({'nativeExtensions': {'old.dll': {'sha256': 'old'}},
                                        'environment': {'status': 'checks_passed'}}))
        before = previous.read_bytes()
        with contextlib.redirect_stderr(io.StringIO()) as progress, contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(MANIFEST.main(['--client', str(self.client), '--check-environment',
                                            '--compare', str(previous)]), 0)
        self.assertEqual(json.loads(output.getvalue())['environment']['status'], 'checks_passed')
        self.assertNotIn('removed extension', progress.getvalue())
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(MANIFEST.main(['--client', str(self.client), '--check-environment',
                                            '--compare', str(previous), '--output', str(previous)]), 1)
        self.assertEqual(previous.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
