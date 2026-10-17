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
| Investigation and design | how, architect, arena, diagnosing-bugs |
| Planning and execution | planning-and-task-breakdown, planning-with-files, swarm, sdlc |
| Verification, review and issues | tdd, code-review-and-quality, issue-writing |
| Instruction authoring | writing-for-agents |
| Diagrams and user manuals | archify, screenshot-manual |

`grill-me` requires `grilling`; `grill-with-docs` also requires `domain-modeling`.
`architect` uses `how` and `arena`; `diagnosing-bugs` uses `tdd` for authorized
corrections. SDLC selects methods through its
[stage routing](sdlc/references/skill-routing.md); its provenance lists the full
skill dependency group, whose transitive resources must remain available.
All declared packages are present. Only applicable methods run on a given task.

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
preserve upstream invocation behavior. Codex's strict skill-creator validator
rejects those extensions; do not claim uniform client compatibility from the
common name/description schema. Matt's supplied agents/openai.yaml files retain
its Codex invocation policies. Codex 0.159.2 discovered all 18 packages in a temporary project; see
[client verification](../docs/client-verification.md). Hook activation, automatic
selection, other clients and end-to-end provider execution remain unverified.

The portable pstack adaptations remove hardcoded Cursor Task APIs and model IDs.
They report unavailable worker/provider capabilities instead of fabricating an
independent result. The AK SDLC now routes stages to these methods and validates their evidence modes.
End-to-end provider execution remains a separate target-host check.

Archify and planning-with-files retain the existing selected baseline revisions.
Newer upstream revisions were observed but are not silently substituted. Hooks
and installers included in upstream packages are source assets; importing them
does not authorize running them or modifying account settings.

See [adoption records](../docs/upstream/README.md) before updating a package.
