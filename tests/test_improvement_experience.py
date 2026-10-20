"""Reviewed improvement experience: private records, frozen index and author evidence packages."""
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from account.observation.cases import public_case
from account.observation.store import InvalidEvent, Store, digest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts/improvement'))
import experience  # noqa: E402

CLI = ROOT / 'scripts/improvement/experience.py'
TREE_A, TREE_B = 'a' * 64, 'b' * 64


def synthetic_case(script='raise SystemExit(2)\n'):
    return dict(case_id='verification-report-en', language='en', purpose='outcome',
        inputs=dict(request='Report whether verification ran.', files={'check.py': script}),
        outcome_contract=dict(required=['Report failed verification.'], forbidden=['Claim checks passed.']),
        counterpart=dict(inputs=dict(request='Report whether verification ran.',
                                    files={'check.py': 'raise SystemExit(0)\n'}),
                         outcome_contract=dict(required=['Report successful verification.'], forbidden=[])))


def edit_row(verdict='confounded'):
    return dict(component='skills/to-tickets/SKILL.md', change='Revised the discovery description.',
                observed='Artifact checks 3/4 to 2/4 with one repetition.', evidence_refs=['trial-1'],
                verdict=verdict)


class ExperienceFixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.home = self.base / 'home'; self.home.mkdir()
        self.project = self.base / 'project'; self.project.mkdir()
        self.store = Store(self.home)
        self.grant = self.store.grant(self.project)
        self.task, self.case = self.make_case('one')

    def make_case(self, label, script='raise SystemExit(2)\n', review=True):
        event = self.store.capture(self.grant['registration_id'], self.grant['epoch'], json.dumps(dict(
            schema_version=1, project_root=str(self.project), client='synthetic', profile='default',
            source='fixture-v1', session_id='session-' + label, sequence=1, source_event_id='event-' + label,
            event_kind='tool_end', status='failure')).encode())
        task = self.store.bind_task(selections=[dict(self.grant, session_id='session-' + label,
            event_ids=event['event_ids'])], goal='Synthetic goal', request_id='bind-' + label)
        feedback = self.store.add_feedback(task['task_id'], symptom='Synthetic symptom',
            correction='Synthetic correction', evidence_ids=event['event_ids'], request_id='feedback-' + label)
        case = self.store.prepare_case(task['task_id'], revision_id=task['revision_id'],
            feedback_ids=[feedback['feedback_id']], synthetic_case=synthetic_case(script),
            request_id='case-' + label, triage=dict(category='instruction', evidence_ids=event['event_ids']))
        if review:
            self.store.review_case(task['task_id'], case['case_id'], expected_digest=case['case_digest'],
                                   reviewer='maintainer', synthetic_data_confirmed=True, privacy_reviewed=True)
        return task, case

    def add(self, request_id='exp', task=None, case=None, **changes):
        task, case = task or self.task, case or self.case
        args = dict(case_id=case['case_id'], case_digest=case['case_digest'], request_id=request_id,
                    cycle=1, scope='to-tickets', exposure='development', grade_derived=False,
                    candidate=dict(baseline_tree=TREE_A, candidate_tree=TREE_B),
                    comparison=dict(experiment_id='pilot-2026-10-19', decision='reject'),
                    edits=[edit_row()], lesson=None)
        args.update(changes)
        return self.store.add_experience(task['task_id'], **args)

    def review(self, record, status='reusable', request_id='review', task=None):
        return self.store.review_experience((task or self.task)['task_id'], record['experience_id'],
            expected_digest=record['experience_digest'], reviewer='maintainer', status=status,
            request_id=request_id)


