# Catalog walkthrough

Read the [one-step screenshot walkthrough](catalog.pdf) to inspect a skill in the
repository map. The [editable source](catalog.json) and [actual screenshot](catalog-detail.png)
are maintained together. This is a toolchain example, not a complete client installation manual.

The screenshot was captured from the local generated map on 2026-10-17 using an
isolated Playwright browser, with Screenshot Manual selected. It contains repository
content only. The captured How to use text was compared with the current catalog
entry, and the full detail panel was visible without internal clipping. The PDF was rendered with PDFium and its single page was visually
checked for readable text, screenshot placement, margins, and footer.

After installing the dependencies documented in
[the screenshot manual skill](../../skills/screenshot-manual/SKILL.md), reproduce
from the repository root (write review output locally):

```sh
python3 skills/screenshot-manual/scripts/build_manual.py docs/manual/catalog.json .local/catalog-manual.pdf
python3 skills/screenshot-manual/scripts/render_pages.py .local/catalog-manual.pdf .local/catalog-manual-pages
```

Inspect every rendered page before replacing the maintained PDF. Capture a new
screenshot and update the source when the documented behavior changes; avoid
publishing browser account data or local paths.

## AK SDLC skill map walkthrough

The separate [two-step workflow walkthrough](workflow.pdf) demonstrates stage
selection and an Anytime trigger search. Its [editable source](workflow.json),
[Intent capture](workflow-stage.png) and [Domain Modeling capture](workflow-trigger.png)
are maintained together. It leaves the original catalog walkthrough unchanged.

The `workflow-map` scenario was exercised on 2026-10-17 in isolated Chrome with
Playwright. Captures use the generated workflow digest `ba13e1ae2b80` at a 2x device
scale; each is a direct screenshot of the relevant detail dialog. Source-link assertions
were checked separately. Screenshots contain public repository content only.
Both PDF pages were rendered with PDFium and visually inspected for legibility,
clipping, captions and pagination; text and page count were checked with pypdf.

```sh
python3 skills/screenshot-manual/scripts/build_manual.py docs/manual/workflow.json .local/workflow-manual.pdf
python3 skills/screenshot-manual/scripts/render_pages.py .local/workflow-manual.pdf .local/workflow-manual-pages
```

Re-capture the actual dialogs and inspect every rendered page after a relevant UI
change. The [workflow-map recipe](../verification/verify-repository/features/workflow-map.md)
owns browser expectations; this walkthrough explains user actions.

The account-source additions keep the two captured skill dialogs and their actions
unchanged, so these screenshots retain their recorded historical digest. For the
new Anytime group and communication/execution policies, use the current
[workflow guide](../map/workflow.md) and [account guide](../../account/README.md).
The maintained browser recipe checks the new entries separately; this PDF is not
an account installation manual.

## Account installation guide walkthrough

The [account source walkthrough](account-source.pdf) shows the installation and hook-guide Anytime
entries. The screenshots demonstrate map navigation, not a completed installation. Its [editable source](account-source.json),
[ownership capture](account-source.png) and [hook capture](account-hooks.png)
show actual expanded dialogs captured on 2026-10-17 in isolated Chrome at 2x
device scale. These captures predate the later improvement-loop qualification
details; the illustrated controls, commands and source links remain applicable. The maintained browser
recipe verifies their source links and the distinction between delivery and native
activation. Installation commands remain authoritative in the account guide.

All three account PDF pages were rendered with PDFium and visually checked for
readable text, complete screenshots, margins and captions. Text and page count were checked with
pypdf. Regenerate with the screenshot-manual scripts above, substituting
`account-source.json`; recapture when either documented dialog changes.

The account walkthrough also covers the account-doctor node and its optional
real-model/Paseo path. Its [doctor capture](account-doctor.png) and third page were
recaptured from the generated map; screenshots prove navigation, not a passing
account check. The [account verification recipe](../verification/verify-repository/features/account-verification.md)
owns the behavioral checks.

## Complete English and Korean user guides

