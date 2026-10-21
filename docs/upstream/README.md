# Source adoption and update records

The public source set contains selections from pstack, Matt Pocock, Addy Osmani,
Hermes method references, and AK-authored material supplied for public reuse. Private source addresses and
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

- [Account source selection](../decisions/account-source-import.md): compare all
  three reference collections, retain small communication/execution policies and
  useful review continuity, and import only the existing planning pin's selected
  POSIX runtime. [Runtime provenance](../../account/hooks/planning-with-files/provenance.json)
  records exact source paths, hashes and license. No account installer, generic
  router, private settings or personal permission exceptions are imported.

- [Improvement experience selection](../decisions/improvement-experience.md): adapt
  Harness² (`1cfe254`, Apache-2.0) reflection and earlier-only retrieval methods as
  design rules for the account improvement loop. No Harness² code, prompts or
  runtime are imported; community validation is provisional.

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
- Architecture policy: retain three minimum principles after source review and
  maintainer direction. Replace mandatory alternatives sections and dependency
  graphs with task-appropriate guidance; link pstack and Matt design material as
  optional references. This does not change the separate architect or SDLC workflows.
- Required diagram production: include Archify at the selected release with its
  runtime, schemas, templates, and third-party notices. The package moved from the
  3.0.1 baseline to v3.2.0 on 2026-10-21; see the Archify update record below.
- Required screenshot manuals: include a focused source/PNG/PDF workflow with a
  reproducible generator, raster preview, and mandatory visual inspection.
- Logging policy: combine Addy's severity and structured-event guidance with
  Matt's targeted temporary probes and cleanup. The [policy](../../policies/logging.md)
  owns pinned sources, license notices, local adaptations, and runtime verification
  expectations. This imports the selected guidance without requiring both complete
  upstream workflows or claiming individual-skill popularity from collection stars.

The AK source's common MCP list was empty. The three initial connection templates
therefore come from provider documentation, not an inferred private configuration.
Account setup scripts, personal host hooks/settings, project history, raw captures,
and unrelated integration configuration are outside this initial portable import.
Graft and other optional toolchains are deferred to keep the requested minimum.

The [issue workflow policy](../../policies/issue-workflow.md) consolidates common
issue lifecycle rules consumed by issue-writing and SDLC. It owns pinned source
attribution and MIT notices. Its [decision note](../decisions/issue-workflow.md)
records fit, adaptations and limited community evidence. This is a local synthesis
of selected guidance, not installation of the three upstream orchestration stacks.
Affected skill provenance declares the shared policy dependencies; distribution
must preserve their links. Tracker execution remains unverified. Codex source discovery is recorded in
[client verification](../client-verification.md); no account installation is claimed.

The three focused additions and their SDLC integration are described in the
[adoption decision](../decisions/skill-integration.md). Their provenance records
pin upstream source and distinguish local extensions from original methods.
The single tdd method replaces duplicated method prose; SDLC retains executable
evidence validation, additional smoke and existing authority gates.

The [verification pair](../decisions/verification.md) adopts pstack generation and
maintenance with all feature-map examples and MIT notices. Local adaptations
remove hardcoded client paths and implied publication, preserve requested coverage
and distinguish product defects from documentation drift. Optional tooling stays
a reference; no additional MCP server is enabled.

The [formal verification pair](../decisions/formal-verification.md) adopts pstack's
beta create/maintain methods at `190d287` with their MIT notice. Local adaptations
allow model invocation only for explicit requests, keep toolchain installs,
product-source harnesses and scratch breaks within task authority, and label
generated-input fallbacks as bounded testing. Setup offers, guide text and the Claude
harness adapter line are not imported. Community validation is provisional.

The [PR/ticket adoption](../decisions/pr-workflow.md) combines pstack PR planning,
Matt's ticket adapter and the original Cursor Team Kit review-preparation skill
discovered through Denyer's port. It extends the existing Addy planning package,
retains one body authority, and makes source-commitment coverage explicit.
Per-package provenance lists additional pinned method sources and their hashes.
No stack runtime, setup skill, MCP or fixed tracker vocabulary is introduced.

