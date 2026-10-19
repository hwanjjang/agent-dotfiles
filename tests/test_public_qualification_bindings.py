"""Current maintained proof bindings; synthetic contexts, no native/auth/VM calls."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from scripts.improvement import evaluation as ev, trial_admission as ad
from test_trial_admission import SyntheticAttempts, save

ROOT = Path(__file__).resolve().parents[1]


def record(name):
    path = ROOT / name
    return json.loads(path.read_bytes()) if path.exists() else {}


def current_sources():
    return {name: hashlib.sha256((ad.p.SOURCE / name).read_bytes()).hexdigest()
            for name in ad.p.SOURCE_NAMES}


def qualification_context(root, *, proof_root=ROOT):
    """Synthetic arm/spec only; qualifications are the actual maintained records."""
    fixture = SyntheticAttempts(root)
    execution = record(ad.QUALIFICATIONS['execution'])
    fixture.runtime.update(source_digests=current_sources(),
        runtime_digests=execution['runtime_digests'], image_digest=execution['image_digest'])
    fixture.spec['identities'].update(runner=ev.digest(fixture.runtime['source_digests']),
        environment=ev.digest({k: v for k, v in fixture.runtime.items()
                               if k != 'source_digests'}))
    fixture.experiment = ev.freeze(fixture.spec)
    declaration = next(iter(fixture.context['collection_by_trial'].values()))
    fixture.context.update(experiment_digest=fixture.experiment['experiment_digest'],
        runtime=fixture.runtime,
        collection_by_trial={row['trial_id']: declaration for row in fixture.experiment['trials']},
        qualification_refs={key: {'path': name, 'sha256': hashlib.sha256(
            (proof_root / name).read_bytes()).hexdigest()}
            for key, name in ad.QUALIFICATIONS.items()})
    save(fixture.context_path, fixture.context)
    return fixture


class MaintainedQualificationTests(unittest.TestCase):
    def test_selected_proof_matches_record_and_current_source_gate(self):
        with tempfile.TemporaryDirectory() as folder:
            fixture = qualification_context(Path(folder).resolve())
            context = ad.load_context(fixture.experiment, fixture.spec, fixture.context_path)
            execution = record(ad.QUALIFICATIONS['execution'])
            proof = record('docs/verification/native-qualification-provenance.json')
            self.assertEqual(ad.p.digest(execution['source_digests']),
                             proof.get('provenance', {}).get('runtime13_compact_identity'))
            grading = record(ad.QUALIFICATIONS['grading'])
            self.assertEqual(ev.digest(grading.get('admission_grader_source_digests', {})),
                             proof['provenance']['admission_grader_identity'])
            proof_path = ROOT / 'docs/verification/native-qualification-provenance.json'
            for name in ad.QUALIFICATIONS.values():
                selected = record(name)
                self.assertEqual(selected['source_digests'], execution['source_digests'])
                self.assertEqual(selected['provenance']['sha256'],
                                 hashlib.sha256(proof_path.read_bytes()).hexdigest())
            matches = (execution['source_digests'] == current_sources()
                       and grading.get('admission_grader_source_digests') == ad.native_grader_sources())
            self.assertEqual(context.qualification_error,
                             None if matches else 'qualification_unavailable')
            self.assertTrue(context.guard.check())

    def test_actual_four_case_routing_record_passes_unchanged_reader(self):
        value = record(ad.ROUTING_QUALIFICATION)
        context = SimpleNamespace(data={'runtime': {'source_digests': value.get('source_digests', {})}},
                                  spec={'runtime': {'model': 'gpt-6-luna'}})
        try:
            ad.qualify_routing(value, context)
        except (ValueError, KeyError, TypeError) as error:
            self.fail('Current routing qualification rejected: ' + str(error))

    def test_rehashed_stale_source_record_remains_unqualified(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            proof_root = root / 'proofs'
            for name in ad.QUALIFICATIONS.values():
                value = record(name)
                if name == ad.QUALIFICATIONS['execution']:
                    value['source_digests']['native_trial.py'] = '0' * 64
                save(proof_root / name, value)
            fixture_root = root / 'fixture'; fixture_root.mkdir(mode=0o700)
            fixture = qualification_context(fixture_root, proof_root=proof_root)
            with patch.object(ad, 'ROOT', proof_root):
                context = ad.load_context(fixture.experiment, fixture.spec, fixture.context_path)
            self.assertEqual(context.qualification_error, 'qualification_unavailable')

    def test_missing_or_false_falsification_record_cannot_qualify_routing(self):
        context = SimpleNamespace(data={'runtime': {'source_digests': current_sources()}},
                                  spec={'runtime': {'model': 'gpt-6-luna'}})
        value = record(ad.ROUTING_QUALIFICATION)
        for bad in ({}, {**copy.deepcopy(value), 'falsification': {
                'false_marker_no_activation': False}}):
            with self.subTest(missing=not bad), self.assertRaises(ValueError):
                ad.qualify_routing(bad, context)


if __name__ == '__main__':
    unittest.main()
