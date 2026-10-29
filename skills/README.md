# Skill source catalog

This checkout contains selected upstream skill packages and AK-authored workflows.
Each package has SKILL.md, its required resources, LICENSE, and provenance.json.
Use the interactive map to inspect invocation, dependencies, outputs, and status.

The files are source packages, not an account installation. Load a SKILL.md from
this checkout when explicitly working with it, or install a selected package and
its declared dependencies through the destination client's supported mechanism.
Do not copy this repository's root AGENTS.md as a shared policy.

| Capability | Packages |
| --- | --- |
| Intent and language | grill-me, grilling, grill-with-docs, domain-modeling |
| Specification | to-spec |
| Investigation and design | how, architect, arena, diagnosing-bugs |
| Planning and execution | planning-and-task-breakdown, planning-with-files, swarm, sdlc |
| Verification construction and maintenance | create-verification-skill, maintain-verification-skill, create-formal-verification-skill, maintain-formal-verification-skill, statechart |
| Verification, review and issues | tdd, code-review-and-quality, make-pr-easy-to-review, issue-writing, to-tickets |
| Instruction authoring | writing-for-agents |
| Research evidence | grounded-citations |
| Diagrams and user manuals | archify, screenshot-manual |

`grill-me` requires `grilling`; `grill-with-docs` also requires `domain-modeling`.
`to-tickets` also consumes `to-spec`'s shared document/meeting source-extraction
reference; keep that package available even when writing only ticket drafts.
`architect` retains ownership of its conditional feasibility-experiment reference.
`grounded-citations` requires Python 3.10+ and explicit task-local `--ledger` state;
it has no Hermes runtime or automatic retrieval dependency.
`create-formal-verification-skill` links `create-verification-skill`, `tdd`,
`diagnosing-bugs`, optional `archify`, `statechart` for TLA+ results and its maintenance pair;
`maintain-formal-verification-skill` links `tdd`, `diagnosing-bugs` and its creator.
Neither bundles or installs a verifier. `statechart` bundles a TypeScript compiler
that runs TLC on a TLA+ model and needs Node.js 22.18+ (or Bun or Deno) and Java
with tla2tools; see its [provenance](statechart/provenance.json).
`architect` uses `how` and `arena`; `diagnosing-bugs` uses `tdd` for authorized
corrections. SDLC selects methods through its
[stage routing](sdlc/references/skill-routing.md); its provenance lists the full
skill dependency group, whose transitive resources must remain available.
All declared packages are present. Only applicable methods run on a given task.

`to-spec` owns specification synthesis and its content contract. AK SDLC passes
stage inputs and assesses the returned artifact; standalone use needs no SDLC
state or tracker. The [extraction decision](../docs/decisions/spec-extraction.md)
records the source comparison and removed duplicate checklists.

`planning-and-task-breakdown` owns the task graph and PR boundaries. `to-tickets`
consumes that plan and uses `issue-writing` for bodies; `make-pr-easy-to-review`
handles author preparation before independent review. These standalone skills
use the [PR policy](../policies/pr-workflow.md) and existing issue lifecycle; the
[decision record](../docs/decisions/pr-workflow.md) explains source selection and
community limits. Keep their declared shared policies and skill dependencies
available when distributing them; neither package installs a tracker or stack tool.

`tdd` is the single testing method, adapted from pstack with local feature and
refactor branches. SDLC owns receipt validation and integrated smoke, not a second
TDD workflow. The [adoption decision](../docs/decisions/skill-integration.md) explains
exceptions and selection evidence. Skills with shared-policy references require
those policy files when distributed; copying only their folders is insufficient.

`issue-writing` and `sdlc` also require the shared
[issue workflow policy](../policies/issue-workflow.md) and its linked policy
resources. Keep those references resolvable when distributing either package;
copying only its skill folder is insufficient. `policy_dependencies` in each
package's provenance records this requirement. The policy is also usable directly
without SDLC; it introduces no tracker runtime or write permissions.

Some upstream frontmatter uses Claude-specific fields such as
`disable-model-invocation`, `user-invocable`, and `hooks`. They are retained to
preserve upstream invocation behavior. The pstack verification and formal
verification pairs instead drop upstream `disable-model-invocation`; the formal pair
relies on a narrow explicit-request description
([decision](../docs/decisions/formal-verification.md)). `statechart` keeps it
([decision](../docs/decisions/statechart.md)). Codex's strict skill-creator validator
rejects those extensions; do not claim uniform client compatibility from the
common name/description schema. Matt's supplied agents/openai.yaml files retain
its Codex invocation policies. Codex 0.159.2 previously discovered the initial 18 packages in a temporary project; see
[client verification](../docs/client-verification.md). Hook activation, automatic
selection, other clients and end-to-end provider execution remain unverified.

The portable pstack adaptations remove hardcoded Cursor Task APIs and model IDs.
They report unavailable worker/provider capabilities instead of fabricating an
independent result. The AK SDLC now routes stages to these methods and validates their evidence modes.
End-to-end provider execution remains a separate target-host check.

planning-with-files retains its existing selected baseline revision. Archify moved to
v3.2.0 on 2026-10-21; see its update record in [docs/upstream](../docs/upstream/README.md).
Newer upstream revisions are not silently substituted. Hooks
and installers included in upstream packages are source assets; importing them
does not authorize running them or modifying account settings.

See [adoption records](../docs/upstream/README.md) before updating a package.

The selected POSIX planning runtime now lives in [account/hooks](../account/hooks/README.md)
with pinned provenance and inactive client templates. The skill source stays here
as its single dependency. [Account instructions](../account/instructions.md) link
to communication and execution policies without copying them into every skill.
SDLC's existing [host adapter contract](sdlc/references/host-adapters.md) now owns
reviewer continuity as well; account exceptions remain local.