The [English guide](user-guide/manual-en.pdf) and [Korean guide](user-guide/manual-ko.pdf)
cover installation, AK SDLC navigation, private synthetic observations, the proposed
eval workflow and recovery in 18 pages each. See the [source and capture notes](user-guide/README.md),
[English editable text](user-guide/manual-en.md) and [Korean editable text](user-guide/manual-ko.md).
The six-step improvement cycle is documented with explicit implemented/planned status
at that capture baseline. See the current native walkthrough below for the later
Claude adapter; comparative model evaluation remains future work.

## Native Claude collection walkthrough

The [two-page walkthrough](native-observation.pdf) covers finding the collection
guide, opting in, verifying callbacks and revoking delivery. Its
[editable source](native-observation.json), [map capture](native-observe.png),
[sanitized native result capture](native-result.png) and
[capture manifest](native-observation-capture.json) are maintained together.

The 2026-10-18 Claude candidate is based on doctor parent `7131b4b`; the manifest binds the runtime and
map sources. The first image shows the actual map; the second is a browser rendering
of selected results from a real disposable Claude 2.1.302 / Haiku 5.5 session, not
a terminal screenshot. Native runtime files match the tested snapshot. Both PDF
pages were rendered and visually checked, with text and page count checked too.
The [native guide](../../account/observation/native.md) owns commands and limits;
the [recipe](../verification/verify-repository/features/native-observation.md)
owns repeatable verification. No real-account collection was activated by this guide.

## Codex and platform coverage walkthrough

