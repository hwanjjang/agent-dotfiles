---
name: swarm
description: Coordinate bounded independent workers for coverage, experiments, or implementation slices and return evidence-backed results.
disable-model-invocation: true
---

# Swarm

Input: scoped work, dependencies, allowed actions, completion criteria, and budget.
Output: consolidated results with exact artifact revisions, checks, and gaps.
Requires host-supported, authorized parallel workers. If unavailable, report the
limitation; sequential execution is acceptable only within the requested method.

## Frame

Choose partitioned coverage, a candidate race, or dependency-aware implementation.
For a race declare first-pass, rank-all, or best-of before starting; use `arena`
when independent judging and synthesis are needed. Do not merge competing versions
as though they were separate implementation slices.

Each brief specifies task ID, scope, inputs and revisions, owned outputs, permitted
actions, acceptance criteria, verification method, and return format. Workers
return PASS, ISSUES, or BLOCKED with evidence. They own their assigned work and
return results rather than delegating again without explicit need and permission.

## Execute

Coverage workers have separate outputs. Implementation workers have separate
branches/worktrees and task records. Establish shared interfaces first, and give
shared files, schemas, migrations, and external mutable resources a single writer
or genuinely isolated instances. Different filenames alone do not prove independence.

Only dispatch tasks whose prerequisites are verified and integrated into the
baseline. Bound concurrency by independent work and available capacity. Refill
free slots as new tasks become ready; avoid unnecessary whole-batch barriers.

## Integrate and verify

One integration writer consumes finished implementation changes serially. Reconcile
with the current baseline, inspect semantic interactions, and rerun affected tests
on the combined revision. Release dependent tasks only after that succeeds.
Coverage reports name the examined revision and requested measurement method.
Drop incomplete evidence, retry within the declared budget, and expose remaining gaps.

On failure, block affected descendants while unrelated tasks continue. Changed
shared contracts invalidate affected evidence. Resume using verified task state;
preserve unresolved work and do not repeat already completed external effects.

Return a concise task/result table, actual participation, findings, missing
coverage, integration revision, and verification. Missing workers or tests never
count as a pass. Completion stops at the authorized endpoint.

Source and local adaptations: [provenance](provenance.json). License: [MIT](LICENSE).
