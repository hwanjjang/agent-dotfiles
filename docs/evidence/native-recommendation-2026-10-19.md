# Actual native report recommendation — 2026-10-19

The maintained `promotion.py recommend-native` consumer returned **reject** on
both read-only executions of the same recorded development comparison. It
recomputed the native report, verified the committed baseline/candidate and
complete arm inventories, and returned identical canonical recommendation bytes.
This is actual negative-path engine evidence for
[#28](https://github.com/hwanjjang/agent-dotfiles/issues/28), not completion of the
comparison, a beneficial candidate, held-out evaluation or account deployment.
Independent review and integration are separate delivery gates.

## Recorded inputs and result

The [original comparison checkpoint](https://github.com/hwanjjang/agent-dotfiles/issues/27#issuecomment-6263757170)
retains five reservations, four initial model turns, three passing outcomes, one
failing outcome, one blocked row and three missing rows. The consumer preserves
all eight scheduled rows. No rows, qualification records, source inventories or
unknown usage values were rewritten to obtain a recommendation.

| Binding | Value |
| --- | --- |
| Experiment digest | `a8b52659ca1566229f888e77d1abe42391bd9f8ca47c3ddfca505f238c3cfc0a` |
| Report file SHA-256 | `0696f39fa8b7eee2e5f4e941d00c16c0d2df8d725960fb3a92ed4eb59f44a93b` |
| Report's canonical payload digest | `5f7a157d52f598aecbdcd79b441b45d0b44ac90700ae6811f9d7aac689bf2e40` |
| Baseline commit | `6517621244c23abad72a6d67fc2fbc3973b2f9c0` |
| Candidate commit | `84ae5a779e8ed06a17be6034caf8b9abbcb40d5d` |
| Committed source delta digest | `a905edea5d5b85064434cea76e41bf47882e7532e24152b20e11b0944913f380` |
| Recommendation consumer SHA-256 | `fe0f70f0b179e5340e21ee61278f929c74432f464b02380ff6be0455163ecc75` |
| Recommendation digest | `43575289627ad4b56273d494ad4e09bf669c2377dcf355a885a67ea09254072b` |

The only committed candidate delta is `skills/to-tickets/SKILL.md`. Both arms
contain 23 files across four skill directories and 11 individual policy files.
Source verification inspected the complete 15-root inventories and exact raw
commit/tree/blob objects, including a second source check before returning.

The rule result records one candidate critical violation, zero baseline critical
violations and zero observed routing pass gain. Missing coverage and primary
metric observations remain incomplete. The frozen experiment uses a diagnostic
rule rather than a supported positive-promotion rule; `unsupported_rule` is
retained. The consumer therefore correctly rejects without requiring a held-out
pack. This limited experiment does not establish that the candidate is generally
worse, nor does the zero observed gain establish equivalence.

The returned reasons also preserve `aggregate_execution_incomplete`,
`diagnostic_only`, `explicit_observed_model_projection_unavailable`,
`same_host_heldout_unimplemented` and `same_host_heldout_unverified` from the
existing report/gate contracts. In particular, `same_host_heldout_unimplemented`
is a retained report blocker, not a claim that the optional receipt verifier is
absent from source. No held-out record was supplied. `source_accepted`,
`promotion_eligible`, `merge_authorized`, `install_authorized` and
`backend_identity_verified` are all false.

## Fix and verification

The pre-fix read-only invocation returned `source_verification_failed`. Its
sandbox also lacked the `/dev/null` exception; that collapsed result alone does
not identify the cause. The root check runs before any Git subprocess opens
`/dev/null`, and the regression tests below isolate the eight-root refusal for a
complete 15-root inventory. The fix aligns root capacity with the existing
64-file bound.
Sorted/unique/nonoverlapping roots, complete inventory equality, permitted modes,
source-delta scope, file/byte limits, guarded evidence and Git-read deadlines are
unchanged. The runtime and admission-grader source identities are unchanged;
this recommendation-only fix requires no model requalification.

Two new regression checks first failed at `source_roots`, then passed: a complete
15-root skill/policy inventory, and 64-root acceptance with 65-root refusal. The
15-root check also rejects an omitted policy root. All 32 promotion tests pass.
The actual recommendation command was then executed twice using the exact same
private report, frozen context, five attempt references and committed objects:

```sh
python3 -B scripts/improvement/promotion.py recommend-native < native-review-input.json
```

Both runs completed with exit 0, empty stderr and the recommendation digest above.
The private input object follows the
[documented native input contract](../decisions/promotion-recommendations.md#native-report-and-committed-source-review).
Private paths, task content, answers, authentication and raw records are retained
locally and are not published here. The public bindings permit audit against
those retained inputs; they are not a public reproduction fixture.

On this macOS host, `sandbox-exec` denied all network operations and filesystem
writes, with exact exceptions for `/dev/null` and the six existing reservation/
attempt lock files that the admission reader opens read/write for `flock`.
Those lock files' content and the complete selected source/evidence inventory
were hashed before and after each invocation and remained unchanged. Source,
installation and account paths had no write exceptions. The consumer performed
no native model execution, authentication copy, VM operation, account install,
Git mutation or remote held-out lookup. The outer harness wrote only private
input/output/receipt files.

Initial sandbox harness attempts omitted the reservation lock and then
`/dev/null` from those exceptions. Their refusal results are retained as harness
preparation failures, separate from the actual comparison and the two successful
read-only recommendation executions. They were not counted as candidate trials.
