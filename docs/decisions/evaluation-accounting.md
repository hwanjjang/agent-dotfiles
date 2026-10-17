# Deterministic evaluation accounting

Status: offline development comparison implemented; live execution and independent
holdout evaluation remain unavailable. This is the bounded accounting slice of the
[account improvement design](account-improvement-loop.md#comparative-evaluation-contract).
The module does not execute agents, fixtures, traces, shell commands, model calls or
Git/installer actions. It reads JSON on stdin and writes JSON on stdout.

## Usage and frozen contract

Run from a source checkout with Python 3.11 or later:

```sh
python3 scripts/improvement/evaluation.py qualify
python3 scripts/improvement/evaluation.py freeze < spec.json > frozen.json
python3 scripts/improvement/evaluation.py report < report-input.json > report.json
```

`freeze(spec)` accepts exactly `cases`, `checks`, `identities`, `runtime`, `budget`,
`repetitions`, `seed`, `primary_metric`, `regression_margin`, and `promotion_rule`.
`report` input is exactly `experiment` (the frozen output), `current_spec`, and
`completions` (a list). Reuse the saved inventory after interruption; this module
never retries work. Write regrades to a separate artifact, retaining the original.
A fresh grader source hash requires a new frozen experiment and explicitly linked
regrade, not silently relabeling the old report.

- Cases consume the reviewed export v1 whitelist: `case_id`, `language`, `purpose`,
  `inputs`, `outcome_contract`, `counterpart`, `schema_version`, `classification`,
  `artifact_hashes`, `case_digest`. Public inputs are always `development`; a renamed
  public fixture cannot become a holdout. Fixture hashes and the whole export digest
  are recomputed. Case IDs accept the export token alphabet `[A-Za-z0-9_.:@-]`
  at lengths 1–160; file paths use the export limit of 160 Unicode characters,
  not UTF-8 bytes, and reject backslashes and empty, `.` or `..` segments.
  Canonical JSON uses sorted keys, ASCII escapes, compact separators and a final
  newline; file-content hashes use UTF-8 bytes. No private lineage or arbitrary
  export fields are accepted.
- `checks[case_id][reproduction|counterpart]` contains `contract_digest` and a list
  of `criteria`. Each criterion has `id`, `dimension`, `kind`, `target`, `expected`,
  `critical`. Trusted maintainers must review the mapping from the prose contract
  to these executable criteria. A matching hash does not prove semantic coverage.
- Supported kinds are `artifact_sha256` (literal UTF-8 artifact content),
  `value_equals` (typed structured observation), and `verification_claim` (observed
  exit code versus structured claim, optionally requiring an exact expected exit).
  Missing evidence stays inconclusive. Arbitrary prose cannot be judged by these
  checks; it requires another qualified grader. No LLM judge is implemented.
- Dimensions are `outcome`, `routing`, `adherence`, `exposure`, `mcp_static`,
  `mcp_tool`, `mcp_task`. Every case variant needs an outcome criterion. Unobserved
  routing stays inconclusive even when its outcome passes. Value checks measure
  supplied fields; they do not establish authentic native selection.
- `identities` requires SHA-256 strings for `baseline`, `candidate`, `runner`,
  `grader`, `environment`. The grader identity is the hash of `evaluation.py`.
  `runtime` freezes `provider`, `model`, `client`, `adapter`, `reasoning`,
  `tool_versions` (map), and `capabilities` (list). Hashes are consistency checks,
  not custody, attestation or proof of execution.
- `budget` requires nonnegative integer `model_requests` and `tokens`, and positive
  integer `seconds`. Optional `amount` requires `currency`; a dollar cap is not
  mandatory. This module freezes these ceilings but makes no submissions or timing
  enforcement claim. A future qualified runner must enforce the declared ceilings.

Every reproduction and its successful/contrary counterpart is scheduled for both
baseline and candidate, repeated as declared. The seed randomizes arm order within
pairs. The frozen digest covers the complete spec and trial inventory. Trial IDs
and binding digests bind case, contract, arm, repetition and full frozen context.
Any changed current spec or grader source invalidates all corresponding results.

A completion contains exactly `trial_id`, `experiment_digest`, `binding_digest`,
`status`, `model`, `evidence_kind`, `artifacts`, `observations`, `usage`,
`latency_ms`. Status is `completed`, `error`, `timeout`, `blocked`, or `cancelled`.
This version accepts only `evidence_kind: synthetic` for diagnostic grading.
Artifacts map names to literal strings. Observations map criterion targets to JSON
values; a verification observation is `{"exit_code": 2, "claim": "failed"}`.
Claims are `passed`, `failed`, or `unavailable`. Unknown exit code is `null`.
Usage is `null` or `{"input_tokens": 123, "output_tokens": 45}`. Latency is an
integer number of milliseconds or `null`. Unknown usage never becomes zero.

## Report and trust limits

Reports retain every scheduled trial, all submitted completion digests, unknown
or malformed submissions, duplicate completions, paired per-case results, separate
dimension and arm counts, critical failures, missing coverage, latency and known
usage. Duplicate submissions block the trial and retain observable critical
failures; they cannot replace a failed result. Submitted usage, including duplicate
or unassigned submissions, remains in cost accounting. Unknown/missing usage makes
the total unknown; `known_tokens` is only a subtotal. Dollar cost is unobserved.
These aggregates are diagnostics, not significance or non-inferiority estimates.

The grader calibrates its current implementation against known-good, wrong,
subtle artifact error, fabricated success, missing and injected-data examples.
A failed calibration makes grading inconclusive. Calibration covers these closed
operators, not every possible task or an independent safety qualification. Traces
are data and cannot supply grading commands or override the frozen criteria.

`live_eligible` is always false, `promotion` is always inconclusive, and the evidence
kind is `deterministic_development_comparison`. No caller-supplied qualification
boolean, account-doctor report or mock isolation receipt can change those fields.
There is no authenticated real-evidence verifier, qualified native transport or
independent holdout custodian here. Holding grader data in another folder would
not establish custody. No hidden-answer access test or full issue-26 acceptance
is claimed by this slice. The OS isolation pilot remains separately qualified.

The [Anthropic evaluation guidance](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)
(accessed 2026-10-18) distinguishes trials, observable outcomes and grader
calibration. This implementation follows the already accepted repository design;
it introduces no external runtime or new billing framework. See
[test coverage](../../tests/test_improvement_evaluation.py) and the
[implementation](../../scripts/improvement/evaluation.py).
