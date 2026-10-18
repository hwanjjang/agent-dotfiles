"""FAKE native lifecycle; actual private journals, serial audit and launch refusal."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from scripts.improvement import trial_admission as ad, trial_reservation as reservation
import test_trial_admission as admission_fixture
from test_trial_reservation import SyntheticSchedule
save = admission_fixture.save


class CostProjectionTests(unittest.TestCase):
    def make(self, routed):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        root=Path(temp.name).resolve()
        factory=admission_fixture.RoutedAttempts if routed else admission_fixture.SyntheticAttempts
        with patch('test_trial_reservation.SyntheticAttempts',factory):schedule=SyntheticSchedule(root)
        for obj,key,value in ((ad,'ROOT',root),(ad.p,'PINNED_RUNTIME',schedule.f.runtime['runtime_digests'])):
            change=patch.object(obj,key,value);change.start();self.addCleanup(change.stop)
        reservation.initialize(schedule.state,schedule.f.experiment,schedule.f.spec,schedule.f.context_path,schedule.plans)
        return schedule

    def corrupt(self, schedule, fault):
        folder=schedule.saved[0]/'records';entries=[]
        latest=json.loads(next(folder.glob('*-usage_snapshot.json')).read_text())
        latest['sequence']=2;latest['total']['totalTokens']=170
        routed='routing' in json.loads(Path(schedule.plans[0]).read_text())
        for path in sorted(folder.iterdir()):
            label=path.name.split('-',1)[1][:-5];value=json.loads(path.read_text())
            terminal=label==('observation_finalized' if routed else 'observation')
            observation=value['observation'] if label=='receipt' else value if terminal else None
            if observation is not None:
                observation['usage']['latest']=copy.deepcopy(latest)
                if fault=='reroute':
                    observation['model_selection']=dict(admission_fixture.RoutedAttempts.model,rerouted=True)
            if label=='receipt' and fault=='clock':value['controller_timing']=dict(clock='wall_clock',scope='controller_setup_task_cleanup',elapsed_ms=5)
            if label=='cleanup':entries.append(('usage_snapshot',latest))
            if not (fault=='missing-final' and label=='observation_finalized' or fault=='missing-route' and label=='routing_observation'):
                entries.append((label,value))
            path.unlink()
        for i,(label,value) in enumerate(entries,1):save(folder/f'{i:03d}-{label}.json',value)

    def test_failed_admission_keeps_persisted_latest_cost_and_blocks_next_launch(self):
        for routed,fault in ((False,'reroute'),(True,'reroute'),(False,'clock'),(True,'clock'),(True,'missing-final'),(True,'missing-route')):
            with self.subTest(routed=routed,fault=fault):
                schedule=self.make(routed);self.corrupt(schedule,fault);f=schedule.f
                with patch.object(ad.nt,'run',side_effect=schedule.run) as native:
                    result=reservation.run_next(schedule.state,f.experiment,f.spec,f.context_path,schedule.plans[0],Path('/synthetic-not-opened/auth'))
                    self.assertEqual(result['known_tokens'],170);self.assertEqual(result['unknown_attempts'],1)
                    self.assertIsNone(result['total_tokens']);self.assertEqual(result['status'],'blocked')
                    with self.assertRaisesRegex(ValueError,'experiment_blocked_or_complete'):
                        reservation.run_next(schedule.state,f.experiment,f.spec,f.context_path,schedule.plans[1],Path('/synthetic-not-opened/auth'))
                    self.assertEqual(native.call_count,1)
                ctx=ad.load_context(f.experiment,f.spec,f.context_path);guard=ad.Guard()
                header=json.loads((schedule.state/reservation.HEADER).read_text())
                fact=ad.read_cost_facts(ctx,header['schedule'][0],guard)
                self.assertEqual(fact['known_tokens'],170);self.assertFalse(fact['complete']);self.assertTrue(guard.check())
                self.assertEqual(header['schedule'][0]['limits']['cleanup_seconds'],45)

    def test_unbound_receipt_or_usage_cannot_create_known_subtotal(self):
        for fault in ('manifest','usage','observation'):
            schedule=self.make(False);f=schedule.f;path=next((schedule.saved[0]/'records').glob('*-receipt.json'))
            value=json.loads(path.read_text())
            if fault=='manifest':value['manifest_digest']='f'*64
            elif fault=='usage':value['observation']['usage']['latest']['total']['totalTokens']=999
            else:
                observed=next((schedule.saved[0]/'records').glob('*-observation.json'))
                first=json.loads(observed.read_text());first['model_requested']='other';save(observed,first)
            save(path,value)
            with patch.object(ad.nt,'run',side_effect=schedule.run):
                result=reservation.run_next(schedule.state,f.experiment,f.spec,f.context_path,schedule.plans[0],Path('/synthetic-not-opened/auth'))
            self.assertEqual(result['known_tokens'],0);self.assertEqual(result['status'],'blocked')
