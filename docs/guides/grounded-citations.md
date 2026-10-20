# Check a report against retrieved sources

Use [grounded-citations](../../skills/grounded-citations/SKILL.md) for source-heavy
research. Python 3.10+ and a selected local task directory are sufficient; Hermes
and network access are not required by this helper. The account delivery tool
ships the package from a committed revision. Existing accounts receive it only
after a separately authorized update.

This reproducible example uses synthetic source text. It demonstrates reference
consistency and quote matching; it is not evidence of real web retrieval or truth.
Run from the repository root with a new task directory:

```sh
mkdir -p .planning/citation-example
cat > .planning/citation-example/page.txt <<'EOF'
The service retains synthetic exports for seven days.
EOF
cat > .planning/citation-example/draft.md <<'EOF'
The service retains synthetic exports for seven days.[1]
EOF
python3 skills/grounded-citations/scripts/sources.py --ledger .planning/citation-example/sources.json add https://example.com/retention --title 'Synthetic retention policy'
python3 skills/grounded-citations/scripts/sources.py --ledger .planning/citation-example/sources.json quote 1 --text 'The service retains synthetic exports for seven days.' --from .planning/citation-example/page.txt
python3 skills/grounded-citations/scripts/sources.py --ledger .planning/citation-example/sources.json render --replace-in .planning/citation-example/draft.md
python3 skills/grounded-citations/scripts/sources.py --ledger .planning/citation-example/sources.json verify .planning/citation-example/draft.md --evidence --strict
```

The commands return `[1]`, report one attached quote, generate a trailing Sources
block, and finish with `citations OK`. Change the quote to say eight days:
`quote` rejects the mismatch. Replace the inline marker with `[9]`:
`verify` returns a failure instead of accepting a source that was never registered.
Sections after an existing Sources list remain part of verification. Replacement
preserves those sections and moves the updated list to the end. Fenced Sources
examples remain body content. Only numbered HTTP(S) entries and rendered evidence
quotes belong to the replaceable list; keep other annotations outside that list.

`ingest` validates every extracted URL before registering any of them. A later
credential-bearing or malformed HTTP(S) URL rejects the input without changing
the register; this is input validation, not a transaction guarantee for interrupted
writes or concurrent writers.

Keep the register on resume so IDs remain stable; `reset` intentionally removes
the mapping. Use a separate register for another task. Raw text and registers
stay ignored/private. Registration normalizes URL fragments and trailing slashes;
retain page/section coordinates beside the claim when those matter. A lock timeout
requires reconciling the original writer before retrying.

For ordinary chat, use the host's descriptive links/native citations near claims.
The numbered-report checker does not verify that output format. Even an
evidence-mode PASS says only that cited IDs/URLs agree with the local register
and each cited source has a matched quote. Inspect whether the quote supports
the particular claim, whether the source is reliable/current, and whether
contradictory evidence or required sources are missing.