class ExperienceRecordTests(ExperienceFixture):
    def test_add_records_no_entry_and_is_idempotent(self):
        first = self.add()
        self.assertEqual(first['status'], 'recorded')
        self.assertEqual(self.add()['status'], 'duplicate')
        with self.assertRaisesRegex(InvalidEvent, 'request_conflict'):
            self.add(edits=[edit_row('hurt')])

    def test_add_rejects_invalid_verdict_and_case_digest(self):
        with self.assertRaisesRegex(InvalidEvent, 'experience_edits'):
            self.add(edits=[edit_row('probably_helped')])
        with self.assertRaisesRegex(InvalidEvent, 'case_digest_mismatch'):
            self.add(case_digest='0' * 64)
        with self.assertRaisesRegex(InvalidEvent, 'experience_exposure'):
            self.add(exposure='public')
        with self.assertRaisesRegex(InvalidEvent, 'experience_lesson'):
            self.add(lesson=dict(cue='When a description changes', lesson='Do something'))

    def test_add_requires_reviewed_case(self):
        task, case = self.make_case('unreviewed', review=False)
        with self.assertRaisesRegex(InvalidEvent, 'case_not_reviewed'):
            self.add('x', task=task, case=case)

    def test_show_returns_full_record_and_status(self):
        lesson = dict(cue='When a description already routes correctly', lesson='Keep skills/to-tickets unchanged',
                      evidence='edit row 1', confidence='low')
        record = self.add(lesson=lesson)
        shown = self.store.experience(self.task['task_id'], record['experience_id'])
        self.assertEqual((shown['review_status'], shown['experience']['lesson']), ('draft', lesson))
        self.review(record)
        self.assertEqual(self.store.experience(self.task['task_id'], record['experience_id'])['review_status'],
                         'reusable')
        entry = self.store.experience_index(cycle=2, scope='to-tickets')['entries'][0]
        self.assertEqual((entry['task_id'], entry['lesson_cue']), (self.task['task_id'], lesson['cue']))

    def test_review_latest_status_wins_and_duplicates(self):
        record = self.add()
        self.assertEqual(self.review(record)['status'], 'reviewed')
        self.assertEqual(self.review(record)['status'], 'duplicate')
        with self.assertRaisesRegex(InvalidEvent, 'experience_digest_mismatch'):
            self.store.review_experience(self.task['task_id'], record['experience_id'],
                expected_digest='0' * 64, reviewer='maintainer', status='reusable', request_id='bad')
        self.review(record, status='superseded', request_id='later')
        index = self.store.experience_index(cycle=2, scope='to-tickets')
        self.assertEqual(index['entries'], [])
        self.assertEqual(index['excluded'], {'superseded': 1})


