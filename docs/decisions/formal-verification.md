# Formal verification skills

Adopted: 2026-10-22. Provisional with respect to community validation; the upstream
author announced the pair as beta. The pair fills one gap: checking a code property
across every case in a stated scope, such as every crash point or step order up to a
bound. The [user-journey verification pair](verification.md) and [tdd](../../skills/tdd/SKILL.md)
check only the cases someone wrote.

## Source and selection

Selected cursor/plugins revision: `190d28736eff128ec94f502a22c7fe0c4b56cd37` (pstack
0.15.29; last pstack commit `88d4751`). Both SKILL.md files are byte-identical from
0.15.28 (`d457567`) through this pin. Sources:

- [#709](https://github.com/cursor/plugins/pull/709) added
  [create-formal-verification-skill](https://github.com/cursor/plugins/blob/190d28736eff128ec94f502a22c7fe0c4b56cd37/pstack/skills/create-formal-verification-skill/SKILL.md),
  first shipped in 0.15.26 and announced with 0.15.27.
- [#721](https://github.com/cursor/plugins/pull/721) made TLA+ the default for
  event-order questions and, when no verifier runs on the language, required testing
  the real code with generated inputs instead of a hand model.
- [#716](https://github.com/cursor/plugins/pull/716) added
  [maintain-formal-verification-skill](https://github.com/cursor/plugins/blob/190d28736eff128ec94f502a22c7fe0c4b56cd37/pstack/skills/maintain-formal-verification-skill/SKILL.md)
  and the coverage record and sync commit that it reads.

Not imported: the setup offer (#715), version and guide changes (#724), the Claude Code
harness adapter line and pstack help text. pstack ranks first in the maintainer
tie-break. Neither Matt Pocock's skills (`5beb35b`) nor Addy Osmani's agent skills
(`aeac41d`) contain a formal verification, model checking or invariant-proving skill,
so the tie-break did not decide anything.

## Upstream evaluations

These are author-run evaluations with small samples and model judges. They are not
local behavior evidence.

- #709: six repositories, one run per repository and version, blinded scores against an
  earlier TLA+-prescriptive draft. On cJSON and arrayvec the skill chose a code-level
  verifier (CBMC, Kani) in 4 of 4 runs. It scored lower on checks: one run never
  confirmed its CBMC loop bounds and another had no single run command.
- #721: preregistered. On a JavaScript library with no verifier, the old text checked
  only a hand-written copy in 6 of 9 runs; the new text checked shipped code in 9 of 9.
- #716: 54 sealed runs. Its own conclusion is "Correctness: no real gain". The skill's
  effect was that runs showed a deliberate break (11 of 11, against 5 of 10 and 4 of 10)
  and updated the sync commit (18 of 18, against 4 of 18). One run edited `.gitignore`
  and one broke and restored a product file in place.

## Community evidence and limits

Searches on 2026-10-22 found no firsthand Reddit, Hacker News or social-media report of
either skill in real use, four days after release. X and Reddit pages could not be
opened directly; Hacker News was searched through its Algolia API.

| Source and date | Context and finding | Limit and consequence |
| --- | --- | --- |
| [elderfo/pi-pstack-adapter#17](https://github.com/elderfo/pi-pstack-adapter/pull/17), 2026-10-18 | Independent port, one run on v0.15.26. A hand-written state checker importing the fixture's real code explored 49 states and caught six mutants and a removed retry guard. The author calls it "bounded finite-state evidence, not certification of TLA+". | A fixture, before #716 and #721. |
| [knowttl/bstack#97](https://github.com/knowttl/bstack/pull/97) and its `docs/design.md`, 2026-10-19 | Design critique: a scratch break in the real code does not change a separate TLA+ model, so TLC alone never catches it; a Kani harness in product source needs its own approval; a missing tool counts as unproven. | Not run on real targets. Adopted as local adaptations and answered in the pilot. |
| [fullerzz/agent-skills#57](https://github.com/fullerzz/agent-skills/pull/57), 2026-10-19 | Selective port: "Upstream evaluation scores are not local behavior evidence"; the generated-input fallback is testing, not proof; isolated mutations. | Adopted, except that this collection allows narrow model invocation. |
| [derwells/skills](https://github.com/derwells/skills) `model-check` evaluations, `249e152` | Its earlier description loaded on 7 of 9 tasks that only needed tests. | Motivates the narrow description and the tdd guard. |
| chhoumann/t3-pstack#30, JoshuaHayesWasHere/jstack#94, michael-denyer/pstack-claude | Straight copies with install checks. | Distribution, not validation. |

General reports about agents and formal methods are mixed and are not about these
skills. Real bugs were found with TLA+ in
[desplega-ai/agent-swarm](https://github.com/desplega-ai/agent-swarm/blob/main/specs/tla/workflows/FINDINGS.md),
which then needed a daily spec-sync workflow, and with Verus on
[zstd-rs](https://github.com/KillingSpark/zstd-rs/issues/117). Recurring failures are
specifications that restate the implementation, trivial or weakened properties
([Hillel Wayne, 2025-06-05](https://buttondown.com/hillelwayne/archive/ai-is-a-gamechanger-for-tla-users/)),
overly restrictive models that make safety vacuous
([Claudia Cauli, 2026-03-08](https://claudiacauli.com/2026/03/08/my-eurosys-2026-paper-is-obsolete/)),
state explosion and shallow use: in [Dan Luu's experiment](https://danluu.com/agentic-testing/)
agents built TLA+ models in 159 of 160 runs, yet no TLA+ result changed the Rust code.
The local non-vacuity, conformance, never-weaken and bounded-claim rules answer these
reports; no independent source yet shows that the wording prevents them.

## Alternatives considered

- [tlaplus/AgentSkills](https://github.com/tlaplus/AgentSkills) (MIT, `f2adb5e`): useful
  TLA+ procedures, but TLA+ only, with no tool choice and no create/maintain loop. A
  possible future reference.
- derwells `model-check` (MIT) and opum-ai/proof-skills (MIT): TLA+ or TLA+/Lean
  workflows with their own tooling. Their ideas are cited; no text is imported.
- michael-denyer/agent-formal-verify (GPL-3.0) and trailofbits/skills property-based
  testing (CC-BY-SA-4.0): their share-alike terms would attach to adapted text in this
  MIT collection. Not imported.
- knowttl/bstack (MIT): a template- and runtime-coupled fork. Only its critiques are used.

## Ownership and use

- Shared source: [create-formal-verification-skill](../../skills/create-formal-verification-skill/SKILL.md)
  and [maintain-formal-verification-skill](../../skills/maintain-formal-verification-skill/SKILL.md).
  Each package's provenance records pinned hashes and adaptations.
- Each target owns its generated verify skill, models, harnesses, coverage record, sync
  commit and evidence. The verify skill handles changes made while it is used; the
  maintain skill handles changes that skipped it.
- tdd owns fixes, diagnosing-bugs owns counterexample reachability, and Archify may
  explain a state machine. SDLC routes to the pair only on request
  ([stage routing](../../skills/sdlc/references/skill-routing.md)); nothing is scheduled.

Both packages drop upstream `disable-model-invocation: true`, as the user-journey pair
did. This diverges from upstream and from fullerzz's port, so each description matches
only explicit requests to formally verify, model-check or formally prove, and tells
code that merely has concurrency or retries to use ordinary tests. If over-triggering is
observed, restore `disable-model-invocation: true` and add `agents/openai.yaml` with
`allow_implicit_invocation: false`.

Local adaptations: tool installs, harnesses inside product source and scratch breaks
stay within task authority; a missing tool is blocked, not a pass; scratch breaks use a
disposable worktree with a version-control check afterward; models must not be vacuous;
generated-input fallbacks are bounded testing, never proof; and a separate design model
must show how a code change reaches it, with a code-level conformance link where
practical.

## Repository pilot and limits

The maintenance-only [verify-account-transactions](../verification/verify-account-transactions/SKILL.md)
skill applies the create method to the account installer's transaction journal, automatic
undo and rollback in `scripts/account_storage.py` at `4130e05`. It checks two promises:
an interrupted apply or rollback can always be rolled back, and rollback never
overwrites a later user edit and changes nothing when it refuses. A model checked with pinned TLA+ tools v1.7.4
(TLC 2.19) covers one transaction, two kills, two I/O errors and one later edit, at 9,642
distinct states. A stdlib harness drives the real functions through 813 kill, error,
edit, lock and real-exit cases. Five broken model variants and five paired code
mutations each fail on their expected property.

Qualification found one modeling error and no violation of the two promises. The
journal is stored with sorted keys, so rollback walks paths in a different order than
the undo; the model was corrected. A scratch break that always journals `rolled-back`
after the undo was reported out of sync and produced harness violations with no model
change. After the model was updated from the code, TLC failed on the same property.
PR review found that the harness skipped directory-descriptor opens. With them
injected, it also reports one observation outside the properties: an I/O error while
`_below` opens a directory during rollback surfaces as `Unsafe parent for <path>`,
the same `ValueError` a safety refusal uses, after the journal is already marked
`rolling-back`. A retry restores every path, so recovery holds, but the message can
mislead a user into not retrying. Product code is unchanged; this is reported for a
separate decision. The existing account tests
passed on the broken code. An [Archify diagram](../architecture/account-transaction-lifecycle.html)
explains the journal statuses and is checked against the model's status set.

Limits: the upstream pair is beta; a pass covers only the stated model and bounds; the
model check runs on macOS with Java 17 and only the real-code harness runs in CI; the TLA+ tools jar has no
published checksum, so its hash was recorded at first download; and native skill
routing is unverified. See [client verification](../client-verification.md) for the
exact checks. Raw TLC output and harness logs stay local.
