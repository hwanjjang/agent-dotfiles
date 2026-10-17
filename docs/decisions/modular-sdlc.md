# Modular AK SDLC proposal

Status: Proposed overall workflow design. Initial skill packages are now included;
see the skill catalog. The complete modular SDLC integration and target-client
orchestration remain unverified.

Investigated: 2026-10-17. This proposal combines public upstream patterns with
the requested direction: stronger preparation, parallel implementation, and
independently usable stages. It does not reproduce a private implementation.

## Direction

Make each stage useful on its own. Compose those same stages through a thin SDLC
orchestrator when the task spans a lifecycle. Keep task routing, scheduling, and
stage methods under separate ownership; the orchestrator must not duplicate the
methods it invokes.

The proposed flow is:

```text
intent <-> research -> spec -> design -> plan -> implement -> verify -> review
                                 |                  ^          |        |
                      independent candidates        +-- fix ---+--------+
                                 |
                      compare, test, select
```

Integration and delivery use the authorized endpoint. Directly invoking design,
review, or verification does not start implementation or publication implicitly.
The pstack mode referenced in this comparison is named `poteto-mode` upstream.

## Stage boundaries and direct use

These are proposed responsibilities, not installed command names. Each stage
accepts existing evidence from other tools or people when it satisfies the input
contract; running every earlier stage is not a prerequisite.

| Stage | Minimum input | Observable output and stop point |
| --- | --- | --- |
| Intent | Request and known constraints | Outcome, actors, scenarios, exclusions, decisions, and unresolved questions. |
| Research | A question and relevant context | Source-backed findings, revision or date, uncertainty, and implications. |
| Spec | Agreed outcome and relevant facts | Observable behavior, acceptance criteria, failure cases, and exclusions. |
| Design | Behavior contract and system context | Interfaces, ownership, alternatives, selection rationale, and validation evidence. |
| Plan | Accepted behavior and sufficient design | Verifiable vertical slices, dependency graph, write ownership, and integration checks. |
| Implement | One ready task and its contracts | Scoped change with tests, exact revision, deviations, and a handoff report. |
| Verify | Artifact revision and required outcomes | Evidence per criterion, failures, and coverage gaps. |
| Review | Exact diff plus spec and applicable standards | Findings separated by requirement fidelity and engineering quality. |
| Orchestrate | Requested outcome, scope, endpoint, and existing evidence | Route and schedule stages, record decisions, integrate results, and stop at the endpoint. |

Every skill should declare its trigger, required inputs, dependencies, owned
outputs, completion criteria, authority limits, and behavior when an input is
missing or stale. A direct invocation can request a material missing input or
offer the preceding stage; it must not invent that stage's result. Shared
contracts have one source. Required resources ship with the skill or an explicit,
verified dependency bundle. Avoid an all-purpose core package that makes every
stage depend on the whole lifecycle.

The task router selects a playbook; the coordinator schedules work; stage skills
own their methods. Workers return results to the coordinator. Nested coordinators
need a concrete scale benefit and explicit ownership, rather than being the
default hierarchy. Use the host's available execution tools; do not introduce a
new scheduling service merely to express this workflow.

## Preparation: use grilling before commitment

Matt's current [grilling primitive][grilling] traverses a decision tree in rounds:
ask decisions whose prerequisites are settled, then recompute the frontier from
the answers. It distinguishes facts the agent can discover from decisions the
user owns. [grill-me][grill-me] is a thin entry point;
[grill-with-docs][grill-docs] adds domain modeling.

Adapt that method into intent preparation:

1. Inspect available context and research discoverable facts first.
2. Identify questions that change the outcome, scope, acceptance criteria, or a
   consequential tradeoff. Include user journeys, failure and recovery behavior,
   operating constraints, and non-goals where relevant.
3. Ask a manageable set of independent questions with recommendations and their
   consequences. Defer questions that depend on unanswered decisions.
4. Preserve decisions, assumptions, open questions, and shared terminology in the
   task's own record. Record durable architectural decisions separately when useful.
5. Finish when consequential uncertainty is resolved or explicitly bounded and
   the outcome can be verified. Reuse decisions already made in the conversation.

This is a deliberate adaptation: do not import an unbounded interview into every
small edit or require repeated confirmation of an already authorized scope.
Dedicated grilling sessions may be deeper. If research or a prototype changes a
premise, reopen the affected decisions and downstream artifacts, not the whole
conversation. Keep unresolved decisions visible rather than silently choosing
for the user.

## Design: independent proposals, one selected contract

