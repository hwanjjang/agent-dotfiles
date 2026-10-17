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
regrade, not silently relabeling the old report. `freeze` deliberately permits a
historical grader identity so old inventories can be reconstructed and reported
as stale; it does not authorize collecting fresh results under that identity.
For a new collection, use the current `evaluation.py` source hash. Frozen payload
comparison uses canonical JSON bytes, distinguishing booleans, integers and floats.

- Cases consume the provisional export v1 shape from the out-of-tree dependency below: `case_id`, `language`, `purpose`,
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


## Unmerged producer dependency

The export producer is **out of tree and unmerged** in this PR baseline. It belongs
to [PR #35](https://github.com/hwanjjang/agent-dotfiles/pull/35) / issue #24,
not to this consumer. Compatibility is provisional until that prerequisite lands
and an in-tree producer/consumer regression can replace the hand-built contract
fixtures. This PR does not satisfy the full issue #26 dependency or execution gate.

The separate local compatibility run used producer revision
[`5adfbf9a94ae06a3c3d32589eba18d4ce9be1bd1`](https://github.com/hwanjjang/agent-dotfiles/commit/5adfbf9a94ae06a3c3d32589eba18d4ce9be1bd1),
with these SHA-256 identities:

| Producer source at that revision | SHA-256 |
| --- | --- |
| `account/observation/cases.py` | `2dedc5d2abfe7cdf3f6b6c054b534bf24bee0624c72ed46365a46ffa6322d095` |
| `account/observation/files.py` | `bbab8cbee0131350719851a6f3eb126c33037aa9292eec6acad93ab0ac08ce3e` |
| `account/observation/store.py` | `6ffb64d5a6c6ec911601790937ec21646ff06032b5cd93117ee7c5962d13b9bd` |

This source-bound local run is not evidence that the producer exists in this
checkout. Review the linked producer separately; do not infer baseline integration
from the consumer tests or screenshot manual.

The local CLI accepts at most 16 MiB of JSON input and bounds completion count,
but expanded per-completion checks can produce much larger output and memory use.
There is no output-size cap. Keep inputs small and inspect duplicate counts; this
is a local diagnostic command, not a service or arbitrary-input execution endpoint.

## Report and trust limits

Reports retain every scheduled trial, all submitted completion digests, unknown
or malformed submissions, duplicate completions, paired per-case results, separate
dimension and arm counts, critical failures, missing coverage, latency and known
usage. Duplicate submissions block the trial and retain all submitted digests and check
rows. Critical violations count each distinct completion digest once per trial;
resubmitting an identical failing row cannot inflate that count. Distinct failing
completions remain counted, and neither can replace a failed result. Submitted usage, including duplicate
or unassigned submissions, remains in cost accounting. Unknown/missing usage makes
the total unknown; `known_tokens` is only a subtotal. Dollar cost is unobserved.
The `pairs` field contains baseline/candidate rows, not a concordant/discordant
paired tally. That tally remains part of open issue #26. These aggregates are
diagnostics, not significance or non-inferiority estimates.

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
