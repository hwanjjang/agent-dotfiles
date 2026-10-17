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
        def interrupt_after_displacement(src, dst):
            result = replace(src, dst)
            if Path(src) == target:
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
        def interrupt_restore(src, dst):
            if Path(dst) == target:
                raise KeyboardInterrupt('process interrupted before restoration rename')
            return replace(src, dst)
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
