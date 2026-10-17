# PR reviewability and ticket decomposition

Adopted 2026-10-17 after primary-source and community review. Select by method fit
and observable gaps; pstack, Matt, then Addy is a tie-breaker, not an effectiveness
ranking. Collection stars do not establish individual-skill quality.

## Ownership and selected sources

| Owner | Adopted method | Local boundary |
| --- | --- | --- |
| [PR policy](../../policies/pr-workflow.md) | Coherent purpose, green merge units, explicit dependencies and candidate-bound evidence. | Portable rules; no new lifecycle, fixed size quota or automatic landing. |
| [planning-and-task-breakdown](../../skills/planning-and-task-breakdown/SKILL.md) | Existing Addy task decomposition plus pstack PR planning and Matt outcome/expand-contract slicing. | One plan contains task graph and PR map; every source commitment and connector has an owner. |
| [to-tickets](../../skills/to-tickets/SKILL.md) | Matt's outcome tickets and blocking edges. | Reuses the plan, issue-writing body method and shared issue lifecycle. Local drafts or authorized publication; no implied implementation. |
| [make-pr-easy-to-review](../../skills/make-pr-easy-to-review/SKILL.md) | Cursor Team Kit's author preparation, history inspection and reviewer guidance. | Real content-preservation checks and explicit rewrite authority; not independent review. Matt `pr` is supporting guidance, not a competing template. |
| [AK SDLC routing](../../skills/sdlc/references/skill-routing.md) | Call focused methods within existing plan and review stages. | Standalone use remains available. Existing TDD, review and merge authorities remain unchanged. |

### pstack and Cursor Team Kit

