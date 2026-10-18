"""Bounded synthetic metadata and stdio; never native clients or model calls."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts/improvement'))
import native_trial as trial
import native_trial_plan as plan
import native_trial_protocol as protocol
from test_native_trial_protocol import FakeSession, usage, terminal
import test_native_trial_plan as plan_fixtures


def routing():
    rows = [dict(slot=i, name=name, main_resource=f'skills/{name}/SKILL.md',
                 main_sha256='a'*64, description_sha256='b'*64)
            for i, name in enumerate(('first', 'second', 'third'))]
    return dict(mode='natural', observer='implicit-stderr-json-v1',
                catalog_scope='declared_experiment_subset', catalog_digest=plan.digest(rows), catalog=rows)


def line(event='codex.skill_invocation', **changes):
    fields = {'event.name':event, 'conversation.id':'thread', 'turn.id':'turn',
              'skill.name':'first', 'skill.invocation_type':'implicit',
              'user.id':'PRIVATE_ID', 'arguments':'PRIVATE_ARGS', 'prompt':'PRIVATE_PROMPT'}
    fields.update(changes)
    return (json.dumps(dict(target='codex_otel.log_only', level='INFO', fields=fields), ensure_ascii=False)+'\n').encode()


def drained(**changes):
    return dict(stdout_eof=True, stderr_eof=True, trailing_bytes=0, pending_records=0, process_reaped=True,
                close_mode='graceful_stdin_eof', **changes)


class RoutingTests(unittest.TestCase):
    def observer(self):
        factory = getattr(protocol, 'RoutingObserver', None)
        self.assertIsNotNone(factory, 'Missing bounded native activation projector')
        result = factory(routing(), 'c'*64)
        result.bind('thread', 'turn')
        return result

    def finish(self, observer, ready=True, **changes):
        return observer.finish(ready, drained(**changes))

    def test_successful_implicit_first_page_is_metadata_only(self):
        observer = self.observer()
        observer.feed(line('codex.user_prompt'))
        observer.feed(line())
        result = self.finish(observer)
        self.assertEqual(result['activation'], 'implicit_main_first_page_read')
        self.assertEqual(result['implicit_reads'], [{'slot':0,'count':1}])
        text = json.dumps(result)
        for forbidden in ('PRIVATE_', '"first"', '"thread"', '"turn"', 'SKILL.md', 'arguments'):
            self.assertNotIn(forbidden, text)
        self.assertFalse(result['all_pages_verified'])
        self.assertIsNone(result['transport']['native_written_count'])

    def test_all_chunk_boundaries_and_prebind_events_preserve_projection(self):
        raw = line('codex.user_prompt')+line(**{'user.id':'비밀'})
        for cut in range(len(raw)+1):
            factory = getattr(protocol, 'RoutingObserver', None)
            self.assertIsNotNone(factory)
            observer = factory(routing(), 'c'*64)
            observer.feed(raw[:cut]);observer.feed(raw[cut:]);observer.bind('thread','turn')
            self.assertEqual(self.finish(observer)['implicit_reads'], [{'slot':0,'count':1}])

    def test_healthy_absence_and_incomplete_negative_are_distinct(self):
        observer = self.observer();observer.feed(line('codex.user_prompt'))
        self.assertEqual(self.finish(observer)['activation'], 'observed_none_in_declared_catalog')
        self.assertEqual(self.finish(self.observer())['status'], 'blocked')
        for change in ({'stderr_eof':False},{'stdout_eof':False}, {'trailing_bytes':1},
                       {'process_reaped':False}, {'pending_records':1}):
            observer=self.observer();observer.feed(line('codex.user_prompt'))
            transport=drained();transport.update(change)
            self.assertEqual(observer.finish(True,transport)['activation'],'unknown')
        observer=self.observer();observer.feed(line('codex.user_prompt'))
        self.assertEqual(self.finish(observer,ready=False)['status'],'blocked')

    def test_identity_unknown_explicit_and_duplicate_health_never_pass(self):
        for change in ({'conversation.id':'other'},{'turn.id':'other'},
                       {'skill.name':'unknown'}, {'skill.invocation_type':'explicit'}):
            observer=self.observer();observer.feed(line('codex.user_prompt'));observer.feed(line(**change))
            self.assertEqual(self.finish(observer)['status'],'blocked')
        observer=self.observer();observer.feed(line('codex.user_prompt')*2)
        self.assertEqual(self.finish(observer)['status'],'blocked')

    def test_invalid_frames_limits_and_error_messages_retain_no_private_data(self):
        for raw in (b'{"fields":{},"fields":{"secret":"PRIVATE"}}\n',b'NaN\n',b'[]\n',
                    b'\xff\n',b'{PRIVATE',b'x'*(protocol.FRAME_LIMIT+1),
                    line()*129):
            observer=self.observer();observer.feed(raw)
            result=self.finish(observer)
            self.assertEqual(result['status'],'blocked')
            self.assertNotIn('PRIVATE',json.dumps(result))

    def test_other_records_and_body_success_markers_are_not_activation(self):
        observer=self.observer();observer.feed(line('codex.user_prompt'))
        observer.feed(line('codex.tool_result', success=True, output='codex.skill_invocation'))
        result=self.finish(observer)
        self.assertEqual(result['activation'],'observed_none_in_declared_catalog')
        self.assertEqual(result['implicit_reads'],[])

    def test_model_selection_projection_is_actual_and_mismatch_safe(self):
        options=dict(prompt='SYNTHETIC',project='/synthetic/project',codehome='/synthetic/home/.codex',
                     metadata_check=lambda:{'status':'recognized','compatibility_match':True},
                     soft_total=131072,soft_output=4096)
        good=protocol.observe(FakeSession([usage(),terminal()]),**options)
        self.assertEqual(good.get('model_selection'),dict(requested='gpt-6-luna',
            observed_thread_start='gpt-6-luna',source='thread/start.result.model',match=True,
            backend_identity_verified=False,rerouted=False))
        session=FakeSession([]);session.responses['thread/start']={'model':'PRIVATE_MODEL'}
        bad=protocol.observe(session,**options)
        self.assertEqual(bad['reason'],'selected_model')
        self.assertNotIn('PRIVATE_MODEL',json.dumps(bad))
        self.assertFalse(bad['model_selection']['match'])

    def test_an_unexpected_started_turn_cannot_be_a_completed_negative(self):
        fake=FakeSession([{'method':'turn/started','params':{'threadId':'thread',
                          'turn':{'id':'other'}}},usage(),terminal()])
        result=protocol.observe(fake,prompt='SYNTHETIC',project='/synthetic/project',
            codehome='/synthetic/home/.codex',metadata_check=lambda:{'status':'recognized','compatibility_match':True},
            soft_total=131072,soft_output=4096)
        self.assertEqual(result['status'],'blocked')
        self.assertEqual(result['reason'],'turn_identity')

    def test_reroute_after_terminal_is_not_discarded_during_drain(self):
        observer=self.observer();session=protocol.NativeSession(protocol.CounterArchive(),time.monotonic()+5)
        session.routing=observer
        # Fixed protocol dispatch consumes late notifications through its own state.
        fake=FakeSession([usage(),terminal()]);fake.routing=observer
        result=protocol.observe(fake,prompt='SYNTHETIC',project='/synthetic/project',
            codehome='/synthetic/home/.codex',metadata_check=lambda:{'status':'recognized','compatibility_match':True},
            soft_total=131072,soft_output=4096)
        accept=getattr(protocol,'accept_event',None);self.assertIsNotNone(accept)
        with self.assertRaises(protocol.Refusal):
            accept(fake,{'method':'model/rerouted','params':{}},late=True)
        self.assertFalse(result['model_selection']['rerouted'] is False)
        session.close()

    def test_actual_stdio_close_drains_delayed_stderr_and_both_eofs(self):
        observer=self.observer();session=protocol.NativeSession(protocol.CounterArchive(),time.monotonic()+5)
        session.routing=observer
        raw=line('codex.user_prompt')+line()
        code='import os,sys;sys.stdin.buffer.read();os.write(2,'+repr(raw)+')'
        with tempfile.TemporaryDirectory() as folder:
            session.start([sys.executable,'-I','-S','-c',code],folder,{'PATH':'/usr/bin:/bin'},lambda _:None)
            try: close=session.close()
            finally: session.close()
        self.assertTrue(close['routing_drain']['stderr_eof'])
        self.assertTrue(close['routing_drain']['stdout_eof'])
        self.assertEqual(observer.finish(True,close['routing_drain'])['implicit_reads'],[{'slot':0,'count':1}])

    def test_utf16_and_unknown_transport_fields_do_not_reach_projection(self):
        observer=self.observer();observer.feed(line('codex.user_prompt'))
        observer.feed('{"target":"PRIVATE"}'.encode('utf-16')+b'\n')
        self.assertEqual(self.finish(observer)['status'],'blocked')
        observer=self.observer();observer.feed(line('codex.user_prompt'))
        transport=drained();transport['unexpected']='PRIVATE_TRANSPORT'
        self.assertNotIn('PRIVATE_TRANSPORT',json.dumps(observer.finish(True,transport)))

    def test_late_usage_failure_invalidates_observation_without_another_interrupt(self):
        fake=FakeSession([usage(),terminal()])
        result=protocol.observe(fake,prompt='SYNTHETIC',project='/synthetic/project',
            codehome='/synthetic/home/.codex',metadata_check=lambda:{'status':'recognized','compatibility_match':True},
            soft_total=131072,soft_output=4096)
        with self.assertRaises(protocol.Refusal):protocol.accept_event(fake,usage(200000,5000),late=True)
        self.assertEqual(result['status'],'blocked')
        self.assertFalse(any(m=='turn/interrupt' for m,_ in fake.calls))

    def test_actual_stdio_drain_processes_late_stdout_reroute(self):
        observer=self.observer();fake=FakeSession([usage(),terminal()]);fake.routing=observer
        result=protocol.observe(fake,prompt='SYNTHETIC',project='/synthetic/project',
            codehome='/synthetic/home/.codex',metadata_check=lambda:{'status':'recognized','compatibility_match':True},
            soft_total=131072,soft_output=4096)
        session=protocol.NativeSession(protocol.CounterArchive(),time.monotonic()+5)
        session.routing=observer;session._turn_context=fake._turn_context
        payload=json.dumps({'method':'model/rerouted','params':{}}).encode()+b'\n'
        code='import os,sys;sys.stdin.buffer.read();os.write(1,'+repr(payload)+')'
        with tempfile.TemporaryDirectory() as folder:
            session.start([sys.executable,'-I','-S','-c',code],folder,{'PATH':'/usr/bin:/bin'},lambda _:None)
            session.close()
        self.assertTrue(result['model_selection']['rerouted'])
        self.assertEqual(result['reason'],'model_rerouted')
        self.assertEqual(observer.finish(True,session.close()['routing_drain'])['status'],'blocked')

    def test_natural_prompt_and_temporary_config_do_not_force_skill(self):
        build=getattr(trial,'trial_prompt',None);self.assertIsNotNone(build)
        data={'prompt':'SYNTHETIC_TASK_ONLY','routing':routing(),'inputs':{}}
        self.assertEqual(build(data),'SYNTHETIC_TASK_ONLY')
        forced={'prompt':'SYNTHETIC_TASK_ONLY','inputs':{'entrypoint':'skills/first/SKILL.md'}}
        self.assertIn('First read',build(forced))
        profile=getattr(trial,'routing_profile',None);self.assertIsNotNone(profile)
        config,env=profile(data)
        import tomllib
        parsed=tomllib.loads(config)
        self.assertEqual(env,{'RUST_LOG':'off,codex_otel.log_only=info','LOG_FORMAT':'json'})
        for name in ('exporter','trace_exporter','metrics_exporter'):
            self.assertEqual(parsed['otel'][name],'none')
        self.assertFalse(parsed['otel']['log_user_prompt'])
        self.assertEqual(parsed['otel']['tool_result']['max_bytes'],0)
        self.assertEqual(profile(forced),(trial.DIRECT_PROFILE,{}))


class RoutingPlanTests(unittest.TestCase):
    setUp=plan_fixtures.PlanTests.setUp
    load=plan_fixtures.PlanTests.load
    refused=plan_fixtures.PlanTests.refused

    def natural(self):
        value=copy.deepcopy(self.value);value['schema_version']=2
        value['routing']=routing();value['inputs'].pop('entrypoint')
        for row in value['routing']['catalog']:
            data=f"---\nname: {row['name']}\ndescription: Actual {row['name']} competing method.\n---\nContent\n".encode()
            path=self.inputs/'bundle'/row['main_resource'];path.parent.mkdir(parents=True);path.write_bytes(data)
            row['main_sha256']=hashlib.sha256(data).hexdigest()
            row['description_sha256']=hashlib.sha256(f"Actual {row['name']} competing method.".encode()).hexdigest()
            value['inputs']['files'].append(dict(kind='bundle',path=row['main_resource'],sha256=row['main_sha256']))
        value['routing']['catalog_digest']=plan.digest(value['routing']['catalog'])
        return value

    def test_natural_catalog_is_frozen_without_target_entrypoint(self):
        value=self.natural();selected=self.load(value)
        self.assertEqual(selected.data['routing'],value['routing'])
        self.assertNotIn('entrypoint',selected.data['inputs'])

    def test_incomplete_duplicate_source_or_label_catalog_refuses(self):
        valid=self.natural()
        for change in ('missing','duplicate','description','extra_field','entrypoint'):
            value=copy.deepcopy(valid)
            if change=='missing':value['routing']['catalog'].pop()
            elif change=='duplicate':value['routing']['catalog'][1]['name']='first'
            elif change=='description':value['routing']['catalog'][0]['description_sha256']='f'*64
            elif change=='entrypoint':value['inputs']['entrypoint']='skills/first/SKILL.md'
            else:value['routing']['expected']='first'
            value['routing']['catalog_digest']=plan.digest(value['routing']['catalog'])
            with self.assertRaises(plan.Refusal):self.load(value)
        self.assertEqual(list(self.state.iterdir()),[])

    def test_ambiguous_metadata_or_undeclared_root_skill_refuses(self):
        value=self.natural()
        selected={(row['kind'],row['path']):(self.inputs/row['kind']/row['path']).read_bytes()
                  for row in value['inputs']['files']}
        for change in ('continuation','root_skill','comment','disabled'):
            rows=copy.deepcopy(value['routing']);files=dict(selected)
            row=rows['catalog'][0];key=('bundle',row['main_resource'])
            if change=='root_skill':files['bundle','SKILL.md']=files[key]
            elif change=='disabled':
                data=files[key].replace(b'---\nContent',b'disable-model-invocation: true\n---\nContent')
                files[key]=data;row['main_sha256']=hashlib.sha256(data).hexdigest()
                rows['catalog_digest']=plan.digest(rows['catalog'])
            else:
                data=files[key].replace(b'competing method.\n',b'competing method.\n  continuation\n'
                    if change=='continuation' else b'competing method. # YAML comment\n')
                files[key]=data;row['main_sha256']=hashlib.sha256(data).hexdigest()
                if change=='comment':row['description_sha256']=hashlib.sha256(
                    b'Actual first competing method. # YAML comment').hexdigest()
                rows['catalog_digest']=plan.digest(rows['catalog'])
            with self.subTest(change=change), self.assertRaises(plan.Refusal):
                plan.validate_routing(rows,files)

    def test_schema1_rejects_routing_and_unknown_versions(self):
        value=copy.deepcopy(self.value);value['routing']=routing()
        with self.assertRaises(plan.Refusal):self.load(value)
        value.pop('routing');value['schema_version']=3
        self.refused(value,'plan_version')


class RoutingCollectionTests(unittest.TestCase):
    import test_native_trial_collection as fixtures
    setUp=fixtures.CollectionTests.setUp
    controller=fixtures.CollectionTests.controller
    observer=RoutingTests.observer

    def prepared(self):
        c=self.controller();c.data['routing']=routing()
        observer=self.observer();observer.feed(line('codex.user_prompt'))
        c.live.routing=observer
        c.live.close.side_effect=lambda: {'process_reaped':True,'group_signal_error':None,
                                         'routing_drain':drained()}
        return c

    def test_final_routing_record_is_after_cleanup_and_collection_unchanged(self):
        c=self.prepared();cleanup=c.cleanup();receipt=c.finish(cleanup,None)
        value=receipt['observation']['routing_observation']
        self.assertEqual(value['activation'],'observed_none_in_declared_catalog')
        self.assertEqual(value['transport']['projected_records_written'],1)
        self.assertEqual(receipt['collection']['status'],'captured')
        self.assertFalse(receipt['natural_routing_qualified'])
        self.assertEqual(value['qualification'],'pending')
        _,records=trial.Journal.resume(c.journal.path,c.journal.limit)
        self.assertEqual(records.get('observation_finalized'),[receipt['observation']])

    def test_failed_projection_capture_cannot_pass_or_leak_exception(self):
        c=self.prepared();cleanup=c.cleanup();save=c.journal.save
        def fail(label,*args,**kwargs):
            if label=='routing_observation':raise OSError('PRIVATE_WRITE_ERROR')
            return save(label,*args,**kwargs)
        with patch.object(c.journal,'save',side_effect=fail):receipt=c.finish(cleanup,None)
        self.assertEqual(receipt['status'],'blocked')
        self.assertEqual(receipt['observation']['routing_observation']['activation'],'unknown')
        self.assertNotIn('PRIVATE_WRITE_ERROR',json.dumps(receipt))

    def test_failed_final_snapshot_capture_blocks_receipt(self):
        c=self.prepared();cleanup=c.cleanup();save=c.journal.save
        def fail(label,*args,**kwargs):
            if label=='observation_finalized':raise OSError('PRIVATE_WRITE_ERROR')
            return save(label,*args,**kwargs)
        with patch.object(c.journal,'save',side_effect=fail):receipt=c.finish(cleanup,None)
        self.assertEqual(receipt['status'],'blocked')
        self.assertTrue(receipt['capture_failed'])
        self.assertNotIn('PRIVATE_WRITE_ERROR',json.dumps(receipt))


class ControllerTimingTests(unittest.TestCase):
    setUp = RoutingCollectionTests.setUp
    controller = RoutingCollectionTests.controller
    observer = RoutingCollectionTests.observer
    prepared = RoutingCollectionTests.prepared

    def test_clock_starts_before_controller_initialization(self):
        with patch.object(trial.Controller, 'initialize') as initialize, \
                patch.object(trial.time, 'monotonic_ns', return_value=1000000000):
            c = trial.Controller(None)
        initialize.assert_called_once_with(None)
        self.assertEqual(c.started_ns, 1000000000)

    def test_receipt_measures_controller_time_not_provider_latency(self):
        c = self.prepared(); cleanup = c.cleanup(); c.started_ns = 1000000000
        with patch.object(trial.time, 'monotonic_ns', return_value=3456000000):
            receipt = c.finish(cleanup, None)
        self.assertEqual(receipt['controller_timing'], {'clock':'monotonic_ns',
            'scope':'controller_setup_task_cleanup', 'elapsed_ms':2456})


class RoutingRecoveryTests(unittest.TestCase):
    setUp=plan_fixtures.PlanTests.setUp
    load=plan_fixtures.PlanTests.load
    natural=RoutingPlanTests.natural

    def test_public_schema2_recovery_reads_owned_journal_and_only_cleans(self):
        import os,shutil
        selected=self.load(self.natural());c=trial.Controller(selected);self.addCleanup(c.release)
        c.observation={'status':'blocked','reason':'synthetic_setup_stop'}
        receipt=c.finish({'complete':False},None);self.assertEqual(receipt['status'],'blocked')
        with patch.object(plan,'SOURCE',self.sources),patch.object(plan,'PINNED_RUNTIME',self.pins):
            with self.assertRaisesRegex(plan.Refusal,'^coordinator_running$'):trial.read_recovery(c.attempt)
        c.release();shutil.rmtree(self.inputs)  # Recovery must not reopen task inputs.
        with patch.object(plan,'SOURCE',self.sources),patch.object(plan,'PINNED_RUNTIME',self.pins), \
             patch.object(trial,'supported_host'),patch.object(trial,'copy_native_home') as auth, \
             patch.object(protocol.NativeSession,'start') as start,patch.object(trial,'bounded') as external:
            data,records,journal=trial.read_recovery(c.attempt)
            try:
                self.assertEqual(data['schema_version'],2)
                self.assertEqual(records['observation_finalized'],[receipt['observation']])
                self.assertEqual(records['routing_observation'],[receipt['observation']['routing_observation']])
            finally:os.close(journal.coordinator_lock)
            result=trial.recover(c.attempt)
        self.assertEqual(result,{'status':'reconciled','cleanup_complete':True})
        self.assertFalse(c.control.exists());self.assertTrue((c.attempt/'manifest.json').exists())
        auth.assert_not_called();start.assert_not_called();external.assert_not_called()

    def test_recovery_versions_modes_and_routing_fields_are_closed(self):
        import os
        value=self.natural();selected=self.load(value);c=trial.Controller(selected)
        c.release();self.addCleanup(c.release);path=c.attempt/'manifest.json'
        changes=[{'schema_version':v} for v in (True,False,0,3,2.0,'2',None)]
        changes.extend([{'schema_version':1},{'mode':'qualification'},{'routing':None},{'unexpected':True},
            {'routing':dict(value['routing'],unexpected=True)}])
        with patch.object(plan,'SOURCE',self.sources),patch.object(plan,'PINNED_RUNTIME',self.pins):
            for change in changes:
                with self.subTest(change=change):
                    broken=copy.deepcopy(value);broken.update(change);path.write_bytes(plan.encoded(broken))
                    with self.assertRaises(plan.Refusal):trial.read_recovery(c.attempt)
            path.write_bytes(plan.encoded(value));data,_,journal=trial.read_recovery(c.attempt)
            os.close(journal.coordinator_lock);self.assertEqual(data['schema_version'],2)

    def test_public_legacy_and_forced_routed_recovery_stay_cleanup_only(self):
        for version in (1,2):
            value=copy.deepcopy(self.value) if version==1 else self.natural()
            if version==2:
                value['routing']['mode']='forced_entrypoint'
                value['inputs']['entrypoint']='skills/first/SKILL.md'
            value['identity']['attempt_id']=f'recover-version-{version}'
            selected=self.load(value);c=trial.Controller(selected);c.release();self.addCleanup(c.release)
            with patch.object(plan,'SOURCE',self.sources),patch.object(plan,'PINNED_RUNTIME',self.pins), \
                 patch.object(trial,'supported_host'),patch.object(trial,'copy_native_home') as auth, \
                 patch.object(protocol.NativeSession,'start') as start,patch.object(trial,'bounded') as external:
                self.assertEqual(trial.recover(c.attempt),{'status':'reconciled','cleanup_complete':True})
            auth.assert_not_called();start.assert_not_called();external.assert_not_called()


if __name__=='__main__':unittest.main()
