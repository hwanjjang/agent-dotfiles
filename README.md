# agent-dotfiles

Single source of truth for AI agent policies, skills, and MCP configurations.

Agent instructions, useful skills, and tool connections tend to spread across
projects, clients, and machines. This repository aims to keep the shared parts in
one reviewable place, so improvements can carry forward to the next task and
environment.

Follow the [AK SDLC skill map](docs/map/workflow.html) for ordered stages, skill
choices and Anytime triggers. See its [guide](docs/map/workflow.md) and
[screenshot walkthrough](docs/manual/workflow.pdf). The complete user guides are available
in [English](docs/manual/user-guide/manual-en.pdf) and [Korean](docs/manual/user-guide/manual-ko.pdf),
with [editable sources and capture notes](docs/manual/user-guide/README.md).

Explore the [interactive map](docs/map/index.html) for usage, behavior, source
links, and implementation status. Open the HTML from a local checkout; GitHub's
file view shows source. See the [map guide](docs/map/README.md) for upkeep and
the [screenshot walkthrough](docs/manual/catalog.pdf) for a usage example.

**Status:** Initial content collection: 23 skill packages, ten portable policies,
three opt-in Claude Code MCP templates, and an external tool registry. Diagram
production and screenshot-based PDF manuals are included. Source adoption and
focused checks are documented. Codex 0.159.2 previously discovered the initial 18 packages in a
temporary project; account installation/update/removal and diagnostic/model-check
commands are implemented. Bounded installed-skill scenarios have separate results;
complete SDLC behavior and authenticated MCP connections are not claimed. See [client verification](docs/client-verification.md) for exact limits,
and browse [skills](skills/README.md), [policies](policies/README.md),
[MCP templates](mcp/README.md), and [adoption records](docs/upstream/README.md).