For consequential design choices, propose three distinct providers working from
the same frozen brief, constraints, revision, and evaluation criteria. Three
providers is a local policy proposal, not an upstream requirement: pstack's
inspected [architect][architect] defaults to two configured model runners.

Require structurally distinct alternatives. Compare caller usage, data and state
ownership, failure behavior, interface simplicity, migration cost, and testability.
Use independent judging and targeted experiments for disputed empirical claims.
The lead selects a base and compatible improvements, records rejected alternatives,
and verifies the synthesized design. Agreement between models is not verification.
Small, well-understood changes can use one design with proportionate checks.

## Parallel implementation contract

Combine Matt's [task-graph frontier and integration branch][implement-spec] with
pstack's [throughput checkpoint][feature] and [scoped worker results][swarm].
Implementation partitions one chosen design; design races compare alternatives.
Do not combine competing implementations as though they were independent slices.

1. **Decompose around outcomes.** Prefer thin end-to-end behavior slices. State
   dependencies explicitly. File separation alone does not prove independence:
   interfaces, schemas, migrations, generated files, and external test resources
   may still couple the work.
2. **Establish shared contracts first.** Settle shared interfaces and ownership
   before dependent workers start. Assign each shared writable artifact one owner;
   separate mutable state where practical and serialize changes where invariants
   require it.
3. **Dispatch only ready work.** A task becomes ready when its prerequisites have
   been verified and integrated into the designated baseline. Use bounded
   concurrency based on actual independent work and host capacity. Refill open
   slots as tasks become ready rather than waiting for unrelated workers.
4. **Isolate writes and records.** Give each implementation worker its own branch
   and worktree, task ID, and output namespace. Give shared databases, ports, and
   test fixtures independent instances or explicit serialized access. Do not
   let concurrent tasks overwrite a global plan or status file.
5. **Send a complete brief.** Include task ID, input revisions, spec/design
   pointers, owned scope, dependency results, acceptance criteria, checks,
   allowed actions, and required report. Missing capability or material ambiguity
   must be reported; a worker must not expand its permissions or ownership.
6. **Require evidence at handoff.** Return the exact revision, changed scope,
   checks and results, contract deviations, and unresolved risks. An announcement
   that work was delegated is not completion. Missing coverage is not a pass.
7. **Use one integration writer.** A designated integrator consumes completed
   changes serially. Reconcile with the current baseline, inspect conflicts and
   semantic interaction, then rerun affected checks on the integrated revision.
   A worker's earlier passing result does not attest the new integration state.
8. **Recover selectively.** Stop or replan descendants of a failed task; let
   unrelated work continue. On a changed shared contract, invalidate affected
   downstream evidence. Record retries and bounds. Resume from verified state
   without duplicating completed work; preserve unintegrated work until resolved.

For example, an agreed notification contract can unlock independent email and
in-app delivery slices. Their separate worktrees still share behavior constraints.
An end-to-end retry test starts only after both implementations are integrated.
The final combined revision must demonstrate the complete user scenario.

When only one safe workstream exists, use one implementer and explain the coupling.
Provider diversity is useful for competing designs and independent reviews;
implementation workers should be selected for task fit, capability, and cost.

## Evidence and adoption choices

All three inspected projects carry MIT licenses at the paths linked below.
This note adopts concepts; it vendors no upstream skill text or executable code.
Future ports must retain notices and record dependencies and local adaptations.

| Source | Selected revision | Adopt first |
| --- | --- | --- |
| [pstack][pstack] ([license][pstack-license]) | `ac4e25a0064cd600afdd605208bad72748cb019a` | Grounding, alternative designs, scoped parallel workers, and evidence-based synthesis. |
| [Matt Pocock][matt] ([license][matt-license]) | `49dd158d1076134a641b33efb035946536778336` | Decision-tree interviewing, composable stages, vertical slices, and dependency-frontier execution. |
| [Addy Osmani][addy] ([license][addy-license]) | `aeac41d4d005999432bb7312f7ff06383a91d59d` | Explicit completion criteria, direct stage invocation, focused review perspectives, and shallow orchestration. |

