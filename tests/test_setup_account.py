"""Exercise account delivery in disposable homes, never by changing HOME."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import setup_account as setup
import account_storage as storage


class AccountSetupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='account install ')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.home = self.root / 'first account'
        self.home.mkdir()
        self.repo = self.root / 'source'
        self.repo.mkdir()
        # A minimal committed source includes real account runtime/templates and two dependent skills.
        for name in ['account', 'policies', 'mcp']:
            shutil.copytree(ROOT / name, self.repo / name)
        for name in ['planning-with-files', 'tdd']:
            shutil.copytree(ROOT / 'skills' / name, self.repo / 'skills' / name,
                            ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        (self.repo / 'README.md').write_text('Synthetic source\n')
        self.git('init', '-q');self.commit('initial')
        env = {k: v for k, v in os.environ.items() if k not in ('CODEX_HOME', 'CLAUDE_CONFIG_DIR', 'HERMES_HOME')}
        self.environ = patch.dict(os.environ, env, clear=True);self.environ.start();self.addCleanup(self.environ.stop)

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.repo), *args], stderr=subprocess.DEVNULL).decode().strip()

    def commit(self, msg):
        self.git('add', '.');self.git('-c', 'user.name=Synthetic', '-c', 'user.email=test@example.invalid', 'commit', '-qm', msg)
        return self.git('rev-parse', 'HEAD')

    def prepare(self, **kwargs):
        return setup.prepare(self.home, self.repo, **kwargs)

    def apply(self, **kwargs):
        plan, changes = self.prepare(**kwargs)
        self.assertFalse(plan['conflicts'])
        with storage.lock(self.home):
            ident = storage.transact(self.home, plan, changes)
        return ident

    def config(self, name, value):
        path = self.home / name;path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value));return path

    def test_preview_does_not_mutate_either_home_or_source(self):
        before = storage.observed(self.home);source = storage.observed(self.repo)
        plan, changes = self.prepare()
        self.assertTrue(changes);self.assertEqual(storage.observed(self.home), before)
        self.assertEqual(storage.observed(self.repo), source)
        self.assertNotIn('.hermes/SOUL.md', plan['changes'])

    def test_preview_describes_exact_hook_activation_without_granting_trust(self):
        plan, _ = self.prepare()
        review = plan['hook_activation']
        self.assertFalse(review['trust_changed_by_installer'])
        self.assertEqual(len(review['codex']), 7)
        self.assertEqual({row['event'] for row in review['codex']},
                         {'SessionStart','UserPromptSubmit','PreToolUse','PostToolUse','PermissionRequest','PreCompact','Stop'})
        self.assertTrue(all(len(row['definition_sha256']) == 64 and 'planning-hook.py' in row['command']
                            for row in review['codex']))
        without, _ = self.prepare(hooks=False)
        self.assertEqual(without['hook_activation']['codex'], [])
        self.assertEqual(without['hook_activation']['claude'], [])
        claude = review['claude']
        self.assertEqual(len(claude), 1)
        self.assertEqual(claude[0]['event'], 'SessionStart')
        self.assertTrue(claude[0]['runs_when_event_fires'])
        self.assertFalse(claude[0]['native_trust_step'])
        self.assertEqual(len(claude[0]['definition_sha256']), 64)

    def test_install_update_uninstall_preserves_unrelated_settings(self):
        self.config('.claude/settings.json', {'permissions': {'deny': ['Bash(rm *)']}, 'hooks': {'Stop': [{'hooks': [{'command': 'personal-check'}]}]}})
        self.config('.codex/auth.json', {'token': 'SYNTHETIC'})
        keep = self.home / '.agents/skills/paseo/SKILL.md';keep.parent.mkdir(parents=True);keep.write_text('host-owned')
        self.apply()
        for client in ('agents', 'claude'):
            self.assertEqual((self.home / f'.{client}/skills/tdd/SKILL.md').read_bytes(), (self.repo / 'skills/tdd/SKILL.md').read_bytes())
        self.assertIsNone(self.apply(action='update'))
        source = self.repo / 'policies/communication.md';source.write_text(source.read_text()+'\nNew synthetic revision.\n')
        revision = self.commit('update policy');self.apply(action='update')
        self.assertEqual(setup.load_receipt(self.home)['source_revision'], revision)
        self.assertIn('New synthetic', (self.home / setup.BUNDLE / 'policies/communication.md').read_text())
        self.apply(action='uninstall')
        self.assertFalse((self.home / '.agents/skills/tdd').exists())
        self.assertFalse(setup.load_receipt(self.home))
        self.assertEqual(keep.read_text(), 'host-owned')
        self.assertEqual(json.loads((self.home / '.codex/auth.json').read_text()), {'token':'SYNTHETIC'})
        config = json.loads((self.home / '.claude/settings.json').read_text())
        self.assertEqual(config['permissions']['deny'], ['Bash(rm *)'])
        self.assertEqual(config['hooks']['Stop'][0]['hooks'][0]['command'], 'personal-check')

    def test_managed_file_drift_blocks_update_and_uninstall(self):
        self.apply();target = self.home / setup.BUNDLE / 'policies/communication.md';target.write_text('local edit')
        for action in ('update', 'uninstall'):
            with self.assertRaisesRegex(ValueError, 'Managed asset changed'):
                self.prepare(action=action)
        self.assertEqual(target.read_text(), 'local edit')

    def test_lifecycle_and_doctor_preserve_observation_records_and_grants(self):
        from account.observation.store import Store
        from account_doctor import diagnose
        store = Store(self.home)
        grant = store.grant(self.repo, start_after=0)
        payload = json.dumps(dict(schema_version=1, project_root=str(self.repo),
            client='synthetic', profile='default', source='fixture-v1',
            session_id='session-1', sequence=1, source_event_id='event-1',
            event_kind='response_end')).encode()
        self.assertEqual(store.capture(grant['registration_id'], grant['epoch'], payload)['status'], 'recorded')
        observations = self.home / '.agents/agent-dotfiles/observations'
        before = storage.observed(observations)
        self.apply()
        self.assertEqual(storage.observed(observations), before)
        source = self.repo / 'policies/communication.md'
        source.write_text(source.read_text() + '\nSynthetic update.\n')
        self.commit('change source')
        update = self.apply(action='update')
        self.assertEqual(storage.observed(observations), before)
        with patch('account_doctor.shutil.which', return_value='/synthetic/client'):
            self.assertEqual(diagnose(self.home)['status'], 'pass')
        self.assertEqual(storage.observed(observations), before)
        with storage.lock(self.home):
            storage.rollback(self.home, update)
        self.assertEqual(storage.observed(observations), before)
        self.apply(action='uninstall')
        self.assertEqual(storage.observed(observations), before)
        self.assertEqual(len(store.events(grant['registration_id'])), 1)
        self.assertEqual(store.capture(grant['registration_id'], grant['epoch'], payload)['status'], 'duplicate')

    def test_native_observation_selection_preserves_planning_and_is_revocable(self):
        from account.observation.store import Store
        from account_doctor import diagnose
        store = Store(self.home)
        grant = store.grant(self.repo, client='claude', source='claude-hooks-v1')
        ident = grant['registration_id']
        plan, _ = self.prepare(observation_registration=ident)
        self.assertEqual(len(plan['hook_activation']['claude_observation']), 5)
        self.assertEqual(len(plan['hook_activation']['codex']), 7)
        self.assertFalse((self.home / '.agents/bin/observation-hook.py').exists())
        self.apply(observation_registration=ident)
        config = json.loads((self.home / '.claude/settings.json').read_text())
        self.assertEqual(len(config['hooks']['SessionStart']), 2)
        command = [sys.executable, str(self.home / '.agents/bin/observation-hook.py'), ident, grant['epoch']]
        payload = json.dumps(dict(cwd=str(self.repo), session_id='session-1', hook_event_name='SessionStart',
                                  transcript_path='PRIVATE_SENTINEL')).encode()
        callback = subprocess.run(command, cwd=self.repo, input=payload, capture_output=True, timeout=5)
        self.assertEqual((callback.returncode, callback.stdout, callback.stderr), (0, b'', b''))
        self.assertEqual(len(store.events(ident)), 1)
        for bad in (b'not JSON', b'x' * 131073):
            callback = subprocess.run(command, cwd=self.repo, input=bad, capture_output=True, timeout=5)
            self.assertEqual((callback.returncode, callback.stdout, callback.stderr), (0, b'', b''))
        # A producer that never closes stdin cannot hold a hook indefinitely.
        stalled = subprocess.Popen(command, cwd=self.repo, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            self.assertEqual(stalled.wait(timeout=6), 0)
            self.assertEqual(stalled.stdout.read(), b'')
            self.assertEqual(stalled.stderr.read(), b'')
        finally:
            if stalled.poll() is None: stalled.kill(); stalled.wait()
            stalled.stdin.close(); stalled.stdout.close(); stalled.stderr.close()
        self.assertEqual(setup.status(self.home)['drift'], [])
        self.assertIsNone(self.apply(action='update'))
        store.revoke(ident)
        with patch('account_doctor.shutil.which', return_value='/synthetic/client'):
            report = diagnose(self.home)
            self.assertEqual(next(c['status'] for c in report['checks'] if c['id'] == 'observation.grant'), 'blocked')
        callback = subprocess.run(command, input=b'not JSON', capture_output=True, timeout=5)
        self.assertEqual((callback.returncode, callback.stdout, callback.stderr), (0, b'', b''))
        self.assertEqual(store.events(ident), [])
        self.apply(action='update', observation_registration='none')
        config = json.loads((self.home / '.claude/settings.json').read_text())
        self.assertEqual(list(config['hooks']), ['SessionStart'])
        self.assertEqual(len(config['hooks']['SessionStart']), 1)
        self.assertFalse((self.home / '.agents/bin/observation-hook.py').exists())

    def test_codex_observation_selection_delivery_and_client_switch(self):
        from account.observation.store import Store
        from account_doctor import diagnose
        import shlex
        store = Store(self.home)
        grant = store.grant(self.repo, client='codex', source='codex-hooks-v1')
        ident = grant['registration_id']
        plan, _ = self.prepare(observation_registration=ident)
        self.assertEqual(len(plan['hook_activation']['codex_observation']), 4)
        self.assertEqual(len(plan['hook_activation']['codex']), 11)
        self.assertEqual(plan['hook_activation']['claude_observation'], [])
        self.assertFalse(plan['hook_activation']['trust_changed_by_installer'])
        self.apply(observation_registration=ident)
        config = json.loads((self.home / '.codex/hooks.json').read_text())
        self.assertEqual(len(config['hooks']['SessionStart']), 2)
        command = shlex.split(plan['hook_activation']['codex_observation'][0]['command'])
        payload = json.dumps(dict(cwd=str(self.repo), session_id='session-1', turn_id='turn-1',
                                 hook_event_name='Stop', last_assistant_message='PRIVATE_SENTINEL')).encode()
        callback = subprocess.run(command, cwd=self.repo, input=payload, capture_output=True, timeout=5)
        self.assertEqual((callback.returncode, callback.stdout, callback.stderr), (0, b'{}\n', b''))
        self.assertEqual(len(store.events(ident)), 1)
        for bad in (b'not JSON', b'x' * 131073):
            callback = subprocess.run(command, cwd=self.repo, input=bad, capture_output=True, timeout=5)
            self.assertEqual((callback.returncode, callback.stdout, callback.stderr), (0, b'{}\n', b''))
        stalled = subprocess.Popen(command, cwd=self.repo, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            self.assertEqual(stalled.wait(timeout=6), 0)
            self.assertEqual(stalled.stdout.read(), b'{}\n')
            self.assertEqual(stalled.stderr.read(), b'')
        finally:
            if stalled.poll() is None: stalled.kill(); stalled.wait()
            stalled.stdin.close(); stalled.stdout.close(); stalled.stderr.close()
        self.assertEqual(setup.status(self.home)['drift'], [])
        self.assertIsNone(self.apply(action='update'))
        # Observer-only delivery must not accidentally depend on planning selection.
        self.apply(action='update', hooks=False)
        config = json.loads((self.home / '.codex/hooks.json').read_text())
        self.assertEqual(set(config['hooks']), {'SessionStart','PreToolUse','PostToolUse','Stop'})
        self.assertTrue(all(len(groups) == 1 for groups in config['hooks'].values()))
        self.assertEqual(json.loads((self.home / '.claude/settings.json').read_text()).get('hooks', {}), {})
        callback = subprocess.run(command, cwd=self.repo, input=payload, capture_output=True, timeout=5)
        self.assertEqual((callback.returncode, callback.stdout, callback.stderr), (0, b'{}\n', b''))
        self.assertEqual(len(store.events(ident)), 2)
        store.revoke(ident)
        callback = subprocess.run(command, cwd=self.repo, input=b'invalid', capture_output=True, timeout=5)
        self.assertEqual((callback.returncode, callback.stdout, callback.stderr), (0, b'{}\n', b''))
        with patch('account_doctor.shutil.which', return_value='/synthetic/client'):
            self.assertEqual(diagnose(self.home)['status'], 'blocked')
        self.assertEqual(store.events(ident), [])
        # One explicit selection switches clients; it never enables both grants.
        claude = store.grant(self.repo, client='claude', source='claude-hooks-v1')
        self.apply(action='update', hooks=True, observation_registration=claude['registration_id'])
        codex_config = json.loads((self.home / '.codex/hooks.json').read_text())
        self.assertEqual(len(codex_config['hooks']['SessionStart']), 1)
        self.assertEqual(len(json.loads((self.home / '.claude/settings.json').read_text())['hooks']['SessionStart']), 2)
        self.apply(action='update', observation_registration='none')
        self.assertEqual(len(json.loads((self.home / '.claude/settings.json').read_text())['hooks']['SessionStart']), 1)
        self.assertIsNotNone(store.registration(claude['registration_id']))
        self.assertFalse((self.home / '.agents/bin/observation-hook.py').exists())

    def test_codex_observation_malformed_capability_has_remediation(self):
        from account.observation.store import Store
        grant = Store(self.home).grant(self.repo, client='codex', source='codex-hooks-v1')
        path = self.repo / 'account/observation/capabilities.json'
        for body in (b'not json', b'\xff'):
            with self.subTest(body=body):
                path.write_bytes(body); self.commit('malformed synthetic capability')
                with self.assertRaisesRegex(ValueError, 'Codex observation capability; disable its registration before downgrading'):
                    self.prepare(observation_registration=grant['registration_id'])

    def test_codex_observation_refuses_source_without_adapter_capability(self):
        from account.observation.store import Store
        grant = Store(self.home).grant(self.repo, client='codex', source='codex-hooks-v1')
        capability = self.repo / 'account/observation/capabilities.json'
        if capability.exists(): capability.unlink()
        (self.repo / 'README.md').write_text('Synthetic legacy source without Codex collector.\n')
        self.commit('source without Codex observation capability')
        with self.assertRaisesRegex(ValueError, 'Codex observation capability'):
            self.prepare(observation_registration=grant['registration_id'])

    def test_modified_managed_hook_is_not_silently_removed(self):
        self.apply();p=self.home / '.codex/hooks.json';config=json.loads(p.read_text())
        config['hooks']['Stop'][0]['hooks'][0]['timeout']=999;p.write_text(json.dumps(config))
        with self.assertRaisesRegex(ValueError, 'Managed hook changed'):
            self.prepare(action='uninstall')

    def test_hermes_opt_in_requires_install_and_persists_then_removes(self):
        with patch.object(setup.shutil, 'which', side_effect=lambda n: None if n=='hermes' else '/synthetic/'+n):
            with self.assertRaisesRegex(ValueError, 'installed hermes'):
                self.prepare(hermes=True)
        p=self.home / '.hermes/SOUL.md';p.parent.mkdir();p.write_text('Keep personality.\n')
        cfg=self.config('.hermes/config.yaml', {'synthetic':'untouched'});original=cfg.read_bytes()
        with patch.object(setup.shutil, 'which', return_value='/synthetic/tool'):
            self.apply(hermes=True);self.assertTrue(setup.load_receipt(self.home)['hermes'])
            self.assertIsNone(self.apply(action='update'))
            self.apply(action='update',hermes=False)
        self.assertFalse((self.home / '.hermes/skills/tdd').exists())
        self.assertEqual(p.read_text(), 'Keep personality.\n');self.assertEqual(cfg.read_bytes(),original)

    def test_mcp_opt_in_and_removal_preserve_personal_entries(self):
        p=self.home / '.codex/config.toml';p.parent.mkdir();p.write_text('model = "personal-model"\n\n[mcp_servers.personal]\nurl = "https://example.invalid/mcp"\n')
        self.config('.claude.json', {'theme':'dark','mcpServers':{'personal':{'url':'https://example.invalid'}}})
        self.apply(mcp=['github','context7','playwright'])
        parsed=setup.tomllib.loads(p.read_text())
        self.assertEqual(parsed['mcp_servers']['github']['bearer_token_env_var'],'GITHUB_MCP_TOKEN')
        self.assertEqual(parsed['mcp_servers']['github']['http_headers']['X-MCP-Readonly'],'true')
        self.apply(action='update',mcp=[])
        self.assertEqual(set(setup.tomllib.loads(p.read_text())['mcp_servers']),{'personal'})
        self.assertEqual(json.loads((self.home / '.claude.json').read_text())['theme'],'dark')

    def test_existing_mcp_collision_is_a_conflict_not_a_replacement(self):
        self.config('.claude.json',{'mcpServers':{'github':{'url':'https://example.invalid'}}})
        with self.assertRaisesRegex(ValueError,'MCP name conflicts'):
            self.prepare(mcp=['github'])
        self.assertFalse((self.home / storage.RECEIPT).exists())

    def test_unowned_directory_needs_exact_plan_and_rollback_recovers_it(self):
        p=self.home / '.agents/skills/tdd';p.mkdir(parents=True);(p/'SKILL.md').write_text('old unowned')
        plan,_=self.prepare();self.assertIn('.agents/skills/tdd',plan['conflicts'])
        planfile=self.root/'approved.json';planfile.write_bytes(storage.encoded(plan))
        argv=['install','--repo',str(self.repo),'--home',str(self.home),'--apply']
        with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(setup.main(argv),2)
            out=io.StringIO()
            with contextlib.redirect_stdout(out):self.assertEqual(setup.main(argv+['--approve-plan',str(planfile)]),0)
        ident=json.loads(out.getvalue())['transaction'];self.assertTrue(p.is_symlink())
        with storage.lock(self.home):storage.rollback(self.home,ident)
        self.assertFalse(p.is_symlink());self.assertEqual((p/'SKILL.md').read_text(),'old unowned')

    def test_interrupted_directory_takeover_can_be_rolled_back(self):
        target = self.home / '.agents/skills/tdd'
        target.mkdir(parents=True)
        (target / 'SKILL.md').write_text('original directory')
        original = storage.observed(target)
        plan, changes = self.prepare()
        replace = storage.os.replace
        def interrupt_after_displacement(src, dst, **kwargs):
            result = replace(src, dst, **kwargs)
            # The directory moving to its journaled displacement: a leaf name below an open directory.
            if src == target.name and 'src_dir_fd' in kwargs and str(dst).startswith('displaced-'):
                raise KeyboardInterrupt('process interrupted after rename')
            return result
        with storage.lock(self.home), patch.object(storage.os, 'replace', interrupt_after_displacement):
            with self.assertRaises(KeyboardInterrupt):
                storage.transact(self.home, plan, changes)
        self.assertFalse(target.exists())
        journal = next((self.home / storage.STATE_DIR / 'transactions').glob('*/journal.json'))
        target.mkdir()
        (target / 'later-edit').write_text('preserve later edits')
        with self.assertRaisesRegex(ValueError, 'later changes'):
            storage.rollback_plan(self.home, journal.parent.name)
        self.assertEqual((target / 'later-edit').read_text(), 'preserve later edits')
        (target / 'later-edit').unlink()
        target.rmdir()
        with storage.lock(self.home):
            storage.rollback(self.home, journal.parent.name)
        self.assertEqual(storage.observed(target), original)
        self.assertFalse(setup.load_receipt(self.home))

    def test_interrupted_directory_restoration_is_retryable(self):
        target = self.home / '.agents/skills/tdd'
        target.mkdir(parents=True)
        (target / 'SKILL.md').write_text('original directory')
        original = storage.observed(target)
        plan, changes = self.prepare()
        with storage.lock(self.home):
            ident = storage.transact(self.home, plan, changes)
        installed_link = os.readlink(target)
        target.unlink()
        with self.assertRaisesRegex(ValueError, 'later changes'):
            storage.rollback_plan(self.home, ident)
        target.symlink_to(installed_link)
        replace, copytree = storage.os.replace, storage.shutil.copytree
        def interrupt_restore(src, dst, **kwargs):
            # The displaced directory moving back into place below an open directory.
            if str(src).startswith('displaced-') and dst == target.name and kwargs.get('dst_dir_fd') is not None:
                raise KeyboardInterrupt('process interrupted before restoration rename')
            return replace(src, dst, **kwargs)
        def interrupt_copy(src, dst, **kwargs):
            if Path(dst) == target:
                Path(dst).mkdir()
                (Path(dst) / 'partial-copy').write_text('interrupted')
                raise KeyboardInterrupt('process interrupted during restoration copy')
            return copytree(src, dst, **kwargs)
        with storage.lock(self.home), patch.object(storage.os, 'replace', interrupt_restore), patch.object(storage.shutil, 'copytree', interrupt_copy):
            with self.assertRaises(KeyboardInterrupt):
                storage.rollback(self.home, ident)
        with storage.lock(self.home):
            storage.rollback(self.home, ident)
        self.assertEqual(storage.observed(target), original)
        self.assertFalse(setup.load_receipt(self.home))

    def test_source_inside_any_selected_destination_is_rejected(self):
        source = self.repo
        for index, suffix in enumerate(['', '/nested-checkout']):
            with self.subTest(suffix=suffix):
                self.home = self.root / ('overlap-account-' + str(index))
                self.home.mkdir()
                self.repo = self.home / ('.agents/skills/tdd' + suffix)
                shutil.copytree(source, self.repo)
                (self.repo / 'uncommitted.txt').write_text('must survive')
                before = storage.observed(self.repo)
                with self.assertRaisesRegex(ValueError, 'Source and delivery overlap'):
                    self.prepare()
                self.assertEqual(storage.observed(self.repo), before)

    def test_stale_preview_rejected_before_any_write(self):
        plan,changes=self.prepare();self.config('.claude/settings.json',{'user_edit':True})
        with storage.lock(self.home),self.assertRaisesRegex(ValueError,'changed since preview'):
            storage.transact(self.home,plan,changes)
        self.assertFalse((self.home / setup.BUNDLE).exists())

    def test_rollback_refuses_overwriting_post_install_edits(self):
        ident=self.apply();p=self.home / '.claude/CLAUDE.md';p.write_text(p.read_text()+'personal update\n')
        with self.assertRaisesRegex(ValueError,'later changes'):
            storage.rollback_plan(self.home,ident)
        self.assertIn('personal update',p.read_text())

    def test_failed_write_rolls_back_and_keeps_private_backup(self):
        original=storage.put;calls=[]
        def fail_once(path,value,**kwargs):
            calls.append(path)
            if len(calls)==4:raise OSError('synthetic failure')
            return original(path,value,**kwargs)
        plan,changes=self.prepare()
        with storage.lock(self.home),patch.object(storage,'put',side_effect=fail_once),self.assertRaisesRegex(ValueError,'rollback|rolled-back'):
            storage.transact(self.home,plan,changes)
        self.assertFalse((self.home / storage.RECEIPT).exists())
        for name in changes:self.assertEqual(storage.observed(storage.safe(self.home,name)),plan['before'][name])
        journals=list((self.home / storage.STATE_DIR / 'transactions').glob('*/journal.json'))
        self.assertEqual(len(journals),1);self.assertEqual(journals[0].stat().st_mode & 0o777,0o600)

    def test_symlink_parent_and_source_delivery_overlap_rejected(self):
        outside=self.root/'elsewhere';outside.mkdir();(self.home/'.agents').symlink_to(outside)
        with self.assertRaisesRegex(ValueError,'Unsafe parent'):
            self.prepare()
        (self.home/'.agents').unlink()
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(setup.main(['install','--home',str(self.home),'--repo',str(self.home)]),2)

    def test_legacy_receipt_cannot_bypass_an_unmatched_instruction_owner(self):
        path = self.home / '.codex/AGENTS.md'
        path.parent.mkdir(parents=True)
        path.write_text('<!-- another-owner:begin -->\nKeep this.\n<!-- another-owner:end -->\n')
        receipt = self.root / 'legacy.json'
        receipt.write_text(json.dumps({'version': 1, 'home': str(self.home),
                                       'instructions': {}, 'hooks': {}}))
        with self.assertRaisesRegex(ValueError, 'Existing managed instructions'):
            self.prepare(legacy=receipt)
        self.assertFalse((self.home / setup.BUNDLE).exists())
        self.assertIn('Keep this.', path.read_text())

    def test_legacy_receipt_retires_only_exact_fragments(self):
        block='<!-- example:begin -->\nOld shared instructions.\n<!-- example:end -->\n'
        p=self.home / '.codex/AGENTS.md';p.parent.mkdir();p.write_text('Personal rule.\n'+block)
        group={'hooks':[{'command':'python3 old-planning-hook.py codex stop.py'}]}
        self.config('.codex/hooks.json',{'hooks':{'Stop':[group,{'hooks':[{'command':'personal-check'}]}]}})
        legacy=self.root/'old-receipt.json';legacy.write_text(json.dumps({'version':1,'home':str(self.home),'instructions':{'.codex/AGENTS.md':block},'hooks':{'.codex/hooks.json':{'Stop':[group]}}}))
        with self.assertRaisesRegex(ValueError,'legacy-receipt'):
            self.prepare()
        plan,changes=self.prepare(legacy=legacy);self.assertIn('legacy instruction/hook ownership transfer',plan['conflicts'])
        with storage.lock(self.home):storage.transact(self.home,plan,changes)
        self.assertIn('Personal rule.',p.read_text());self.assertNotIn('Old shared',p.read_text())
        groups=json.loads((self.home/'.codex/hooks.json').read_text())['hooks']['Stop']
        self.assertTrue(any(g['hooks'][0]['command']=='personal-check' for g in groups))

    # ---- accounts managed by earlier tools: shared instruction links and exact retirement ----

    def shared_instructions(self, personal='Personal rule.\n'):
        """One real instruction file; both client entries are links to it, as left by earlier managers."""
        target = self.home / '.agents/AGENTS.md'
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(personal)
        for name in ('.claude/CLAUDE.md', '.codex/AGENTS.md'):
            link = self.home / name
            link.parent.mkdir(parents=True, exist_ok=True)
            link.symlink_to('../.agents/AGENTS.md')
        return target

    def block(self, owner, line):
        return f'<!-- {owner}:begin -->\n{line}\n<!-- {owner}:end -->\n'

    def receipt_file(self, name, instructions=None, hooks=None):
        path = self.root / name
        path.write_text(json.dumps({'version': 1, 'home': str(self.home), 'instructions': instructions or {},
                                    'hooks': hooks or {}, 'tools': {'ignored': {}}, 'links': {}}))
        return path

    def test_symlinked_instruction_files_are_edited_through_one_target(self):
        target = self.shared_instructions()
        self.apply()
        for name in ('.claude/CLAUDE.md', '.codex/AGENTS.md'):
            self.assertEqual(os.readlink(self.home / name), '../.agents/AGENTS.md')
        text = target.read_text()
        self.assertTrue(text.startswith('Personal rule.\n'))
        self.assertEqual(text.count(setup.BEGIN), 1)
        self.assertIn('Read and follow', text)
        self.assertNotIn('@' + str(self.home), text)
        receipt = setup.load_receipt(self.home)
        self.assertEqual(set(receipt['instructions']), {'.agents/AGENTS.md'})
        self.assertEqual(receipt['instruction_links'],
                         {'.claude/CLAUDE.md': '.agents/AGENTS.md', '.codex/AGENTS.md': '.agents/AGENTS.md'})
        self.assertEqual(setup.status(self.home)['drift'], [])
        self.assertIsNone(self.apply(action='update'))
        self.apply(action='uninstall')
        self.assertEqual(target.read_text(), 'Personal rule.\n')
        for name in ('.claude/CLAUDE.md', '.codex/AGENTS.md'):
            self.assertTrue((self.home / name).is_symlink())

    def test_rollback_restores_a_shared_instruction_file(self):
        target = self.shared_instructions()
        ident = self.apply()
        with storage.lock(self.home):
            storage.rollback(self.home, ident)
        self.assertEqual(target.read_text(), 'Personal rule.\n')
        self.assertTrue((self.home / '.claude/CLAUDE.md').is_symlink())
        self.assertFalse((self.home / storage.RECEIPT).exists())

    def test_retargeted_instruction_link_is_reported_as_drift(self):
        self.shared_instructions()
        self.apply()
        link = self.home / '.codex/AGENTS.md'
        link.unlink()
        link.write_text('A separate regular file.\n')
        self.assertEqual(setup.status(self.home)['drift'], ['.codex/AGENTS.md'])

    def test_a_linked_claude_entry_uses_the_plain_form(self):
        # A path without whitespace is where the import form would otherwise apply.
        with tempfile.TemporaryDirectory(prefix='accountinstall') as plain:
            self.home = Path(plain).resolve()
            shared = self.home / '.agents/CLAUDE-shared.md'
            shared.parent.mkdir(parents=True)
            shared.write_text('Personal rule.\n')
            link = self.home / '.claude/CLAUDE.md'
            link.parent.mkdir(parents=True)
            link.symlink_to('../.agents/CLAUDE-shared.md')
            self.apply()
            self.assertIn('Read and follow', shared.read_text())
            self.assertNotIn('@', shared.read_text())

    def test_a_regular_claude_entry_keeps_the_import_form(self):
        with tempfile.TemporaryDirectory(prefix='accountinstall') as plain:
            self.home = Path(plain).resolve()
            self.apply()
            self.assertIn('@' + str(self.home / setup.BUNDLE / 'account/instructions.md'),
                          (self.home / '.claude/CLAUDE.md').read_text())
            self.assertIn('Read and follow', (self.home / '.codex/AGENTS.md').read_text())

    def test_instruction_links_that_are_not_one_account_markdown_file_are_refused(self):
        outside = self.root / 'outside.md'
        outside.write_text('Not ours.\n')
        agents = self.home / '.agents'
        agents.mkdir()
        (agents / 'real.md').write_text('Real.\n')
        (agents / 'chain.md').symlink_to('real.md')
        (agents / 'folder.md').mkdir()
        (agents / 'notes.txt').write_text('Text.\n')
        (agents / 'skills/x').mkdir(parents=True)
        (agents / 'skills/x/NOTES.md').write_text('Skill notes.\n')
        # A link inside the account that the text passes through and comes back from: the kernel and the lexical
        # form agree, but the file is no longer named through real directories only.
        (agents / 'sub').mkdir()
        (agents / 'bridge').symlink_to('sub')
        # `..` after a link is resolved by the kernel in the link's target, not in the account path.
        bridge_target = self.root / 'bridge-target'
        bridge_target.mkdir()
        (self.home / 'bridge').symlink_to(bridge_target)
        (self.home / 'AGENTS.md').write_text('Unrelated personal file.\n')
        (self.root / 'AGENTS.md').write_text('Outside file.\n')
        (self.home / 'alias').symlink_to(agents)
        # An outside name for the same inode: equal files, different paths (a hard link made by the account owner).
        hard_dir = self.root / 'hard-target'
        (hard_dir / 'sub').mkdir(parents=True)
        os.link(self.home / 'AGENTS.md', hard_dir / 'AGENTS.md')
        (self.home / 'bridge-hard').symlink_to(hard_dir / 'sub')
        for tree in ('.agents/agent-dotfiles/bundle', '.agents/agent-dotfiles/state', '.codex/hooks', '.claude/hooks',
                     '.AGENTS/Agent-Dotfiles/state', '.agents/Skills/x', '.Codex/Hooks', '.claude/HOOKS'):
            (self.home / tree).mkdir(parents=True)
            (self.home / tree / 'NOTES.md').write_text('Payload notes.\n')
        cases = {
            'leaves the account': (str(outside), 'leaves the account'),
            'is a chain': ('../.agents/chain.md', 'one regular file'),
            'is missing': ('../.agents/missing.md', 'one regular file'),
            'is a directory': ('../.agents/folder.md', 'one regular file'),
            'is not Markdown': ('../.agents/notes.txt', 'Markdown'),
            'is inside a skill': ('../.agents/skills/x/NOTES.md', 'protected'),
            'is inside the bundle': ('../.agents/agent-dotfiles/bundle/NOTES.md', 'protected'),
            'is inside the state': ('../.agents/agent-dotfiles/state/NOTES.md', 'protected'),
            'is inside the Codex hooks': ('hooks/NOTES.md', 'protected'),
            'is inside the Claude hooks': ('../.claude/hooks/NOTES.md', 'protected'),
            'is inside the state under another spelling': ('../.AGENTS/Agent-Dotfiles/state/NOTES.md', 'protected'),
            'is inside a skill under another spelling': ('../.agents/Skills/x/NOTES.md', 'protected'),
            'is inside the Codex hooks under another spelling': ('../.Codex/Hooks/NOTES.md', 'protected'),
            'is inside the Claude hooks under another spelling': ('../.claude/HOOKS/NOTES.md', 'protected'),
            'ends with a slash': ('../.agents/real.md/', 'one regular file'),
            'ends with a dot component': ('../.agents/real.md/.', 'one regular file'),
            'goes through a regular file': ('../.agents/real.md/../real.md', 'one regular file'),
            'passes through a directory link outside the account': ('../bridge/../AGENTS.md', 'one regular file'),
            'reaches a hard link of an account file through an outside directory link': ('../bridge-hard/../AGENTS.md', 'one regular file'),
            'passes through a missing directory': ('../missing/../.agents/real.md', 'one regular file'),
            'passes through a directory link inside the account': ('../alias/real.md', 'one regular file|Unsafe parent'),
            'passes through a directory link inside the account and returns': ('../.agents/bridge/../real.md', 'one regular file'),
        }
        entry = self.home / '.codex/AGENTS.md'
        entry.parent.mkdir(exist_ok=True)
        before = storage.observed(self.home)
        for label, (target, message) in cases.items():
            with self.subTest(label):
                entry.symlink_to(target)
                try:
                    with self.assertRaisesRegex(ValueError, message):
                        self.prepare()
                finally:
                    entry.unlink()
                self.assertEqual(storage.observed(self.home), before)
        self.assertFalse((self.home / setup.BUNDLE / 'account').exists())
        self.assertEqual((self.home / 'AGENTS.md').read_text(), 'Unrelated personal file.\n')
        self.assertEqual((self.root / 'hard-target/AGENTS.md').read_text(), 'Unrelated personal file.\n')
        self.assertEqual((self.root / 'AGENTS.md').read_text(), 'Outside file.\n')

    def test_managed_target_accepts_an_instruction_file_only_behind_a_current_link(self):
        self.assertFalse(storage.managed_target('.agents/AGENTS.md', self.home))
        self.shared_instructions()
        self.assertTrue(storage.managed_target('.agents/AGENTS.md', self.home))
        self.assertFalse(storage.managed_target('.agents/other.md', self.home))

    def test_removing_the_only_block_keeps_the_file_that_links_name(self):
        target = self.shared_instructions('')
        self.apply()
        self.apply(action='uninstall')
        self.assertEqual(target.read_text(), '')
        self.assertEqual(os.readlink(self.home / '.codex/AGENTS.md'), '../.agents/AGENTS.md')
        self.assertTrue((self.home / '.codex/AGENTS.md').exists())

    def test_one_client_entry_may_link_to_the_other(self):
        real = self.home / '.claude/CLAUDE.md'
        real.parent.mkdir(parents=True)
        real.write_text('Personal rule.\n')
        (self.home / '.codex').mkdir()
        (self.home / '.codex/AGENTS.md').symlink_to('../.claude/CLAUDE.md')
        self.apply()
        receipt = setup.load_receipt(self.home)
        self.assertEqual(set(receipt['instructions']), {'.claude/CLAUDE.md'})
        self.assertEqual(receipt['instruction_links'], {'.codex/AGENTS.md': '.claude/CLAUDE.md'})
        self.assertIn('Read and follow', real.read_text())
        self.apply(action='uninstall')
        self.assertEqual(real.read_text(), 'Personal rule.\n')
        self.assertTrue((self.home / '.codex/AGENTS.md').is_symlink())

    def test_receipt_cannot_claim_files_outside_instruction_links(self):
        self.shared_instructions()
        self.apply()
        path = self.home / storage.RECEIPT
        receipt = json.loads(path.read_text())
        forged = {
            'link to a hook file': dict(receipt, instruction_links={'.codex/AGENTS.md': '.codex/hooks.json'}),
            'link into a skill': dict(receipt, instruction_links={'.codex/AGENTS.md': '.agents/skills/x/NOTES.md'}),
            'file without a link': dict(receipt, instruction_links={}),
        }
        for label, value in forged.items():
            with self.subTest(label):
                path.write_text(json.dumps(value))
                with self.assertRaisesRegex(ValueError, 'instruction_links|unsupported configuration'):
                    setup.load_receipt(self.home)

    def test_absolute_instruction_link_inside_the_account_is_followed(self):
        target = self.home / '.agents/AGENTS.md'
        target.parent.mkdir()
        target.write_text('Personal rule.\n')
        (self.home / '.codex').mkdir()
        (self.home / '.codex/AGENTS.md').symlink_to(target)
        self.apply()
        self.assertEqual(setup.load_receipt(self.home)['instruction_links'], {'.codex/AGENTS.md': '.agents/AGENTS.md'})
        self.assertEqual(target.read_text().count(setup.BEGIN), 1)
        self.assertEqual((self.home / '.codex/AGENTS.md').readlink(), target)

    def test_update_and_uninstall_stop_when_an_installed_link_changed(self):
        self.shared_instructions()
        self.apply()
        other = self.home / '.agents/OTHER.md'
        other.write_text('Elsewhere.\n')
        link = self.home / '.codex/AGENTS.md'
        link.unlink()
        link.symlink_to('../.agents/OTHER.md')
        for action in ('update', 'uninstall'):
            with self.subTest(action), self.assertRaisesRegex(ValueError, r'Instruction link changed since installation: \.codex/AGENTS\.md'):
                self.prepare(action=action)
        self.assertEqual(other.read_text(), 'Elsewhere.\n')

    def test_rollback_stops_when_the_link_no_longer_names_the_file(self):
        self.shared_instructions()
        ident = self.apply()
        other = self.home / '.agents/OTHER.md'
        other.write_text('Elsewhere.\n')
        for name in ('.claude/CLAUDE.md', '.codex/AGENTS.md'):
            (self.home / name).unlink()
            (self.home / name).symlink_to('../.agents/OTHER.md')
        with self.assertRaisesRegex(ValueError, 'Unsupported rollback destination'):
            storage.rollback_plan(self.home, ident)
        self.assertEqual(other.read_text(), 'Elsewhere.\n')

    def test_legacy_receipts_repeat_and_name_the_linked_instruction_file(self):
        first = self.block('flyingcorp', 'Read and follow "/old/flyingcorp.md".')
        second = self.block('sdlc-installer', 'Read and follow "/old/sdlc.md".')
        target = self.shared_instructions('Personal rule.\n\n' + second + '\n' + first)
        one = self.receipt_file('one.json', instructions={'.agents/AGENTS.md': first})
        two = self.receipt_file('two.json', instructions={'.codex/AGENTS.md': second})
        # The refusal names the file and the remaining owner, not the block text.
        with self.assertRaisesRegex(ValueError, r'ownership transfer \(\.agents/AGENTS\.md: sdlc-installer\)') as caught:
            self.prepare(legacy=[one])
        self.assertNotIn('Read and follow', str(caught.exception))
        plan, changes = self.prepare(legacy=[one, two])
        self.assertIn('legacy instruction/hook ownership transfer', plan['conflicts'])
        with storage.lock(self.home):
            storage.transact(self.home, plan, changes)
        text = target.read_text()
        self.assertTrue(text.startswith('Personal rule.\n'))
        self.assertNotIn(':begin', text.replace(setup.BEGIN, ''))
        self.assertEqual(text.count(setup.BEGIN), 1)

    def test_legacy_instruction_value_may_list_blocks(self):
        first = self.block('flyingcorp', 'Old one.')
        second = self.block('sdlc-installer', 'Old two.')
        target = self.shared_instructions('Personal rule.\n' + second + first)
        receipt = self.receipt_file('both.json', instructions={'.agents/AGENTS.md': [first, second]})
        plan, changes = self.prepare(legacy=[receipt])
        with storage.lock(self.home):
            storage.transact(self.home, plan, changes)
        self.assertNotIn('Old', target.read_text())

    def test_legacy_receipts_stay_exact(self):
        block = self.block('flyingcorp', 'Old one.')
        target = self.shared_instructions('Personal rule.\n' + block)
        cases = {
            'Unsupported legacy configuration paths': self.receipt_file('path.json', instructions={'.agents/OTHER.md': block}),
            'exact marked block': self.receipt_file('shape.json', instructions={'.agents/AGENTS.md': 'Old one.\n'}),
            'own block': self.receipt_file('own.json', instructions={
                '.agents/AGENTS.md': self.block('agent-dotfiles', 'Ours.')}),
            'changed': self.receipt_file('changed.json', instructions={'.agents/AGENTS.md': self.block('flyingcorp', 'Different.')}),
        }
        for message, receipt in cases.items():
            with self.subTest(message), self.assertRaisesRegex(ValueError, message):
                self.prepare(legacy=[receipt])
        newer = self.root / 'newer.json'
        newer.write_text(json.dumps({'version': 2, 'home': str(self.home), 'block': block}))
        with self.assertRaisesRegex(ValueError, 'Unsupported legacy receipt version'):
            self.prepare(legacy=[newer])
        foreign = self.root / 'foreign.json'
        foreign.write_text(json.dumps({'version': 1, 'home': str(self.root / 'other account'), 'instructions': {}, 'hooks': {}}))
        with self.assertRaisesRegex(ValueError, 'another account'):
            self.prepare(legacy=[foreign])
        self.assertEqual(target.read_text(), 'Personal rule.\n' + block)

    def test_previous_account_dispatcher_is_not_layered_silently(self):
        group = {'hooks': [{'type': 'command', 'command': f'python3 {self.home}/.agents/bin/flyingcorp-hook.py claude session-start'}]}
        self.config('.claude/settings.json', {'hooks': {'SessionStart': [group]}})
        with self.assertRaisesRegex(ValueError, r'\.claude/settings\.json.*SessionStart'):
            self.prepare()
        receipt = self.receipt_file('hook.json', hooks={'.claude/settings.json': {'SessionStart': [group]}})
        plan, changes = self.prepare(legacy=[receipt])
        with storage.lock(self.home):
            storage.transact(self.home, plan, changes)
        groups = json.loads((self.home / '.claude/settings.json').read_text())['hooks']['SessionStart']
        self.assertNotIn(group, groups)
        self.assertTrue(groups)

    def test_a_previous_planning_route_in_any_event_is_not_kept_silently(self):
        commands = ('python3 /x/.agents/bin/flyingcorp-hook.py claude stop',
                    'python3 /x/.claude/skills/planning-with-files/scripts/stop.py')
        for index, command in enumerate(commands):
            with self.subTest(command):
                self.home = self.root / f'route account {index}'
                self.home.mkdir()
                group = {'hooks': [{'type': 'command', 'command': command}]}
                self.config('.claude/settings.json', {'hooks': {'Stop': [group]}})
                with self.assertRaisesRegex(ValueError, r'\.claude/settings\.json Stop'):
                    self.prepare()
                receipt = self.receipt_file(f'stop-{index}.json', hooks={'.claude/settings.json': {'Stop': [group]}})
                plan, changes = self.prepare(legacy=[receipt])
                with storage.lock(self.home):
                    storage.transact(self.home, plan, changes)
                hooks = json.loads((self.home / '.claude/settings.json').read_text())['hooks']
                self.assertNotIn(group, hooks.get('Stop', []))

    def test_a_hermes_entry_may_link_to_the_same_shared_file(self):
        target = self.shared_instructions()
        soul = self.home / '.hermes/SOUL.md'
        soul.parent.mkdir()
        soul.symlink_to('../.agents/AGENTS.md')
        with patch.object(setup.shutil, 'which', side_effect=lambda name: '/synthetic/' + name):
            self.apply(hermes=True)
        receipt = setup.load_receipt(self.home)
        self.assertEqual(set(receipt['instructions']), {'.agents/AGENTS.md'})
        self.assertEqual(receipt['instruction_links']['.hermes/SOUL.md'], '.agents/AGENTS.md')
        self.assertEqual(target.read_text().count(setup.BEGIN), 1)
        self.assertTrue(soul.is_symlink())

    def test_malformed_legacy_receipts_are_refused_with_a_message(self):
        malformed = {
            'not an object': [],
            'hooks is a list': {'version': 1, 'home': str(self.home), 'hooks': []},
            'events is a list': {'version': 1, 'home': str(self.home), 'hooks': {'.codex/hooks.json': []}},
            'groups is not a list': {'version': 1, 'home': str(self.home), 'hooks': {'.codex/hooks.json': {'Stop': {}}}},
            'instructions is a list': {'version': 1, 'home': str(self.home), 'instructions': []},
        }
        for label, value in malformed.items():
            with self.subTest(label):
                path = self.root / 'malformed.json'
                path.write_text(json.dumps(value))
                with self.assertRaisesRegex(ValueError, 'legacy receipt|Legacy receipt'):
                    self.prepare(legacy=[path])
                with contextlib.redirect_stderr(io.StringIO()) as error:
                    code = setup.main(['install', '--home', str(self.home), '--repo', str(self.repo), '--legacy-receipt', str(path)])
                self.assertEqual(code, 2)
                self.assertTrue(error.getvalue().startswith('Account setup: '))

    def test_an_inline_codex_hook_of_the_previous_dispatcher_is_reported(self):
        config = self.home / '.codex/config.toml'
        config.parent.mkdir()
        config.write_text('[[hooks.Stop]]\n[[hooks.Stop.hooks]]\ncommand = "python3 /x/.agents/bin/flyingcorp-hook.py codex stop"\n')
        with self.assertRaisesRegex(ValueError, 'Inline Codex'):
            self.prepare()

    def test_status_reports_a_shared_file_that_became_a_link(self):
        self.shared_instructions()
        self.apply()
        target = self.home / '.agents/AGENTS.md'
        real = self.home / '.agents/REAL.md'
        target.rename(real)
        target.symlink_to('REAL.md')
        self.assertIn('.agents/AGENTS.md', setup.status(self.home)['drift'])

    def assert_a_swapped_directory_is_not_followed(self, directory, target):
        """Replace an account directory by a link to an outside one right before its file is written."""
        self.home = self.root / ('swap account ' + directory.strip('.'))
        self.home.mkdir()
        self.shared_instructions()
        self.config('.claude/settings.json', {'permissions': {'deny': ['Bash(rm *)']}})
        outside = self.root / ('outside of ' + directory.strip('.'))
        outside.mkdir()
        for name in ('AGENTS.md', 'settings.json'):
            (outside / name).write_text('Outside file.\n')
        plan, changes = self.prepare()
        real_put, swapped = storage.put, []

        def swap_then_put(path, value, **kwargs):
            if path == self.home / target and not swapped:
                swapped.append(True)
                (self.home / directory).rename(self.home / (directory + '-moved'))
                (self.home / directory).symlink_to(outside)
            return real_put(path, value, **kwargs)

        with patch.object(storage, 'put', side_effect=swap_then_put), storage.lock(self.home):
            with self.assertRaises(ValueError):
                storage.transact(self.home, plan, changes)
        self.assertTrue(swapped)
        for name in ('AGENTS.md', 'settings.json'):
            self.assertEqual((outside / name).read_text(), 'Outside file.\n')

    def test_the_directory_of_a_shared_instruction_file_swapped_for_a_link_is_not_followed(self):
        self.assert_a_swapped_directory_is_not_followed('.agents', '.agents/AGENTS.md')

    def test_the_directory_of_a_config_file_swapped_for_a_link_is_not_followed(self):
        self.assert_a_swapped_directory_is_not_followed('.claude', '.claude/settings.json')

    def test_the_journal_directory_swapped_for_a_link_does_not_move_account_directories_outside(self):
        target = self.home / '.agents/skills/tdd'
        target.mkdir(parents=True)
        (target / 'SKILL.md').write_text('original directory')
        outside = self.root / 'outside of the journal'
        outside.mkdir()
        plan, changes = self.prepare()
        real_put, swapped = storage.put, []

        def swap_then_put(path, value, **kwargs):
            if path == target and not swapped:
                swapped.append(True)
                transactions = self.home / storage.STATE_DIR / 'transactions'
                (outside / next(transactions.iterdir()).name).mkdir()
                transactions.rename(transactions.with_name('transactions-moved'))
                transactions.symlink_to(outside)
            return real_put(path, value, **kwargs)

        with patch.object(storage, 'put', side_effect=swap_then_put), storage.lock(self.home):
            with self.assertRaises(ValueError):
                storage.transact(self.home, plan, changes)
        self.assertTrue(swapped)
        self.assertEqual((target / 'SKILL.md').read_text(), 'original directory')
        # The installer's own journal file is a state file and stays path-based; no account content moved.
        self.assertFalse([item for item in outside.rglob('*') if item.name.startswith('displaced-') or item.name == 'SKILL.md'])

    def test_a_link_retargeted_during_the_writes_rolls_the_apply_back(self):
        target = self.shared_instructions()
        other = self.home / '.agents/OTHER.md'
        other.write_text('Elsewhere.\n')
        plan, changes = self.prepare()
        real_put, swapped = storage.put, []

        def retarget_then_put(path, value, **kwargs):
            if not swapped:
                swapped.append(True)
                (self.home / '.codex/AGENTS.md').unlink()
                (self.home / '.codex/AGENTS.md').symlink_to('../.agents/OTHER.md')
            return real_put(path, value, **kwargs)

        with patch.object(storage, 'put', side_effect=retarget_then_put), storage.lock(self.home):
            with self.assertRaisesRegex(ValueError, r'Transaction failed.*rolled-back') as caught:
                storage.transact(self.home, plan, changes)
        self.assertRegex(str(caught.exception.__cause__), r'Concurrent change: \.codex/AGENTS\.md')
        self.assertEqual(target.read_text(), 'Personal rule.\n')
        self.assertFalse((self.home / storage.RECEIPT).exists())

    def test_the_codex_adapter_scripts_are_a_previous_route_in_any_client_file(self):
        group = {'hooks': [{'type': 'command', 'command': 'python3 /x/.codex/hooks/stop.py'}]}
        self.config('.claude/settings.json', {'hooks': {'Stop': [group]}})
        with self.assertRaisesRegex(ValueError, r'\.claude/settings\.json Stop'):
            self.prepare()
        receipt = self.receipt_file('adapter-stop.json', hooks={'.claude/settings.json': {'Stop': [group]}})
        self.assertTrue(self.prepare(legacy=[receipt])[1])
        # The doctor reports the same route when it appears after an installation.
        self.home = self.root / 'doctor route account'
        self.home.mkdir()
        self.apply()
        settings = self.home / '.claude/settings.json'
        config = json.loads(settings.read_text())
        config['hooks'].setdefault('Stop', []).append(group)
        settings.write_text(json.dumps(config))
        import account_doctor
        checks = {row['id']: row['status'] for row in account_doctor.diagnose(self.home)['checks']}
        self.assertEqual(checks['hooks.claude'], 'fail')

    def test_the_doctor_names_an_instruction_file_in_the_account_root(self):
        (self.home / 'AGENTS.md').write_text('Personal rule.\n')
        (self.home / '.codex').mkdir()
        (self.home / '.codex/AGENTS.md').symlink_to('../AGENTS.md')
        self.apply()
        import account_doctor
        checks = {row['id']: row['status'] for row in account_doctor.diagnose(self.home)['checks']}
        self.assertEqual(checks.get('instructions.AGENTS.md'), 'pass')

    def test_an_uninstall_preview_fingerprints_the_installed_links(self):
        self.shared_instructions()
        self.apply()
        plan, _ = self.prepare(action='uninstall')
        self.assertEqual(sorted(name for name in plan['before'] if name in ('.claude/CLAUDE.md', '.codex/AGENTS.md')),
                         ['.claude/CLAUDE.md', '.codex/AGENTS.md'])

    def test_a_link_changed_after_the_preview_stops_the_apply(self):
        target = self.shared_instructions()
        plan, changes = self.prepare()
        other = self.home / '.agents/OTHER.md'
        other.write_text('Elsewhere.\n')
        (self.home / '.codex/AGENTS.md').unlink()
        (self.home / '.codex/AGENTS.md').symlink_to('../.agents/OTHER.md')
        with storage.lock(self.home), self.assertRaisesRegex(ValueError, r'changed since preview: \.codex/AGENTS\.md'):
            storage.transact(self.home, plan, changes)
        self.assertEqual(target.read_text(), 'Personal rule.\n')
        self.assertEqual(other.read_text(), 'Elsewhere.\n')

    def snapshot(self):
        """Every account path outside the installer's own state, as comparable data."""
        found = {}
        for root, dirs, files in os.walk(self.home):
            for name in sorted(dirs + files):
                item = Path(root) / name
                key = str(item.relative_to(self.home))
                if key.startswith('.agents/agent-dotfiles'):
                    continue
                if item.is_symlink():
                    found[key] = ('link', os.readlink(item))
                elif item.is_dir():
                    continue  # Empty directories left behind by an install are not state.
                else:
                    found[key] = ('file', item.read_bytes(), item.stat().st_mode & 0o777)
        return found

    def build_previous_account(self):
        """Replica of an account managed by earlier tools, with synthetic content only."""
        events = ['SessionStart', 'UserPromptSubmit', 'PreToolUse', 'PostToolUse', 'PermissionRequest', 'PreCompact', 'Stop']
        home = self.home
        fly = self.block('flyingcorp', f'Read and follow "{home}/.agents/instructions/flyingcorp.md".')
        sdlc = self.block('sdlc-installer', f'Read and follow "{home}/.agents/policies/sdlc.md" at task intake.')
        self.shared_instructions('Personal rule.\n\n' + sdlc + '\n' + fly)
        for name, text in {'.agents/bin/flyingcorp-hook.py': '# old dispatcher\n',
                           '.agents/instructions/flyingcorp.md': 'Old shared rules.\n',
                           '.agents/policies/sdlc.md': 'Old SDLC policy.\n'}.items():
            (home / name).parent.mkdir(parents=True, exist_ok=True)
            (home / name).write_text(text)
        old_codex = {e: {'matcher': '*', 'hooks': [{'type': 'command', 'command': f'python3 {home}/.agents/bin/flyingcorp-hook.py codex {e}'}]}
                     for e in events}
        adapter = {e: {'hooks': [{'type': 'command', 'command': f'python3 {home}/.agents/adapters/planning-with-files/codex/hooks/run_sh.py {e}'}]}
                   for e in events}
        graft = {'hooks': [{'type': 'command', 'command': f'node "{home}/.codex/hooks/graft/graft-hooks.cjs" prompt'}]}
        old_claude = {'matcher': 'startup', 'hooks': [{'type': 'command', 'command': f'python3 {home}/.agents/bin/flyingcorp-hook.py claude session-start'}]}
        personal = {'hooks': [{'type': 'command', 'command': 'personal-check'}]}
        self.config('.codex/hooks.json', {'hooks': {e: [adapter[e], old_codex[e], graft, personal] for e in events}})
        self.config('.claude/settings.json', {'permissions': {'deny': ['Bash(rm *)']},
                                              'hooks': {'SessionStart': [graft, old_claude], 'Stop': [personal]}})
        for rel in ('.codex/hooks/run_sh.py', '.claude/hooks/planning-with-files-dispatch.sh'):
            write_old = home / rel
            write_old.parent.mkdir(parents=True, exist_ok=True)
            write_old.write_text('# previous manager runtime file\n')
        for skill in ('planning-with-files', 'tdd'):
            old = home / '.agents/skills' / skill
            old.mkdir(parents=True)
            (old / 'SKILL.md').write_text(f'old {skill}\n')
            for client in ('.claude', '.codex'):
                alias = home / client / 'skills' / skill
                alias.parent.mkdir(parents=True, exist_ok=True)
                alias.symlink_to(old)
        return {
            'fly': self.receipt_file('flyingcorp-install.json', instructions={'.agents/AGENTS.md': fly},
                                     hooks={'.claude/settings.json': {'SessionStart': [old_claude]},
                                            '.codex/hooks.json': {e: [old_codex[e]] for e in events}}),
            'sdlc': self.receipt_file('retire-sdlc.json', instructions={'.agents/AGENTS.md': sdlc}),
            'adapter': self.receipt_file('retire-adapter.json', hooks={'.codex/hooks.json': {e: [adapter[e]] for e in events}}),
        }

    def test_takeover_of_an_account_managed_by_earlier_tools_round_trips(self):
        receipts = self.build_previous_account()
        original = self.snapshot()
        arguments = ['--home', str(self.home), '--repo', str(self.repo)]
        for receipt in receipts.values():
            arguments += ['--legacy-receipt', str(receipt)]
        preview = io.StringIO()
        with contextlib.redirect_stdout(preview):
            self.assertEqual(setup.main(['install'] + arguments), 0)
        plan = json.loads(preview.getvalue())
        self.assertEqual(self.snapshot(), original)
        self.assertIn('legacy instruction/hook ownership transfer', plan['conflicts'])
        for name in ('.agents/skills/tdd', '.agents/skills/planning-with-files', '.claude/skills/tdd',
                     '.codex/skills/planning-with-files', '.codex/hooks/run_sh.py',
                     '.claude/hooks/planning-with-files-dispatch.sh'):
            self.assertIn(name, plan['conflicts'])
        self.assertEqual(plan['instruction_links'],
                         {'.claude/CLAUDE.md': '.agents/AGENTS.md', '.codex/AGENTS.md': '.agents/AGENTS.md'})
        saved = self.root / 'approved-plan.json'
        saved.write_text(preview.getvalue())
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(setup.main(['install', '--apply'] + arguments), 2)
        applied = io.StringIO()
        with contextlib.redirect_stdout(applied):
            self.assertEqual(setup.main(['install', '--apply', '--approve-plan', str(saved)] + arguments), 0)
        ident = json.loads(applied.getvalue())['transaction']

        text = (self.home / '.agents/AGENTS.md').read_text()
        self.assertTrue(text.startswith('Personal rule.\n'))
        self.assertNotIn('flyingcorp', text)
        self.assertNotIn('sdlc-installer', text)
        self.assertEqual(text.count(setup.BEGIN), 1)
        for name in ('.claude/CLAUDE.md', '.codex/AGENTS.md'):
            self.assertEqual(os.readlink(self.home / name), '../.agents/AGENTS.md')
        codex = json.loads((self.home / '.codex/hooks.json').read_text())['hooks']
        for groups in codex.values():
            commands = json.dumps(groups)
            self.assertNotIn('flyingcorp-hook', commands)
            self.assertNotIn('adapters/planning-with-files', commands)
            self.assertIn('graft-hooks.cjs', commands)
            self.assertIn('personal-check', commands)
            self.assertIn('planning-hook.py', commands)
        claude = json.loads((self.home / '.claude/settings.json').read_text())
        self.assertEqual(claude['permissions'], {'deny': ['Bash(rm *)']})
        self.assertNotIn('flyingcorp-hook', json.dumps(claude))
        self.assertIn('personal-check', json.dumps(claude['hooks']['Stop']))
        for client in ('agents', 'claude'):
            self.assertTrue((self.home / f'.{client}/skills/tdd').is_symlink())
        self.assertEqual(setup.status(self.home)['drift'], [])
        self.assertNotIn('previous manager', (self.home / '.codex/hooks/run_sh.py').read_text())
        import account_doctor
        report = {row['id']: row['status'] for row in account_doctor.diagnose(self.home)['checks']}
        for ident_check in ('installation', 'owned-content', 'instructions.agents', 'hooks.codex', 'hooks.claude',
                            'codex.skill-paths', 'claude.skill-paths'):
            self.assertEqual(report[ident_check], 'pass', ident_check)

        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(setup.main(['rollback', '--apply', '--transaction', ident, '--home', str(self.home)]), 0)
        self.assertEqual(self.snapshot(), original)

    def test_second_host_has_own_paths_and_no_host_secrets_in_source(self):
        self.apply();first=setup.load_receipt(self.home)
        self.home=self.root/'different host';self.home.mkdir();self.apply();second=setup.load_receipt(self.home)
        self.assertEqual(first['source_revision'],second['source_revision'])
        self.assertNotEqual(first['home'],second['home'])
        self.assertNotIn(first['home'],json.dumps(second))
        self.assertNotIn(str(self.home),(self.repo/'account/instructions.md').read_text())

    def test_source_is_committed_and_update_removes_retired_skill(self):
        before=self.git('rev-parse','HEAD')
        (self.repo/'policies/communication.md').write_text('Uncommitted content')
        self.apply()
        self.assertEqual(setup.load_receipt(self.home)['source_revision'],before)
        self.assertNotEqual((self.home/setup.BUNDLE/'policies/communication.md').read_text(),'Uncommitted content')
        shutil.rmtree(self.repo/'skills/tdd');self.commit('retire skill')
        self.apply(action='update')
        self.assertFalse((self.home/'.agents/skills/tdd').is_symlink())
        self.assertTrue((self.home/'.agents/skills/planning-with-files').is_symlink())

    def test_config_drift_and_disabled_mcp_are_not_overwritten(self):
        self.apply(mcp=['context7'])
        p=self.home/'.codex/config.toml';p.write_text(p.read_text()+'enabled = false\n')
        self.assertIn('.codex/config.toml',setup.status(self.home)['drift'])
        with self.assertRaisesRegex(ValueError,'outside the marked block'):
            self.prepare(action='update')

    def test_inline_planning_hooks_and_global_override_are_reported(self):
        p=self.home/'.codex/config.toml';p.parent.mkdir()
        p.write_text('[[hooks.Stop]]\n[[hooks.Stop.hooks]]\ncommand = "python3 old-planning-hook.py"\n')
        with self.assertRaisesRegex(ValueError,'Inline Codex'):
            self.prepare()
        p.unlink();(p.parent/'AGENTS.override.md').write_text('Temporary preference')
        with self.assertRaisesRegex(ValueError,'masks global guidance'):
            self.prepare()

    def test_failure_replacing_directory_preserves_original(self):
        p=self.home/'.agents/skills/tdd';p.mkdir(parents=True);(p/'SKILL.md').write_text('original')
        with patch.object(storage, '_put_file', side_effect=OSError('synthetic')):
            with self.assertRaises(OSError):storage.put(p,{'link':'/synthetic/destination'},displaced=self.root/'displaced-test')
        self.assertEqual((p/'SKILL.md').read_text(),'original')

    def test_receipt_cannot_claim_paseo_or_authentication(self):
        self.apply();path=self.home/storage.RECEIPT;receipt=json.loads(path.read_text())
        for name in ['.agents/skills/paseo','.codex/auth.json']:
            changed=dict(receipt);changed['assets']=dict(receipt['assets'],**{name:None});path.write_text(json.dumps(changed))
            with self.assertRaisesRegex(ValueError,'unsupported asset'):
                setup.load_receipt(self.home)

    def test_hook_toggle_keeps_skills_and_unrelated_hooks(self):
        self.apply();self.apply(action='update',hooks=False)
        self.assertTrue((self.home/'.agents/skills/tdd').is_symlink())
        self.assertFalse((self.home/'.agents/bin/planning-hook.py').exists())
        self.assertFalse(json.loads((self.home/'.codex/hooks.json').read_text()).get('hooks'))
        self.apply(action='update',hooks=True)
        self.assertTrue((self.home/'.agents/bin/planning-hook.py').exists())


if __name__=='__main__':unittest.main()
