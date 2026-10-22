# Focused skills and AK SDLC integration

Adopted: 2026-10-17. The maintainer selected three focused additions and one TDD
method. Existing stage IDs, publication authority and reviewer gates remain.

## Selection and adaptations

| Source | Selected method | Local adaptation |
| --- | --- | --- |
| [pstack tdd](https://github.com/cursor/plugins/blob/09d06eb4b97a1020ab31e84030e38baf1099c7dc/pstack/skills/tdd/SKILL.md) | Focused regression first; practical alternatives instead of bad tests. | One `tdd` package; extend to test-first features and refactors without manufactured failures. |
| [Matt diagnosing-bugs](https://github.com/mattpocock/skills/blob/49dd158d1076134a641b33efb035946536778336/skills/engineering/diagnosing-bugs/SKILL.md) | Symptom-specific feedback, reduction, falsifiable hypotheses and cleanup. | Difficult bugs only; bounded investigation, no fixed hypothesis count, tdd owns corrections and shared logging policy owns probes. |
| [Matt writing-for-agents](https://github.com/mattpocock/skills/blob/49dd158d1076134a641b33efb035946536778336/skills/productivity/writing-for-agents/SKILL.md) | Precise pointers, progressive disclosure, observable completion and pruning. | Concise authoring workflow; client invocation claims require actual client verification. |

These are reviewed adaptations, not verbatim upstream packages. Per-package
provenance owns exact hashes, resource exclusions and dependency lists; licenses
remain beside each skill. No account-specific authorization is imported.

Pstack's smaller method fits this collection's proportional verification better
than adding competing TDD frameworks. Matt's broader TDD requires pre-agreed test
seams and routes refactoring to review; Addy's includes a much larger development
reference. [Superpowers](https://github.com/obra/superpowers/blob/main/skills/test-driven-development/SKILL.md)
was also considered and its unconditional process is not adopted. Preference order
is only a tie-breaker; it does not establish quality or community popularity.

## Ownership and behavior

The [routing contract](../../skills/sdlc/references/skill-routing.md) is the single
stage-to-skill map. It connects early grilling, investigation, architectural
alternatives, task dependencies, parallel implementation, review and documentation.
Methods remain directly usable without starting the SDLC state machine. The
coordinator retains task state and authorized endpoint; workers own bounded slices.

The [tdd skill](../../skills/tdd/SKILL.md) owns testing procedure and practical
exceptions. [SDLC verification](../../skills/sdlc/references/verification.md#tdd-method-and-alternative-evidence)
owns evidence records and additional integrated smoke. Explicit alternative checks
need reason, attempts, limits, real scenario coverage for all acceptance criteria
and separate smoke. They are never labeled TDD or used to hide unavailable checks.
Existing records keep the default TDD contract; `refactor_performed: false` permits
Green reuse only if no changes followed it. Historical rules are superseded by
the dated normative amendment, not silently treated as competing instructions.

Three-provider design is a local preference for consequential choices. Actual
availability, isolation and method limits must be reported. Dependency-aware swarm
implementation requires independent work and one integration writer. A missing
provider is not replaced by an invented independent result.

## Community evidence and limits

The [pstack/Matt discussion](https://www.reddit.com/r/cursor/comments/1wrmig0/killer_combo_cursor_projects_pstack_huge/)
describes combining planning and implementation but also reports overlap and cost
concerns. It evaluates workflows, not every constituent skill. A
[diagnosing-bugs comparison](https://www.reddit.com/r/claudeskills/comments/1wv6eoq/matt_pocock_and_superpowers_are_overratedfor/)
reports equal 9/15 success in one developer's limited historical-bug experiment,
with additional time. That report is not independently reproduced and motivates
the difficult-bug trigger rather than universal use.

Evidence was reviewed on 2026-10-17. No sufficient independent, version-specific
consensus was found for the selected pstack tdd or writing-for-agents revision.
Selection remains provisional with respect to community validation. Source fit,
maintainer direction and focused checks justify adoption, not repository stars.

## Verification boundaries

State-contract regression tests exercise accepted and rejected evidence modes,
including failure, stale candidates, missing coverage and reused smoke evidence.
They do not prove model adherence. Metadata, dependency/link checks and the
generated map verify packaging. See [client verification](../client-verification.md)
for the separately recorded discovery and runtime boundaries.

No additional mandatory policy or MCP server is needed. GitHub's read-only profile
remains read-only; authorized issue/PR writes can use the registered `gh` capability.
The product verification-skill pair is now adopted in the
[verification decision](verification.md), with a bounded repository pilot. Other
projects still qualify their generated verifier on their own runtime. The
[formal verification decision](formal-verification.md) adds the separate on-request pair
for properties that tests rarely reach. This change does not install hooks, enable servers,
create PRs or grant deployment authority.