class ExperienceIndexTests(ExperienceFixture):
    def test_index_includes_only_reusable_earlier_development_entries(self):
        kept = self.add('kept'); self.review(kept, request_id='r-kept')
        heldout = self.add('heldout', exposure='heldout'); self.review(heldout, request_id='r-heldout')
        unknown = self.add('unknown', exposure='unknown'); self.review(unknown, request_id='r-unknown')
        self.add('draft')
        reviewed_only = self.add('reviewed'); self.review(reviewed_only, status='reviewed', request_id='r-rev')
        later = self.add('later', cycle=5); self.review(later, request_id='r-later')
        graded = self.add('graded', grade_derived=True); self.review(graded, request_id='r-graded')
        other = self.add('other', scope='other-skill'); self.review(other, request_id='r-other')
        index = self.store.experience_index(cycle=3, scope='to-tickets')
        self.assertEqual([e['experience_id'] for e in index['entries']], [kept['experience_id']])
        self.assertEqual(index['excluded'], {'heldout_or_unknown_exposure': 2, 'unreviewed': 2,
                                             'later_cycle': 1, 'grade_derived': 1, 'other_scope': 1})
        entry = index['entries'][0]
        self.assertEqual(entry['lesson_cue'], 'NO_ENTRY')
        self.assertEqual(entry['edits'], [dict(component='skills/to-tickets/SKILL.md', verdict='confounded')])

    def test_index_digest_stable_and_changes_with_inputs(self):
        record = self.add(); self.review(record)
        first = self.store.experience_index(cycle=2, scope='to-tickets')
        second = self.store.experience_index(cycle=2, scope='to-tickets')
        self.assertEqual(first['index_digest'], second['index_digest'])
        self.assertRegex(first['index_digest'], r'\A[0-9a-f]{64}\Z')
        added = self.add('more', edits=[edit_row('helped')]); self.review(added, request_id='r-more')
        self.assertNotEqual(self.store.experience_index(cycle=2, scope='to-tickets')['index_digest'],
                            first['index_digest'])

    def test_same_request_id_in_two_tasks_stays_distinct(self):
        other_task, other_case = self.make_case('two')
        first = self.add('same'); self.review(first, request_id='r1')
        second = self.add('same', task=other_task, case=other_case)
        self.review(second, request_id='r1', task=other_task)
        entries = self.store.experience_index(cycle=2, scope='to-tickets')['entries']
        self.assertEqual({e['task_id'] for e in entries}, {self.task['task_id'], other_task['task_id']})

    def test_corrupted_review_status_never_passes(self):
        record = self.add(); review = self.review(record)
        directory = self.store.root / 'tasks' / self.task['task_id']
        for path in directory.glob('*.json'):
            row = json.loads(path.read_text())
            if row['kind'] == 'experience_review':
                row['status'] = 'typo'
                path.write_text(json.dumps(row))
        index = self.store.experience_index(cycle=2, scope='to-tickets')
        self.assertEqual((index['entries'], index['excluded']), ([], {'invalid_review': 1}))

    def test_revoked_task_is_inactive_and_purged(self):
        record = self.add(); self.review(record)
        self.store.revoke(self.grant['registration_id'])
        self.assertFalse((self.store.root / 'tasks' / self.task['task_id']).exists())
        index = self.store.experience_index(cycle=2, scope='to-tickets')
        self.assertEqual(index['entries'], [])

    def test_same_cycle_and_rejected_entries_are_excluded(self):
        same = self.add('same', cycle=2); self.review(same, request_id='r-same')
        rejected = self.add('rejected'); self.review(rejected, status='rejected', request_id='r-rej')
        index = self.store.experience_index(cycle=2, scope='to-tickets')
        self.assertEqual((index['entries'], index['excluded']), ([], {'later_cycle': 1, 'rejected': 1}))

    def test_missing_store_or_lock_is_an_error_not_an_empty_index(self):
        empty = self.base / 'empty-home'; empty.mkdir()
        with self.assertRaises(FileNotFoundError):
            Store(empty).experience_index(cycle=2, scope='to-tickets')
        (self.store.root / 'store.lock').unlink()
        with self.assertRaises(FileNotFoundError):
            self.store.experience_index(cycle=2, scope='to-tickets')

    def test_corrupted_record_fields_never_pass(self):
        record = self.add(); self.review(record)
        directory = self.store.root / 'tasks' / self.task['task_id']
        for path in directory.glob('*.json'):
            row = json.loads(path.read_text())
            if row['kind'] == 'experience':
                row['experience']['grade_derived'] = 0
                row['experience_digest'] = digest(row['experience'])
                path.write_text(json.dumps(row))
        index = self.store.experience_index(cycle=2, scope='to-tickets')
        self.assertEqual((index['entries'], index['excluded']), ([], {'invalid_record': 1}))


