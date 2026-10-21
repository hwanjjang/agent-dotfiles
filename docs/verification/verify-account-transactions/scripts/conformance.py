"""Drive the real account transaction functions through every kill and I/O-fault point.

Each case builds a synthetic home with the model's three paths (a skill directory replaced by
a link, a settings file and the receipt), applies one transaction, optionally edits a path as
the user, and runs `rollback` until it succeeds or refuses. Faults are injected at the
file-system calls that scripts/account_storage.py makes itself (replace, unlink, symlink, mkdir,
every os.open including directory descriptors, and the capture copies):
  kill  - the call does not happen and the process dies (every later call from the module also
          dies, as `finally` blocks would not run); the lock fd is still closed, as the kernel would
  error - the call raises OSError instead of taking effect
Families: A apply kill x rollback kill; B1 apply error x rollback kill; B2 two apply errors (faults
inside the undo); R rollback kill after a complete apply; D one or two rollback errors; C apply
complete or killed, then a user edit or deletion of each path; E the lock held by another process;
F a real os._exit at each apply step, compared with the simulated kill and then rolled back.
The properties are the model's P1/P2, checked on real files. Python 3.11+, stdlib only.
"""
import argparse
import importlib.util
import itertools
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

PROPERTIES = ('ChangesAreJournaled', 'NoSpuriousRefusal', 'NoClobber', 'RefusalChangesNothing', 'LockRefusal', 'KillFidelity')
SKILL, SETTINGS = '.agents/skills/tdd', '.claude/settings.json'
ORIGINALS = {}


class Killed(BaseException):
    """A process death: not an Exception, so no handler in the code under test catches it."""


