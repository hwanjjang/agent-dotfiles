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


## Native isolation qualification guide

The [native isolation walkthrough](native-isolation.pdf), [editable source](native-isolation.json)
and [actual map capture](native-isolation.png) show how to locate and expand the
new synthetic qualification guide. The capture uses workflow digest `7d40116c807c`,
isolated Chrome and public repository content only, on 2026-10-18. It proves map
navigation, not CLI execution. The separate maintained CLI smoke exercised the
actual Linux client, mock turn, native failed tool and cleanup; scope and commands
remain authoritative in the [qualification guide](../decisions/evaluation-isolation-pilot.md).
The single PDF page was rendered with PDFium and visually inspected for readable
text, complete capture, captions and margins; text and page count were checked
with pypdf. Rebuild using the screenshot-manual commands above with
`native-isolation.json`, and recapture when the documented dialog changes.
