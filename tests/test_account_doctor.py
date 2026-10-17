"""Account diagnostics must distinguish delivery, native readiness and model evidence."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import setup_account as setup


class DoctorCliTests(unittest.TestCase):
    def test_uninstalled_account_is_not_healthy_and_is_not_mutated(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                try:
                    code = setup.main(['doctor', '--home', tmp, '--json'])
                except SystemExit as error:
                    self.fail('doctor command is unavailable: ' + str(error))
            result = json.loads(output.getvalue())
            self.assertEqual(code, 1)
            self.assertEqual(result['status'], 'fail')
            self.assertEqual(list(home.iterdir()), [])

    def test_doctor_refuses_apply(self):
        output = io.StringIO()
        with contextlib.redirect_stderr(output):
            try:
                code = setup.main(['doctor', '--apply'])
            except SystemExit as error:
                self.fail('doctor must reject mutation through its own validation: ' + str(error))
        self.assertEqual(code, 2)

class NativeEvidenceTests(unittest.TestCase):
    def test_skill_invocation_requires_success_and_exact_owned_body(self):
        from account_model_check import routing_sources_loaded
        with tempfile.TemporaryDirectory() as temp:
            home=Path(temp).resolve();folder=home/setup.BUNDLE/'skills/to-spec';folder.mkdir(parents=True)
            source='---\nname: to-spec\n---\n\n# Unique body\nExact method.\n'
            sources={'skills/to-spec/SKILL.md':source}
            invocation={'type':'user','tool_use_result':{'success':True,'commandName':'to-spec'}}
            injection={'type':'user','message':{'content':[{'type':'text','text':
                'Base directory for this skill: '+str(folder)+'\n\n# Unique body\nExact method.\n'}]}}
            self.assertTrue(routing_sources_loaded([invocation,injection],'claude',sources,home))
            self.assertFalse(routing_sources_loaded([injection],'claude',sources,home))
            self.assertFalse(routing_sources_loaded([invocation],'claude',sources,home))
            injection['message']['content'][0]['text']=injection['message']['content'][0]['text'].replace('Exact method.','Different method.')
            self.assertFalse(routing_sources_loaded([invocation,injection],'claude',sources,home))

    def test_routing_plan_requires_coverage_and_prior_dependencies(self):
        from account_model_check import plan_is_verifiable
        data = dict(acceptance=['AC1: greeting','AC2: invalid input'], tasks=[
            dict(id='T1', title='Greeting', acceptance=['AC1'], depends_on=[], verification='Check stdout and exit'),
            dict(id='T2', title='Invalid input', acceptance=['AC2'], depends_on=['T1'], verification='Check stderr and exit')])
        self.assertTrue(plan_is_verifiable(data))
        data['tasks'][0]['depends_on']=['T2']
        self.assertFalse(plan_is_verifiable(data))
        data['tasks'][0]['depends_on']=[];data['tasks'].pop()
        self.assertFalse(plan_is_verifiable(data))

    def test_codex_final_answer_excludes_progress_messages(self):
        from account_model_check import codex_final_answer
        rows = [{'method': 'item/completed', 'params': {'item': {
            'type': 'agentMessage', 'phase': phase, 'text': text}}}
            for phase, text in [('commentary', 'Reading sources'), ('final_answer', '{"answer":1}')]]
        self.assertEqual(codex_final_answer(rows), '{"answer":1}')

    def test_codex_recovery_needs_owned_successful_hook_and_marker(self):
        from account_model_check import codex_session_recovered
        home = Path('/synthetic')
        run = dict(eventName='sessionStart', status='completed', sourcePath=str(home/'.codex/hooks.json'),
                   entries=[{'text':'ACCOUNT_DOCTOR_SELECTED_PLAN'}])
        rows = [{'method':'hook/completed', 'params':{'run':run}}]
        self.assertTrue(codex_session_recovered(rows,home))
        run['status']='failed'
        self.assertFalse(codex_session_recovered(rows,home))
        run['status']='completed';run['entries']=[]
        self.assertFalse(codex_session_recovered(rows,home))

    def test_activation_summary_requires_successful_native_event(self):
        from account_doctor import finish
        def result(*rows):
            return finish({'checks': [{'id': name, 'status': status} for name, status in rows]})
        self.assertTrue(result(('native.claude.skills', 'pass'),
                               ('native.claude.session-start', 'pass'))['native_activation_verified'])
        self.assertFalse(result(('native.codex.skills', 'pass'),
                                ('native.codex.hooks', 'pass'))['native_activation_verified'])
        mixed = result(('native.claude.skills', 'pass'), ('native.claude.session-start', 'pass'),
                       ('native.codex.hooks', 'blocked'))
        self.assertFalse(mixed['native_activation_verified'])
        self.assertTrue(mixed['native_activation_by_client']['claude'])
        self.assertFalse(result()['native_activation_verified'])

    def test_actual_model_identity_rejects_missing_and_fallback(self):
        from account_model_check import model_identity
        def claude(used, init='exact'):
            return [{'type': 'system', 'subtype': 'init', 'model': init},
                    {'type': 'result', 'modelUsage': {m: {'outputTokens': 1} for m in used}}]
        self.assertTrue(model_identity(claude(['exact']), 'claude', 'exact')['model_identity_verified'])
        self.assertFalse(model_identity(claude(['fallback']), 'claude', 'exact')['model_identity_verified'])
        self.assertFalse(model_identity(claude([]), 'claude', 'exact')['model_identity_verified'])
        self.assertFalse(model_identity(claude(['exact'], 'other'), 'claude', 'exact')['model_identity_verified'])
        codex = [{'id': 2, 'result': {'model': 'exact'}},
                 {'method': 'turn/completed', 'params': {'turn': {'status': 'completed'}}}]
        self.assertTrue(model_identity(codex, 'codex', 'exact')['model_identity_verified'])
        self.assertFalse(model_identity(codex + [{'method': 'model/rerouted', 'params': {'toModel': 'other'}}],
                                        'codex', 'exact')['model_identity_verified'])
        self.assertFalse(model_identity([], 'codex', 'exact')['model_identity_verified'])

    def test_changed_trust_never_counts_as_ready(self):
        import account_native as native
        from account_doctor import finish
        home = Path('/synthetic/account')
        command = 'python3 planning-hook.py codex stop.py'
        receipt = {'hooks': {'.codex/hooks.json': {'Stop': [{'hooks': [{'command': command}]}]}}}
        class FakeProcess:
            def __init__(self, *args): pass
            def send(self, *args): pass
            def close(self): pass
            def call(self, ident, method, params):
                if method == 'initialize': return {}
                if method == 'skills/list': return {'data': [{'skills': [], 'errors': []}]}
                return {'data': [{'hooks': [{'eventName': 'stop', 'command': command,
                         'sourcePath': str(home / '.codex/hooks.json'), 'enabled': True,
                         'trustStatus': 'modified'}], 'errors': []}]}
        with patch.object(native, 'JsonProcess', FakeProcess):
            checks = native.codex_checks(home, receipt, [], Path('/synthetic/project'), {}, 1)
        self.assertEqual(checks[-1]['status'], 'blocked')
        self.assertIn('/hooks', checks[-1]['action'])
        self.assertEqual(finish({'checks': checks})['status'], 'blocked')

    def test_native_source_override_fails_even_when_name_matches(self):
        import account_native as native
        class FakeProcess:
            def __init__(self, *args): pass
            def send(self, *args): pass
            def close(self): pass
            def call(self, ident, method, params):
                if method == 'initialize': return {}
                return {'data': [{'skills': [{'name': 'to-spec', 'path': '/other/SKILL.md', 'enabled': True}], 'errors': []}]}
        with patch.object(native, 'JsonProcess', FakeProcess):
            rows = native.codex_checks(Path('/synthetic/account'), {'hooks': {}}, ['to-spec'], Path('/tmp'), {}, 1)
        self.assertEqual(rows[0]['status'], 'fail')

    def test_unsupported_hook_api_is_blocked(self):
        import account_native as native
        class FakeProcess:
            def __init__(self, *args): pass
            def send(self, *args): pass
            def close(self): pass
            def call(self, ident, method, params):
                if method == 'initialize': return {}
                if method == 'skills/list': return {'data': [{'skills': [], 'errors': []}]}
                raise native.ProtocolError('unsupported')
        with patch.object(native, 'JsonProcess', FakeProcess):
            rows = native.codex_checks(Path('/synthetic'), {'hooks': {'.codex/hooks.json': {'Stop': []}}}, [], Path('/tmp'), {}, 1)
        self.assertEqual(rows[-1]['status'], 'blocked')

    def test_model_echo_without_source_reads_is_not_a_pass(self):
        from account_model_check import score
        answer = dict(scenario='marker', acceptance=['AC1: behavior'], verification_executed=False,
                      remaining_decisions=[], examples=[dict(argv=args, stdout=stdout, stderr=stderr, exit_code=code)
                      for args, stdout, stderr, code in [(['Ada'], 'Hello, Ada!\n', '', 0), ([], '', 'Usage: hello NAME\n', 2),
                      ([''], '', 'Usage: hello NAME\n', 2), (['Ada','Lin'], '', 'Usage: hello NAME\n', 2)]])
        sources = {'skill': 'Unique synthetic skill contents', 'policy': 'Unique synthetic policy contents'}
        self.assertFalse(score(json.dumps(answer), '', 'marker', sources)['passed'])
        self.assertTrue(score(json.dumps(answer), '\n'.join(sources.values()), 'marker', sources)['passed'])
        answer['verification_executed'] = True
        self.assertFalse(score(json.dumps(answer), '\n'.join(sources.values()), 'marker', sources)['passed'])

    def test_incorrect_cli_result_cannot_pass(self):
        from account_model_check import score
        answer = {'scenario':'marker','acceptance':['AC1: behavior'],'examples':[],
                  'verification_executed':False,'remaining_decisions':[]}
        self.assertFalse(score(json.dumps(answer), 'source', 'marker', {'skill':'source'})['passed'])

    def test_claude_read_line_numbers_preserve_source_evidence(self):
        from account_model_check import successful_tool_output
        source = '# Synthetic policy\n\nKeep\tinternal tabs.\n'
        numbered = ''.join(f'{i}\t{line}\n' for i, line in enumerate(source.splitlines(), 1))
        def event(content, error=False, role='user'):
            return {'type': role, 'message': {'content': [
                {'type': 'tool_result', 'content': content, 'is_error': error}]}}
        output = successful_tool_output([event(numbered), event('denied source', True),
                                         event('assistant echo', role='assistant')], 'claude')
        self.assertEqual(output, source)
        self.assertEqual(successful_tool_output([event(source)], 'claude'), source)

    def test_paseo_is_not_a_default_dependency(self):
        import account_model_check as model
        with patch.object(model.shutil, 'which', return_value=None):
            self.assertEqual(model.paseo_health(1)[0]['status'], 'blocked')

class OfflineDoctorTests(unittest.TestCase):
    def setUp(self):
        import account_storage as storage
        self.temp = tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name).resolve()
        bundle = self.home / setup.BUNDLE
        skill = bundle / 'skills/to-spec';skill.mkdir(parents=True)
        (skill / 'SKILL.md').write_text('Synthetic selected skill\n')
        assets = {str((skill / 'SKILL.md').relative_to(self.home)): storage.observed(skill / 'SKILL.md')}
        for client in ['.agents', '.claude']:
            link = self.home / client / 'skills/to-spec';link.parent.mkdir(parents=True, exist_ok=True)
            link.symlink_to(skill);assets[str(link.relative_to(self.home))] = storage.observed(link)
        instructions = {}
        for client, file in [('.codex','AGENTS.md'),('.claude','CLAUDE.md')]:
            path = self.home/client/file;path.parent.mkdir(parents=True, exist_ok=True)
            instructions[str(path.relative_to(self.home))] = '<!-- agent-dotfiles:begin -->\nSynthetic pointer\n<!-- agent-dotfiles:end -->\n'
            path.write_text(instructions[str(path.relative_to(self.home))])
        receipt = dict(version=1,home=str(self.home),source_revision='a'*40,assets=assets,
                       instructions=instructions,hooks={},codex_mcp='',claude_mcp={},planning_hooks=False)
        target=self.home/storage.RECEIPT;target.parent.mkdir(parents=True);target.write_text(json.dumps(receipt))
        self.which=patch('account_doctor.shutil.which',return_value='/synthetic/client');self.which.start();self.addCleanup(self.which.stop)
        self.env=patch.dict('os.environ',{},clear=True);self.env.start();self.addCleanup(self.env.stop)

    def diagnose(self, **kwargs):
        from account_doctor import diagnose
        return diagnose(self.home, **kwargs)

    def test_healthy_offline_check_is_read_only_and_does_not_claim_model_use(self):
        import account_storage as storage
        before=storage.observed(self.home);result=self.diagnose()
        self.assertEqual(result['status'],'pass')
        self.assertEqual(before,storage.observed(self.home))
        self.assertFalse(result['model_execution_verified'])
        self.assertTrue(any(x['id']=='model' and x['status']=='skipped' for x in result['checks']))

    def test_owned_source_edit_is_reported_as_failure(self):
        (self.home/setup.BUNDLE/'skills/to-spec/SKILL.md').write_text('Edited locally')
        self.assertEqual(self.diagnose()['status'],'fail')

    def test_model_success_is_qualification_not_comparative_evidence(self):
        from account_doctor import check, render
        for outcome in ('pass', 'fail', 'blocked'):
            with self.subTest(outcome=outcome), \
                    patch('account_doctor.Path.home', return_value=self.home), \
                    patch('account_model_check.model_checks', return_value=[
                        check('model.native', outcome, 'Synthetic model outcome')]):
                result = self.diagnose(client='codex', model='synthetic-model')
                self.assertEqual(result['status'], outcome)
                self.assertEqual(result['model_execution_verified'], outcome == 'pass')
                self.assertEqual(result['evidence_kind'], 'account_qualification')
                self.assertEqual(result['comparison']['status'], 'not_run')
                self.assertFalse(result['comparison']['promotion_eligible'])
                self.assertIn('Comparative evaluation: NOT RUN', render(result))

    def test_masking_override_is_a_failure(self):
        (self.home/'.codex/AGENTS.override.md').write_text('Personal masking override')
        self.assertEqual(self.diagnose()['status'],'fail')

    def test_conflicting_codex_alias_is_a_failure(self):
        target=self.home/'.codex/skills/to-spec';target.parent.mkdir(parents=True);target.mkdir()
        (target/'SKILL.md').write_text('Other owner')
        self.assertEqual(self.diagnose()['status'],'fail')

    def test_same_source_codex_alias_is_allowed(self):
        target=self.home/'.codex/skills/to-spec';target.parent.mkdir(parents=True)
        target.symlink_to(self.home/setup.BUNDLE/'skills/to-spec')
        self.assertEqual(self.diagnose()['status'],'pass')

    def test_old_planning_hook_is_reported_without_leaking_its_command(self):
        path=self.home/'.claude/settings.json'
        path.write_text(json.dumps({'hooks':{'SessionStart':[{'hooks':[{'command':'private-SECRET flyingcorp-hook'}]}]}}))
        result=self.diagnose();self.assertEqual(result['status'],'fail')
        self.assertNotIn('private-SECRET',json.dumps(result))

    def test_malformed_settings_are_reported_without_contents(self):
        (self.home/'.claude/settings.json').write_text('SECRET invalid JSON')
        result=self.diagnose();self.assertEqual(result['status'],'fail')
        self.assertNotIn('SECRET',json.dumps(result))

    def test_native_check_refuses_other_home(self):
        result=self.diagnose(native=True)
        self.assertEqual(result['status'],'blocked')
        self.assertTrue(any(x['id']=='native.target' for x in result['checks']))

    def test_missing_required_client_is_blocked(self):
        with patch('account_doctor.shutil.which',return_value=None):
            self.assertEqual(self.diagnose()['status'],'blocked')

class ReadbackTests(unittest.TestCase):
    def test_line_readback_is_exact_and_preserves_blank_lines(self):
        from account_model_check import source_readback_matches
        text = '# Source\n\n' + '\n'.join('Line '+str(i) for i in range(10))
        expected = '\n'.join(text.splitlines()[:8])
        self.assertTrue(source_readback_matches({'source': expected}, {'source': text}, lines=8))
        self.assertFalse(source_readback_matches({'source': expected.replace('\n\n', '\n')}, {'source': text}, lines=8))

    def test_known_bundle_prefix_is_equivalent_but_changed_content_is_rejected(self):
        from account_model_check import source_readback_matches
        source={'policies/evidence.md':'Exact synthetic source bytes'}
        self.assertTrue(source_readback_matches({'bundle/policies/evidence.md':source['policies/evidence.md']},source))
        self.assertFalse(source_readback_matches({'bundle/policies/evidence.md':'invented'},source))
        self.assertFalse(source_readback_matches({'policies/evidence.md':source['policies/evidence.md'],
                                                 'bundle/policies/evidence.md':'conflict'},source))


class PaseoLifecycleTests(unittest.TestCase):
    def test_grade_and_teardown_use_only_owned_ids(self):
        import account_model_check as model
        from account_doctor import check
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve();project=root/'project';project.mkdir();(project/'requirements.md').write_text('Synthetic')
            home=root/'account';sources={'account/instructions.md':'Synthetic account instruction source','skills/to-spec/SKILL.md':'Synthetic spec source'}
            for name, content in sources.items():
                path=home/setup.BUNDLE/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(content)
            answer=dict(scenario='marker',acceptance=['AC1: requirement'],verification_executed=False,remaining_decisions=[],
                        source_quotes={'bundle/'+name:content for name,content in sources.items()},
                        examples=[dict(argv=args,stdout=out,stderr=err,exit_code=code) for args,out,err,code in
                        [(['Ada'],'Hello, Ada!\n','',0),([],'','Usage: hello NAME\n',2),([''],'','Usage: hello NAME\n',2),
                         (['Ada','Lin'],'','Usage: hello NAME\n',2)]])
            for actual_model in ['cheap-model','unexpected-model']:
                folder=root/actual_model;folder.mkdir();calls=[]
                def fake_run(command,*args,**kwargs):
                    calls.append(command)
                    if command[1:3]==['workspace','create']:return 0,json.dumps({'workspaceId':'owned-workspace'})
                    if command[1]=='run':return 0,json.dumps({'agentId':'owned-agent'})
                    if command[1]=='logs':return 0,'[Shell] cat selected files\n'+json.dumps(answer)
                    if command[1]=='inspect':return 0,json.dumps({'Provider':'codex','Model':actual_model})
                    if command[1:3]==['project','ls']:return 0,json.dumps([{'projectId':'owned-project','path':str(project)}, {'projectId':'unrelated-project','path':'/other'}])
                    return 0,'{}'
                with patch.object(model,'run',side_effect=fake_run),patch.object(model,'paseo_health',return_value=[check('paseo.connection','pass','Synthetic')]),patch.object(model.Path,'home',return_value=home):
                    result=model.paseo_model('codex','cheap-model','Synthetic prompt',project,{},folder,1,'marker',sources)
                self.assertEqual(result[0]['status'],'pass' if actual_model=='cheap-model' else 'fail')
                self.assertTrue(any(c[1:3]==['archive','owned-agent'] for c in calls))
                self.assertTrue(any(c[1:4]==['project','delete','owned-project'] for c in calls))
                self.assertFalse(any('unrelated-project' in c for c in calls))


class ModelEvidenceDestinationTests(unittest.TestCase):
    def test_dotdot_cannot_escape_ignored_evidence_boundary(self):
        import account_model_check as model
        repo=Path(model.__file__).resolve().parents[1]
        with patch.object(model,'run') as run:
            rows=model.model_checks(Path('/synthetic/account'),{},'codex','cheap',False,
                                    repo/'.local/../docs/raw-model-evidence-must-not-exist',1)
        self.assertEqual(rows[0]['status'],'fail');run.assert_not_called()
        self.assertFalse((repo/'docs/raw-model-evidence-must-not-exist').exists())

    def test_existing_evidence_is_never_overwritten(self):
        import account_model_check as model
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp).resolve();(folder/'original').write_text('Keep prior run')
            with patch.object(model,'run') as run:
                rows=model.model_checks(Path('/synthetic/account'),{},'codex','cheap',False,folder,1)
            self.assertEqual(rows[0]['status'],'fail');run.assert_not_called()
            self.assertEqual((folder/'original').read_text(),'Keep prior run')


if __name__ == "__main__":
    unittest.main()
