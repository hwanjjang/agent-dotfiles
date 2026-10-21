"""Check the account transaction journal: TLA+ model, real-code conformance and coverage sync.

  run.py NEW_EVIDENCE_DIR   full check; writes result.json and raw tool output there
  run.py --doctor           read-only prerequisite check (Python 3.11+, Java, pinned TLC jar)
  run.py --check-sync       read-only: does the coverage record still describe the code?

Run from the repository root. Exit 0 only when everything matches expectations; 1 for a
failed, blocked or out-of-sync check; 2 for usage errors. Python 3.11+, stdlib only.
"""
import argparse
import ast
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import time
import tokenize
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
MODEL = HERE.parent / 'model'
SKILL = HERE.parent / 'SKILL.md'
JAR_SHA256 = '936a262061c914694dfd669a543be24573c45d5aa0ff20a8b96b23d01e050e88'  # tla2tools.jar v1.7.4
DEFAULT_JAR = ROOT / '.local/tools/tla2tools-1.7.4/tla2tools.jar'
PROPERTIES = ('ChangesAreJournaled', 'NoSpuriousRefusal', 'NoClobber', 'RefusalChangesNothing')


def rel(path):
    try:
        return Path(path).resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return '<outside checkout>'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def jar_path():
    return Path(os.environ.get('VERIFY_TLA2TOOLS_JAR') or DEFAULT_JAR)


def doctor():
    problems, facts = [], {'python': sys.version.split()[0]}
    if sys.version_info < (3, 11):
        problems.append('Python 3.11+ is required (use python3.11, as scripts/setup-account.sh does)')
    java = shutil.which('java')
    if not java:
        problems.append('java is not on PATH (Java 11+; validated with OpenJDK 17)')
    else:
        out = subprocess.run([java, '-version'], capture_output=True, text=True).stderr
        facts['java'] = out.splitlines()[0] if out else 'unknown'
    jar = jar_path()
    if not jar.is_file():
        problems.append(f'TLA+ tools jar missing; download v1.7.4 into {rel(DEFAULT_JAR)} (see SKILL.md)')
    elif sha(jar) != JAR_SHA256:
        problems.append('TLA+ tools jar sha256 differs from the pinned v1.7.4 hash')
    else:
        facts['tla2tools_sha256'] = JAR_SHA256
    return problems, facts


# ---------------------------------------------------------------- coverage sync

def coverage_record():
    text = SKILL.read_text()
    match = re.search(r'<!-- coverage-record -->\s*```json\n(.*?)\n```', text, re.S)
    if not match:
        raise SystemExit('SKILL.md has no coverage record block')
    return json.loads(match.group(1))


def function_hashes(path):
    """sha256 of each top-level function's tokens, ignoring comments and blank lines."""
    source = (ROOT / path).read_text()
    tree = ast.parse(source)
    hashes = {}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            segment = ast.get_source_segment(source, node, padded=True)
            if node.decorator_list:
                segment = '\n'.join(source.splitlines()[node.decorator_list[0].lineno - 1:node.end_lineno])
            tokens = [(t.type, t.string) for t in tokenize.generate_tokens(io.StringIO(segment).readline)
                      if t.type not in (tokenize.COMMENT, tokenize.NL)]
            hashes[node.name] = hashlib.sha256(repr(tokens).encode()).hexdigest()[:16]
    return hashes


def code_references():
    """Every `@code file:line text` in the model must still match that source line."""
    stale = []
    for number, line in enumerate((MODEL / 'AccountTransactions.tla').read_text().splitlines(), 1):
        match = re.search(r'@code (\S+):(\d+) (.*)$', line)
        if not match:
            continue
        path, at, text = match.group(1), int(match.group(2)), match.group(3).strip()
        lines = (ROOT / path).read_text().splitlines()
        if at > len(lines) or lines[at - 1].strip() != text:
            stale.append(f'model line {number}: {path}:{at} no longer reads "{text}"')
    return stale


def within(node, parents, test):
    current = parents.get(node)
    while current is not None:
        if test(current):
            return True
        current = parents.get(current)
    return False


