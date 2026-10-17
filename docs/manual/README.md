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
