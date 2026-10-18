"""Bounded artifact collection through actual local filesystem descriptors."""
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from unittest.mock import patch
from pathlib import Path
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1] / 'scripts/improvement/native_trial_results.py'


def collector():
    if not SOURCE.is_file():
        raise AssertionError('Declared artifact collection is not implemented')
    spec = importlib.util.spec_from_file_location('native_trial_results', SOURCE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ResultsTests(unittest.TestCase):
    def test_actual_present_and_missing_files_have_only_typed_observations(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            value = b'SYNTHETIC_RESULT_NOT_A_SUCCESS_FLAG'
            (root / 'result.txt').write_bytes(value)
            result = collector().collect(root, ['result.txt', 'absent.txt'])
            self.assertEqual(result, {
                'schema_version': 1, 'kind': 'bounded_artifact_snapshot',
                'status': 'captured', 'files': [
                    {'path': 'result.txt', 'status': 'present', 'bytes': len(value),
                     'sha256': hashlib.sha256(value).hexdigest()},
                    {'path': 'absent.txt', 'status': 'missing', 'bytes': None,
                     'sha256': None}],
                'reason': None, 'quiescent_state_verified': False})
            self.assertNotIn(value.decode(), str(result))


    def assertBlocked(self, result, reason=None):
        self.assertEqual(result['status'], 'blocked')
        self.assertEqual(result['files'], [])
        self.assertFalse(result['quiescent_state_verified'])
        self.assertIsInstance(result['reason'], str)
        if reason is not None:
            self.assertEqual(result['reason'], reason)

    def test_nested_missing_empty_and_exact_byte_bounds(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            (root/'nested').mkdir()
            (root/'nested/empty').touch()
            (root/'full').write_bytes(b'abcd')
            result = collector().collect(root, ['nested/empty', 'full', 'absent/child'],
                                         max_file_bytes=4, max_total_bytes=4)
            self.assertEqual(result['status'], 'captured')
            self.assertEqual([row['bytes'] for row in result['files']], [0, 4, None])
            self.assertEqual(result['files'][0]['sha256'], hashlib.sha256(b'').hexdigest())

    def test_invalid_paths_and_declarations_are_rejected_before_reads(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            for paths in [None, (), [], ['.'], ['..'], ['/absolute'], ['x/../y'],
                          ['x//y'], ['./x'], ['x/'], ['x\\y'], ['a\x00b'],
                          ['auth.json'], ['x/.env'], ['.env.private'],
                          ['transport-canary.txt'], ['a', 'a'], [False],
                          ['x'*161], ['/'.join(['x']*17)], ['x'+str(i) for i in range(65)]]:
                with self.subTest(paths=paths):
                    self.assertBlocked(collector().collect(root, paths), 'invalid_declaration')
            for field in ['max_file_bytes', 'max_total_bytes']:
                for value in [False, 0, -1, 1.5, 262145]:
                    with self.subTest(field=field, value=value):
                        self.assertBlocked(collector().collect(root, ['x'], **{field:value}),
                                           'invalid_declaration')
            for invalid in ['string-root', Path('relative'), root/'..', Path('/bad\x00root'), Path('//ambiguous/root')]:
                self.assertBlocked(collector().collect(invalid, ['x']), 'invalid_declaration')

    def test_per_file_and_aggregate_overflow_discard_partial_rows(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            (root/'a').write_bytes(b'ab')
            (root/'b').write_bytes(b'cde')
            self.assertBlocked(collector().collect(root, ['a','b'], max_file_bytes=2), 'size_limit')
            self.assertBlocked(collector().collect(root, ['a','b'], max_total_bytes=4), 'size_limit')

    def test_default_maximum_and_utf8_byte_counts_are_exact(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary).resolve()
            for index in range(4):
                (root/str(index)).write_bytes(b'x'*65536)
            result=collector().collect(root, ['0','1','2','3'])
            self.assertEqual(result['status'], 'captured')
            self.assertEqual(sum(row['bytes'] for row in result['files']), 262144)
            (root/'text').write_text('가', encoding='utf-8')
            result=collector().collect(root, ['text'])
            self.assertEqual(result['files'][0]['bytes'], 3)
            self.assertBlocked(collector().collect(root, ['text'], max_file_bytes=2), 'size_limit')

    def test_leaf_and_ancestor_symlinks_cannot_expose_other_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            outer = Path(temporary).resolve()
            root = outer/'root'; root.mkdir()
            (outer/'outside').write_bytes(b'UNREAD_PROTECTED_SYNTHETIC_BYTES')
            (root/'link').symlink_to(outer/'outside')
            (root/'directory-link').symlink_to(outer, target_is_directory=True)
            for path in ['link', 'directory-link/outside']:
                self.assertBlocked(collector().collect(root, [path]), 'unsafe_path')
            (outer/'root-link').symlink_to(root, target_is_directory=True)
            self.assertBlocked(collector().collect(outer/'root-link', ['link']), 'unsafe_root')

    def test_hardlinks_directories_and_fifo_are_rejected_without_reading(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            (root/'original').write_bytes(b'SYNTHETIC')
            os.link(root/'original', root/'hardlink')
            (root/'directory').mkdir()
            os.mkfifo(root/'pipe')
            for name in ['original', 'hardlink', 'directory', 'pipe']:
                with self.subTest(name=name):
                    self.assertBlocked(collector().collect(root, [name]), 'unsafe_file')

    def test_non_directory_ancestor_is_not_observed_missing(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve(); (root/'file').touch()
            self.assertBlocked(collector().collect(root, ['file/child']), 'unsafe_path')
            self.assertBlocked(collector().collect(root/'absent', ['x']), 'unsafe_root')

    def test_file_mutation_and_replacement_during_real_read_are_blocked(self):
        for replace in [False, True]:
            with self.subTest(replace=replace), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve(); target=root/'result'
                target.write_bytes(b'initial')
                module = collector(); actual_read = os.read; mutated = []
                def change_after_read(descriptor, size):
                    data = actual_read(descriptor, size)
                    if data and not mutated:
                        mutated.append(True)
                        if replace:
                            (root/'replacement').write_bytes(b'changed')
                            os.replace(root/'replacement', target)
                        else:
                            target.write_bytes(b'changed-more')
                    return data
                with patch.object(module.os, 'read', side_effect=change_after_read):
                    self.assertBlocked(module.collect(root, ['result']), 'changed')

    def test_root_replacement_during_real_read_is_blocked(self):
        with tempfile.TemporaryDirectory() as temporary:
            outer=Path(temporary).resolve(); root=outer/'root'; root.mkdir()
            (root/'result').write_bytes(b'initial')
            module=collector(); actual_read=os.read; changed=[]
            def swap_root(descriptor, size):
                data=actual_read(descriptor, size)
                if data and not changed:
                    changed.append(True)
                    root.rename(outer/'previous-root'); root.mkdir()
                return data
            with patch.object(module.os, 'read', side_effect=swap_root):
                self.assertBlocked(module.collect(root, ['result']), 'changed')

    def test_unexpected_read_error_is_fixed_and_does_not_leak_diagnostic(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary).resolve(); (root/'result').touch()
            module=collector()
            with patch.object(module.os, 'read', side_effect=PermissionError('DO_NOT_RETAIN_DIAGNOSTIC')):
                result=module.collect(root, ['result'])
            self.assertBlocked(result, 'read_error')
            self.assertNotIn('DO_NOT_RETAIN', json.dumps(result))

    def test_descriptors_are_closed_after_present_missing_and_failed_capture(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary).resolve(); (root/'result').write_bytes(b'aa')
            module=collector(); actual_open=os.open; opened=[]
            def record_open(*args, **kwargs):
                descriptor=actual_open(*args, **kwargs); opened.append(descriptor)
                return descriptor
            # Membership is checked against the real os.open before this wrapper
            # is installed; update only this deterministic support declaration.
            with patch.object(module.os, 'open', side_effect=record_open) as wrapped:
                with patch.object(module.os, 'supports_dir_fd', os.supports_dir_fd | {wrapped}):
                    for paths, limits, expected in [(['result','missing'], {}, 'captured'),
                                                    (['result'], {'max_file_bytes':1}, 'blocked')]:
                        result=module.collect(root, paths, **limits)
                        self.assertEqual(result['status'], expected)
            self.assertTrue(opened)
            for descriptor in set(opened):
                with self.assertRaises(OSError): os.fstat(descriptor)

    def test_isolated_cli_validates_json_and_keeps_only_declared_metadata(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary).resolve(); value=b'PRIVATE_SYNTHETIC_OUTPUT'
            (root/'answer').write_bytes(value)
            valid=subprocess.run([sys.executable, '-I', '-S', str(SOURCE), '--root', str(root)],
                input=json.dumps({'paths':['answer','missing']}), text=True,
                capture_output=True, timeout=5)
            self.assertEqual(valid.returncode, 0, valid.stderr)
            result=json.loads(valid.stdout)
            self.assertEqual(result['files'][0]['sha256'], hashlib.sha256(value).hexdigest())
            self.assertNotIn(value.decode(), valid.stdout+valid.stderr)
            for invalid in ['{"paths":["answer"],"paths":["missing"]}',
                            '{"paths":["answer"],"success":true}',
                            '{"paths":["answer"],"max_file_bytes":NaN}', 'x'*16385]:
                failed=subprocess.run([sys.executable, '-I', '-S', str(SOURCE), '--root', str(root)],
                    input=invalid, text=True, capture_output=True, timeout=5)
                self.assertEqual(failed.returncode, 1)
                self.assertBlocked(json.loads(failed.stdout), 'invalid_input')
                self.assertEqual(failed.stderr, '')


if __name__ == '__main__':
    unittest.main()
