# SDLC intake and reassessment

Decision: 2026-10-18, [issue #62](https://github.com/hwanjjang/agent-dotfiles/issues/62).
The maintainer selected one `sdlc` entry point, an internal assessment reference,
reuse of existing methods/records, and reassessment after consequential changes
or resumption. A standalone skill is deferred until actual reuse warrants it.

## Ownership and behavior

[`references/intake.md`](../../skills/sdlc/references/intake.md) owns how to assess
the request, current evidence, reusable work and missing prerequisites. The
existing [routing table](../../skills/sdlc/references/skill-routing.md) owns which
method to use; each selected skill still owns its procedure. Triage and existing
stage receipts retain the decision, evidence and next action. No schema migration,
new lifecycle stage, classifier agent or global router is introduced.

Clarity, size and startability are separate judgments. An issue URL does not imply
build, and a PR URL does not imply review or correction authority. Existing spec,
planning, tracker synchronization and resumption methods remain in place. The old
ak-flying-agent experiences motivated inspection; they were not retained evidence
of defects in this version. Changes target intake/handoff, not those whole systems.

Use “Use sdlc to handle this issue; finish with a plan” or “Use sdlc to review this
PR; review only.” The same entry can accept a general request or continue an
existing task. Native slash syntax is client-specific; no `aksdlc` alias is added.
Routine standalone work retains its existing scope without new lifecycle state.

## Evidence and tradeoffs

The baseline native pilot preserved vague-work, dependency and review boundaries,
but its planning case wrote a plan without loading the focused planning method
or stating a PR boundary. The internal reference makes that method handoff
explicit. Some pilot smoke attempts were denied by the test runner's allowlist;
these are harness limitations, not evidence of a defective SDLC method. Before/
after cases use the same corrected harness and preserve the pilot results.

The [behavior recipe](../verification/verify-repository/features/sdlc-intake.md)
separates native activation, actual execution and artifact quality. It records
bounded observations, not a general reliability or speed claim. Existing state
tests remain structural evidence; they do not establish remote synchronization.

Inspected reference patterns:

- [pstack dispatch](https://github.com/cursor/plugins/blob/0b8e952052d482ee6de06deebf14d590d77b1b34/pstack/skills/poteto-mode/SKILL.md)
  and [session pickup](https://github.com/cursor/plugins/blob/0b8e952052d482ee6de06deebf14d590d77b1b34/pstack/skills/poteto-mode/playbooks/session-pickup.md):
  one entry and reconstruction of remaining work. Do not adopt its program runtime.
- [Matt's triage](https://github.com/mattpocock/skills/blob/49dd158d1076134a641b33efb035946536778336/skills/engineering/triage/SKILL.md):
  evidence-based readiness distinct from implementation. Do not import tracker labels.
- [Addy's evaluation design](https://github.com/addyosmani/agent-skills/blob/aeac41d4d005999432bb7312f7ff06383a91d59d/evals/README.md):
  inspect actual actions/artifacts separately from activation. The native harness
  here is locally authored, reusing this repository's existing CLI-check pattern.

The [prior review comment](https://github.com/hwanjjang/agent-dotfiles/issues/62#issuecomment-6250553946)
records dated original community reports, contexts, positive/negative observations
and verification limits. Reports about skipped handoffs, stale tracker state and
overlapping routers motivated behavior cases; they do not prove local failures or
a community consensus. Community validation of this particular integration remains
provisional. No third-party runtime or evaluator implementation was copied.
