# Repository feature verification map

This is the authoritative recipe index for the repository verifier's declared
pilot scope. It maps user-visible behavior, not package implementation internals.
Use [the verifier](../SKILL.md) for shared prerequisites, invocation and cleanup.

| Feature / scenario ID | User goal | Surface | Recipe |
| --- | --- | --- | --- |
| catalog-search | Find a verification capability and recover from an empty search | Local HTML UI | [Search](catalog-search.md) |
| catalog-source | Read usage and reach the corresponding maintained source | Local HTML UI and file links | [Usage and source](catalog-source.md) |
| workflow-map | Follow SDLC stages and find cross-stage methods | Separate local HTML UI | [Workflow map](workflow-map.md) |
| account-installation | Install, update, remove and recover owned account content | Python CLI / disposable accounts | [Account lifecycle](account-installation.md) |
| account-verification | Diagnose setup and exercise installed sources through an actual model; optional Paseo | CLI / native clients | [Account verification](account-verification.md) |
| native-observation | Opt in one project, verify metadata/attribution/capacity and revoke it | Observation CLI / installer / Claude and Codex hooks | [Native observations](native-observation.md) |
| native-isolation | Qualify a synthetic native client and tool inside an outer OS boundary | Python CLI / existing Docker host | [Native isolation](native-isolation.md) |
| native-trials | Check frozen selected inputs, run one authorized trial, and reconcile exact owned residue | Python CLI / pinned native profile and existing Docker host | [Native trials](native-trials.md) |
| evaluation-accounting | Freeze development evidence and account for every scheduled trial | Offline Python CLI | [Evaluation accounting](evaluation-accounting.md) |
| task-feedback | Bind selected observations, record feedback and revoke private task state | Synthetic CLI / disposable home | [Task feedback](task-feedback.md) |
| reviewed-cases | Prepare, inspect, review and export a synthetic development case | Case CLI / disposable home | [Reviewed cases](reviewed-cases.md) |
| sdlc-intake | Select the next SDLC action and reuse current work | Native client / synthetic local projects | [Intake behavior](sdlc-intake.md) |
| map-freshness | Determine whether the generated map matches maintained metadata | Python CLI | [Freshness](map-freshness.md) |

Evidence is per run, outside this source. No last-run status is stored in the map;
source availability is not runtime success. Link IDs to SDLC scenarios when this
verifier is used in that workflow. Screenshots may feed the existing manual process.
The collection's [interactive map](../../../map/index.html) links these recipes;
it is a navigation view, not a second copy of their expected behavior.

The separate workflow-map recipe covers its own theme, mobile layout, dialogs, canvas controls and
search; those checks do not certify the original catalog viewer.

Unmapped for the original viewer: theme, zoom, keyboard navigation, responsive layouts, all filter
combinations, PDF generation, native client activation, MCP and constituent skill behavior.
These require their own checks when affected; this seed does not certify them.

- [Promotion recommendation](promotion-recommendation.md): deterministic evidence binding and refusal paths.
