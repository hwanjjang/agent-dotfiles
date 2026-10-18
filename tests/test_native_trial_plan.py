"""Frozen input checks use synthetic files, never a native/account runtime."""
import copy
import hashlib
import json
import os
import subprocess
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts/improvement'))
import native_trial_plan as plan


class PlanTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.inputs = self.root / 'inputs'
        self.inputs.mkdir()
        (self.inputs / 'case').mkdir()
        (self.inputs / 'bundle').mkdir()
        (self.inputs / 'case/fixture.txt').write_text('SYNTHETIC_CASE')
        (self.inputs / 'bundle/instructions.md').write_text('SYNTHETIC_ARM')
        self.state = self.root / 'state'
        self.state.mkdir(mode=0o700)
        self.binaries = {}
        for name in ('codex', 'code_mode_host', 'docker', 'executor_archive'):
            path = self.root / name
            path.write_text('SYNTHETIC_' + name)
            path.chmod(0o700)
            self.binaries[name] = path
        self.sources = self.root / 'source'
        self.sources.mkdir()
        self.source_names = ('native_trial.py', 'native_trial_plan.py', 'native_trial_protocol.py',
                             'native_trial_owner.py', 'native_usage.py', 'native_execution.py',
                             'native_execution_catalog.py', 'native_execution_command_skills.js',
                             'native_isolation.py', 'native_trial_qualification.py', 'native_execution_loader.js',
                             'native_trial_results.py', 'trial_reservation.py')
        for name in self.source_names:
            (self.sources / name).write_text('SYNTHETIC_SOURCE_' + name)
        digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
        self.pins = {k: digest(v) for k, v in self.binaries.items() if k != 'docker'}
        self.value = {
            'schema_version': 1,
            'profile': 'codex-0.163-macos-arm64-linux-arm64-v1',
            'mode': 'trial',
            'identity': {'trial_id': 'a' * 64, 'binding_digest': 'b' * 64,
                         'experiment_digest': 'c' * 64, 'case_id': 'synthetic-case',
                         'arm': 'baseline', 'variant': 'reproduction', 'repetition': 0,
                         'attempt_id': 'synthetic-attempt'},
            'inputs': {'root': str(self.inputs), 'entrypoint': 'instructions.md',
                       'files': [{'kind': kind, 'path': name,
                                  'sha256': digest(self.inputs / kind / name)}
                                 for kind, name in [('case', 'fixture.txt'),
                                                    ('bundle', 'instructions.md')]]},
            'prompt': 'Use the selected remote executor for the synthetic case.',
            'runtime': {**{k: str(v) for k, v in self.binaries.items()},
                        'hashes': {k: digest(v) for k, v in self.binaries.items()},
                        'image': 'sha256:' + 'd' * 64,
                        'docker_host': 'unix:///synthetic/docker.sock',
                        'metadata_digest': 'e' * 64},
            'limits': {'setup_seconds': 180, 'wall_seconds': 90, 'cleanup_seconds': 45,
                       'soft_total_tokens': 131072, 'soft_output_tokens': 4096,
                       'retained_bytes': 262144},
            'sources': {name: digest(self.sources / name) for name in self.source_names},
            'state_root': str(self.state),
        }
        self.path = self.root / 'plan.json'

    def load(self, value=None):
        self.path.write_text(json.dumps(self.value if value is None else value))
        with patch.object(plan, 'SOURCE', self.sources, create=True), \
             patch.object(plan, 'PINNED_RUNTIME', self.pins, create=True):
            return plan.load_plan(self.path)

    def refused(self, value, reason):
        with self.assertRaisesRegex(plan.Refusal, '^' + reason + '$'):
            self.load(value)

    def test_plan_keeps_package_import_available_in_a_fresh_isolated_process(self):
        repository = Path(__file__).resolve().parents[1]
        code = ('import sys; sys.path.insert(0, sys.argv[1]); '
                'from scripts.improvement import native_trial_plan as plan; '
                'assert plan.PROFILE == "codex-0.163-macos-arm64-linux-arm64-v1"; '
                'plan.validate_collection({"schema_version":1,"paths":["result.txt"],'
                '"max_file_bytes":65536,"max_total_bytes":262144},"trial")')
        result = subprocess.run([sys.executable, '-I', '-S', '-c', code, str(repository)],
                                capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, '')

    def test_reservation_gate_is_a_required_immutable_source(self):
        value = copy.deepcopy(self.value)
        del value['sources']['trial_reservation.py']
        self.refused(value, 'source_fields')
        (self.sources / 'trial_reservation.py').write_text('CHANGED_GATE')
        self.refused(self.value, 'source_changed')

    def test_valid_selected_plan_is_checked_without_mutating_state(self):
        before = list(self.state.iterdir())
        result = self.load()
        self.assertEqual(result.data['identity']['arm'], 'baseline')
        self.assertEqual(result.files[('case', 'fixture.txt')], b'SYNTHETIC_CASE')
        self.assertEqual(len(result.digest), 64)
        self.assertEqual(list(self.state.iterdir()), before)

    def test_optional_collection_is_frozen_and_check_does_not_capture(self):
        value = copy.deepcopy(self.value)
        value['collection'] = {'schema_version': 1, 'paths': ['result.txt'],
                               'max_file_bytes': 65536, 'max_total_bytes': 262144}
        result = self.load(value)
        self.assertEqual(result.data['collection'], value['collection'])
        self.assertNotEqual(result.digest, self.load().digest)
        self.assertEqual(list(self.state.iterdir()), [])

    def test_collection_invalid_declarations_fail_during_plan_check(self):
        valid = {'schema_version': 1, 'paths': ['result.txt'],
                 'max_file_bytes': 65536, 'max_total_bytes': 262144}
        for declaration, reason in [
            (None, 'collection_fields'), ({}, 'collection_fields'),
            (dict(valid, extra=True), 'collection_fields'),
            (dict(valid, schema_version=True), 'collection_version'),
            (dict(valid, schema_version=2), 'collection_version'),
            (dict(valid, paths=[]), 'collection_declaration'),
            (dict(valid, paths=['../outside']), 'collection_declaration'),
            (dict(valid, paths=['auth.json']), 'collection_declaration'),
            (dict(valid, paths=['transport-canary.txt']), 'collection_declaration'),
            (dict(valid, paths=['same','same']), 'collection_declaration'),
            (dict(valid, paths=[str(i) for i in range(9)]), 'collection_declaration'),
            (dict(valid, paths=[str(i)+'😀'*159 for i in range(8)]), 'collection_declaration'),
            (dict(valid, max_file_bytes=True), 'collection_declaration'),
            (dict(valid, max_file_bytes=65537), 'collection_declaration'),
            (dict(valid, max_total_bytes=262145), 'collection_declaration'),
        ]:
            with self.subTest(reason=reason, declaration=declaration):
                value = copy.deepcopy(self.value); value['collection'] = declaration
                self.refused(value, reason)
                self.assertEqual(list(self.state.iterdir()), [])
        value = copy.deepcopy(self.value)
        value.update(collection=valid, mode='qualification')
        self.refused(value, 'collection_mode')

    def test_collector_source_drift_invalidates_plan(self):
        (self.sources/'native_trial_results.py').write_text('SOURCE_DRIFT')
        self.refused(self.value, 'source_changed')

    def test_source_and_selected_input_drift_refuse(self):
        (self.inputs / 'case/fixture.txt').write_text('CHANGED')
        self.refused(self.value, 'input_changed')
        (self.inputs / 'case/fixture.txt').write_text('SYNTHETIC_CASE')
        (self.sources / 'native_trial.py').write_text('CHANGED')
        self.refused(self.value, 'source_changed')

    def test_unsafe_and_conflicting_relative_paths_refuse(self):
        for path in ('../private', '/private', 'a//b', 'a/./b', 'arm/fixture.txt',
                     'transport-canary.txt', 'auth.json', '.credentials.json'):
            value = copy.deepcopy(self.value)
            value['inputs']['files'][0]['path'] = path
            self.refused(value, 'input_path')

    def test_symlink_hardlink_and_writable_input_refuse(self):
        original = self.inputs / 'case/fixture.txt'
        outside = self.root / 'outside'
        original.rename(outside)
        original.symlink_to(outside)
        self.refused(self.value, 'input_unsafe')
        original.unlink()
        os.link(outside, original)
        self.refused(self.value, 'input_unsafe')
        original.unlink()
        outside.rename(original)
        original.chmod(0o666)
        self.refused(self.value, 'input_unsafe')

    def test_symlinked_input_ancestor_refuses(self):
        actual = self.root / 'actual-case'
        (self.inputs / 'case').rename(actual)
        (self.inputs / 'case').symlink_to(actual, target_is_directory=True)
        self.refused(self.value, 'input_unsafe')

    def test_duplicate_file_missing_entrypoint_and_unknown_fields_refuse(self):
        value = copy.deepcopy(self.value)
        value['inputs']['files'].append(value['inputs']['files'][0])
        self.refused(value, 'input_duplicate')
        value = copy.deepcopy(self.value)
        value['inputs']['entrypoint'] = 'absent.md'
        self.refused(value, 'entrypoint_missing')
        value = copy.deepcopy(self.value)
        value['auth_source'] = 'MUST_NEVER_BE_DISCOVERED'
        self.refused(value, 'plan_fields')

    def test_runtime_pin_endpoint_budget_and_identity_refuse(self):
        for target, key, replacement, reason in [
            ('runtime', 'docker_host', 'tcp://localhost:2375', 'runtime_endpoint'),
            ('runtime', 'metadata_digest', 'invalid', 'runtime_metadata'),
            ('limits', 'wall_seconds', 91, 'limits'),
            ('limits', 'wall_seconds', True, 'limits'),
            ('identity', 'arm', 'other-arm', 'identity'),
            ('identity', 'attempt_id', '../attempt', 'identity'),
        ]:
            value = copy.deepcopy(self.value)
            value[target][key] = replacement
            self.refused(value, reason)
        value = copy.deepcopy(self.value)
        value['runtime']['hashes']['codex'] = 'f' * 64
        self.refused(value, 'runtime_pin')

    def test_preexisting_attempt_and_unowned_public_state_refuse(self):
        attempt = self.state / ('a' * 64) / 'synthetic-attempt'
        attempt.parent.mkdir(mode=0o700)
        attempt.mkdir(mode=0o700)
        self.refused(self.value, 'attempt_exists')
        attempt.rmdir()
        self.state.chmod(0o755)
        self.refused(self.value, 'state_unsafe')

    def test_duplicate_json_key_is_not_silently_accepted(self):
        self.path.write_text('{"schema_version":1,"schema_version":1}')
        with self.assertRaisesRegex(plan.Refusal, '^plan_json$'):
            plan.load_plan(self.path)

    def test_existing_case_identity_grammar_and_snapshot_isolation(self):
        value = copy.deepcopy(self.value)
        value['identity']['case_id'] = 'CASE.email@example:variant'
        result = self.load(value)
        result.data['identity']['arm'] = 'MUTATED'
        result.files[('case', 'fixture.txt')] = b'MUTATED'
        self.assertEqual(result.data['identity']['arm'], 'baseline')
        self.assertEqual(result.files[('case', 'fixture.txt')], b'SYNTHETIC_CASE')

    def test_qualification_mode_requires_the_fixed_selected_fixture_before_launch(self):
        value = copy.deepcopy(self.value)
        value['mode'] = 'qualification'
        self.refused(value, 'qualification_fixture')


if __name__ == '__main__':
    unittest.main()