def load(path, label):
    spec = importlib.util.spec_from_file_location(f'account_storage_{label}', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Faults:
    """Counts the module's own file-system calls and injects one kill or up to two errors."""

    PATCHED = (('os', 'replace'), ('os', 'unlink'), ('os', 'symlink'), ('os', 'mkdir'), ('os', 'open'),
               ('shutil', 'copytree'), ('shutil', 'copyfile'))

    def __init__(self, storage, kill_at=None, error_at=()):
        self.file = storage.__file__
        self.kill_at, self.error_at = kill_at, set(error_at)
        self.count, self.dead, self.fired = 0, False, set()

    def die(self):
        raise Killed()

    def _wrap(self, name, original):
        def call(*args, **kwargs):
            if sys._getframe(1).f_code.co_filename != self.file:
                return original(*args, **kwargs)
            if self.dead:
                raise Killed()
            self.count += 1
            if self.count == self.kill_at:
                self.dead = True
                self.fired.add(self.count)
                self.die()
            if self.count in self.error_at:
                self.fired.add(self.count)
                raise OSError(5, 'injected I/O error')
            return original(*args, **kwargs)
        return call

    def __enter__(self):
        self.saved = [(mod, attr, getattr(sys.modules[mod], attr)) for mod, attr in self.PATCHED]
        for mod, attr, original in self.saved:
            setattr(sys.modules[mod], attr, self._wrap(attr, original))
        return self

    def __exit__(self, *exc):
        for mod, attr, original in self.saved:
            setattr(sys.modules[mod], attr, original)
        return False


class Case:
    def __init__(self, storage, root, create=True):
        self.s = storage
        self.home = root / 'home'
        if create:
            self._create()
        self.names = [SKILL, SETTINGS, storage.RECEIPT]  # setup_account.prepare order: assets, configs, receipt
        values = {SKILL: {'link': str(self.home / '.agents/agent-dotfiles/bundle/skills/tdd')},
                  SETTINGS: {'data': b'{"theme": "dark"}\n', 'mode': 0o644},
                  storage.RECEIPT: {'data': b'{"version": 1}\n', 'mode': 0o600}}
        # The original fingerprints do not depend on where the home is.
        self.before = {n: self.obs(n) for n in self.names} if create else ORIGINALS[storage.__file__]
        ORIGINALS.setdefault(storage.__file__, self.before)
        self.after = {n: storage.desired(values[n]) for n in self.names}
        self.plan = {'before': dict(self.before), 'after': dict(self.after)}
        self.changes = {n: values[n] for n in self.names}
        self.edited = {}      # name -> observed value the user left
        self.violations = []
        self.wrapped_io = 0   # rollback I/O errors surfaced as ValueError('Unsafe parent ...')

    def _create(self):
        skill = self.home / SKILL
        skill.mkdir(parents=True)
        (skill / 'SKILL.md').write_text('original skill\n')
        settings = self.home / SETTINGS
        settings.parent.mkdir(parents=True)
        settings.write_text('{"theme": "light"}\n')
        os.chmod(settings, 0o644)

    def obs(self, name):
        return self.s.observed(self.home / name)

    def transaction(self):
        found = sorted((self.home / self.s.STATE_DIR / 'transactions').glob('*/journal.json'))
        if not found:
            return None, None
        journal = found[-1]
        return journal.parent.name, json.loads(journal.read_text())['status']

    def snapshot(self):
        ident, status = self.transaction()
        folder = self.home / self.s.STATE_DIR / 'transactions' / (ident or '-')
        journal = (folder / 'journal.json').read_bytes() if ident else None
        return {n: self.obs(n) for n in self.names}, journal, status, self.s.observed(folder / 'displaced-0')

    def portable(self):
        """Path fingerprints with link targets relative to the home, plus journal status and displacement."""
        paths, _, status, displaced = self.snapshot()
        home = str(self.home)
        rel = {n: ({'link': v['link'].replace(home, '~')} if v and 'link' in v else v) for n, v in paths.items()}
        return rel, status, displaced

    def later_edit(self, name):
        return name in self.edited and self.obs(name) not in (self.before[name], self.after[name])

    def fail(self, prop, detail):
        self.violations.append({'property': prop, 'detail': detail})

    def check_journaled(self, when):
        _, status = self.transaction()
        changed = [n for n in self.names if n not in self.edited and self.obs(n) != self.before[n]]
        if changed and status not in ('applied', 'pending', 'recovery-required', 'rolling-back'):
            self.fail('ChangesAreJournaled', f'{when}: {changed} differ from the original while the journal is {status}')

    def apply(self, fault):
        with Faults(self.s, **fault) as f:
            try:
                with self.s.lock(self.home):
                    self.s.transact(self.home, self.plan, self.changes)
                outcome = 'applied'
            except Killed:
                outcome = 'killed'
            except (ValueError, OSError) as error:
                outcome = 'raised:' + type(error).__name__
        self.check_journaled('after apply')
        return outcome, f

    def edit(self, name, how):
        path = self.home / name
        if path.is_symlink() or path.is_file():
            path.unlink()
        elif path.is_dir():
            shutil.rmtree(path)
        if how == 'edit':
            if name == SKILL:
                path.mkdir(parents=True)
                (path / 'user-note.md').write_text('mine\n')
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('user edit\n')
        self.edited[name] = self.obs(name)

    def rollback(self, fault, label):
        ident, status = self.transaction()
        if ident is None:
            return 'no-journal', None
        start, start_journal, start_status, start_displaced = self.snapshot()
        edits = [n for n in self.names if self.later_edit(n)]
        gap_allowed = start_status != 'applied' and start_displaced == self.before[SKILL]
        with Faults(self.s, **fault) as f:
            try:
                with self.s.lock(self.home):
                    self.s.rollback(self.home, ident)
                outcome = 'rolled-back'
            except Killed:
                outcome = 'killed'
            except ValueError as error:
                if isinstance(error.__cause__, OSError):
                    # An I/O error that _below reports as 'Unsafe parent': an error, not a refusal.
                    self.wrapped_io += 1
                    outcome = 'error'
                    self.check_journaled(f'after {label}')
                    return outcome, f
                outcome = 'refused'
                end, end_journal, _, _ = self.snapshot()
                if (end, end_journal) != (start, start_journal):
                    self.fail('RefusalChangesNothing', f'{label}: refused ({error}) after changing {[n for n in self.names if end[n] != start[n]] or "the journal"}')
                if not edits and any(start[n] != self.before[n] for n in self.names):
                    self.fail('NoSpuriousRefusal', f'{label}: refused ({error}) with no later edit while {start_status}')
            except OSError:
                outcome = 'error'
        for name in edits:
            if self.obs(name) != start[name] and not (name == SKILL and start[name] is None and gap_allowed):
                self.fail('NoClobber', f'{label}: changed {name} that held a later edit')
        if outcome == 'rolled-back':
            wrong = [n for n in self.names if n not in self.edited and self.obs(n) != self.before[n]]
            if wrong:
                self.fail('ChangesAreJournaled', f'{label}: rollback finished with {wrong} not restored')
        self.check_journaled(f'after {label}')
        return outcome, f


def run_case(storage, spec):
    """spec: apply fault, optional user edit, faulted first rollback; then fault-free rollbacks."""
    with tempfile.TemporaryDirectory(prefix='fv-case-') as tmp:
        case = Case(storage, Path(tmp))
        apply_outcome, apply_faults = case.apply(spec.get('apply', {}))
        if spec.get('edit'):
            name, how = spec['edit']
            if how == 'delete' and case.obs(name) is None:
                return None
            case.edit(name, how)
        trail = [apply_outcome]
        rb_faults = None
        if spec.get('rollback'):
            outcome, rb_faults = case.rollback(spec['rollback'], 'faulted rollback')
            trail.append(outcome)
        for attempt in range(2):
            outcome, _ = case.rollback({}, f'rollback {attempt + 1}')
            trail.append(outcome)
            if outcome in ('rolled-back', 'refused', 'no-journal'):
                break
        return {'case': spec, 'trail': trail, 'apply_steps': apply_faults.count,
                'fired': {'apply': sorted(apply_faults.fired), 'rollback': sorted(rb_faults.fired) if rb_faults else []},
                'rollback_steps': rb_faults.count if rb_faults else None,
                'wrapped_io': case.wrapped_io, 'violations': case.violations}


def triggered(result, spec):
    """Whether every requested fault point existed in this run (later points are skipped)."""
    if result is None:
        return False
    for phase in ('apply', 'rollback'):
        fault = spec.get(phase) or {}
        wanted = ({fault['kill_at']} if fault.get('kill_at') else set()) | set(fault.get('error_at', ()))
        if set(result['fired'][phase]) != wanted:
            return False
    return True


def families():
    """Yield (family, spec); callers stop a counter when its fault point no longer exists."""
    edits = [(n, how) for n in (SKILL, SETTINGS, 'RECEIPT') for how in ('edit', 'delete')]
    yield 'A', lambda k, j: {'apply': {'kill_at': k}, 'rollback': {'kill_at': j} if j else None}
    yield 'B1', lambda k, j: {'apply': {'error_at': (k,)}, 'rollback': {'kill_at': j} if j else None}
    yield 'B2', lambda k, j: {'apply': {'error_at': (k, k + j)}} if j else None
    yield 'R', lambda k, j: None if j else {'apply': {}, 'rollback': {'kill_at': k}}
    yield 'D', lambda k, j: {'apply': {}, 'rollback': {'error_at': (k,) if not j else (k, k + j)}}
    yield 'C', edits


def enumerate_cases(storage, budget=None):
    results = []
    receipt = storage.RECEIPT
    for family, make in families():
        if family == 'C':
            for k in itertools.count(0):
                stop = False
                for name, how in make:
                    name = receipt if name == 'RECEIPT' else name
                    spec = {'apply': {'kill_at': k} if k else {}, 'edit': (name, how)}
                    result = run_case(storage, spec)
                    if result is None:
                        continue
                    if k and not triggered(result, spec):
                        stop = True
                        break
                    results.append(dict(result, family='C'))
                if stop:
                    break
            continue
        for k in itertools.count(1):
            probe = make(k, 0) or {'apply': {'error_at': (k,)}}
            if not triggered(run_case(storage, probe), probe):
                break  # step k no longer exists
            for j in itertools.count(0):
                spec = make(k, j)
                if spec is None:
                    if j:
                        break
                    continue
                result = run_case(storage, spec)
                if not triggered(result, spec):
                    break
                results.append(dict(result, family=family))
    results.append(dict(lock_contention(storage), family='E'))
    results.extend(dict(r, family='F') for r in real_exits(storage))
    return results


CHILD = """
import importlib.util, os, sys
from pathlib import Path
sys.path.insert(0, sys.argv[3])
import conformance as c
storage = c.load(sys.argv[1], 'child')
case = c.Case(storage, Path(sys.argv[2]))
faults = c.Faults(storage, kill_at=int(sys.argv[4]))
faults.die = lambda: os._exit(0)
with faults:
    with storage.lock(case.home):
        storage.transact(case.home, case.plan, case.changes)
os._exit(3)
"""


def real_exits(storage):
    """Kill a real process with os._exit at each apply step; the state must match the simulated kill."""
    results = []
    for k in itertools.count(1):
        with tempfile.TemporaryDirectory(prefix='fv-exit-') as real, tempfile.TemporaryDirectory(prefix='fv-sim-') as sim:
            code = subprocess.run([sys.executable, '-I', '-c', CHILD, storage.__file__, real,
                                   str(Path(__file__).parent), str(k)], timeout=60).returncode
            if code == 3:
                break  # step k no longer exists
            exited = Case(storage, Path(real), create=False)
            simulated = Case(storage, Path(sim))
            simulated.apply({'kill_at': k})
            left, expected = exited.portable(), simulated.portable()
            if left != expected:
                exited.fail('KillFidelity', f'step {k}: a real exit left {left}, the simulation {expected}')
            exited.check_journaled('after a real exit')
            outcome, _ = exited.rollback({}, 'rollback after a real exit')
            results.append({'case': {'apply': {'exit_at': k}}, 'trail': ['exited', outcome], 'violations': exited.violations})
    return results


def lock_contention(storage):
    """A second process holds the lock: apply and rollback refuse and change nothing."""
    with tempfile.TemporaryDirectory(prefix='fv-lock-') as tmp:
        case = Case(storage, Path(tmp))
        with case.s.lock(case.home):
            ident = case.s.transact(case.home, case.plan, case.changes)
        holder = subprocess.Popen(
            [sys.executable, '-I', '-c',
             'import importlib.util,sys,time\n'
             's=importlib.util.spec_from_file_location("s",sys.argv[1]);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)\n'
             'from pathlib import Path\n'
             'with m.lock(Path(sys.argv[2])):\n print("held",flush=True);sys.stdin.readline()\n',
             storage.__file__, str(case.home)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        try:
            assert holder.stdout.readline().strip() == 'held'
            start = case.snapshot()
            refused = []
            for label, action in (('apply', lambda: case.s.transact(case.home, case.plan, case.changes)),
                                  ('rollback', lambda: case.s.rollback(case.home, ident))):
                try:
                    with case.s.lock(case.home):
                        action()
                    refused.append(False)
                except ValueError as error:
                    refused.append('Another account transaction is active' in str(error))
            if not all(refused) or case.snapshot() != start:
                case.fail('LockRefusal', f'lock held elsewhere: refused={refused}, unchanged={case.snapshot() == start}')
        finally:
            holder.stdin.write('\n')
            holder.stdin.flush()
            holder.wait(timeout=10)
        return {'case': {'lock': 'held by a second process'}, 'trail': ['refused'], 'violations': case.violations}


def mutate(source, mutation, directory):
    text = Path(source).read_text()
    require = text.count(mutation['find'])
    if require != 1:
        raise SystemExit(f"mutation {mutation['id']}: expected one match, found {require}")
    target = Path(directory) / ('account_storage_' + mutation['id'].replace('-', '_') + '.py')
    text = text.replace(mutation['find'], mutation['replace'])
    for find, replace in mutation.get('also', ()):
        if text.count(find) != 1:
            raise SystemExit(f"mutation {mutation['id']}: expected one match for an additional edit")
        text = text.replace(find, replace)
    target.write_text(text)
    return target


def summarize(results):
    found = {}
    for result in results:
        for v in result['violations']:
            found.setdefault(v['property'], []).append({'family': result['family'], 'case': result['case'],
                                                        'trail': result['trail'], 'detail': v['detail']})
    wrapped = [r for r in results if r.get('wrapped_io')]
    return {'wrapped_io_reported_as_refusal': {'cases': len(wrapped), 'example': wrapped[0]['case'] if wrapped else None},
            'cases': len(results), 'by_family': {f: sum(r['family'] == f for r in results) for f in sorted({r['family'] for r in results})},
            'violations': {p: len(v) for p, v in found.items()},
            'examples': {p: v[:3] for p, v in found.items()}}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--storage', default='scripts/account_storage.py', help='module under test (default: %(default)s)')
    parser.add_argument('--mutations', help='expectations.json; also run each paired code mutation')
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args(argv)
    if sys.version_info < (3, 11):
        raise SystemExit('Python 3.11+ is required, as for scripts/setup-account.sh')
    started = time.monotonic()
    base = summarize(enumerate_cases(load(args.storage, 'base')))
    report = {'storage': args.storage, 'base': base, 'base_passed': not base['violations'], 'mutations': []}
    if args.mutations:
        with tempfile.TemporaryDirectory(prefix='fv-mutants-') as tmp:
            for mutation in json.loads(Path(args.mutations).read_text())['variants']:
                code = mutation['code_mutation']
                path = mutate(args.storage, dict(code, id=mutation['id']), tmp)
                result = summarize(enumerate_cases(load(path, mutation['id'].replace('-', '_'))))
                report['mutations'].append({'id': mutation['id'], 'expect': mutation['expect'],
                                            'caught': mutation['expect'] in result['violations'],
                                            'violations': result['violations'], 'cases': result['cases'],
                                            'example': (result['examples'].get(mutation['expect']) or [None])[0]})
    report['seconds'] = round(time.monotonic() - started, 1)
    report['passed'] = report['base_passed'] and all(m['caught'] for m in report['mutations'])
    if args.json:
        print(json.dumps(report, indent=2, default=str))
    else:
        print(f"base: {base['cases']} cases {base['by_family']}, violations {base['violations'] or 'none'}")
        print(f"observation: rollback I/O errors reported as 'Unsafe parent' refusals in {base['wrapped_io_reported_as_refusal']['cases']} cases")
        for m in report['mutations']:
            print(f"mutation {m['id']}: expect {m['expect']} -> {'caught' if m['caught'] else 'MISSED'} {m['violations']}")
        print(f"{'PASS' if report['passed'] else 'FAIL'} in {report['seconds']} s")
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
