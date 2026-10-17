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