The [spec extraction](../decisions/spec-extraction.md) combines Matt's focused
`to-spec` synthesis with the existing AK specification contract. The spec method
and content checklist moved into one standalone skill; SDLC now links to it.
Automatic issue publication, fixed labels and exhaustive story templates were
not adopted. Current discovery and behavioral limits remain separately recorded.

The [account-content preservation decision](../decisions/account-content-preservation.md)
adds a portable Hermes-derived citation helper and narrowly adapts document/meeting
extraction and feasibility experiments into existing owners. Affected packages
retain selected revisions, hashes and MIT notices, including secondary Hermes/GSD
attribution. Community effectiveness remains provisional.

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

## Archify update — 2026-10-21

AK selected the update from the 3.0.1 baseline (`d5a1333`) to the published v3.2.0
release (`208acba8d412335185b2056fedf54b3405df43fb`, tree `39069dd`). The skill's
[provenance.json](../../skills/archify/provenance.json) owns the exact identity,
packaging changes and validation; the [tool registry](../../tools/registry.json) and
the catalog entry carry the same pin, and `tests/test_archify_vendored.py` checks that
they agree.

- **Included changes.** Ten diagram types (ERD, class, tree, timeline and waterfall
  join the original five), reader-controlled Live/Still motion built into every diagram
  (a new page starts Still until the reader chooses Live), bundled viewer locales, and
  one-page explainer pages whose charts use unmodified Pele 1.3.0 chunks (MIT). The
  package no longer ships its own tests.
- **Local changes.** None to upstream text or code. Trailing whitespace was normalized
  in 17 text files for repository diff checks. provenance.json lists the normalization and
  the digest of every vendored file, and the test fails on an edit that is not recorded.
- **Behavior to know.** `finalize` and `deliver` make a bounded request (1 second,
  cached for 24 hours) to the project's update manifest and report it in the receipt;
  `ARCHIFY_UPDATE_CHECK_DISABLED=1` removes the check. Since 3.2 the skill lets the agent
  describe the manifest's summary of at most 160 characters and tells it to treat that
  text as untrusted data; it never installs or runs an update. Do not update an
  installed copy in place: it is owned by the account installer, and an edit blocks the
  next update. After an explainer made on request the skill may offer a proactive mode and
  edits a global rules file only if the user accepts.
- **Community evidence.** Limited. Independent first-hand reports were not found; web
  searches returned aggregator pages, release notes and the project's own pages. One
  critical article (braindetox.kr, 2026-09-30) assesses the 3.0.1 documentation, not
  tested results, and says the automated gates check form, not truth. The upstream issues
  read on 2026-10-21 include open viewer, timeline/waterfall, explainer chart and Windows
  reports, and none about the architecture or workflow `finalize` path on Linux. The
  selection is provisional with respect to community validation.
- **Checks.** The payload equals the upstream tree at the pinned revision except the
  whitespace-only files. On Linux with Node.js 22 and a Chromium browser, `doctor` passes,
  every bundled example of the ten types validates, and `finalize` passed its validate,
  deliver, check and browser-check gates for the architecture example and for the
  explainer example with `--browser-check`. Not exercised: Windows, macOS, a model-driven
  session and perceptual review of generated pages.
- **Rollback.** Restore `skills/archify` and the pins from the repository commit before this
  update; its provenance record names upstream `d5a1333`.

## Source-package limitations

- Archify's bundled `package.json` retains upstream monorepo commands that refer to
  sibling `scripts/` and `viewer/` directories absent here, and the package no longer
  ships its tests. Do not use its npm scripts as this checkout's validation command.
  The checked portable entry is `node skills/archify/bin/archify.mjs doctor`, together
  with `tests/test_archify_vendored.py` and the finalize runs listed in the update record.
- The imported AK SDLC still uses `AK` as the authorizer label for reviewer-effort
  overrides and retains historical repository-layout examples in its playbook.
  It is an AK workflow building block, not a fully generalized principal/host adapter.
  Apply the destination project's actual instructions and layout. No historical
  source sentence creates publication authority for a new user or repository.