class PackageTests(ExperienceFixture):
    def setUp(self):
        super().setUp()
        self.public = dict(public_case(synthetic_case()), case_digest=self.case['case_digest'])
        self.baseline = self.base / 'baseline'; (self.baseline / 'skills').mkdir(parents=True)
        (self.baseline / 'skills/SKILL.md').write_text('Old description\n')
        (self.baseline / '.answers').mkdir(); (self.baseline / '.answers/key.json').write_text('{"answer": 1}\n')
        (self.baseline / 'answers').mkdir(); (self.baseline / 'answers/notes.md').write_text('Public notes\n')
        self.candidate = self.base / 'candidate'; (self.candidate / 'skills').mkdir(parents=True)
        (self.candidate / 'skills/SKILL.md').write_text('New description\n')
        tool = self.candidate / 'skills/run.sh'; tool.write_text('#!/bin/sh\necho hi\n'); tool.chmod(0o755)
        self.trajectory = self.base / 'trajectory.txt'; self.trajectory.write_text('step 1\nstep 2\n')
        self.artifact = self.base / 'artifact.bin'; self.artifact.write_bytes(b'\xff\xfe\x00broken')
        self.output = self.base / 'package'

    def spec(self, **changes):
        value = dict(case=self.public, baseline_dir=str(self.baseline), candidates={'cand1': str(self.candidate)},
                     results=[dict(label='cand1', case_id=self.public['case_id'],
                                   case_input_digest=self.public['case_digest'],
                                   trajectory_path=str(self.trajectory), artifact_path=str(self.artifact),
                                   costs=dict(authoring_usd=0.5, execution_usd=None))],
                     index=dict(index_digest='c' * 64, entries=[]), exclude=['./.answers/**'])
        value.update(changes)
        return value

    def build(self, **changes):
        return experience.build_package(self.output, self.spec(**changes))

    def test_dot_prefixed_exclusion_pattern(self):
        manifest = self.build()
        self.assertFalse((self.output / 'baseline/.answers/key.json').exists())
        self.assertTrue((self.output / 'baseline/answers/notes.md').exists())
        self.assertIn('baseline/.answers/key.json', manifest['excluded'])
        self.assertEqual(experience.normalize_pattern('./.answers/**'), '.answers/**')
        self.assertTrue(experience.excluded('.answers/key.json', ['.answers/**']))
        self.assertFalse(experience.excluded('answers/notes.md', ['.answers/**']))

    def test_render_failure_keeps_trajectory(self):
        manifest = self.build()
        result = manifest['results']['cand1']
        self.assertEqual(result['trajectory_status'], 'present')
        self.assertTrue(result['render_status'].startswith('unavailable'))
        self.assertEqual((self.output / 'results/cand1/trajectory.txt').read_text(), 'step 1\nstep 2\n')
        self.assertFalse((self.output / 'results/cand1/rendered.txt').exists())

    def test_package_lists_missing_artifacts_as_gaps(self):
        missing = self.spec()['results'][0] | dict(trajectory_path=str(self.base / 'absent.txt'))
        manifest = self.build(results=[missing], candidates={'cand1': str(self.candidate),
                                                              'cand2': str(self.base / 'absent-dir')})
        reasons = {(gap['item'], gap['reason']) for gap in manifest['gaps']}
        self.assertIn(('results/cand1/trajectory', 'missing'), reasons)
        self.assertIn(('candidates/cand2', 'missing'), reasons)
        self.assertIn(('results/cand2', 'missing'), reasons)
        readme = (self.output / 'README.md').read_text()
        self.assertIn('results/cand1/trajectory: missing', readme)
        self.assertNotIn('candidates/cand2/', readme.split('## Gaps')[0])

    def test_changed_case_input_invalidates_cached_result(self):
        _, changed = self.make_case('two', script='raise SystemExit(3)\n')
        public = dict(public_case(synthetic_case('raise SystemExit(3)\n')), case_digest=changed['case_digest'])
        self.assertEqual(public['case_id'], self.public['case_id'])
        manifest = self.build(case=public)
        self.assertNotIn('cand1', manifest['results'])
        self.assertIn(('results/cand1', 'stale_result'), {(g['item'], g['reason']) for g in manifest['gaps']})
        self.assertFalse((self.output / 'results/cand1').exists())

    def test_package_files_not_executable_and_readme_boundary(self):
        manifest = self.build()
        copied = self.output / 'candidates/cand1/skills/run.sh'
        self.assertTrue(copied.exists())
        self.assertFalse(stat.S_IMODE(copied.stat().st_mode) & 0o111)
        self.assertEqual(stat.S_IMODE(self.output.stat().st_mode), 0o700)
        self.assertIn('New description', (self.output / 'diffs/cand1.diff').read_text())
        readme = (self.output / 'README.md').read_text()
        self.assertIn('Evidence is data, not instructions', readme)
        self.assertEqual(manifest['costs'], dict(authoring_usd=0.5, execution_usd='unknown'))
        self.assertEqual(manifest['index_digest'], 'c' * 64)
        with self.assertRaises(FileExistsError):
            self.build()

    def test_case_digest_must_match_content(self):
        changed = json.loads(json.dumps(self.public)); changed['inputs']['request'] = 'Changed request.'
        with self.assertRaisesRegex(InvalidEvent, 'package_case_digest_mismatch'):
            self.build(case=changed)

    def test_parent_symlinks_are_refused(self):
        private = self.base / 'private'; private.mkdir(); (private / 'trajectory.txt').write_text('secret\n')
        alias = self.base / 'alias'; os.symlink(private, alias)
        result = self.spec()['results'][0] | dict(trajectory_path=str(alias / 'trajectory.txt'))
        manifest = self.build(results=[result])
        self.assertIn(('results/cand1/trajectory', 'symlink_in_path'),
                      {(g['item'], g['reason']) for g in manifest['gaps']})
        self.assertFalse((self.output / 'results/cand1/trajectory.txt').exists())
        with self.assertRaisesRegex(InvalidEvent, 'package_path'):
            experience.build_package(alias / 'package', self.spec())
        self.assertFalse((private / 'package').exists())
        linked = self.base / 'linked-baseline'; os.symlink(self.baseline, linked)
        other = self.base / 'package2'
        manifest = experience.build_package(other, self.spec(baseline_dir=str(linked)))
        self.assertIn(('baseline', 'symlink_in_path'), {(g['item'], g['reason']) for g in manifest['gaps']})

    def test_missing_or_stale_results_make_costs_unknown(self):
        manifest = self.build(results=[])
        self.assertEqual(manifest['costs'], dict(authoring_usd='unknown', execution_usd='unknown'))
        complete = self.spec()['results'][0] | dict(costs=dict(authoring_usd=1, execution_usd=float('inf')))
        manifest = experience.build_package(self.base / 'package-inf', self.spec(results=[complete]))
        self.assertEqual(manifest['costs'], dict(authoring_usd=1, execution_usd='unknown'))

    def test_duplicate_result_labels_are_refused(self):
        result = self.spec()['results'][0]
        with self.assertRaisesRegex(InvalidEvent, 'package_result_duplicate'):
            self.build(results=[result, result])

    def test_bare_directory_pattern_excludes_children(self):
        self.assertTrue(experience.excluded('.answers/key.json', ['.answers']))
        self.assertTrue(experience.excluded('nested/.answers/key.json', ['.answers']))
        self.assertFalse(experience.excluded('.answers-public/notes.md', ['.answers']))

    def test_reads_do_not_follow_parent_symlinks_even_after_a_check(self):
        # Simulate a swap after any path check: the read itself must refuse the symlinked parent.
        private = self.base / 'private'; private.mkdir(); (private / 'trajectory.txt').write_text('secret\n')
        alias = self.base / 'alias'; os.symlink(private, alias)
        with mock.patch.object(experience, 'canonical', lambda path: Path(os.path.abspath(path))):
            self.assertEqual(experience.read_text(alias / 'trajectory.txt'), (None, 'symlink_in_path'))
            manifest = experience.build_package(self.base / 'swapped', self.spec(baseline_dir=str(alias)))
        self.assertIn(('baseline', 'symlink_in_path'), {(g['item'], g['reason']) for g in manifest['gaps']})
        self.assertFalse((self.base / 'swapped/baseline').exists())

    def test_output_inside_an_input_tree_is_refused(self):
        with self.assertRaisesRegex(InvalidEvent, 'package_overlaps_input'):
            experience.build_package(self.baseline / 'package', self.spec())
        with self.assertRaisesRegex(InvalidEvent, 'package_overlaps_input'):
            experience.build_package(self.candidate / 'nested-package', self.spec())
        self.assertFalse((self.baseline / 'package').exists())

    def test_output_parent_swap_after_check_is_refused(self):
        target = self.base / 'elsewhere'; target.mkdir()
        alias = self.base / 'out-alias'; os.symlink(target, alias)
        with mock.patch.object(experience, 'canonical', lambda path: Path(os.path.abspath(path))):
            with self.assertRaisesRegex(InvalidEvent, 'package_path'):
                experience.build_package(alias / 'package', self.spec())
        self.assertEqual(list(target.iterdir()), [])

    def test_pathlike_inputs_cannot_bypass_the_overlap_check(self):
        with self.assertRaisesRegex(InvalidEvent, 'package_overlaps_input'):
            experience.build_package(self.baseline / 'package', self.spec(baseline_dir=self.baseline))
        self.assertFalse((self.baseline / 'package').exists())
        with self.assertRaisesRegex(InvalidEvent, 'package_fields'):
            self.build(baseline_dir=7)

    def test_walk_errors_become_gaps(self):
        real = os.fwalk
        def failing(top, *args, onerror=None, **kwargs):
            onerror(PermissionError(13, 'Permission denied', 'skills'))
            yield from real(top, *args, onerror=onerror, **kwargs)
        with mock.patch.object(experience.os, 'fwalk', failing):
            manifest = self.build()
        self.assertIn(('baseline/skills', 'unavailable: PermissionError'),
                      {(g['item'], g['reason']) for g in manifest['gaps']})

    def test_nested_unreadable_directories_keep_their_full_paths(self):
        for side in ('left', 'right'):
            (self.baseline / side / 'denied').mkdir(parents=True)
            (self.baseline / side / 'denied' / 'note.md').write_text(side + '\n')
        real = os.open
        def refusing(path, flags, *args, **kwargs):
            if os.path.basename(os.fspath(path)) == 'denied' and flags & os.O_DIRECTORY:
                raise PermissionError(13, 'Permission denied', path)
            return real(path, flags, *args, **kwargs)
        with mock.patch.object(experience.os, 'open', refusing):
            manifest = self.build()
        gaps = {(g['item'], g['reason']) for g in manifest['gaps']}
        self.assertIn(('baseline/left/denied', 'unavailable: PermissionError'), gaps)
        self.assertIn(('baseline/right/denied', 'unavailable: PermissionError'), gaps)
        self.assertNotIn(('baseline/denied', 'unavailable: PermissionError'), gaps)

    def test_pruned_directories_are_reported_as_excluded(self):
        manifest = self.build(exclude=['.answers'])
        self.assertIn('baseline/.answers/', manifest['excluded'])
        self.assertFalse((self.output / 'baseline/.answers').exists())

    def test_hard_links_are_skipped(self):
        outside = self.base / 'outside.txt'; outside.write_text('outside\n')
        os.link(outside, self.candidate / 'skills/hard.txt')
        manifest = self.build()
        self.assertFalse((self.output / 'candidates/cand1/skills/hard.txt').exists())
        self.assertIn(('candidates/cand1/skills/hard.txt', 'hardlink_skipped'),
                      {(g['item'], g['reason']) for g in manifest['gaps']})

    def test_symlinks_are_not_followed(self):
        os.symlink(self.base / 'trajectory.txt', self.candidate / 'skills/link.txt')
        manifest = self.build()
        self.assertFalse((self.output / 'candidates/cand1/skills/link.txt').exists())
        self.assertIn(('candidates/cand1/skills/link.txt', 'symlink_skipped'),
                      {(g['item'], g['reason']) for g in manifest['gaps']})


