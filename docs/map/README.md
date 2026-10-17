# Repository map

Open [index.html](index.html) in a browser to explore the catalog. It works offline
without a server or third-party assets. GitHub's file view shows HTML source;
open the file from a local checkout to use the viewer.

Search, filter by type or status, and select a node for usage, behavior, expected
results, source links, and related items. Map mode offers zoom and Fit; List mode
is the default on narrow screens. Press `/` to search, use Tab and Enter to select
an item, and Escape to close details. An item hash such as
`index.html#item=maintenance` opens its details directly.

A [screenshot walkthrough](../manual/catalog.pdf) demonstrates the detail panel;
its [source and reproduction steps](../manual/README.md) are maintained alongside it.

## What the map means

- **Available:** The source file exists in this checkout. This does not claim an
  installed skill, deployed policy, working MCP connection, or verified client
  behavior.
- **Planned:** An empty content directory. It is not an executable workflow.
- **Reference:** An external public research source. Opening the map installs
  nothing and makes no network requests; source links load only when followed.

Lines highlight documented links for the selected node. They are navigation
relationships, not runtime calls, mandatory execution order, or inferred impact.

## One map source, generated presentation

| File | Role |
| --- | --- |
| [catalog.json](catalog.json) | Authoritative map metadata: entries, summaries, usage pointers, statuses, and explicit relationships. |
| [viewer.template.html](viewer.template.html) | Viewer layout and interactions. |
| [../../scripts/build_map.py](../../scripts/build_map.py) | Standard-library Python generator and validation. Requires Python 3.9+. |
| [index.html](index.html) | Generated standalone viewer; commit it with its inputs. Do not edit it directly. |

Policy, skill, configuration, and repository instruction files remain the
authority for their behavior. Catalog text is a concise navigation aid, not a
second copy of those instructions. Keep usage pointers aligned with the source.

From the repository root:

```sh
python3 scripts/build_map.py
python3 scripts/build_map.py --check
python3 -m unittest discover -s tests -p 'test_build_map.py'
```

Generation is deterministic. `--check` validates the catalog and fails when the
HTML differs from its current inputs. No build dependency needs installing.

## Updating content

1. Add or change the authoritative source file.
2. Update its catalog entry: stable `id`, `title`, `kind`, `group`, `status`,
   `summary`, `when`, `usage`, `behavior`, `outputs`, and `tags`. Use a
   repository-relative `source`, or an HTTPS `url` for an external reference.
3. Replace the relevant planned directory placeholder with real entries as
   content arrives. An available entry points to a file; a planned entry points
   to an empty content directory.
4. Add explicit `from`, `to`, and `label` relationships only when the source
   supports them. Keep IDs stable so shared item links continue working.
5. Regenerate, run the checks above, and open the map. Check the changed item's
   filters, details, links, and status before committing the source, metadata,
   and HTML together.

The generator checks that policy and MCP files (except directory README.md files)
and skill entry points (`skills/**/SKILL.md`) are represented. Skill supporting
files belong to their skill's entry; they do not need separate nodes. It rejects
missing/escaping/local source paths, credential-bearing URLs, invalid
relationships, duplicate IDs, and stale planned placeholders.

Validation cannot determine whether arbitrary prose contains private information
or whether an external repository is public. Follow README's public Git boundary
and review catalog metadata and generated HTML together. Raw research, screenshots,
and browser evidence stay under ignored `.planning/` or `.local/`.

## Design references

The [pstack map](https://erictechpro.github.io/super-board/pstack/) informed grouped
exploration, item details, and explicit gaps. The
[Hermes Skill Atlas](https://github.com/codesstar/hermes-skill-atlas) offers an
example of structured catalog data with an offline viewer. The
[skill-map project](https://github.com/crystian/skill-map) offers a separate graph
specification and implementation. These are research references; this viewer
does not bundle their code or depend on their runtimes.

The [repository feature map](../verification/verify-repository/features/README.md)
is a separate maintenance source for real catalog verification recipes. Catalog
entries link to it; do not duplicate its expected behavior or store runtime pass
status in catalog.json.

No hosted publication or automatic installation is configured.

## Separate AK SDLC view

The [AK SDLC skill map](workflow.html) adds ordered stages and Anytime triggers
without changing this catalog viewer. Read its [guide](workflow.md) for usage and
the separate `scripts/build_workflow.py` generation/check command. Changes to
shared catalog entries require regenerating and checking both viewers.

Every current skill has an `explanation` object in the catalog (optional for other
entry types): `example` (situation, request, steps and result), `flows`, conditional
`calls`, `adaptation_notes` and labeled `sources`. The workflow viewer uses these
in its existing detail sections. Shared summaries, behavior and results also
appear in this catalog viewer. Keep examples illustrative and verify claims
against the local skill before borrowing a reference map's explanation. Record
the explanation's source basis and reviewed fingerprints in
[skill-explanations.json](skill-explanations.json). Locally authored skills use
their public local sources; a reference-map counterpart is not required. See the
[workflow guide](workflow.md#source-and-maintenance) for the update procedure.
