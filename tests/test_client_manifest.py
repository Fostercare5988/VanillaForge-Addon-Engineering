"""The addon inventory reads Git checkouts only, never the client installation."""
import contextlib
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

    def test_inventory_touches_only_addon_folders(self):
        # CORE: never open the client installation, its DLLs or its archives.
        for name in ('ClassicAPI.dll', 'WoW.exe', 'dlls.txt', 'realmlist.wtf'):
            (self.client / name).write_bytes(b'client fixture')
        (self.client / 'Data').mkdir()
        (self.client / 'Data' / 'patch.MPQ').write_bytes(b'archive fixture')
        addon = self.client / 'Interface/AddOns/Example'
        (addon / '.git').mkdir(parents=True)
        (addon / 'Example.toc').write_text('## Interface: 11200\n')
        opened = []
        original_open, original_bytes = Path.open, Path.read_bytes

        def watch_open(path, *args, **kwargs):
            opened.append(path)
            return original_open(path, *args, **kwargs)

        def watch_bytes(path):
            opened.append(path)
            return original_bytes(path)

        output = self.root / 'inventory.json'
        with patch.object(Path, 'open', watch_open), patch.object(Path, 'read_bytes', watch_bytes), \
             patch.object(MANIFEST, 'get_git_info', return_value={'head': 'a' * 40, 'clean': True}), \
             contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(MANIFEST.main(['--client', str(self.client), '--output', str(output)]), 0)
        addons = (self.client / 'Interface' / 'AddOns').resolve()
        client_reads = [path for path in opened
                        if Path(path).resolve().is_relative_to(self.client.resolve())
                        and not Path(path).resolve().is_relative_to(addons)]
        self.assertEqual(client_reads, [])
        report = json.loads(output.read_text())
        self.assertEqual(set(report), {'generatedAt', 'authoritativeClientRoot', 'scope',
                                       'deployedAddons', 'unmanagedAddons'})
        for removed in ('generate_manifest', 'MPQArchive', 'get_pe_version_strings', 'sha256_file'):
            self.assertFalse(hasattr(MANIFEST, removed), removed)

    def test_full_manifest_options_are_gone(self):
        for option in ('--check-environment', '--historical'):
            with self.subTest(option=option), contextlib.redirect_stderr(io.StringIO()), \
                 self.assertRaises(SystemExit) as exit:
                MANIFEST.main(['--client', str(self.client), option, str(self.root)])
            self.assertEqual(exit.exception.code, 2)

    def test_old_client_fields_in_a_baseline_produce_no_deltas(self):
        output = self.root / 'inventory.json'
        previous = self.root / 'previous.json'
        previous.write_text(json.dumps({'clientExecutableInfo': {'sha256': 'old'},
                                       'nativeExtensions': {'old.dll': {'sha256': 'old'}}}))
        with contextlib.redirect_stdout(io.StringIO()) as printed, contextlib.redirect_stderr(io.StringIO()):
            result = MANIFEST.main(['--client', str(self.client), '--addons-only',
                                    '--output', str(output), '--compare', str(previous)])
        self.assertEqual(result, 0)
        self.assertEqual(json.loads(output.read_text())['scope'], 'addon Git/TOC inventory')
        self.assertNotIn('removed extension', printed.getvalue())
        self.assertNotIn('EXE:', printed.getvalue())

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


if __name__ == '__main__':
    unittest.main()
