---
name: create-formal-verification-skill
description: Create and qualify a project-local skill that formally verifies one stated code property. Use only when asked to formally verify, model-check or formally prove a property, or to create a formal verification skill; code that merely has concurrency, retries or state machines gets ordinary tests.
---

# Create a formal verification skill

Input: target checkout, any named area or bug, and authorized tool access. Output:
one verified property, a project-local verify skill and qualification evidence. A
test checks the cases someone wrote; formal verification checks every case in a
stated scope: every step order in a model, every input up to a bound, or every
input. Write for a cold, mid-change reader who must trust the result without
learning the tool. Follow shared [evidence](../../policies/evidence.md) and
[security](../../policies/security.md) policies. User-journey checks belong to
[create-verification-skill](../create-verification-skill/SKILL.md).

## Choose the target and tool

Answer from the codebase and ask only what it cannot establish. If focused tests
can settle the question, say so and use [tdd](../tdd/SKILL.md) instead. Start from
a named area or bug; otherwise pick the strongest promise whose break harms users
and whose breaking case tests rarely reach, not the easiest to verify. Verify one
property.

Let the question choose the cheapest tool. Bad event orders usually suit a model
checker over a small design model; TLA+ is the default in any language. Whether the
code behaves for every input (memory safety, overflow, a data-structure invariant)
usually suits a verifier on the code; a property needed at every size can need a
proof. If no verifier runs on the language, say so and test the real code with
generated inputs, not a hand model: that is bounded testing, never verified or
proved. Prefer tools the developers can install and run, and say why you chose one.
Install tools only within task authority, pinning the exact version and, for a
downloaded artifact, its checksum. A missing or unrunnable tool is blocked/not-run,
never a pass. A harness inside product source, such as a Kani harness in a crate,
needs explicit authorization like any product-source edit.

## Meet the bar

- **True to the code:** each model or proof part points to code a reviewer can
  open; one indivisible code step is one verification step; use the repo's names.
- **Able to fail:** show each property failing on a broken variant of the code it
  guards, such as a removed check or a reordered step.
- **Not vacuous:** the relevant states are reached and actions fire, assumptions do
  not exclude the bad behavior, and bounds are large enough. A timeout is
  inconclusive; a zero exit alone is not proof.
- **Findings stay findings:** report a current violation as a counterexample in the
  code's terms. Never weaken the property, model, bounds or assumptions to pass.
  Change product code only on request, through tdd; use
  [diagnosing-bugs](../diagnosing-bugs/SKILL.md) when real-code reachability is unclear.
- **Honest about scope:** say what is verified, under which bounds and assumptions,
  and what is left out. A pass covers the model or bound, not the whole system.
- **Readable without the tool:** state the property and the harm in one plain
  sentence each; tell a counterexample as a few steps in the code's words. An
  [archify](../archify/SKILL.md) lifecycle diagram may explain it; it is not proof.
- **Cheap to rerun:** one command, a reproducible tool version and a short run.
- **Kept in step:** record the files and functions each check covers and the commit
  at which you last confirmed that the verification describes them.

## Write the verify skill

Use the target's existing verification location and host-supported skill layout.
Valid frontmatter naming the area and the changes that call for it is required for
registration. Without native discovery, keep a documented source path and report
manual loading. Do not overwrite an existing verifier blindly.

From the skill alone, the next agent must tell whether a change touches the verified
code, run the check, tell a real bug from a modeling error and update verification
for an intended change. Include the coverage record and sync commit; move the sync
commit only after confirming the verification describes the new commit. A later
covered-code change means review required, not a proven bug. For a separate design
model, explain how to carry a code change into it and add a code-level conformance
link where practical: replay recorded executions, turn counterexamples into tests or
check a harness on the code. Use real commands, paths and nouns; no placeholders.
Keep raw tool output such as state dumps and solver logs in the target's ignored
evidence area; do not commit it or change ignore rules without authority.

## Qualify before handoff

Follow the generated skill once, as the next agent would, on a scratch change that
breaks the property in the real code; it must catch the break. Break a disposable
worktree or copy, never a checkout with uncommitted work unless authorized. A syntax
error, missing tool, timeout or generic changed-file warning is not detection. A
code break does not change a separate design model: show that the procedure leads
from the broken code to the model change and that the check then fails with a
matching counterexample; record that translation's limits. If the skill misses the
break or a step does not run, fix the skill or verification, not the scratch change.
Drop the break, confirm with version control that only intended verification files
differ from the start, and confirm the check is back at its baseline: passing, or
failing only on findings you will report. A verify skill that never ran is a
labeled draft with the exact gap.

## Hand off

Report the property, tool, version and reason, bounds and assumptions, findings in
plain words, the rerun command, qualification evidence and what is not covered.
Separate model results from implementation evidence, and bounded testing from proof.
Suggest a second target only if you found a close one. Use
[maintain-formal-verification-skill](../maintain-formal-verification-skill/SKILL.md)
for changes that skipped the recheck. Under SDLC, the coordinator owns acceptance and
these results feed its evidence records. Schedule nothing implicitly.

Source and local adaptations: [provenance](provenance.json). [MIT license](LICENSE).