def assumptions():
    """Facts outside account_storage.py that the model relies on."""
    source = (ROOT / 'scripts/setup_account.py').read_text()
    tree = ast.parse(source)
    parents = {child: node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)}
    calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)]
    locked = lambda n: isinstance(n, ast.With) and any(
        isinstance(i.context_expr, ast.Call) and getattr(i.context_expr.func, 'id', '') == 'lock' for i in n.items)
    failed = []
    prepare = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'prepare')
    changes = [n for n in ast.walk(prepare) if isinstance(n, ast.Call) and getattr(n.func, 'id', '') == 'change']
    last = max(changes, key=lambda n: (n.lineno, n.col_offset))
    if not (isinstance(last.args[0], ast.Name) and last.args[0].id == 'RECEIPT'):
        failed.append('prepare no longer emits the receipt as its last change')
    for call in calls:
        if call.func.id == 'rollback' and not within(call, parents, locked):
            failed.append(f'setup_account.py:{call.lineno} calls rollback outside `with lock(...)`')
        if call.func.id == 'transact':
            in_run = within(call, parents, lambda n: isinstance(n, ast.FunctionDef) and n.name == 'run')
            if not in_run:
                failed.append(f'setup_account.py:{call.lineno} calls transact outside run()')
    for call in calls:
        if call.func.id == 'run' and not call.args:
            guarded = within(call, parents, lambda n: isinstance(n, ast.If) and 'args.apply' in ast.unparse(n.test)
                             and call in [c for s in n.body for c in ast.walk(s)])
            if guarded and not within(call, parents, locked):
                failed.append(f'setup_account.py:{call.lineno} applies run() outside `with lock(...)`')
    return failed


DIAGRAM = ROOT / 'docs/architecture/account-transaction-lifecycle.json'


def diagram_drift():
    """The explanatory lifecycle diagram must show exactly the model's journal statuses."""
    if not DIAGRAM.exists():
        return [f'{rel(DIAGRAM)} is missing']
    text = (MODEL / 'AccountTransactions.tla').read_text()
    quoted = lambda name: set(re.findall(r'"([a-z-]+)"', re.search(rf'^{name} ==(.*)$', text, re.M).group(1)))
    statuses = quoted('Accepts') | quoted('Statuses')
    drawn = {state['id'].replace('_', '-') for state in json.loads(DIAGRAM.read_text())['states']}
    return [] if drawn == statuses else [f'diagram states {sorted(drawn)} differ from model statuses {sorted(statuses)}']


def check_sync():
    record = coverage_record()
    reasons = diagram_drift()
    for path, spec in record['covered'].items():
        current = function_hashes(path)
        for name, recorded in spec['functions'].items():
            if name not in current:
                reasons.append(f'{path}: covered function {name} is gone (renamed, moved or split?)')
            elif current[name] != recorded:
                reasons.append(f'{path}: {name} changed since the sync commit')
        for name in sorted(set(current) - set(spec['functions']) - set(spec['excluded'])):
            reasons.append(f'{path}: new function {name} is neither covered nor excluded')
    reasons += code_references()
    reasons += assumptions()
    commits = subprocess.run(['git', 'log', '--oneline', f"{record['sync_commit']}..HEAD", '--', *record['covered'],
                              'scripts/setup_account.py'], cwd=ROOT, capture_output=True, text=True)
    return {'status': 'in-sync' if not reasons else 'out-of-sync', 'sync_commit': record['sync_commit'],
            'reasons': reasons, 'commits_since_sync': commits.stdout.splitlines() if commits.returncode == 0 else ['git log failed']}


# ---------------------------------------------------------------- TLC