Addy's [orchestration catalog][orchestration] distinguishes direct use, independent
parallel reports, and coordinated investigation. Use these distinctions to avoid
turning every stage into a hierarchy of agents. As another comparison,
[Superpowers' dispatch skill][superpowers] limits parallel dispatch to independent
problem domains. Neither parallel research nor parallel review alone establishes
a safe implementation scheduler.

Public feedback informs adoption, but does not establish measured superiority:

- A [grill-me user report][grill-feedback] describes value in challenging plans.
  A [dependency issue][grill-dependency] also reports that installing the wrapper
  without its primitive fails. Test direct invocation with declared dependencies.
- A [pstack user report][pstack-feedback] praises workflow rigor and efficiency.
  Treat that as anecdotal interest, not a benchmark or a reason to copy every rule.
- An [Addy community post][addy-feedback] highlights lifecycle discipline.
  [Parallel-plan overwrite reports][parallel-feedback] and
  [duplicated review-method reports][duplication-feedback] identify useful failure
  cases: isolate task state and keep methods under one authority. These are
  reported experiences, not claims that every current version reproduces them.

## Implementation sequence and acceptance

First implement intent/research/spec with explicit inputs and outputs. Next add
design selection and planning contracts, then a single-task implementer and
verification/review. Add bounded parallel coordination over those working stages.
The final SDLC entry point composes them instead of introducing another copy.

Before declaring this workflow usable, demonstrate:

- Each stage works directly with supplied artifacts and its declared dependencies.
- The orchestrator invokes the same method and respects the requested stop point.
- Independent implementation slices overlap; dependent slices wait for verified
  integration; conflicting shared writes have a single owner.
- A failed worker, stale base, changed interface, missing dependency, and interrupted
  run each produce an observable recovery path without fabricated success.
- The integrated user scenario passes, not just each worker's isolated tests.

Compare representative tasks with the previous single-worker approach using
elapsed time, total cost, rework, integration conflicts, and escaped defects.
Do not infer benefit from agent count, popularity, or successful Markdown parsing.
When skills are implemented, map each skill's invocation, prerequisites, outputs,
and relationships; keep this proposal distinct from executable capability.

[pstack]: https://github.com/cursor/plugins/tree/ac4e25a0064cd600afdd605208bad72748cb019a/pstack
[matt]: https://github.com/mattpocock/skills/tree/49dd158d1076134a641b33efb035946536778336
[addy]: https://github.com/addyosmani/agent-skills/tree/aeac41d4d005999432bb7312f7ff06383a91d59d
[pstack-license]: https://github.com/cursor/plugins/blob/ac4e25a0064cd600afdd605208bad72748cb019a/pstack/LICENSE
[matt-license]: https://github.com/mattpocock/skills/blob/49dd158d1076134a641b33efb035946536778336/LICENSE
[addy-license]: https://github.com/addyosmani/agent-skills/blob/aeac41d4d005999432bb7312f7ff06383a91d59d/LICENSE
[grilling]: https://github.com/mattpocock/skills/blob/49dd158d1076134a641b33efb035946536778336/skills/productivity/grilling/SKILL.md
[grill-me]: https://github.com/mattpocock/skills/blob/49dd158d1076134a641b33efb035946536778336/skills/productivity/grill-me/SKILL.md
[grill-docs]: https://github.com/mattpocock/skills/blob/49dd158d1076134a641b33efb035946536778336/skills/engineering/grill-with-docs/SKILL.md
[architect]: https://github.com/cursor/plugins/blob/ac4e25a0064cd600afdd605208bad72748cb019a/pstack/skills/architect/SKILL.md
[feature]: https://github.com/cursor/plugins/blob/ac4e25a0064cd600afdd605208bad72748cb019a/pstack/skills/poteto-mode/playbooks/feature.md
[swarm]: https://github.com/cursor/plugins/blob/ac4e25a0064cd600afdd605208bad72748cb019a/pstack/skills/swarm/SKILL.md
[implement-spec]: https://github.com/mattpocock/skills/blob/49dd158d1076134a641b33efb035946536778336/skills/engineering/implement-spec/SKILL.md
[orchestration]: https://github.com/addyosmani/agent-skills/blob/aeac41d4d005999432bb7312f7ff06383a91d59d/references/orchestration-patterns.md
[superpowers]: https://github.com/obra/superpowers/blob/bb92a77741419a4ab5f06e711a283343f1ada0c3/skills/dispatching-parallel-agents/SKILL.md
[grill-feedback]: https://www.linkedin.com/posts/mistertest_i-am-using-matt-pococks-grill-me-skill-with-activity-7442808343947038720-V4i6
[grill-dependency]: https://github.com/mattpocock/skills/issues/685
[pstack-feedback]: https://www.reddit.com/r/cursor/comments/1wrmig0/killer_combo_cursor_projects_pstack_huge/
[addy-feedback]: https://www.reddit.com/r/WebAfterAI/comments/1tb2w7q/google_chrome_engineer_addy_osmanis_agent_skills/
[parallel-feedback]: https://github.com/addyosmani/agent-skills/issues/518
[duplication-feedback]: https://github.com/addyosmani/agent-skills/issues/172
