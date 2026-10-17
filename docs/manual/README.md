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

The [three-page Codex walkthrough](codex-observation.pdf) follows the existing
`native-observation` scenario: select one client, review native trust, inspect
actual results and retain platform blockers. Its [editable source](codex-observation.json),
[current map capture](codex-observe.png), [macOS results](codex-native-result.png),
[Linux matrix](linux-observation-result.png) and [capture manifest](codex-observation-capture.json)
are maintained together. The two result images are browser renderings of selected
actual qualification evidence, not terminal captures. The macOS result is a fresh
corrected parent-native runtime run, before later capacity/attribution changes;
Linux results remain historical pre-guard partial
coverage and do not qualify the corrected Linux runtime.
The native guide owns exact source revisions and coverage; the earlier Claude
walkthrough retains its historical capture and is not a current Codex map.

All three Codex PDF pages are rendered and visually inspected during this update;
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