Pinned `cursor/plugins` revision: `101b274dd991f694e1f7024be2157e5f3adf07de`.
Inspect [multi-phase-plan](https://github.com/cursor/plugins/blob/101b274dd991f694e1f7024be2157e5f3adf07de/pstack/skills/poteto-mode/playbooks/multi-phase-plan.md),
[opening-a-pr](https://github.com/cursor/plugins/blob/101b274dd991f694e1f7024be2157e5f3adf07de/pstack/skills/poteto-mode/playbooks/opening-a-pr.md),
[shipping](https://github.com/cursor/plugins/blob/101b274dd991f694e1f7024be2157e5f3adf07de/pstack/skills/poteto-mode/playbooks/shipping.md),
[orchestrate](https://github.com/cursor/plugins/blob/101b274dd991f694e1f7024be2157e5f3adf07de/pstack/skills/poteto-mode/playbooks/orchestrate.md)
and [sequence-verifiable-units](https://github.com/cursor/plugins/blob/101b274dd991f694e1f7024be2157e5f3adf07de/pstack/skills/principle-sequence-verifiable-units/SKILL.md).
These support per-PR purpose/evidence, parent bases, verified sequencing and one
owner of shared stack changes. Omit the complete program runtime, fixed worker
counts, universal performance gates, cloud assumptions and all-ready PR default.
Development red evidence never makes a broken intermediate merge acceptable.

[make-pr-easy-to-review](https://github.com/cursor/plugins/blob/101b274dd991f694e1f7024be2157e5f3adf07de/cursor-team-kit/skills/make-pr-easy-to-review/SKILL.md)
belongs to **Cursor Team Kit**, not native pstack. The user-supplied
[Denyer port](https://github.com/michael-denyer/pstack-claude/blob/5bd452955f8ded23ee81e022a19c537d6e523350/plugins/pstack/skills/make-pr-easy-to-review/SKILL.md)
is byte-identical at these pins; its
[NOTICE](https://github.com/michael-denyer/pstack-claude/blob/5bd452955f8ded23ee81e022a19c537d6e523350/NOTICE.md)
attributes the original. Import from the original with its Cursor MIT notice.
Replace printed-only tree hashes with checked comparison; keep behavior and tests
together at PR boundaries instead of applying a tests-last grouping mechanically.

### Matt Pocock

Pinned revision: `49dd158d1076134a641b33efb035946536778336`.
[to-tickets](https://github.com/mattpocock/skills/blob/49dd158d1076134a641b33efb035946536778336/skills/engineering/to-tickets/SKILL.md)
supplies vertical outcomes, acceptance, blocking relationships and wide-refactor
exceptions. The local adapter reuses adequate plans and destination conventions;
it does not require setup, fixed labels or repeat approval already supplied.
[implement-spec](https://github.com/mattpocock/skills/blob/49dd158d1076134a641b33efb035946536778336/skills/engineering/implement-spec/SKILL.md)
can collect all tickets into one integration branch and draft PR. Ticket slicing
alone therefore does not promise reviewable PR slicing.

[pr](https://github.com/mattpocock/skills/blob/49dd158d1076134a641b33efb035946536778336/skills/engineering/pr/SKILL.md)
informs optional visual explanation, real evidence and reversibility discussion.
Keep the destination template authoritative and do not fabricate before-results.
Matt's [credits](https://github.com/mattpocock/skills/blob/49dd158d1076134a641b33efb035946536778336/skills/engineering/pr/CREDITS.md)
attribute its visual approach to Dex Horthy / Humanlayer's `show-me`; this adoption
copies none of those visual examples and installs no additional dependency.

### Addy Osmani and other references

Pinned Addy revision: `aeac41d4d005999432bb7312f7ff06383a91d59d`.
[planning-and-task-breakdown](https://github.com/addyosmani/agent-skills/blob/aeac41d4d005999432bb7312f7ff06383a91d59d/skills/planning-and-task-breakdown/SKILL.md),
[incremental-implementation](https://github.com/addyosmani/agent-skills/blob/aeac41d4d005999432bb7312f7ff06383a91d59d/skills/incremental-implementation/SKILL.md),
[git-workflow-and-versioning](https://github.com/addyosmani/agent-skills/blob/aeac41d4d005999432bb7312f7ff06383a91d59d/skills/git-workflow-and-versioning/SKILL.md)
and [code-review-and-quality](https://github.com/addyosmani/agent-skills/blob/aeac41d4d005999432bb7312f7ff06383a91d59d/skills/code-review-and-quality/SKILL.md)
support verifiable slices, contracts, scope ownership and separation of mechanical
changes. Keep the existing planning/review packages; omit numeric size gates and
repeated human checkpoints that do not resolve a decision.

[Google small-CL guidance](https://google.github.io/eng-practices/review/developer/small-cls.html)
supports self-contained changes, related tests and a working system after each
merge. [GitHub gh-stack](https://github.com/github/gh-stack/tree/29a36d314be664583705f18e41cebdf2b61ad514)
and [cloud-stacked-diffs](https://github.com/dabit3/cloud-stacked-diffs/tree/f628921e5fb6687aa7cc2f980e20bfe844a3a964)
were inspected as execution references. They do not become required tools or MCPs.
Verify actual installed commands and authority before any future stack operation.

## Community evidence and limits

- [Matt #310](https://github.com/mattpocock/skills/issues/310) reports a real use of
  the earlier `to-issues` leaving a connector unowned between preparation and UI.
  The issue now names `to-tickets`. This motivates explicit coverage and connector
  ownership. [#959](https://github.com/mattpocock/skills/issues/959) reports lost
  source commitments and was closed as a duplicate; do not count the two as
  independent confirmation of one defect. Their October triage replies are
  labeled AI-generated, not independent human endorsements.
- [Matt discussion #638](https://github.com/mattpocock/skills/discussions/638)
  proposes separating slicing from publication. It is one design request, not a
  measured result. Our separation also follows existing local authority boundaries.
- [Addy #431](https://github.com/addyosmani/agent-skills/issues/431) discusses large
  specs despite small tasks. The author's response favors a bounded extension to
  existing spec work, supporting restraint rather than a second planning system.
- The [Reddit Stack Changes post](https://www.reddit.com/r/ClaudeCode/comments/1uadx5n/i_built_a_claude_code_skill_for_splitting_large/)
  is author promotion, not independent validation. A separate
  [stacked-PR friction report](https://www.reddit.com/r/github/comments/1wmd7qy/why_are_stacked_prs_so_annoying_to_work_with/)
  raises CI/merge usability concerns but does not evaluate these skills.

Search did not establish independent, version-specific consensus for
`make-pr-easy-to-review`. Mirrors, installation counts and directory scores are
not substitutes. Adoption rests on source fit, explicit user selection and local
checks; community validation remains limited. Raw research stays local.

## Qualification

Check source/license/dependency closure and map links, then exercise bounded
scenarios: retained source constraints and connector ownership, distinct task/PR
graphs, local-only drafts, uncertain publication recovery, metadata-only tree
preservation and authorized split verification. Record actual checks and limits
in [client verification](../client-verification.md). This adoption publishes no
issues/PRs, rewrites no live history and installs no account configuration.