def tlc(evidence, label, variant, invariants, coverage=False):
    folder = evidence / 'tlc' / label
    folder.mkdir(parents=True)
    shutil.copy(MODEL / 'AccountTransactions.tla', folder)
    bounds = json.loads((MODEL / 'expectations.json').read_text())['bounds']
    cfg = 'CONSTANTS\n' + ''.join(f'    {k} = {v}\n' for k, v in bounds.items())
    cfg += f'    Variant = "{variant}"\nSPECIFICATION Spec\nINVARIANTS\n' + ''.join(f'    {i}\n' for i in invariants)
    (folder / 'run.cfg').write_text(cfg)
    command = ['java', '-XX:+UseParallelGC', f'-Djava.io.tmpdir={folder / "tmp"}', f'-Duser.home={folder / "home"}',
               '-cp', str(jar_path()), 'tlc2.TLC', '-workers', '1', '-nowarning',
               '-metadir', str(folder / 'states'), '-config', 'run.cfg']
    if coverage:
        command += ['-coverage', '1']
    (folder / 'tmp').mkdir()
    started = time.monotonic()
    proc = subprocess.run(command + ['AccountTransactions.tla'], cwd=folder, capture_output=True, text=True, timeout=600)
    (folder / 'output.txt').write_text(proc.stdout + proc.stderr)
    out = proc.stdout
    result = {'label': label, 'variant': variant, 'invariants': invariants, 'exit': proc.returncode,
              'seconds': round(time.monotonic() - started, 1)}
    violated = re.search(r'Invariant (\w+) is violated', out)
    result['violated'] = violated.group(1) if violated else None
    result['deadlock'] = 'Deadlock reached' in out
    result['clean'] = 'Model checking completed. No error has been found.' in out
    counts = re.search(r'(\d+) states generated, (\d+) distinct states found', out)
    depth = re.search(r'depth of the complete state graph search is (\d+)', out)
    if counts:
        result['states_generated'], result['distinct_states'] = int(counts.group(1)), int(counts.group(2))
    if depth:
        result['depth'] = int(depth.group(1))
    if coverage:
        result['coverage'] = {m.group(1): int(m.group(3)) for m in
                              re.finditer(r'^<(\w+) line \d+.*?>: (\d+):(\d+)$', out, re.M)}
    if violated:
        steps = re.findall(r'^State \d+: <(\w+)', out, re.M)
        result['counterexample'] = steps
    return result


def next_actions():
    text = (MODEL / 'AccountTransactions.tla').read_text()
    body = re.search(r'^Next ==\n(.*?)\n\n', text, re.S | re.M).group(1)
    return re.findall(r'\\/\s*(\w+)', body)


# ---------------------------------------------------------------- full run