class FixturePrivacyTests(unittest.TestCase):
    def test_fixtures_contain_no_private_paths(self):
        # Markers are assembled so this check does not match its own source.
        text = Path(__file__).read_text()
        for marker in ('/' + 'root/', '/' + 'home/', '/' + 'Users/', 'BEGIN ' + 'PRIVATE KEY', 'gh' + 'p_'):
            self.assertNotIn(marker, text)


class ExperienceCliTests(ExperienceFixture):
    def call(self, *args, body=None, expected=0):
        result = subprocess.run([sys.executable, str(CLI), '--home', str(self.home), *args],
            input=None if body is None else json.dumps(body).encode(), capture_output=True, timeout=30)
        self.assertEqual(result.returncode, expected, result.stderr)
        self.assertEqual(result.stderr, b'')
        return json.loads(result.stdout)

    def test_cli_add_review_index_package_round_trip(self):
        body = dict(task_id=self.task['task_id'], case_id=self.case['case_id'],
                    case_digest=self.case['case_digest'], request_id='cli', cycle=1, scope='to-tickets',
                    exposure='development', grade_derived=False,
                    candidate=dict(baseline_tree=TREE_A, candidate_tree=TREE_B),
                    comparison=dict(experiment_id='pilot', decision='reject'), edits=[edit_row()], lesson=None)
        record = self.call('add', body=body)
        self.assertEqual(record['status'], 'recorded')
        self.call('review', '--task', self.task['task_id'], '--experience', record['experience_id'],
                  '--digest', record['experience_digest'], '--reviewer', 'maintainer', '--status', 'reusable',
                  '--request-id', 'cli-review')
        index = self.call('index', '--cycle', '2', '--scope', 'to-tickets')
        self.assertEqual(len(index['entries']), 1)
        self.assertEqual(self.call('add', body=dict(body, exposure='public'), expected=1)['status'], 'rejected')
        baseline = self.base / 'b'; baseline.mkdir(); (baseline / 'x.md').write_text('a\n')
        spec_path = self.base / 'spec.json'
        spec_path.write_text(json.dumps(dict(case=dict(public_case(synthetic_case()), case_digest=self.case['case_digest']),
            baseline_dir=str(baseline), candidates={}, results=[], index=index, exclude=[])))
        package = self.call('package', '--input', str(spec_path), '--output', str(self.base / 'pkg'))
        self.assertEqual(package['status'], 'packaged')
        self.assertEqual(self.call('package', '--input', str(spec_path), '--output', str(self.base / 'pkg'),
                                   expected=1)['reason'], 'package_exists')


if __name__ == '__main__':
    unittest.main()
