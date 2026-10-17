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
| Investigation and design | how, architect, arena |
| Planning and execution | planning-and-task-breakdown, planning-with-files, swarm, sdlc |
| Review and issues | code-review-and-quality, issue-writing |
| Diagrams and user manuals | archify, screenshot-manual |

`grill-me` requires `grilling`; `grill-with-docs` requires both `grilling` and
`domain-modeling`. `architect` requires `how` and `arena`. The imported SDLC
requires planning-with-files, archify, and screenshot-manual for applicable work.
These packages are all present. Other references are optional context or explicit
capability requirements, not silently installed tools.

Some upstream frontmatter uses Claude-specific fields such as
`disable-model-invocation`, `user-invocable`, and `hooks`. They are retained to
preserve upstream invocation behavior. Codex's strict skill-creator validator
rejects those extensions; do not claim uniform client compatibility from the
common name/description schema. Matt's supplied agents/openai.yaml files retain
its Codex invocation policies. Client discovery, hook activation, provider routing,
and end-to-end multi-agent execution still require target-client checks.

The portable pstack adaptations remove hardcoded Cursor Task APIs and model IDs.
They report unavailable worker/provider capabilities instead of fabricating an
independent result. The AK SDLC is an imported baseline; the modular design proposal
is not yet a fully integrated replacement for its stage contracts.

Archify and planning-with-files retain the existing selected baseline revisions.
Newer upstream revisions were observed but are not silently substituted. Hooks
and installers included in upstream packages are source assets; importing them
does not authorize running them or modifying account settings.

See [adoption records](../docs/upstream/README.md) before updating a package.
