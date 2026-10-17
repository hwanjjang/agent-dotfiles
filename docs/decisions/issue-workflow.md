# Issue workflow selection

Decision date: 2026-10-17. Status: adopted as source guidance; authenticated tracker
execution is not verified. The [policy](../../policies/issue-workflow.md) owns the
rules, pinned source revisions and license notices. This note records rationale.

## Problem and choice

Issue-writing already defines a useful issue body. SDLC includes progress-comment
rules, but those rules are scattered and tied to its PR workflow. Agents also need
a reusable answer to when to create, update, comment, hand off and close an issue.

Use one common policy. Keep writing structure in issue-writing and stage/endpoint
requirements in SDLC. Both consume the policy. The policy can also be selected
directly for issue work without invoking SDLC. No new orchestrator or tracker
adapter is required for this source change.

Selection follows task fit, primary-source review and community evidence. The
maintainer's pstack, Matt, Addy preference resolves comparable or ambiguous choices;
it does not establish technical superiority or justify importing an entire stack.

| Source | Useful coverage | Adaptation for this repository |
| --- | --- | --- |
| pstack orchestrate | Ownership, bounded briefs, current-revision verification and resumption | Keep these principles without imposing its large-program store or cloud execution model on every issue. |
| Matt triage and Agent Brief | Read prior discussion, verify claims, preserve resolved questions and define checkable outcomes | Use the existing body/spec as requirements authority. Handoff links to it rather than becoming a competing specification. |
| Addy Factory workshop | One maintained handoff, live tracker state and explicit work claiming | Adopt resumable state while distinguishing a comment from an atomic claim. No queue or claim runtime is bundled. |
| Existing AK skills | Task authority, meaningful updates, main-agent publication and concise issue bodies | Move common issue rules into the policy; keep SDLC-specific stage and PR review obligations in SDLC. |

GitHub's [Safe Outputs documentation](https://github.github.com/gh-aw/reference/safe-outputs/)
was also inspected as an external implementation reference. Its constrained output
system is product-specific; no gateway or GitHub Actions runtime is adopted here.
The policy describes expected behavior, not server-enforced concurrency or permissions.

## Community evidence

The following original discussions and replies were inspected on 2026-10-17.
Version pins are not supplied by the commenters. These are anecdotal reports, not
controlled comparisons; community validation of this specific policy remains
provisional. No popularity ranking was established.

- [Cursor Projects with pstack](https://www.reddit.com/r/cursor/comments/1wrmig0/killer_combo_cursor_projects_pstack_huge/): the author describes coordinating and verifying cloud work; a reply uses pstack implementation with Matt's planning/ticket skills. The author also warns of overlapping end-to-end workflows and prefers a smaller selection from Matt. Context is Cursor/Grok Bot; observed page dates were relative, so no exact post date is inferred. This supports checking composition conflicts, not proving the proposed issue policy.
- [Comparison discussion](https://www.reddit.com/r/AgentSkills/comments/1w7zmqf/superpowers_vs_agent_skills_vs_matt_pocock_which/): replies describe pstack coordination with Matt engineering skills, and another user values Matt's handoff and maintained specs/issues. Other replies report prompt conflicts or prefer no additional stack. Relative dates and unspecified revisions limit comparison. Different comments in this thread are not treated as independent experiments.
- [Issue-workflow overhead report](https://www.reddit.com/r/vibecoding/comments/1t2tkvw/am_i_overengineering_matt_pococks_ai_coding/), posted 2026-05-03: the author reports better results with narrow issue slices and multiple audit stages, but roughly an hour per small issue. This is a customized workflow, not a test of stock Matt triage. It motivates proportionate updates and avoiding mandatory ceremony.

Targeted searches for pstack orchestration and Addy's Factory handoff also returned
mirrors, catalogs and unrelated matches. No independently corroborated comparison
of their issue-comment/handoff protocols was found. Author demos establish intended
behavior, not community preference. Collection stars and installation counts were
excluded from the selection rationale.

The bounded evidence favors explicit ownership and selective composition while
exposing complexity and conflict risks. It does not settle a winner. The local
body/history/handoff split is an integration decision whose actual usefulness
should be assessed on future authorized issue work.

## Verification boundary

This change requires coherent rules, resolvable dependencies, scenario review and
current map metadata. It does not require publishing test comments on real issues.
The GitHub MCP template remains read-only. Live writes, concurrent-update behavior
and installed-client loading need separate authorized checks before claiming they
work. Distribution must preserve the shared policy dependencies declared by the
affected skills rather than copying their folders alone.
