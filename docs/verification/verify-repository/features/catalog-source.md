# Read usage and locate its source

Scenario ID: `catalog-source`. A maintainer can inspect a capability and follow its
source pointer. Shared setup and command: [verifier](../SKILL.md).

## Sub-features

- Open create-verification-skill, maintain-verification-skill and repository-verifier.
- Each detail view supplies usage and the corresponding maintained source link.

## How to get to it (user POV)

Open `docs/map/index.html`, clear search, then select each named card.

## Driving it with Playwright

Preconditions: doctor passed and search is empty. Select each card, require nonempty
usage and a source link matching its catalog entry, and confirm that linked file
exists. Capture `verification-detail.png`; record `catalog-source` in `result.json`.
The helper checks link targets but does not open Markdown in an external viewer.

## Gotchas

An available card describes source availability, not installation or successful
MCP connection. External links and every related-item interaction are outside this
scenario. No private evidence directory is mapped as a public source.
