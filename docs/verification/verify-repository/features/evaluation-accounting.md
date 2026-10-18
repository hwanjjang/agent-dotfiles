# Offline evaluation accounting

Scenario ID: `evaluation-accounting`.

Run from the repository with Python 3.11+. No credentials, account installation or model service is needed.

1. Run `python3 scripts/improvement/evaluation.py qualify`; expect calibrated closed operators.
2. Run the focused `tests/test_improvement_evaluation.py` checks.
3. Freeze a reviewed development case with its contrary counterpart, both source identities, runtime settings, budgets and repetitions. Retain the resulting inventory.
4. Submit supplied synthetic completions through `report`; inspect each scheduled trial and unknown usage. Missing/duplicate trials must remain visible; changed spec must block them.
5. Verify `live_eligible` is false and promotion remains inconclusive even for positive synthetic evidence.

The [contract](../../../decisions/evaluation-accounting.md) defines exact input fields. Use ignored local files for reports; no trace-supplied commands execute. Browser-check the improvement-eval map entry and inspect the screenshot manual. These checks qualify the offline operator only.

The producer and evaluator are available in the same checkout. Run the real Store
integration checks with `python3 -m unittest discover -s tests -p test_improvement_integration.py`.
Follow the [reviewed case recipe](reviewed-cases.md) to prepare, inspect, review and
export English/Korean development cases. Pass only those exported public files to
`freeze`; review the explicit executable criteria against each prose contract.
The private preview and extra lineage fields must reject as evaluator input.

Inspect `paired_summary`: each scheduled case/variant/repetition has one pair.
Fail→pass is improved, pass→fail regressed, pass/pass both_pass, fail/fail both_fail;
any blocked/inconclusive arm is unresolved. The five counts must sum to
`scheduled_pairs` for overall and every dimension. Inspect the frozen
`primary_metric` dimension separately; outcome success does not imply routing
success. Retain missing, duplicate and failed submissions, and unknown usage.
Changed source identities need a new freeze or explicitly linked regrade.

Earlier pinned-producer/manual runs remain historical. Use the workflow-map
verifier and catalog verifier after status changes. Current integration still
qualifies only offline development accounting, not isolated model execution.

## Trusted offline artifact admission

Read the [admission contract](../../../decisions/evaluation-accounting.md#admit-recorded-native-artifact-snapshots)
for exact input and ownership requirements. Run:

```sh
python3 scripts/improvement/trial_admission.py --help
python3 -m unittest discover -s tests -p 'test_trial_admission.py'
```

The focused tests use synthetic qualification records and native journals. They
exercise artifact digest grading, observed missing versus absent capture, active
ownership locks, helper changes after freeze and during grading, missing composite
qualification mappings, duplicate and distinct attempts, unknown usage and
caller-flag refusal. They do not qualify real authentication or a native runtime.

For a separately retained operator smoke, prepare an owned disposable fixture and
invoke the actual `native_trial_results.py` collector on known correct binary,
wrong and missing files. Connect those actual snapshots to explicitly fake journal
and qualification fixtures, then invoke `trial_admission.py report` using the
contract above. Require pass/fail/fail artifact outcomes, an unsubmitted scheduled
trial remaining inconclusive, and `live_eligible=false`. Submit one attempt twice:
require duplicate coverage with one cumulative usage charge. An arbitrary
qualification flag must reject. Preserve both collector and admission outputs,
unknown totals, and removal of only the owned disposable fixture.

This smoke demonstrates collector/reader/evaluator integration with synthetic
lifecycle evidence, not a real native trial. There is no public one-command fixture
generator; preserve the explicit setup and commands in the verification record.
Actual retained attempts with missing or mismatched current authenticated
qualification must remain blocked. Never rewrite qualification or evidence digests
to obtain a pass. The browser helper checks catalog navigation separately and
does not execute this CLI recipe.

## Serial reservation gate

Follow the [authoritative serial contract](../../../decisions/evaluation-accounting.md#serial-native-launch-reservations)
for `initialize`, `status`, `run-next`, frozen stdin and private-root requirements.
Run `python3 scripts/improvement/trial_reservation.py --help` and
`python3 -m unittest discover -s tests -p 'test_trial_reservation.py'` separately
from the browser helper. Tests use synthetic qualifications, journals and fixed
native-run stubs; they do not establish real native execution or authentication.

In an owned synthetic CLI/process fixture, retain initialization, ordered
reservation and status results, concurrent-lock refusal, wrong-order and extra-field
refusal, and a crash-gap or failed attempt that blocks the next launch. Check that
initial-turn slots and declared phase-time never refund, unknown cost remains
unknown, and an overshoot stops later launches. Audit with omitted completion
references: `execution_accounting` must still include every reserved attempt.
Record actual parser/process results separately from the fixed stub's fake native
facts. There is no public fixture-generator command or caller qualification flag.

The unmodified CLI with current public qualification must refuse initialization
when that qualification is stale; do not rewrite proof to enable a real run.
Require `hard_provider_cap=false`, unknown wire/billing data and
`live_eligible=false`. Preserve original failed attempts and owned cleanup evidence.
These checks verify the cooperating-host gate, not provider hard caps, natural
routing, comparative benefit or account activation.

## Routing, selected-client-model and declared-scope checks

Follow the [routing/model contract](../../../decisions/evaluation-accounting.md#declared-catalog-routing-and-client-model-observations)
and [scope declaration](../../../decisions/evaluation-accounting.md#optional-same-host-scope-declaration).
Run `test_trial_admission.py`, `test_native_cost_projection.py` and
`test_improvement_evaluation.py` with the existing unit-test runner.
For a separate actual offline CLI smoke, use explicitly synthetic qualification
and native journals: require an implicit-read observation to satisfy its routing
criterion, healthy none to fail an expected-read criterion while outcome still
passes, and a tampered qualification record to block. Check finalized-record order,
exact model facts, missing/duplicate/drift rejection and unchanged attempt accounting.
Keep adherence, exposure and MCP dimensions inconclusive when unobserved.

Use `evaluation.py freeze/report` on synthetic scope fixtures to verify the unchanged
development route, accepted declaration, rejected caller self-certification and
pack drift, and blocked stale current scope. Require unverified scope, not-assessed
exposure, null custody, false live eligibility and inconclusive promotion. Do not
generate held-out cases or claim actual model behavior as part of these checks.
Actual routing/model qualification requires a separate source-bound native run;
current public proof is insufficient. No public fixture-generator command exists.

In cost-projection regressions, legacy/routed reroutes, malformed controller clocks
and missing final routing records must retain the bound latest persisted token
subtotal while completeness is false and the next serial launch is blocked.
Source/runtime/manifest/receipt, usage and final guard checks still apply. A late
guarded-evidence change after model completeness must restore the model-unavailable
blocker, reset the selection label and clear copied attempt model claims. Repeated
references to one known or unknown controller clock count as one attempt; distinct
attempts remain separate, and duplicate trial coverage still blocks grading.
