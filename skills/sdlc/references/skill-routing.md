# Stage-to-skill routing

This table is the authoritative skill routing for AK SDLC. The coordinator owns
stage selection, task state, authority and handoff; each selected skill owns its
method. It does not introduce additional stages or require every skill on every
task. Preserve the existing non-PR scope rule: focused skills can run directly
without initializing the SDLC state machine.

Resolve skills from the host catalog or this checkout's sibling directories. Read
the actual SKILL.md before use and record the resolved source with the stage's
inputs. Source files can be read directly when native invocation is unavailable;
report that fallback instead of claiming installed discovery. Missing required
methods or host capabilities remain explicit gaps; never silently download tools.

| Stage | Trigger and skill | Handoff |
| --- | --- | --- |
| intent | Use [grill-me](../../grill-me/SKILL.md) for consequential unresolved intent early; use [grill-with-docs](../../grill-with-docs/SKILL.md) instead when durable domain terms or ADRs are needed. Both use grilling; the latter also uses domain-modeling. Reuse settled answers. | Outcome, exclusions, constraints, acceptance criteria and remaining decisions. Stop questioning once the task is actionable; implementation choices supported by source need no user interview. |
| investigation | [how](../../how/SKILL.md) for unfamiliar behavior or ownership; [diagnosing-bugs](../../diagnosing-bugs/SKILL.md) for difficult defects or uncertain regressions. | Source-backed flow, reproduction, facts/hypotheses and limits. Diagnosis does not implement while investigation is still review-only or plan-only. |
| spec | Synthesize clarified requirements and investigation into the canonical spec. Reuse domain-modeling only for terms/decisions that need durable records. | Observable behavior, interfaces and verification strategy; no automatic tracker publication. |
| design | [architect](../../architect/SKILL.md), with [arena](../../arena/SKILL.md) for consequential competing designs; [archify](../../archify/SKILL.md) for applicable structural/flow diagrams. | Selected interfaces/ownership, rationale, rejected alternatives and empirical checks; diagrams accompany the design, not replace it. |
| plan | [planning-and-task-breakdown](../../planning-and-task-breakdown/SKILL.md) turns the selected design into verifiable slices. [planning-with-files](../../planning-with-files/SKILL.md) is the one execution notebook. | User scenarios, dependencies, owned outputs/shared-resource constraints, acceptance and test commands. |
| verification setup / upkeep (within the applicable stage) | [create-verification-skill](../../create-verification-skill/SKILL.md) when a real target lacks repeatable user-facing checks; [maintain-verification-skill](../../maintain-verification-skill/SKILL.md) for requested drift audits or repairs. | Project-local verifier and feature/scenario links, qualified coverage and explicit gaps. No new lifecycle stage or automatic full-app audit. |
| test-design / build | [tdd](../../tdd/SKILL.md) owns test-first behavior and its exceptions. Use [swarm](../../swarm/SKILL.md) only for authorized, independent implementation slices. | Actual changes plus focused test or alternative evidence; coordinator integrates and checks the combined candidate. |
| self-verification | The [verification contract](verification.md) consumes tdd evidence and adds integrated smoke using the target’s verifier and affected feature recipes when available. [screenshot-manual](../../screenshot-manual/SKILL.md) supplies actual screenshot/PDF manuals when applicable. | Candidate-bound checks, scenario coverage, documentation and explicit gaps. |
| pr-review / correction | [code-review-and-quality](../../code-review-and-quality/SKILL.md) supplies review dimensions. SDLC owns reviewer independence, fallback and finding disposition. Behavioral corrections return to tdd; uncertain causes return to diagnosing-bugs. | Findings, corrective evidence and renewed review at the actual head/base. |
| issue body / completion | [issue-writing](../../issue-writing/SKILL.md) only when composing an authorized issue body. Shared issue policy owns updates/comments/closure. | Scoped published record or local handoff; no implied publication or merge. |

## Parallel design and implementation

For consequential design, architect prefers three genuinely different providers
through arena when available and authorized. Use the same frozen brief and
selection criteria. Do not count three sessions of one provider as three
providers. Record actual participation; reduce or proceed sequentially only when
the requested method permits it, otherwise report the capability gap. Three is
this collection's preference, not pstack's universal requirement.

The plan declares a dependency graph, single owners for shared interfaces and
mutable resources, and tasks ready from the verified baseline. Swarm executes
independent slices in isolated worktrees/state. Main remains the sole writer of
shared SDLC state and integrates changes serially. Release dependent tasks only
after affected checks pass on the combined revision. Conflicting slices are
serialized; unavailability is not a reason to pretend parallel work occurred.
Carry unresolved findings and invalidate affected descendants after contract
changes. Use the existing host's scheduling rather than introducing infrastructure.

## One TDD method

`tdd` is the only TDD package in this collection. Diagnosing-bugs, review corrections
and build all call it; neither Matt nor Addy's TDD package is installed alongside
it. [Verification](verification.md#tdd-method-and-alternative-evidence) defines
SDLC receipt mechanics, not another implementation method. Historical imported
policy wording is superseded by that contract where it conflicts.

`writing-for-agents` is an authoring aid when the artifact itself is a skill,
policy or instruction. It is not another universal execution stage. All focused
skills remain directly usable within their own scope and dependencies.
