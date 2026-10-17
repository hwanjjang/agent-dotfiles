---
name: planning-and-task-breakdown
description: Turn an existing spec or clear requirements into verifiable vertical slices, task dependencies, reviewable PR boundaries and implementation briefs.
---

# Planning and Task Breakdown

Input: intended behavior, acceptance criteria, relevant design and repository facts.
Output: an ordered task graph, appropriate PR boundaries and implementation/verification handoffs.
This skill writes plans, not production code. Reuse existing decisions and plans.

1. Inspect relevant source and constraints. Identify unknowns that change the
   decomposition. Research discoverable facts; ask for consequential user decisions.
2. Split into thin end-to-end outcomes. Establish shared contracts before their
   consumers. Record dependency edges and reject cycles or resolve their ownership.
   For wide refactors, expand compatibly, migrate callers, then remove the old
   contract. If internal steps cannot stay green, group them behind a verified
   integration boundary instead of presenting them as independent merge units.
3. Give every task a stable ID, outcome, acceptance criteria, input references,
   dependencies, owned write scope, checks, integration requirements, and allowed
   actions. Size by coherent verifiable behavior, not a fixed file-count limit.
4. For work headed to PRs, follow the [PR policy](../../policies/pr-workflow.md).
   A single coherent PR needs only a stated boundary. For multiple PRs, record
   each purpose, included task IDs, owned scope, dependencies, intended base and
   verification. Apply that policy's merge-unit and base rules to the map; reuse
   an adequate existing map rather than maintaining a competing decomposition.
5. Mark the ready frontier. Separate independent work from shared writes and
   ordering constraints. Specify one integration owner and the checks that unlock
   descendants. Use `swarm` only when implementation is authorized and parallel
   workers are available; this planning invocation ends with the plan.
6. Put task state in the project's existing task-scoped location. In a new project,
   prefer an ignored `.planning/<task-id>/` directory. Reuse the same task's record;
   never overwrite another task's unfinished plan. Keep one task-status authority.
7. Use an external tracker only when authorized. Otherwise keep local tasks. If a
   tracker owns task status, the plan links to its items rather than duplicating it.
8. Trace every source commitment, acceptance criterion, failure scenario and
   integration boundary to an owning task and verification. Explicitly assign
   connecting paths between prepared contracts, readers and user-facing consumers;
   a prep task names the later completion owner. Repair missing coverage before
   producing tickets. Honor requested approval checkpoints; do not ask again
   for decisions or scope already approved.

A useful task handoff contains:

- Outcome and acceptance criteria.
- Dependencies and input revisions.
- Ownership boundaries and shared contract references.
- Focused tests or direct verification and the integrated scenario to check.
- Open questions, assumptions, and conditions requiring replanning.

Report the critical path, available parallelism, verification checkpoints, and
unresolved blockers. A plan is complete when the work can be assigned without
inventing requirements, every intended outcome has a verification path, and any
planned PR sequence has coherent, verifiable merge units. Ticket materialization
uses the separate `to-tickets` adapter; it must consume this plan rather than
create a competing decomposition.

Source and local adaptations: [provenance](provenance.json). License: [MIT](LICENSE).
