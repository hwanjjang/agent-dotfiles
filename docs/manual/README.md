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
show the actual expanded dialogs from workflow digest `b4f054f4165a`, captured
on 2026-10-17 in isolated Chrome at 2x device scale. The maintained browser
recipe verifies their source links and the distinction between delivery and native
activation. Installation commands remain authoritative in the account guide.

Both PDF pages were rendered with PDFium and visually checked for readable text,
complete screenshots, margins and captions. Text and page count were checked with
pypdf. Regenerate with the screenshot-manual scripts above, substituting
`account-source.json`; recapture when either documented dialog changes.

## Complete English and Korean user guides

The [English guide](user-guide/manual-en.pdf) and [Korean guide](user-guide/manual-ko.pdf)
cover installation, AK SDLC navigation, private synthetic observations, the proposed
eval workflow and recovery in 18 pages each. See the [source and capture notes](user-guide/README.md),
[English editable text](user-guide/manual-en.md) and [Korean editable text](user-guide/manual-ko.md).
The six-step improvement cycle is documented with explicit implemented/planned status.
Actual native collection and comparative model evaluation remain future work.

## Offline development evaluation

[PDF](evaluation.pdf) · [editable source](evaluation.json) · [capture manifest](evaluation-capture.json). The actual offline CLI journey retains all eight scheduled synthetic trials, including failure, timeout, duplicate and missing evidence. It qualifies deterministic accounting only; no native model, unseen holdout or promotion claim.

Both evaluation pages were rendered with PDFium and visually checked for readable
headings, complete intended capture regions, captions and pagination. PDF text and
page count were checked with pypdf. The first image is an actual catalog dialog;
the second explicitly renders the actual synthetic CLI result in a browser. Neither
image demonstrates native model execution. Rebuild with the screenshot-manual
scripts above using `evaluation.json`; refresh its capture manifest after changes.

## Development recommendation

[promotion.json](promotion.json), [PDF](promotion.pdf), and [capture provenance](promotion-capture.json) explain the actual synthetic CLI handoff and source-review map. The browser-rendered result is labelled explicitly; it does not show native model execution. A positive arithmetic fixture remains operationally inconclusive.
