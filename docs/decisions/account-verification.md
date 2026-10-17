# Account verification: doctor plus bounded model scenario

Reviewed: 2026-10-17. The maintainer requires actual inexpensive-model execution,
with Codex/Claude as base clients and Paseo optional. A receipt/hash check alone
missed an effective integration gap: changed Codex hooks require trust review.

Keep one `setup-account.sh doctor` entry point, reuse `status` for ownership, and
extend the existing repository verification map instead of adding another account
verification skill. Offline diagnostics, native discovery/trust and real model
behavior each report their own outcome. The model scenario grades concrete CLI
examples and source use; no launch-only PASS, provider substitution or retry loop.
Paseo is opt-in and uses the same scenario with its own identity/readback/cleanup
checks. No new dependency manager or evaluation framework is necessary here.

The [improvement-loop design](account-improvement-loop.md#account-qualification-and-reuse)
owns the connection to eval: doctor qualifies the installed setup before trials
and after delivery. It does not compare current/candidate arms or qualify source
promotion. A failed doctor run can inform a reviewed reproduction; its raw native
logs are not synthetic observation records. This keeps one store, one comparison
contract and one installer rather than adding a parallel self-improvement system.

Integration reviewed on 2026-10-17 against the incoming design and current primary
sources: [pstack's eval playbook](https://github.com/cursor/plugins/blob/main/pstack/skills/poteto-mode/playbooks/eval.md)
requires organic tasks, blinded judging and actual trace evidence;
[Matt's retro](https://github.com/mattpocock/skills/blob/main/skills/engineering/retro/SKILL.md)
classifies failures and prefers existing deterministic checks for mechanical
defects; [Addy's eval guide](https://github.com/addyosmani/agent-skills/blob/main/evals/README.md)
separates structural, approximate routing and behavioral checks. Its plugin
examples distinguish invocation indicators from outcome scores. These patterns
support the existing design; no external implementation was imported. Moving
upstream sources were reviewed as references, not pinned runtime dependencies.
[Anthropic's evaluation guidance](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)
also separates trials, traces and outcomes and recommends inspecting grader errors.

One [community discussion and its replies](https://www.reddit.com/r/ClaudeCode/comments/1ujxpic/how_do_you_actually_test_a_selfimproving_agent/),
accessed 2026-10-17 (displayed as three months old; exact publication date unavailable),
distinguishes cleaner instructions from improved task results and calls for held-out,
regression and operational checks. The author's personal example concerns an
architecture check, not a controlled agent benchmark, and promotes a longer writeup;
replies offer advice without pinned models, clients or trial results. It is useful
criticism of self-improvement claims, not independent validation of these repositories
or a skill popularity ranking. Community validation remains provisional.

Primary comparisons: [pstack setup](https://github.com/cursor/plugins/blob/main/pstack/docs/guide/01-setup.md)
offers project-local verification when needed; its
[verification skill](https://github.com/cursor/plugins/blob/main/pstack/skills/create-verification-skill/SKILL.md)
separates launch, doctor, drive, evidence and cleanup. Our existing adopted method
already supplies that contract. [Matt's installation guide](https://github.com/mattpocock/skills/blob/main/README.md)
and [Addy's review skill](https://github.com/addyosmani/agent-skills/blob/main/skills/code-review-and-quality/SKILL.md)
were inspected as installation/behavior-quality comparisons; neither is adopted as
a second account doctor. [Codex hooks](https://learn.chatgpt.com/docs/hooks) explicitly
bind trust to the current definition. [Claude's CLI](https://code.claude.com/docs/en/cli-reference)
provides stream output and native initialization used by the adapter. Runtime schemas
and installed CLI help, rather than inferred API shapes, were checked locally.
[Paseo Codex](https://paseo.sh/docs/codex.md) and
[orchestration](https://paseo.sh/docs/orchestration.md) document reuse of the local
Codex installation/account and the CLI route. The tested local Paseo was 0.11.4;
no remote-daemon or UI behavior is inferred.

Community evidence is limited: [one Reddit report](https://www.reddit.com/r/ClaudeCode/comments/1s8qzgs/skills_broken_in_2188_heres_the_fix/)
and its [linked issue](https://github.com/anthropics/claude-code/issues/41530)
report custom skills disappearing in Claude Code 2.1.88 versus 2.1.87. They concern
the same experience and count once. This supports checking actual discovery after
upgrades, not a claim about current versions or a community preference for our
custom command. Selection rests on the observed gap and reproducible checks;
community validation of this implementation remains provisional.

The native/model results discussed below used delivered source `ed1da039` and
a pre-split doctor orchestrator. At initial doctor PR commit `1df5ade`, only the
native transport and model-scenario modules matched the final historical runtime
byte-for-byte; the entire candidate was not freshly native/model qualified.
Review corrections subsequently change those modules. Historical runs do not
qualify the corrected implementation. Separate actual Codex GPT-6-Luna and Claude
Haiku 5.5 runs subsequently exercised the corrected harness against the existing
`ed1da039` installation; see the current [verification record](../client-verification.md). Candidate-bound checks, source identities
and review status are recorded in
[PR #30](https://github.com/hwanjjang/agent-dotfiles/pull/30).

Model choice remains an explicit host decision. A local catalog can describe a
model as fast/affordable without proving widespread use or current API pricing.
The host check used its offered GPT-6-Luna; no popularity ranking is asserted.
Claude's documented inexpensive [Haiku 5.5](https://platform.claude.com/docs/en/models/haiku-5-5/overview)
was not recognized by the tested CLI and its account hit the weekly quota.
After the reset, an explicit retry with the client's offered Haiku 4.5 passed the
bounded scenario. Read's line-number presentation required a tested evidence-parser
correction; the same live output was regraded without a second model request.
A subsequent explicit Haiku 5.5 run passed too, with both initialization and
actual model usage identifying `claude-haiku-5-5` and no recognition warning.
Availability findings are specific to each execution, not permanent model exclusions.
The follow-up checker compares Claude initialization with actual usage IDs. Codex
uses its installed app-server protocol's thread model and reroute notifications
for the same completed turn, with provider fallback disabled. Its JSON exec stream
did not expose enough identity evidence. This is a transport change for observation,
not a stronger sandbox or provider-internal attestation.

Natural spec-to-plan routing uses native structured output to avoid testing a
model's JSON formatting instead of the selected workflows. Source use still needs
successful tool output, or Claude's successful Skill invocation followed by its
exact owned instruction body. The official [headless guide](https://code.claude.com/docs/en/headless)
documents structured output and native initialization/usage fields; the
[skills guide](https://code.claude.com/docs/en/skills) documents automatic selection.
Paseo/Claude uses exact first-eight-line readback because Read exposes lines and
manual 180-character counting proved unreliable. Original failed attempts are
preserved, and successful content comparisons remain exact.

Native hook trust remains an explicit account action under the official
[Codex hook contract](https://learn.chatgpt.com/docs/hooks). Previewing event,
command, definition hash and persistent sandbox-external execution makes a combined
install/activation request reviewable. It does not override host approval review
or authorize trust for later changed definitions.
Raw model/native evidence
stays local. No account instruction content, private endpoint or permission
exception is copied into public decision notes.
