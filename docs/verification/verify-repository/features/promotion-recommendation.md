# Promotion recommendation

Feature ID: `promotion-recommendation`. Map ID: `improvement-review`.
The [recommendation contract](../../../decisions/promotion-recommendations.md)
owns schemas, source/read limits, frozen rules and authority. Use Python 3.11+,
local Git and disposable synthetic evidence. Existing GitHub CLI is required only
for actual remote anchor checks; those checks neither post comments nor log in.
The optional preflight launch path requires separately authorized native execution.

## PR-01 — legacy diagnostic compatibility

Run `python3 -m unittest discover -s tests -p 'test_improvement_promotion.py'`.
Separately freeze a synthetic development experiment, compare its completions and
invoke `python3 scripts/improvement/promotion.py recommend` with the five documented
fields on stdin. Check recomputation, canonical type tampering, stale identities,
missing coverage, optional currency, per-case regression and by-arm critical counts.
A baseline defect fixed by the candidate remains diagnostic; candidate critical
violations reject. Favorable legacy arithmetic stays operationally inconclusive.

## PR-02 — native committed-source review

Use the existing tests' disposable Git/record fixtures, not fabricated operational
proof. In a separate actual CLI process call `promotion.py recommend-native` with
the documented closed input. Require a recomputed sealed `NativeBatch` report and
exact complete arm inventories from full commit object IDs. Exercise raw invalid
UTF-8 blob bytes, wrong commits/refs, forged reports, outside-root changes,
incomplete selected inventories and unsupported modes. Dirty checkout content
must not become committed source evidence. Test bounded raw process/cap cleanup.

A complete development report without held-out evidence stays inconclusive unless
its frozen rule rejects. Current actual public qualification must stay unavailable;
FAKE qualification or a caller `verified` flag cannot replace it. The source diff
binds tested bytes only: it does not prove an MCP connection or all-client support.

## PR-03 — selected same-host receipts and preflight

Run `python3 -m unittest discover -s tests -p 'test_improvement_heldout.py'`.
In a distinct actual CLI subprocess use the existing synthetic conformance fixtures
with real Git objects, sealed batch reads and serial state. Label qualification,
lifecycle/clock, context/tool receipts and remote metadata **FAKE**. Check:

- Source-bound requirements-only `fork_turns: none`, distinct preparer/author IDs,
  digest-only output and candidate-anchor-before-pack chronology.
- Actual metadata transport contracts through fixed GET only; body/issue/edit
  mismatch and late local drift refuse, transport absence stays inconclusive.
- Exact scheduled attempts and an outside-execution-root preflight receipt,
  created before the first reservation under the existing lease; a missing
  receipt after launches begin cannot be reminted.
- Known author exposure during comparison is exposed; unknown delivery is
  inconclusive; any candidate edit invalidates. Feedback after completion
  reclassifies future reuse without changing the recorded earlier comparison.
- Only eligible development **and** held-out rules can return a bounded
  recommendation. A no-benefit frozen result rejects and stops; do not search
  until it improves. All source/install/merge/backend authority flags stay false.

For an actual pilot, first qualify current sources and freeze the real candidate,
then create the new selected fork-none preparer and remote anchors under the
[existing protocol](../../../decisions/account-improvement-loop.md#same-host-held-out-evaluation).
This recipe does not authorize those operations or claim they ran. Current
conformance establishes neither unseen cases nor actual model performance.

## PR-04 — map, diagram and manual navigation

Regenerate/check both maps, then use both maintained browser recipes. Open
`improvement-review` and follow the source link. Step 5 must distinguish available
source/native/same-host verifier code from pending actual qualifying comparisons.
Read the [source-backed workflow](../../../architecture/native-recommendation-workflow.html)
and [native recommendation walkthrough](../../../manual/native-recommendation.pdf)
with its [editable source](../../../manual/native-recommendation.json).
The [older diagnostic manual](../../../manual/promotion.pdf) remains a legacy
route walkthrough; it is not native/held-out qualification. Render every changed
manual page and inspect actual captures separately from automated browser checks.

## Refusal and evidence scope

Both recommendation CLIs reject malformed/extra top-level input with exit 1 and
a small envelope. Invalid nested evidence can return exit 0 with a full reject
recommendation. Preflight refusal uses exit 2. Inspect the payload, not exit 0 alone.
Retain original failed executions, source hashes, exact commands and synthetic
labels in ignored local evidence. A cwd snapshot proves only that cwd subset;
source inspection separately establishes the recommendation route's lack of model,
merge/install or account actions. The preflight route explicitly delegates one
existing serial launch. No absence-of-hostile-read or complete filesystem audit
is claimed.