For current qualification status, use the
[native platform matrix](../../account/observation/native.md#native-platform-evidence--2026-10-18).
It owns source revisions, actual coverage, cleanup and unresolved gaps. The PDFs
below retain their original evidence boundaries; a later status update does not
requalify or rewrite their captures.

The [three-page Codex walkthrough](codex-observation.pdf) follows the existing
`native-observation` scenario: select one client, review native trust, inspect
actual results and retain platform blockers. Its [editable source](codex-observation.json),
[map capture at its capture revision](codex-observe.png), [macOS results](codex-native-result.png),
[Linux matrix](linux-observation-result.png) and [capture manifest](codex-observation-capture.json)
are maintained together. The two result images are browser renderings of selected
actual qualification evidence, not terminal captures. The macOS result is a fresh
corrected parent-native runtime run, before later capacity/attribution changes;
Linux results remain historical pre-guard partial
coverage and do not qualify the corrected Linux runtime. The later offline Linux
prerequisite result is recorded in the native guide, not these historical captures.
The native guide owns exact source revisions and coverage; the earlier Claude
walkthrough retains its historical capture and is not a current Codex map. The
observation dialog text has changed since these captures; their editable source
and PDFs describe the recorded revision, not the current dialog.

All three Codex PDF pages were rendered and visually inspected at their capture revision;
text/page-count checks and browser navigation are recorded separately. Rebuild
with the existing screenshot-manual scripts and recapture affected map dialogs
when their metadata changes. No account installation or activation was performed
by the documentation workflow.

## Collector capacity and attribution supplement

The [two-page supplement](collector-capacity.pdf), [editable source](collector-capacity.json)
and [capture manifest](collector-capacity-capture.json) reuse `native-observation`.
Its [capacity result image](collector-capacity-result.png) and
[boundary snapshot image](collector-attribution-result.png) are browser renderings
of selected actual synthetic benchmark/probe results, not terminal screenshots.
Capacity/recovery and the p95 target passed one final reference-host run; the
earlier candidate missed the target and remains historical evidence. Snapshot delivery hashes do not
qualify exact exposure. Both PDF pages are rendered and visually inspected, with
text and page count checked. Earlier native model results retain their own source
boundaries; this supplement does not requalify them against the capacity runtime.

## Native isolation qualification guide

The [native isolation walkthrough](native-isolation.pdf), [editable source](native-isolation.json)
and [actual map capture](native-isolation.png) show how to locate and expand the
new synthetic qualification guide. The capture uses workflow digest `c8bcdb25297a`,
isolated Chrome and public repository content only, on 2026-10-18. It is bound to
that earlier map revision; the current map includes later main additions. It proves
map navigation, not CLI execution. The separate maintained CLI smoke exercised the
actual Linux client, mock turn, native failed tool and cleanup; scope and commands
remain authoritative in the [qualification guide](../decisions/evaluation-isolation-pilot.md).
The single PDF page was rendered with PDFium and visually inspected for readable
text, complete capture, captions and margins; text and page count were checked
with pypdf. Rebuild using the screenshot-manual commands above with
`native-isolation.json`, and recapture when the documented dialog changes.

## Offline development evaluation

[PDF](evaluation.pdf) · [editable source](evaluation.json) · [capture manifest](evaluation-capture.json). The captured pre-main 30-call CLI journey prepares and reviews four English/Korean development cases with the in-tree producer, then retains all 16 scheduled trials. Eight matched pairs comprise one improved, one regressed, one both-pass, one both-fail and four unresolved. Missing and duplicate evidence stays visible. This qualifies deterministic integration/accounting; native model execution and independent holdout qualification remain unavailable. Earlier eight-trial captures remain historical in Git history. This receipt is a historical pre-main capture, identified by its baseline and source/map hashes. [PR #40](https://github.com/hwanjjang/agent-dotfiles/pull/40) records the separate current-head CLI and map verification; the images and PDF have not been recaptured.

Both evaluation pages were rendered with PDFium and visually checked for readable
headings, complete intended capture regions, captions and pagination. PDF text and
page count were checked with pypdf. The first image is an actual catalog dialog;
the second explicitly renders the actual synthetic CLI result in a browser. Neither
image demonstrates native model execution. Rebuild with the screenshot-manual
scripts above using `evaluation.json`; refresh its capture manifest after changes.

## Development recommendation

[promotion.json](promotion.json), [PDF](promotion.pdf), and [capture provenance](promotion-capture.json) explain the actual synthetic CLI handoff and source-review map. The browser-rendered result is labelled explicitly; it does not show native model execution. A positive arithmetic fixture remains operationally inconclusive. These are historical pre-main captures: their unmerged-producer wording describes the recorded baseline. The [current recommendation contract](../decisions/promotion-recommendations.md) and [in-tree producer contract](../decisions/evaluation-accounting.md#in-tree-reviewed-producer) own current availability; the receipt hashes and rendered assets are preserved.

## Explicit task feedback walkthrough

The [two-page walkthrough](task-feedback.pdf) covers selecting observations, recording
feedback, inspecting immutable task revisions and revoking private state. Its
[editable source](task-feedback.json), [map image](task-feedback-map.png),
[CLI result image](task-feedback-result.png) and [capture manifest](task-feedback-capture.json)
are maintained together. The 2026-10-18 capture uses a candidate based on `48b854b`.
The CLI image is a labeled browser-rendered summary of an actual disposable
synthetic run, not a terminal screenshot. Both PDF pages were rendered and visually
checked, including readable labels, complete images and page text.

These screenshots and PDF retain their original capture identity. Integration onto
Claude parent `5b99061` adds the inherited native process-project check before input
reads. A fresh synthetic feedback CLI journey and 175 focused tests passed on that
integrated candidate; the manifest distinguishes these checks from the historical
capture. This does not extend the screenshots to new native delivery evidence.

The PR33 correction adds conservative cleanup for corrupt task records, a 128 KiB
encoded stored-row limit and strict optional revision validation. Expiry blocks
access immediately; `prune` performs physical deletion. The dated screenshots
precede those safeguards and the corrected map wording; use the current Store
guide and repeatable recipe for these boundaries. Separate correction tests and
actual CLI checks verify them. The revised PDF text and captions include this
errata; both revised pages were rendered and individually viewed. Its screenshots
remain historical and do not depict a new run.

The [observation guide](../../account/observation/README.md) remains authoritative;
the [task-feedback recipe](../verification/verify-repository/features/task-feedback.md)
owns repeatable checks. Rebuild with the screenshot-manual scripts above, replacing
the source name with task-feedback.json. This slice does not implement reviewed
case export, native Codex collection or comparative evaluation.

## Reviewed synthetic case walkthrough

The [two-page case walkthrough](reviewed-cases.pdf) follows evidence-bound caller
triage, prepare/show/review/export and revoke using synthetic development inputs.
Its [editable source](reviewed-cases.json), [map image](reviewed-cases-map.png),
[CLI result image](reviewed-cases-result.png) and [capture manifest](reviewed-cases-capture.json)
are maintained together. The current correction capture is based on `d8cd2c5`.
Its result image renders selected actual disposable CLI results in a browser; it
is not a terminal screenshot or a native/model comparison.

Earlier captures on `48b854b`, integration onto `16fa81f` (187 tests), and refresh
onto `57173d8` (193 tests) remain historical provenance in the capture manifest
and Git history. Current images and PDF were recaptured for explicit caller triage,
actual failed-tool eligibility and precise output refusals. Caller attribution is
checked against selected evidence; it is not a diagnosed cause. Public v1 payloads
remain unchanged. Fresh correction validation passed 200 tests and the separate
bilingual CLI journey, including category and destination refusals.

The [Store guide](../../account/observation/README.md#prepare-and-export-a-reviewed-synthetic-case)
owns commands and privacy limits; the [case recipe](../verification/verify-repository/features/reviewed-cases.md)
owns repeatable checks. Review assertions do not guarantee sanitization; public
cases remain development data. Automated diagnosis remains planned. Both current
PDF pages were rendered and individually viewed, with required text/page count
checked. Rebuild using the existing screenshot-manual commands with
reviewed-cases.json and recapture after workflow changes.

## Native executor fixture walkthrough

The [two-page walkthrough](native-execution.pdf), [editable source](native-execution.json)
and [capture receipt](native-execution-capture.json) explain receipt interpretation
and selected source-bound native mock evidence. The [CLI image](native-execution-cli.png)
and [native summary image](native-execution-native.png) are browser renderings of
actual results, not terminal or real-model screenshots. Both PDF pages were
rendered and visually checked. The [fixture guide](../decisions/native-execution-fixture.md)
owns prerequisites and limits. Rebuild with the screenshot-manual scripts above
using `native-execution.json`; recapture after result or behavior changes.

The earlier native-isolation map screenshot retains its dated capture; the current
dialog additionally links this reusable fixture. The browser recipe verifies the
current dialog separately; this supplement does not requalify older captures.

## Frozen-trial preparation walkthrough

The [preparation PDF](frozen-trial-dispatch.pdf), [editable source](frozen-trial-dispatch.json)
and [capture receipt](frozen-trial-dispatch-capture.json) show the supervisor/payload
boundary and an actual synthetic Store export -> freeze -> prepare journey. Images
are browser renderings of sanitized CLI summaries, not terminal or model captures.
The [preparation guide](../decisions/frozen-trial-dispatch.md) owns the contract;
actual trial execution and evidence admission remain separate.

## Optional native outcome collection walkthrough

The [two-page walkthrough](native-outcome-collection.pdf),
[editable source](native-outcome-collection.json) and
[capture manifest](native-outcome-collection-capture.json) cover the optional
trial-only declaration, actual check refusals and three credential-free native
collection cases. The [check image](native-outcome-collection-check.png) and
[result image](native-outcome-collection-result.png) are actual browser renders
of sanitized recorded results, not terminal or model-performance captures.
Source bytes match checkpoint `1d831bf6e62e`; the native runs occurred before
that commit and were independently matched afterwards. Earlier trial manuals
retain their own historical qualification boundaries.

Both PDF pages were rendered with PDFium and visually inspected; text and page
count were checked with pypdf. The initial clipped summary capture was corrected
and both final browser captures passed overflow checks. No authentication, model
inference, evaluator admission or account activation was performed by this
documentation workflow. The [native guide](../native-trials.md) owns commands
and limits; the [verification recipe](../verification/verify-repository/features/native-trials.md)
owns repeatable checks. Rebuild with the screenshot-manual scripts above using
`native-outcome-collection.json`, and recapture when the documented behavior changes.

For this collection walkthrough, the private native bridge supplies the observation
projection and its own coordinator receipt. Production setup/cleanup/capture are
exercised; production `observe`/`finish` collection gates have unit coverage only.