def full(evidence):
    expectations = json.loads((MODEL / 'expectations.json').read_text())
    tracked = [MODEL / 'AccountTransactions.tla', MODEL / 'expectations.json', SKILL, HERE / 'run.py',
               HERE / 'conformance.py', ROOT / 'scripts/account_storage.py', ROOT / 'scripts/setup_account.py']
    hashes = {rel(p): sha(p) for p in tracked}
    report = {'started': time.strftime('%Y-%m-%dT%H:%M:%S%z'), 'revision': git('rev-parse', 'HEAD'),
              'worktree_clean': git('status', '--porcelain', '--', *[rel(p) for p in tracked]) == '',
              'sources': hashes, 'checks': {}, 'failures': []}
    problems, facts = doctor()
    report['tools'] = facts
    if problems:
        report['outcome'] = 'blocked'
        report['failures'] = problems
        return report
    fail = report['failures'].append

    base = tlc(evidence, 'base', 'none', ['TypeOK', *PROPERTIES], coverage=True)
    report['checks']['base'] = base
    if not base['clean'] or base['exit'] != 0:
        fail(f"base model: {base['violated'] or 'did not complete'}" + (' (deadlock)' if base['deadlock'] else ''))
    expected = expectations['base']
    for key in ('distinct_states', 'depth'):
        if expected.get(key) is not None and base.get(key) != expected[key]:
            fail(f'base {key} {base.get(key)} differs from the recorded {expected[key]}; update expectations only after review')
    idle = [a for a in next_actions() if base.get('coverage', {}).get(a, 0) == 0]
    report['checks']['vacuity'] = {'actions': next_actions(), 'never_taken': idle}
    if idle or not base.get('coverage'):
        fail(f'actions never taken in the base run: {idle or "coverage missing"}')

    report['checks']['witnesses'] = []
    for witness in expectations['witnesses']:
        result = tlc(evidence, 'witness-' + witness, 'none', ['TypeOK', witness])
        report['checks']['witnesses'].append({k: result.get(k) for k in ('label', 'exit', 'violated', 'counterexample')})
        if result['violated'] != witness or result['exit'] == 0:
            fail(f'witness {witness} was not reached')

    report['checks']['variants'] = []
    for variant in expectations['variants']:
        result = tlc(evidence, 'variant-' + variant['id'], variant['id'], ['TypeOK', variant['expect']])
        report['checks']['variants'].append({k: result.get(k) for k in ('variant', 'exit', 'violated', 'counterexample')})
        if result['violated'] != variant['expect'] or result['exit'] == 0:
            fail(f"variant {variant['id']} did not violate {variant['expect']}")

    proc = subprocess.run([sys.executable, str(HERE / 'conformance.py'), '--json', '--storage', 'scripts/account_storage.py',
                           '--mutations', str(MODEL / 'expectations.json')], cwd=ROOT, capture_output=True, text=True, timeout=900)
    (evidence / 'conformance.json').write_text(proc.stdout + proc.stderr)
    try:
        conformance = json.loads(proc.stdout)
    except json.JSONDecodeError:
        conformance = {'passed': False, 'error': proc.stderr[-2000:]}
    report['checks']['conformance'] = {
        'passed': conformance.get('passed'), 'exit': proc.returncode, 'seconds': conformance.get('seconds'),
        'observation': conformance.get('base', {}).get('wrapped_io_reported_as_refusal'),
        'base': {k: conformance.get('base', {}).get(k) for k in ('cases', 'by_family', 'violations')},
        'mutations': [{k: m[k] for k in ('id', 'expect', 'caught', 'violations')} for m in conformance.get('mutations', [])]}
    if not conformance.get('passed') or proc.returncode != 0:
        fail('conformance: ' + json.dumps(conformance.get('base', {}).get('violations') or conformance.get('error')))

    sync = check_sync()
    report['checks']['sync'] = sync
    if sync['status'] != 'in-sync':
        fail('out-of-sync: ' + '; '.join(sync['reasons']))

    report['sources_unchanged'] = {rel(p): sha(p) for p in tracked} == hashes
    if not report['sources_unchanged']:
        fail('a tracked source changed during the run')
    report['outcome'] = 'passed' if not report['failures'] else 'failed'
    return report


def git(*args):
    proc = subprocess.run(['git', *args], cwd=ROOT, capture_output=True, text=True)
    return proc.stdout.strip() if proc.returncode == 0 else None


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0],
                                     formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    parser.add_argument('evidence', nargs='?', type=Path, help='new evidence directory (must not exist)')
    parser.add_argument('--doctor', action='store_true')
    parser.add_argument('--check-sync', action='store_true')
    args = parser.parse_args(argv)
    if args.doctor:
        problems, facts = doctor()
        print(json.dumps({'ready': not problems, 'problems': problems, **facts}, indent=2))
        return 0 if not problems else 1
    if args.check_sync:
        result = check_sync()
        print(json.dumps(result, indent=2))
        return 0 if result['status'] == 'in-sync' else 1
    if not args.evidence:
        parser.print_usage(sys.stderr)
        return 2
    try:
        args.evidence.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        print(f'Refusing to reuse an existing evidence directory: {args.evidence}', file=sys.stderr)
        return 2
    evidence = args.evidence.resolve()
    started = time.monotonic()
    report = full(evidence)
    report['seconds'] = round(time.monotonic() - started, 1)
    (evidence / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
    print(f"{report['outcome'].upper()} in {report['seconds']} s; evidence {rel(evidence)}/result.json")
    for failure in report['failures']:
        print('  - ' + failure)
    return 0 if report['outcome'] == 'passed' else 1


if __name__ == '__main__':
    sys.exit(main())
