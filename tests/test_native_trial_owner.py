"""Synthetic native-home custody and bounded metadata tests only."""
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts' / 'improvement'))
import native_trial_owner as m


def model():
    return {'slug': 'test-model', 'shell_type': 'shell_command',
            'tool_mode': 'code_mode_only', 'apply_patch_tool_type': 'freeform',
            'supports_search_tool': True, 'use_responses_lite': True,
            'multi_agent_version': 'v2', 'input_modalities': ['text', 'image'],
            'experimental_supported_tools': ['send_user_message_async', 'clock']}


class OwnerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=os.environ.get('NATIVE_TRIAL_TEST_TMP'))
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.source = self.root / 'synthetic-cache'
        self.source.write_bytes(b'synthetic-secret-not-real')
        self.source.chmod(0o600)
        self.home = self.root / 'fresh-home'

    def owner(self): return m.copy_native_home(self.source, self.home)
    def clean(self, owner, **kwargs):
        return owner.cleanup(processes_stopped=True, codex_executable=str(self.root / 'pinned-codex'),
                             deadline=time.monotonic()+5, **kwargs)
    def cache(self, owner, row=None, raw=None):
        p = owner.root / 'models_cache.json'
        p.write_text(raw if raw is not None else json.dumps({'models': [model() if row is None else row]}))
        p.chmod(0o600)
        return p

    def test_copy_private_file_source_unchanged_and_cleanup(self):
        owner = self.owner()
        self.assertEqual(owner.identity, (self.home.stat().st_dev, self.home.stat().st_ino, os.getuid()))
        self.assertEqual((self.home/'auth.json').read_bytes(), self.source.read_bytes())
        self.assertEqual(stat.S_IMODE(self.home.stat().st_mode), 0o700)
        self.assertEqual(stat.S_IMODE((self.home/'auth.json').stat().st_mode), 0o600)
        result = self.clean(owner)
        self.assertTrue(result['home_absent']); self.assertTrue(result['auth_absent'])
        self.assertTrue(self.source.exists())

    def test_refuses_non0600_hardlink_empty_oversize_and_fifo(self):
        for mode in (0o400, 0o640, 0o1600):
            self.source.chmod(mode)
            with self.subTest(mode=mode), self.assertRaises(m.Refusal): self.owner()
            self.assertFalse(self.home.exists())
        self.source.chmod(0o600)
        alias = self.root/'hardlink'; os.link(self.source, alias)
        with self.assertRaises(m.Refusal): self.owner()
        alias.unlink()
        for data in (b'', b'x'*(1024*1024+1)):
            self.source.write_bytes(data)
            with self.assertRaises(m.Refusal): self.owner()
        self.source.unlink(); os.mkfifo(self.source, 0o600)
        with self.assertRaises(m.Refusal): self.owner()

    def test_refuses_symlink_ancestors_and_existing_destination(self):
        link = self.root/'link'; link.symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(m.Refusal): m.copy_native_home(link/self.source.name, self.home)
        with self.assertRaises(m.Refusal): m.copy_native_home(self.source, link/'other')
        self.home.mkdir(); (self.home/'keep').write_text('keep')
        with self.assertRaises(m.Refusal): self.owner()
        self.assertEqual((self.home/'keep').read_text(), 'keep')

    def test_process_uncertainty_preserves_cache(self):
        owner = self.owner()
        for stopped in (False, None, 1):
            r = owner.cleanup(processes_stopped=stopped, codex_executable='/synthetic/codex', deadline=time.monotonic()+5)
            self.assertFalse(r['home_absent']); self.assertTrue((self.home/'auth.json').exists())

    def test_native_replaced_auth_and_unknown_residue(self):
        owner = self.owner(); (self.home/'auth.json').unlink()
        (self.home/'auth.json').write_bytes(b'refreshed-synthetic'); (self.home/'auth.json').chmod(0o600)
        (self.home/'unknown-link').symlink_to(self.source)
        r = self.clean(owner)
        self.assertTrue(r['auth_absent']); self.assertFalse(r['home_absent'])
        self.assertTrue(self.source.exists())

    def test_alias_pair_unlinks_entries_only_and_recovery_uses_same_helper(self):
        owner = self.owner()
        target = self.root/'pinned-codex'; target.write_bytes(b'not-executed')
        aliasdir = self.home/'tmp'/'arg0-macos'/'codex-arg0ABC123'; aliasdir.mkdir(parents=True)
        for name in ('applypatch', 'apply_patch'): (aliasdir/name).symlink_to(target)
        recovered = m.NativeHome(owner.root, owner.identity)
        r = self.clean(recovered)
        self.assertTrue(r['home_absent']); self.assertEqual(r['aliases_removed'], 2)
        self.assertEqual(target.read_bytes(), b'not-executed')

    def test_wrong_alias_target_home_identity_and_deadline_refuse(self):
        owner = self.owner()
        aliasdir = self.home/'tmp'/'arg0-macos'/'codex-arg0ABC123'; aliasdir.mkdir(parents=True)
        (aliasdir/'apply_patch').symlink_to(self.source)
        self.assertFalse(self.clean(owner)['home_absent'])
        bad = m.NativeHome(owner.root, (owner.identity[0], owner.identity[1]+1, owner.identity[2]))
        self.assertFalse(self.clean(bad)['home_absent'])
        r = owner.cleanup(processes_stopped=True, codex_executable=str(self.root/'pinned-codex'), deadline=0)
        self.assertFalse(r['home_absent'])

    def test_external_copy_interruption_cleans_owned_partial_file(self):
        real_write = m.os.write
        for index, error in enumerate((ValueError('synthetic timeout'), KeyboardInterrupt('synthetic interrupt'))):
            with self.subTest(interruption=type(error).__name__):
                destination = self.root/('interrupted-home-'+str(index))
                def interrupted_write(fd, data):
                    real_write(fd, data[:3])
                    raise error
                caught = None
                try:
                    with patch.object(m.os, 'write', side_effect=interrupted_write):
                        m.copy_native_home(self.source, destination)
                except BaseException as exc:
                    caught = exc
                self.assertIsInstance(caught, m.Refusal)
                self.assertEqual(str(caught), 'copy_interrupted')
                self.assertIsNone(caught.owner)
                self.assertFalse(destination.exists())
                self.assertEqual(self.source.read_bytes(), b'synthetic-secret-not-real')

    def test_external_copy_interruption_retains_identity_if_root_replaced(self):
        moved = self.root/'interrupted-owned-home'
        real_write = m.os.write
        def interrupted_write(fd, data):
            real_write(fd, data[:3])
            self.home.rename(moved); self.home.mkdir(mode=0o700)
            (self.home/'sentinel').write_text('unowned replacement')
            raise KeyboardInterrupt('must not escape in fixed refusal')
        caught = None
        try:
            with patch.object(m.os, 'write', side_effect=interrupted_write): self.owner()
        except BaseException as exc:
            caught = exc
        self.assertIsInstance(caught, m.Refusal)
        self.assertEqual(str(caught), 'copy_failed_cleanup_unconfirmed')
        self.assertEqual(caught.owner.identity, (moved.stat().st_dev,moved.stat().st_ino,os.getuid()))
        self.assertEqual((self.home/'sentinel').read_text(), 'unowned replacement')
        self.assertEqual((moved/'auth.json').read_bytes(), b'syn')

    def test_cleanup_interruption_retains_partial_owner_for_runner_finally(self):
        caught = None
        try:
            with patch.object(m.os, 'write', side_effect=ValueError('synthetic timeout')), \
                 patch.object(m.NativeHome, 'cleanup', side_effect=KeyboardInterrupt('cleanup interrupt')):
                self.owner()
        except BaseException as exc:
            caught = exc
        self.assertIsInstance(caught, m.Refusal)
        self.assertEqual(str(caught), 'copy_failed_cleanup_unconfirmed')
        self.assertIsNotNone(caught.owner)
        self.assertTrue((self.home/'auth.json').exists())
        self.assertTrue(self.clean(caught.owner)['home_absent'])

    def test_copy_partial_write_failure_cleans_only_owned_home(self):
        with patch.object(m.os, 'write', side_effect=OSError('private error')):
            with self.assertRaises(m.Refusal) as caught: self.owner()
        self.assertFalse(self.home.exists()); self.assertNotIn('private', str(caught.exception))

    def test_unknown_deadline_refuses_without_purging_auth(self):
        owner = self.owner()
        for invalid in (float('inf'), float('nan'), True, None):
            r = owner.cleanup(processes_stopped=True, codex_executable='/synthetic/codex', deadline=invalid)
            self.assertEqual(r['status'], 'incomplete')
            self.assertTrue((self.home/'auth.json').exists())

    def test_partial_failure_retains_recovery_identity_on_replaced_home(self):
        moved = self.root/'moved-owned-home'
        def fail_write(fd, data):
            self.home.rename(moved); self.home.mkdir(mode=0o700)
            (self.home/'sentinel').write_text('replacement')
            raise OSError('private error')
        with patch.object(m.os, 'write', side_effect=fail_write):
            with self.assertRaises(m.Refusal) as caught: self.owner()
        self.assertEqual(str(caught.exception), 'copy_failed_cleanup_unconfirmed')
        self.assertIsNotNone(caught.exception.owner)
        self.assertEqual((self.home/'sentinel').read_text(), 'replacement')
        self.assertTrue((moved/'auth.json').exists())

    def test_short_writes_and_changed_source_stamp(self):
        real_write = m.os.write
        with patch.object(m.os, 'write', side_effect=lambda fd, data: real_write(fd, data[:2])):
            owner = self.owner()
        self.assertEqual((self.home/'auth.json').read_bytes(), self.source.read_bytes())
        self.assertTrue(self.clean(owner)['home_absent'])
        real_read = m.os.read; changed = False
        def changing_read(fd, count):
            nonlocal changed
            data = real_read(fd, count)
            if data and not changed:
                changed = True; self.source.write_bytes(b'changed synthetic data')
            return data
        with patch.object(m.os, 'read', side_effect=changing_read):
            with self.assertRaises(m.Refusal) as caught: self.owner()
        self.assertEqual(str(caught.exception), 'source_changed_during_copy')
        self.assertFalse(self.home.exists())

    def test_auth_hardlink_is_retained_and_alias_parent_shape_strict(self):
        owner = self.owner(); os.link(self.home/'auth.json', self.root/'auth-hardlink')
        self.assertEqual(self.clean(owner)['reason'], 'cleanup_auth_unsafe')
        (self.root/'auth-hardlink').unlink()
        for parent in ('codex-arg0ABC123', 'codex-arg0DEF456'):
            d = self.home/'tmp'/'arg0-macos'/parent; d.mkdir(parents=True)
            (d/'apply_patch').symlink_to(self.root/'pinned-codex')
        r = self.clean(owner)
        self.assertEqual(r['aliases_removed'], 1); self.assertFalse(r['home_absent'])
        self.assertTrue(r['auth_absent'])

    def test_metadata_post_read_change_hardlink_and_owner_replacement(self):
        owner = self.owner(); cache = self.cache(owner)
        real_read = m.os.read; changed = False
        def changing_read(fd, count):
            nonlocal changed
            data = real_read(fd, count)
            if data and not changed:
                changed = True; cache.write_text(json.dumps({'models': []}))
            return data
        with patch.object(m.os, 'read', side_effect=changing_read):
            self.assertEqual(m.project_model_metadata(owner, 'test-model')['status'], 'read_refused')
        self.cache(owner); os.link(cache, self.root/'cache-link')
        self.assertEqual(m.project_model_metadata(owner, 'test-model')['status'], 'read_refused')
        (self.root/'cache-link').unlink()
        self.home.rename(self.root/'oldhome'); self.home.mkdir(mode=0o700)
        self.assertEqual(m.project_model_metadata(owner, 'test-model')['status'], 'read_refused')

    def test_metadata_root_path_replaced_during_read_refuses(self):
        owner = self.owner(); self.cache(owner)
        real_read = m.os.read; changed = False
        def changing_read(fd, count):
            nonlocal changed
            data = real_read(fd, count)
            if data and not changed:
                changed = True; self.home.rename(self.root/'original-home')
                self.home.mkdir(mode=0o700)
            return data
        with patch.object(m.os, 'read', side_effect=changing_read):
            self.assertEqual(m.project_model_metadata(owner, 'test-model')['status'], 'read_refused')

    def test_copy_destination_entry_replaced_during_write_refuses(self):
        real_write = m.os.write; changed = False
        def replacing_write(fd, data):
            nonlocal changed
            count = real_write(fd, data)
            if not changed:
                changed = True; (self.home/'auth.json').unlink()
                (self.home/'auth.json').write_bytes(b'replacement-synthetic')
                (self.home/'auth.json').chmod(0o600)
            return count
        with patch.object(m.os, 'write', side_effect=replacing_write):
            with self.assertRaises(m.Refusal): self.owner()
        self.assertFalse(self.home.exists())

    def test_cleanup_bounds_symlinked_ancestor_and_link_recheck(self):
        owner = self.owner()
        aliasdir = self.home/'tmp'/'arg0-macos'/'codex-arg0ABC123'; aliasdir.mkdir(parents=True)
        alias = aliasdir/'apply_patch'; alias.symlink_to(self.root/'pinned-codex')
        real_readlink = m.os.readlink; reads = 0
        def changing_link(name, **kwargs):
            nonlocal reads
            reads += 1
            if reads == 2: return str(self.source)
            return real_readlink(name, **kwargs)
        with patch.object(m.os, 'readlink', side_effect=changing_link):
            r = self.clean(owner)
        self.assertEqual(r['reason'], 'cleanup_alias_changed'); self.assertTrue(alias.is_symlink())
        moved = self.root/'old-home'; self.home.rename(moved)
        self.home.symlink_to(moved, target_is_directory=True)
        self.assertFalse(self.clean(owner)['home_absent'])

    def test_umask_077_and_depth_entry_limits(self):
        old = os.umask(0o077)
        try: owner = self.owner()
        finally: os.umask(old)
        nested = self.home
        for i in range(17): nested = nested/'d'; nested.mkdir()
        self.assertEqual(self.clean(owner)['reason'], 'cleanup_entry_limit')
        self.assertTrue(self.home.exists())

    def test_metadata_bounds_invalid_json_states_and_capabilities(self):
        owner = self.owner()
        for raw in ('{"models":NaN}', '{"models":'+json.dumps([model()]*1001)+'}', 'x'*(4*1024*1024+1)):
            self.cache(owner, raw=raw)
            self.assertNotEqual(m.project_model_metadata(owner, 'test-model')['status'], 'recognized')
        self.cache(owner, raw=json.dumps({'models': [model(), model()]}))
        self.assertEqual(m.project_model_metadata(owner, 'test-model')['match_count'], 2)
        for field, value, expected in (
                ('shell_type', 'disabled', 'disabled'), ('tool_mode', 'direct', 'unsupported_tool_mode'),
                ('tool_mode', None, 'unsupported_tool_mode'),
                ('experimental_supported_tools', ['clock']*33, 'capability_unknown'),
                ('input_modalities', ['audio'], 'recognized'),
                ('apply_patch_tool_type', None, 'recognized')):
            row = model(); row[field] = value; self.cache(owner, row)
            self.assertEqual(m.project_model_metadata(owner, 'test-model')['status'], expected)
        row = model(); row['experimental_supported_tools'] = ['private-tool', 'private-tool']
        self.cache(owner, row); r = m.project_model_metadata(owner, 'test-model')
        self.assertEqual(r['compatibility']['selectors']['experimental_supported_tools'],
                         {'known_mask': 0, 'unknown_count': 2, 'duplicate_count': 1, 'total_count': 2})
        self.assertNotIn('private-tool', json.dumps(r))

    def test_metadata_eight_selectors_sanitizes_arbitrary_contents(self):
        owner = self.owner(); row = model()
        row.update(base_instructions='SECRET person@example.invalid', description='private')
        self.cache(owner, row)
        r = m.project_model_metadata(owner, 'test-model')
        self.assertEqual(r['status'], 'recognized'); self.assertFalse(r['runtime_registry_qualified'])
        c = r['compatibility']; self.assertEqual(c['model'], 'test-model')
        self.assertEqual(len(c['selectors']), 8)
        self.assertEqual(c['selectors']['shell_type'], 'unified_exec')
        self.assertEqual(c['selectors']['input_modalities'], 3)
        self.assertTrue(all(v == 'explicit' for v in c['field_states'].values()))
        self.assertNotIn('SECRET', json.dumps(r)); self.assertNotIn('example.invalid', json.dumps(r))

    def test_metadata_defaults_nulls_required_unknown_and_strict_types(self):
        owner = self.owner(); row = model()
        for key in ('apply_patch_tool_type', 'supports_search_tool', 'use_responses_lite', 'multi_agent_version', 'input_modalities'): row.pop(key)
        self.cache(owner, row); c = m.project_model_metadata(owner, 'test-model')['compatibility']
        self.assertEqual(c['selectors']['input_modalities'], 3)
        self.assertFalse(c['selectors']['supports_search_tool'])
        self.assertEqual(c['field_states']['multi_agent_version'], 'defaulted')
        for key, value in [('shell_type', 'unknown-secret'), ('supports_search_tool', 1), ('tool_mode', 'unknown'), ('input_modalities', ['text','text']), ('experimental_supported_tools', ['unknown-secret']), ('experimental_supported_tools', None)]:
            row = model(); row[key] = value; self.cache(owner, row)
            r = m.project_model_metadata(owner, 'test-model')
            self.assertNotEqual(r['status'], 'recognized'); self.assertNotIn('unknown-secret', json.dumps(r))
        row = model(); row.pop('experimental_supported_tools'); self.cache(owner, row)
        r = m.project_model_metadata(owner, 'test-model')
        self.assertEqual(r['compatibility']['field_states']['experimental_supported_tools'], 'missing_required')

    def test_metadata_duplicate_keys_symlink_and_no_matching_model(self):
        owner = self.owner(); p = self.cache(owner, raw='{"models":[],"models":[]}')
        self.assertNotEqual(m.project_model_metadata(owner, 'test-model')['status'], 'recognized')
        self.cache(owner, raw='{"models":[]}')
        self.assertEqual(m.project_model_metadata(owner, 'test-model')['match_count'], 0)
        p.unlink(); p.symlink_to(self.source)
        self.assertEqual(m.project_model_metadata(owner, 'test-model')['status'], 'read_refused')


if __name__ == '__main__': unittest.main()
