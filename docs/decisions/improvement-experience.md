# Improvement experience selection

Decision date: 2026-10-20. Status: adopted as design guidance for
[issue #80](https://github.com/hwanjjang/agent-dotfiles/issues/80). Private storage, the
frozen index and author packages are a manual CLI
([store guide](../../account/observation/README.md#record-and-retrieve-improvement-experience)); automated use in a
candidate-authoring loop is not implemented. The
[account improvement design](account-improvement-loop.md#learn-from-earlier-attempts)
owns the rules. This note records the sources, the choice and its limits.
Community validation is **provisional**.

## Problem and choice

The improvement loop records findings, cases, candidates and comparison results.
Nothing carries what earlier attempts showed into the next candidate. A rejected
attempt, such as the [completed development comparison](../evidence/native-development-pilot-2026-10-19.md),
is preserved as evidence but not as a reusable lesson. The next candidate author
starts without knowing which edits helped, hurt or could not be attributed.

Adopt a reviewed **improvement experience** record and a bounded retrieval rule.
Keep grading, held-out evaluation, promotion and delivery unchanged. Document
propose → probe → compose exploration as an optional method that is not yet
active. A proposed component-selection heuristic was evaluated before any edit
and not added.
The [workflow diagram](../architecture/improvement-experience-workflow.html)
shows where the record enters and leaves the loop.

## Sources

| Source | Revision and license | Useful method | Adaptation |
| --- | --- | --- | --- |
| [Harness²](https://github.com/google-research/harness2) and [paper](https://arxiv.org/abs/2610.14224) | `1cfe254` (2026-10-13), Apache-2.0; paper v1 2026-10-09 | Reflection writes one row per changed harness component with `helped`/`hurt`/`no observed effect`/`confounded`, then at most one cue/lesson/evidence/confidence entry or `NO_ENTRY` (`harness2/core/prompts.py` L1105–1160). A per-domain library keeps adopted harnesses and lessons; each task reads only earlier entries (`core/library.py`, `core/schedule.py` L701). Proposal scoping and composition (`core/recursion.py` L368–445). | Keep the attribution rules, `NO_ENTRY` and earlier-only retrieval. Add human review, a frozen index, held-out exclusion and private storage. Defer exploration. Do not import code. |
| [Matt Pocock retro](https://github.com/mattpocock/skills/blob/5beb35b040e3de97e54fa9e386d7e42d15c295c2/skills/engineering/retro/SKILL.md) | `5beb35b`, MIT | Classify a mechanical violation and prefer a deterministic check over a prose rule; remove instructions that do not change behavior. | Already reflected in the loop's mechanical-check rule and writing-for-agents step 5. No skill imported. |
| [Addy Osmani agent-skills #398](https://github.com/addyosmani/agent-skills/issues/398) | Open proposal, 2026-07-13 | Small scoped memory entries; most tasks add none; human review, invalidation and selective retrieval. | Corroborates `NO_ENTRY`, review before reuse and selective retrieval. It is a proposal, not deployment evidence. |

The repository preference order (pstack, Matt, Addy) was not needed as a
tie-breaker. No pstack workflow covering cross-cycle lessons was found; its
[eval playbook](https://github.com/cursor/plugins/blob/main/pstack/skills/poteto-mode/playbooks/eval.md)
already informs the comparison design.

## Adopted and declined

Adopted as design:

- Per-component edit rows with four verdicts. Prefer `confounded` for several
  components changed together or a difference resting on one repetition.
- Selection, adoption or rejection does not establish which edit helped.
- At most one lesson, or `NO_ENTRY`. Rejected and inconclusive attempts are kept.
- Diff against the original baseline, and also against the parent for sequential
  candidates. Harness² `1cfe254` diffs reflection evidence against the adopted
  harness instead (`core/selection.py` L418 → `core/context.py` L306; upstream
  [PR #79](https://github.com/google-research/harness2/pull/79)).
- Retrieval reads only entries from earlier cycles that a maintainer marked reusable,
  through a frozen index; the loop section defines the exact rule.
- Workspace facts are labeled and re-verified before reuse.

Deferred: propose → probe → compose. Paper ablations support it, but the local
evaluator compares only baseline and candidate, and an extra paid exploration
round needs a concrete competing hypothesis first.

Declined:

- The Harness² runtime and executors. Its Codex executor bypasses the sandbox and
  hook trust, and executor network access is unrestricted by default.
- Verifier-free output selection as promotion evidence. Harness² builds its final
  selection pool from refined candidates only (`core/selection.py` L93–111).
- Copying the whole library into author context.
- Automatic trigger insertion as proof of skill discovery.
- Fixed recursion budgets.
- Score denominators that drop ungraded rows.

Other verified Harness² defects become requirements for the later implementation
([#81](https://github.com/hwanjjang/agent-dotfiles/issues/81)):

| Harness² defect | Location or report | Requirement here |
| --- | --- | --- |
| Answer-path patterns are normalized with `lstrip("./")`, which turns `.answers/**` into `answers/**` | `core/context.py` L206/L410; [PR #70](https://github.com/google-research/harness2/pull/70) | Normalize patterns by removing a prefix, not a character set |
| Cached rollouts are reused without checking task-input identity | `core/runmark.py` L91–102; [issue #65](https://github.com/google-research/harness2/issues/65) | Check input identity before reusing a cached result |
| A rendering failure overwrites a valid trajectory | `core/context.py` L319–332 | Keep separate statuses for trajectory and rendering evidence |
| Executor rollout cost is never recorded | ledger `rollout_usd` | Record execution cost, or mark it unknown |

## Evidence strength

The paper reports, for Gemini 3.5 Flash with OpenCode at k=1, how much the score
drops when each part is removed:

| Part removed | WorkBuddy-Bench | JobBench |
| --- | --- | --- |
| Library | −3.1 | −1.8 |
| Proposal scoping | −2.9 | −3.7 |
| Composition | −1.6 | −1.9 |

The ablation rows have no variance or confidence intervals. The main results use
three shuffled task streams with standard deviations of roughly 1–6 points. The
authors' model, Claude Opus 4.8, also judges JobBench. These are author-reported
benchmark results. They justify a local design trial; they do not show that the
method transfers to shared policies or to Korean routing.

## Community evidence

Inspected on 2026-10-20. No independent model-backed replication was found.

- [Hacker News discussion](https://news.ycombinator.com/item?id=50151059)
  (2026-10-19, about 75 points). Commenters criticize the README imagery and the
  absence of a runnable end-to-end example. Two commenters say practitioners
  already update skills and prompts from past runs; another compares it to the
  Hermes agent. These are opinions, not results.
- [Jahanzaib guide](https://www.jahanzaib.ai/blog/google-harness2-setup-guide)
  (2026-10-18) and [NxCode](https://www.nxcode.io/resources/news/harness2-recursive-agent-harness-local-demo-2026)
  (2026-10-19, commercial site) report running the deterministic demo only. No model-backed
  benchmark was run.
- [Wavect](https://wavect.io/blog/google-harness2-setup-cost-safety/)
  (2026-10-16, commercial blog) warns that benchmark gains are not production
  gains, that k-budget deltas are extra spend, and that editable guardrails are
  not a security boundary.
- Upstream reports from 2026-10-16 to 2026-10-19 are code-level defects or
  proposals, not method evaluations: [#65](https://github.com/google-research/harness2/issues/65),
  [PR #70](https://github.com/google-research/harness2/pull/70),
  [PR #79](https://github.com/google-research/harness2/pull/79) and
  [#4](https://github.com/google-research/harness2/issues/4). No maintainer replies
  were observed.

Access limits: Reddit returned a block page, and X was not fetched. An issue and
the PR that follows it count as one experience. Repository stars were not used.

## Component-selection heuristic: evaluated, not added

Harness² edit prompts map failure types to the lightest component: bounded
fallbacks for tool errors, scripts for mechanical repetition, triggered skills,
and enforcement only after repeated evidence (`core/prompts.py` L347–371). Before
adding a similar heuristic to writing-for-agents, the current skill was tested.

**Method.** Fresh Claude Haiku contexts received the current
`skills/writing-for-agents/SKILL.md` and six scenarios: an authentication failure,
a single unexplained mistake, a repeated syntactic defect, unbounded tool retries,
a customer-specific fact, and automatic hook installation. Each scenario ran three
times. The builder graded the answers against a rubric written before the runs.

**Result.** All 18 scenario runs already made the intended choice, so adding the
heuristic was not expected to change behavior. Following writing-for-agents
step 5, it was not added.

**Limits.** The test used one model and English scenarios that named the
candidate forms explicitly, and the builder, not an independent grader, applied
the rubric. A future observed failure can reopen the question
with its own case.

## Verification boundary

The design defines rules and a worked example; [#81](https://github.com/hwanjjang/agent-dotfiles/issues/81)
adds offline-tested private storage, retrieval and packaging with synthetic
fixtures only. No real candidate has used them yet. The heuristic
evaluation is a bounded pre-change check. It does not show how installed clients
behave in ordinary work.
