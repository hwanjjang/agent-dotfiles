---
name: architect
description: Explore architectural alternatives and produce a selected interface and ownership design before consequential implementation.
disable-model-invocation: true
---

# Architect

Input: intended behavior, scenarios, constraints, and existing system context.
Output: caller usage, types and signatures, ownership boundaries, failure behavior,
selection rationale, and open questions. Stop at the design unless implementation
is already part of the authorized request.

Dependencies: `how` for unfamiliar system context; `arena` for independent
candidate comparison. Load those installed skills by name, or their sibling
SKILL.md files in this source checkout. Missing dependencies must be reported.

## Phase A: Ground the problem

Use `how` to trace the affected subsystem. Inspect history when changing ownership
or layering. Reuse adequate existing evidence; greenfield work may need no source
walkthrough. Resolve consequential missing requirements before committing to a shape.

## Phase B: Sketch and select

For consequential decisions, use `arena` with three providers when available and
permitted. Three is this adaptation's preferred panel, not an upstream default.
Record actual capability and any agreed reduction. A small, settled design may
use a single sketch and direct verification without claiming independent selection.

Give each candidate [the runner brief](references/runner-prompt.md), the frozen
requirements, and an isolated output location. Require structurally different
alternatives. Screen them against [design red flags](references/design-red-flags.md).
Compare interface depth, state ownership, testability, migration and operational cost.

Record the selection using [the rationale](references/rationale-template.md).
Use [bounded feasibility experiments](references/feasibility-experiments.md)
for disputed empirical claims that source inspection cannot resolve. The resulting design
must remain coherent after combining compatible improvements.

## Handoff

Confirm the sketch satisfies the specified scenarios and explains error/recovery
behavior. Identify assumptions needing validation. Respect a requested checkpoint;
reuse decisions and authorization already given. Hand the selected design to
planning or implementation only within the requested scope.

If implementation exposes repeated structural contradictions, revisit the affected
requirements and design rather than accumulating workarounds. Invalidate dependent
plans and evidence when the contract changes.

Source and local adaptations: [provenance](provenance.json). License: [MIT](LICENSE).
