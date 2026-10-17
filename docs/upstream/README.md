# Source adoption and update records

The public source set contains selections from pstack, Matt Pocock, Addy Osmani,
and AK-authored material supplied for public reuse. Private source addresses and
raw history are intentionally absent. Source-level private provenance is retained
locally; public AK packages use this repository's MIT license.

Per-skill `provenance.json` is the authority for origin, selected revision, imported
paths, local changes, dependencies, and validation limits. Public upstream imports
retain their license beside the skill. Required Addy checklists are included inside
the review package so a selected installation does not lose root-level resources.
Portable policies carry attribution and license information in their source.
`license_path` identifies the license in the upstream repository; the redistributed
license is always `skills/<name>/LICENSE`. Archify also retains third-party terms
in its `THIRD_PARTY_NOTICES.md`; the root MIT license does not replace those terms.

The [external tool registry](../../tools/registry.json) separately owns executable
and connection dependencies. Client MCP examples live under `mcp/claude-code/`;
these files are templates and are not activated by this checkout.

## Import decisions

- pstack: port investigation, candidate selection, architecture, and scoped workers;
  retain design resources. Replace Cursor-specific runtime assumptions with declared
  host capabilities. Carry evidence and behavioral-test principles as policies.
- Matt Pocock: bring the interview primitives and domain documentation as a dependency
  group. Bound consequential decisions, preserve existing authority, and document
  missing-dependency behavior. Retain supplied invocation metadata.
- Addy Osmani: bring planning and quality review. Make planning independently usable,
  keep task state isolated, and bundle review checklists. Review experiments use
  disposable workspaces; no review verdict grants publication authority.
- AK-authored source: import SDLC and issue-writing, plus architecture and security
  policies. Remove private links and project attribution; scope communication and
  publication authority to each task. Retain state scripts and their tests.
- Required diagram production: include Archify at the selected baseline pin with
  its runtime, schemas, templates, and third-party notices.
- Required screenshot manuals: include a focused source/PNG/PDF workflow with a
  reproducible generator, raster preview, and mandatory visual inspection.

The AK source's common MCP list was empty. The three initial connection templates
therefore come from provider documentation, not an inferred private configuration.
Account setup scripts, personal host hooks/settings, project history, raw captures,
and unrelated integration configuration are outside this initial portable import.
Graft and other optional toolchains are deferred to keep the requested minimum.

## Update procedure

1. Inspect the pinned origin and local adaptations before selecting a new revision.
2. Fetch into ignored local staging. Review the upstream delta, license, dependencies,
   client requirements, and permission or output changes.
3. Reapply only adaptations still needed. Preserve method coverage, invocation
   behavior, and resource closure; do not overwrite the local package blindly.
4. Run relevant syntax, resource, executable, and behavioral checks. Record which
   client-level or authenticated checks were actually performed.
5. Update provenance and the map in the same change. Review all public content for
   private links and values before an authorized commit.

Source presence, structural validation, executable checks, and real client behavior
are separate claims. No account installation, external publication, or complete
SDLC behavioral evaluation was performed by this import.

## Source-package limitations

- Archify's bundled `package.json` and some tests retain upstream monorepo commands
  that refer to sibling `scripts/` and `viewer/` directories absent here. Do not use
  its `npm test` as this checkout's validation command. The checked portable entry
  is `node skills/archify/bin/archify.mjs doctor`; demo rendering was also exercised.
  These checks do not establish the full custom-diagram finalize/provenance workflow.
- The imported AK SDLC still uses `AK` as the authorizer label for reviewer-effort
  overrides and retains historical repository-layout examples in its playbook.
  It is an AK workflow building block, not a fully generalized principal/host adapter.
  Apply the destination project's actual instructions and layout. No historical
  source sentence creates publication authority for a new user or repository.