[Account source](account/README.md) adds a portable instruction entry point and
selected planning hook runtime/templates. Communication and execution rules have
one owner in `policies/`; system/Paseo skills and personal settings remain under
their existing managers. Use the [account guide](account/README.md) for preview,
install, update, uninstall and guarded rollback on macOS/Linux/WSL. Codex and Claude
Code are default; an installed Hermes is opt-in. See the [installation decision](docs/decisions/account-installation.md)
and the earlier [source selection](docs/decisions/account-source-import.md).
Use `sh scripts/setup-account.sh doctor` for setup diagnostics, `--native` for
client discovery and hook trust, and explicit `--model-smoke --client ... --model ...`
for an actual installed-skill scenario. `--with-paseo` adds optional local Paseo
coverage; `--scenario routing` tests natural spec-to-plan skill selection in native
clients. Model identity and per-client SessionStart recovery have separate evidence.
The [account guide](account/README.md#diagnose-and-exercise-the-installation)
owns commands, evidence privacy, cost boundaries and coverage limits.

[Private observations](account/observation/README.md) support explicit immutable task
selections and local feedback. See the [task-feedback walkthrough](docs/manual/task-feedback.pdf)
and [verification recipe](docs/verification/verify-repository/features/task-feedback.md).
[Reviewed synthetic case export](account/observation/README.md#prepare-and-export-a-reviewed-synthetic-case)
is available with an [exact-digest review walkthrough](docs/manual/reviewed-cases.pdf).
Evidence-bound caller triage is available; automatic diagnosis and promotion-eligible held-out evaluation remain planned.

The shared [logging policy](policies/logging.md) combines Addy Osmani's severity
and structured-event rules with Matt Pocock's temporary debug-log cleanup rules.

The [architecture policy](policies/architecture.md) keeps three minimum principles:
findable code, clear boundaries and responsibilities, and verifiable changes.
Detailed design guidance is optional and used when the task needs it.

The [issue workflow policy](policies/issue-workflow.md) defines issue creation,
updates, comments, handoff and closure. Use it directly or through issue-writing
and SDLC; see the [selection and community evidence](docs/decisions/issue-workflow.md).

The [PR workflow policy](policies/pr-workflow.md) keeps review and merge units
coherent. Planning owns task and PR boundaries; [to-tickets](skills/to-tickets/SKILL.md)
materializes tickets, and [make-pr-easy-to-review](skills/make-pr-easy-to-review/SKILL.md)
prepares reviewer guidance. See the [source comparison and adaptations](docs/decisions/pr-workflow.md).

SDLC [shares matching required and additional reviewers](skills/sdlc/references/optional-reviewers.md#one-assignment-per-reviewer)
through one assignment and result; distinct reviewers remain independent. Each
selected reviewer uses [code-review-and-quality](skills/code-review-and-quality/SKILL.md)
inside that context; the method also works standalone.

[to-spec](skills/to-spec/SKILL.md) turns settled requirements into a standalone
specification. AK SDLC uses the same method; its former spec checklist now links
to that authority. See the [extraction decision](docs/decisions/spec-extraction.md).

The [verification adoption](docs/decisions/verification.md) adds project-local
verification generation and maintenance. The [repository feature map](docs/verification/verify-repository/features/README.md)
connects this checkout’s catalog journeys to a runnable verifier; it does not claim
account installation or MCP connectivity.

## Repository structure

```text
agent-dotfiles/
├── AGENTS.md       # Instructions for maintaining this repository
├── CLAUDE.md       # Claude entry point to the same maintenance instructions
├── account/        # Account delivery guide, portable entry point and hook source/templates
├── docs/decisions/ # Researched repository design decisions
├── docs/map/       # Catalog data, viewer template, and generated interactive map
├── policies/       # Shared agent instructions and operating principles
├── skills/         # Reusable task workflows
├── mcp/            # Credential-free MCP configuration
├── scripts/        # Maintenance and account delivery tooling
├── tests/          # Focused maintenance and content-tool checks
├── tools/          # External capability registry and prerequisites
├── README.md
└── LICENSE
```

Content is selected for the workflows described below. Every imported skill carries
its license, provenance, dependencies, and adaptation notes. Raw source staging and
private provenance remain local.

Skills should use `skills/<skill-name>/SKILL.md`, with supporting scripts,
references, and assets kept alongside the skill. MCP configuration formats and
installation paths will be documented as integrations are added.

`AGENTS.md` is the single source of repository maintenance instructions.
`CLAUDE.md` imports it and contains no independent rules. These files govern this
repository, separate from reusable policy content in `policies/`, and should not
be installed as another project's agent policies.

The [structure decision](docs/decisions/repository-structure.md) compares nine
upstream repositories and explains this initial layout. Active external research
is part of maintaining this project; `AGENTS.md` defines that requirement.

## Content scope

The [AK SDLC design](docs/decisions/modular-sdlc.md) is connected through the
[stage-to-skill routing](skills/sdlc/references/skill-routing.md): early intent
clarification, parallel design, dependency-aware implementation and focused
verification. Skills remain independently usable. The single pstack-derived
`tdd` method serves bug fixes and test-first feature changes; diagnosis and review
corrections reuse it. Source integration and evidence checks are implemented;
complete multi-provider execution still needs a target-host run.
The [intake decision](docs/decisions/sdlc-intake.md) connects requests, issues and
PRs to evidence-based next actions inside SDLC; its [native behavior recipe](docs/verification/verify-repository/features/sdlc-intake.md)
checks selection, execution and results separately.

| Area | Purpose |
| --- | --- |
| Policies | Shared guidance for execution, communication, verification, and handling permissions. |
| Skills | Focused workflows for recurring work, with clear triggers and observable completion criteria. |
| MCP configuration | Reusable connection definitions and prerequisites, with credentials supplied locally. |

For additions and updates, record upstream links, selected revisions, licenses,
dependencies, and deliberate adaptations. Add client-specific setup and update
tooling when there is configuration to distribute.

The intended result is a common foundation that projects can adapt to their own
conventions. Client-specific behavior belongs in an explicit adapter or setup
step, with compatibility checked in that client.

The [account improvement loop](docs/decisions/account-improvement-loop.md) connects
private observations to reviewed cases, comparative evaluation and account updates.
Each candidate attempt is designed to leave a reviewed
[improvement experience](docs/decisions/improvement-experience.md) for later authors;
its storage and retrieval are not implemented yet.
Its first slice provides a [private synthetic observation store](account/observation/README.md)
with scoped grants, durable records, batch replay and revocation. Optional
[Claude and Codex native collection](account/observation/native.md) use explicit
project consent and one selected client registration; default installations collect
nothing. Codex requires native trust for four observer definitions. The
[native platform matrix](account/observation/native.md#native-platform-evidence--2026-10-18)
owns per-client, source-bound results, interruption limits, historical prerequisites
and untried environments. Comparisons between different models remain future work; the completed development pilot compares two configurations using one client-selected model. The implemented [account doctor](account/README.md#diagnose-and-exercise-the-installation)
qualifies setup and bounded model behavior before experiments or after deployment;
its PASS does not establish improvement over a baseline.
The [collector capacity guide](account/observation/capacity.md) records bounded
delivery attribution and 10,000 synthetic callback recovery, including the measured
p95 latency and its reference-host limit. Delivery identity never implies exact model exposure.
The [isolation qualification guide](docs/decisions/evaluation-isolation-pilot.md)
provides macOS Python canaries and a guarded Linux native synthetic workflow.
A passing native fixture does not enable live provider access or promotion.

Offline development comparison and recorded-artifact admission are implemented in
[deterministic evaluation accounting](docs/decisions/evaluation-accounting.md).
Neither executes models or establishes held-out or promotion eligibility. The [selected-trial preparation adapter](docs/decisions/frozen-trial-dispatch.md)
projects one executor input without exposing the grading envelope; it performs
no execution or real-evidence admission.

The [reusable native executor fixture](docs/decisions/native-execution-fixture.md)
and [two-page walkthrough](docs/manual/native-execution.pdf) add retained mock
receipts and selected native-route checks. The [completed development pilot](docs/evidence/native-development-pilot-2026-10-19.md) records all eight actual trials and rejects the candidate. The [frozen native-trial operator guide](docs/native-trials.md)
documents implemented `check/run/recover` and the separate credential-free
`command-skills-loader` fixture. The [selected evidence](docs/verification/native-trials.json) records current source-bound
credential-free and authenticated qualification at runtime revision `3905185` for the exercised pinned profile;
these commands do not enable comparative evaluation or account activation. A
[screenshot manual](docs/manual/native-trials.pdf) explains the results.

The [scoped grading-integrity evidence](docs/verification/scoped-grading-integrity.json)
records scoped credential-free native/child access checks and grading-drift tests.
The [collection record](docs/verification/native-outcome-collection.json) adds
recorded source13 bounded artifact collection with present/missing, unsafe and
interrupted cases. Execution, scoped grading, collection and fixed routing
qualification records now share [original-proof provenance](docs/verification/native-qualification-provenance.json).
The credential-free bridge does not exercise production `observe`/`finish`;
a later [partial pilot](docs/native-trials.md#offline-artifact-admission) exercised
the normal production path; its retained schedule has three pass, one fail, one
blocked and three missing rows. That historical comparison remains incomplete.
Eight recorded observations qualified the process-query, cleanup-settling and
exact-prompt source recorded in the [previous checkpoint](docs/native-trials.md#previous-fully-qualified-checkpoint--2026-10-19).
The later startup-diagnostic, interruption-retention, pre-turn-continuation and
owned-child cleanup changes have local conformance checks. Their
[current renewal](docs/evidence/reference-cell-qualification-2026-10-19.json) has
eight fresh passing controls after a reviewed private fixed-input contract revision;
all owned resources were cleaned. Earlier failures remain recorded. Fixed controls
do not establish production interruption or candidate comparison outcomes. Separate [actual interruption and eight-row comparison evidence](docs/evidence/native-development-pilot-2026-10-19.md) now records those outcomes, with verified cleanup and no candidate benefit. The
[serial reservation gate](docs/decisions/evaluation-accounting.md#serial-native-launch-reservations)
now binds ordered initial turns, declared phase-time and observed soft-token
accounting. It does not impose a hard provider budget. The [declared-catalog routing and client-model component](docs/decisions/evaluation-accounting.md#declared-catalog-routing-and-client-model-observations)
admits bound receiver records offline only with matching source-bound qualification;
the completed bounded EN/KO development pilot found no routing gain and one artifact regression. An optional [same-host scope declaration](docs/decisions/evaluation-accounting.md#optional-same-host-scope-declaration)
is explicitly unverified, with no custody or unseen-case claim. The trusted host controller keeps
normal account access; no external evaluator environment is required.

The [source-review recommendation guide](docs/decisions/promotion-recommendations.md)
documents the diagnostic gate, native report/committed-object verification and
selected same-host evidence verifier. The [workflow diagram](docs/architecture/native-recommendation-workflow.html)
shows optional preflight and read-only recommend/reject/inconclusive paths. Positive
FAKE conformance is not actual improvement; the actual fixed comparison returned reject, with no candidate acceptance.
Recommendations never authorize source acceptance, merge or installation.

The [implementation handoff](docs/decisions/account-improvement-loop.md#implementation-handoff-and-evidence-boundaries)
links the remaining result-collection, grading, pilot, same-host held-out evaluation and delivery work.
The [held-out protocol](docs/decisions/account-improvement-loop.md#same-host-held-out-evaluation)
uses fresh contexts on the current host/account; additional hosts, accounts and
external custodians are not required. Its selected receipt verifier is implemented;
actual pack preparation and comparison remain pending. Candidate freezing is
separate; these conformance fixtures do not create a real candidate. Account
application remains deferred pending maintainer direction.
It distinguishes a completed development experiment from an eligible candidate:
no improvement is a valid result, and neither fixture tests nor a recommendation
authorize account activation.

## Principles

- **Keep shared instructions small.** Put durable defaults in policies and load
  task-specific detail through skills and references when needed.
- **Clarify consequential uncertainty.** Resolve questions that change the
  outcome or scope; handle routine implementation choices within the request.
- **Compose focused skills.** Give each skill a clear job, dependencies, and a
  result that can be checked. Add coordination only when the work needs it.
- **Verify the outcome.** Inspect the actual artifact or behavior. Use focused
  tests, reproductions, or direct checks, and report limits in the evidence.
- **Preserve local ownership.** Keep authentication, personal preferences, and
  machine-specific values local. Updates should preserve unrelated settings and
  surface conflicts before replacing them.
- **Improve from observed friction.** Capture reusable lessons when they help
  future work. Prefer a structural fix or an executable check when it can prevent
  a recurring mistake.

[Pull request CI](.github/README.md) documents the repository checks and their scope.

## Working loop

```text
Understand the request → Inspect the context → Execute → Verify → Report
                                                  ↑               |
                                                  └── Adjust ─────┘
```

Scale the process to the task. A small edit may need only a direct change and a
check. Work spanning multiple stages or sessions benefits from a written plan,
current progress, and a clear next action.

For software work, clarify the intended behavior, settle important design choices,
build in small verifiable steps, and review the change against the request. A bug
fix should have a reproduction and evidence that the fix resolves it. Use a
regression test when a practical test path exists.

Completion means the requested result has been checked. A report should say what
changed, how it was verified, and what remains unresolved. Save additional records
when they support review, resumption, or a reusable improvement.

## Configuration boundaries

The proposed configuration model separates three kinds of information:

| Scope | Examples |
| --- | --- |
| Shared source | Common policies, maintained skills, upstream provenance, and credential-free MCP definitions. |
| Project | Repository instructions, domain terminology, build and test commands, and task records. |
| Account or machine | Credentials, authentication state, personal preferences, local paths, and environment-specific overrides. |

Maintain shared changes in the source repository and distribute them through a
reviewable update. Installation should show what it owns and which revision it
delivered. Runtime checks should then confirm that the client discovers the skills
and can use the intended MCP capabilities.

## What belongs in public Git

This is a public repository. Commit material that another person can review and
reuse without access to a contributor's accounts or private environment.

| Commit | Examples |
| --- | --- |
| Repository documentation and instructions | README, AGENTS.md, CLAUDE.md, licenses, and reviewed design decisions. |
| Reusable policies and skills | Portable instructions, SKILL.md files, supporting scripts, references, and redistributable assets. |
| Sanitized configuration | MCP definitions with public endpoints or placeholders, environment variable names, and examples containing synthetic values only. |
| Reproducible maintenance material | Setup scripts, meaningful tests, dependency locks, upstream revisions, attribution, and documented patches when added. |

### Keep local and untracked

| Do not commit | Examples and location |
| --- | --- |
| Secrets and authentication state | API keys, access/refresh tokens, passwords, cookies, OAuth state, private keys, and client certificates. Keep these in a credential store or the account environment. |
| Effective account configuration | MCP configurations containing credentials, private endpoints, account IDs, or personal absolute paths. Keep local overrides outside the checkout or under `.local/`. |
| Personal agent overrides | `CLAUDE.local.md`, `.claude/settings.local.json`, `.codex/config.local.toml`, and `.mcp.local.json`. |
| Working plans and session state | `.planning/`, raw conversations, agent memory, scratch notes, and handoff records. Use `.local/` for other local working files. |
| Raw evidence and backups | Logs, screenshots, recordings, configuration backups, and diagnostic exports. Use `.local/`, `artifacts/`, `backups/`, or `tmp/`. |
| Generated environment files | Dependency directories, build output, caches, and OS metadata. |

The local directories above are ignored by Git. They are storage conventions,
not secure credential stores. Keep durable decisions in reviewed documentation;
publish examples or evidence only after removing private data and confirming that
they may be shared.

`.env` and `.env.*` are ignored, with `.env.example` allowed for synthetic
examples. Use names such as `SERVICE_API_TOKEN` to describe required credentials;
never include their values. Private service addresses and personal paths should
be replaced with placeholders such as `https://service.example/mcp` and
`/path/to/tool`.

Before committing, inspect the staged diff and newly added files against these
boundaries. Ignore rules do not inspect file contents or remove files already
tracked by Git. Keep local files out of commits rather than force-adding them.

## Selecting upstream skills

Adopt skills for a concrete need encountered in real work. Before adding one,
check its trigger, expected output, dependencies, supported environment, license,
and overlap with existing skills.

Record the source and selected revision. Keep upstream work distinguishable from
local policy, and document adaptations so later updates can be reviewed. Evaluate
a skill on a representative task before treating it as a shared default.

## References and influences

Selected skills and adaptations from these projects are included. Per-package
provenance records exactly which material is present; their whole plugin ecosystems
and account installers are not automatically activated.

| Reference | What this draft draws from |
| --- | --- |
| [pstack](https://github.com/cursor/plugins/tree/main/pstack) | Engineering rigor, task routing, small changes, and direct evidence that the result works. |
| [Matt Pocock's skills](https://github.com/mattpocock/skills) | Small composable skills, intent clarification, shared domain language, and short feedback loops. |
| [Addy Osmani's agent skills](https://github.com/addyosmani/agent-skills) | Separation of workflows, personas, and entry commands; explicit repository-only instruction scope and attention to skill packaging boundaries. |

The [repository research instructions](AGENTS.md#external-research-is-part-of-this-project)
define the preference tie-breaker, community-feedback checks for individual skills and
workflows, and how to select alternatives.
The structure decision also compares other
maintained repositories, with source revisions and tradeoffs recorded.

The [pstack map](https://erictechpro.github.io/super-board/pstack/) and
[Matt Pocock skills map](https://erictechpro.github.io/super-board/mattpocock/)
helped compare workflow stages and coverage gaps. They are secondary navigation
guides; use the upstream repositories to verify current behavior and dependencies.

Technical references:

- [Agent Skills specification](https://agentskills.io/specification) for skill
  structure and loading supporting material on demand.
- [MCP architecture](https://modelcontextprotocol.io/docs/learn/architecture) for
  connecting clients to tools, resources, and prompts.
- [Cursor plugin documentation](https://cursor.com/docs/plugins) for client-specific
  packaging of skills, rules, hooks, and MCP integrations.

## License

[MIT](LICENSE).
