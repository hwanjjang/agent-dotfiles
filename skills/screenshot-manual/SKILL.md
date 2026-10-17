---
name: screenshot-manual
description: Create or update a user manual with actual workflow screenshots, editable source, and a rendered and visually checked PDF.
---

# Screenshot manual

Input: audience, user goal, product revision, relevant scenarios, and an authorized
capture environment or supplied screenshots. Output: editable JSON source,
sanitized screenshots, PDF, and a verification summary. Do not publish implicitly.

## Capture and author

1. When a project verifier exists, reuse its stable feature/scenario IDs and
   maintained user paths; link recipes instead of copying their verification rules.
   Previously captured evidence is reusable only when revision and scenario match.
   Walk through each user scenario on the actual product. Use an available browser
   or native capture tool within the task's authority. Capture screenshots at the
   points where users need to identify a control or recognize the result. An image
   proves only the state it shows; verify the behavior separately.
2. Use synthetic accounts and data when possible. Inspect each screenshot for
   private content before including it. If supplied screenshots lack a known
   revision or capture context, report that limit; do not claim you ran the scenario.
3. Create a task-local JSON source using [the example](assets/manual.example.json).
   Write user actions and expected results in the audience's language. Keep steps
   focused and captions specific. Include prerequisites in the scenario description.
4. Screenshots are relative paths beside the source. Keep source, images, renders,
   and draft PDFs in the destination's ignored artifact area until reviewed for
   publication. Never publish authenticated storage or raw diagnostic logs.

## Build and verify

Prerequisites: Python 3.9+, dependencies in `requirements.txt`, and a compatible
TTF font for non-ASCII content. The font must cover every character used; retain
its redistribution license if bundling it. No credential variables are required.
Install dependencies in an isolated environment, not into a system interpreter.

Run these commands using this installed skill's directory:

```sh
python scripts/build_manual.py /path/to/manual.json /path/to/manual.pdf
python scripts/render_pages.py /path/to/manual.pdf /path/to/new-page-renders
```

For Korean or other non-ASCII text, add `--font /path/to/compatible-font.ttf` to
build_manual.py. For an intentional rebuild, `--overwrite` replaces the PDF;
use a new render directory so prior evidence remains distinct.

Read the PDF's text and page count with pypdf; check required instructions and
expected outcomes are present. Render every page and inspect the images for
cropping, overlap, missing glyphs, caption mismatch, and unreadable screenshot
labels. Enlarge a relevant capture or split a step when necessary. Rebuild and
rerender after changes. Poppler's `pdftoppm` is an alternative renderer when
available; this package includes PDFium rendering for a portable local toolchain.

Complete only when the scenario content, screenshots, and final PDF agree and
visual review has passed. Deliver the PDF with its editable source and identify
the product revision, scenarios exercised, generation checks, visual inspection,
and any limitations. A successful build or file existence is not sufficient.
