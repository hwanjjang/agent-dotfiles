---
name: maintain-formal-verification-skill
description: Bring an existing project formal verification skill back in line with changed code and classify each check as in sync, updated, bug or blocked. Use only when asked to recheck formal verification after covered code changed, or to resync a stale formal model, proof or harness.
---

# Maintain a formal verification skill

Input: an existing project-local skill that runs a model checker, prover or
code-level verifier against named code, and authorized tool access. Output: one
outcome per check with evidence, plus authorized verification updates. When code
changes and its verification does not, a check can keep passing on code that no
longer exists; that pass is dangerous because it looks like proof. The verify skill
handles changes made while an agent uses it; this skill handles changes that skipped
it, such as merges, edits made without it and drift across commits. Follow shared
[evidence](../../policies/evidence.md) and [security](../../policies/security.md)
policies. This is not a mandatory audit on every edit and adds no SDLC stage.

## Outcomes

- **in sync:** nothing since the sync commit alters what the check describes; it passes.
- **updated:** the code changed, the verification now describes it, and it passes.
- **bug:** the verification describes the current code and the code breaks the
  property. This is a code finding, not drift.
- **blocked:** the check could not be realigned or run, including a missing tool or
  an unauthorized update; say exactly why. It is never a pass.

A check can be both updated and bug: the update describes the code again, then the
property fails on it.

## Scope and authority

Edit only the verification: models, harnesses, property files and the verify skill.
An audit-only request authorizes no edits; report the update you would make. Never
edit product code unless asked; a harness inside product source needs explicit
authorization. Never weaken a property or model to pass; report the failure. Install
tools only within task authority, at the recorded version and checksum, and keep raw
tool output in the target's ignored evidence area. Put verification updates in a
change separate from any product fix; authorized fixes use [tdd](../tdd/SKILL.md).

## Pass

1. **Find the checks** by what they do, not by name, or use the one the user named;
   resolve the target if several remain plausible. For each, collect the property,
   covered code, bounds, assumptions, run command and sync commit. With no verify
   skill, stop and point to [create-formal-verification-skill](../create-formal-verification-skill/SKILL.md).
   Without a recorded, reachable sync commit, use the last commit that changed the
   verification files, and say so.
2. **Run each check as it is** and record the result before changing anything. A
   pass means the old description still holds, not that the code is correct. Leave
   a failure unclassified until step 5.
3. **Read every change to covered code** from the sync commit to the current commit,
   with its commit message. Follow renamed, split or moved covered code and new code
   that touches guarded state. Judge each change against the model or harness, not
   the commit message:
   - **No effect:** formatting, comments or paths the verification does not cover.
   - **No longer described:** an indivisible step became two, a branch was added or
     removed, a check moved, a new path reaches guarded state or a range changed.
   - **Promise changed on purpose:** a doc comment, test, changelog or commit message
     says so. The property must change; cite that evidence.
   - **Promise may be broken:** nothing says it changed; a later failure is a bug
     candidate.
4. **Update from the code, not from the result.** Write each change before the rerun
   so that every changed part points to code a reviewer can open and indivisible
   steps stay indivisible. Change a property only for an intended promise change,
   recording old wording, new wording and evidence. Keep bounds unless the change
   makes them wrong, and report any reduction.
5. **Rerun and judge.** A pass may come from a description that can no longer fail:
   break the new code the way the property guards against, in a disposable worktree
   or copy, confirm the check catches it, then drop the break and confirm that only
   intended verification changes remain. For a separate design model, derive the
   broken behavior from the code and recheck that relevant states stay reachable. On
   failure, replay the counterexample against the real code step by step, with
   [diagnosing-bugs](../diagnosing-bugs/SKILL.md) when reachability is uncertain. A
   step that cannot happen means the verification is wrong: fix it and say what was
   wrong. If every step can happen, it is a bug: name the introducing commit, tell
   the steps in the code's words and the harm in one sentence. A cheap real-code test
   or reproduction may support the report; do not commit it to product code.
6. **Update the verify skill:** covered code, commands, bounds, assumptions and the
   sync commit, set to the commit you checked. Do not move it for a blocked check,
   and say so. Then follow the verify skill once as the next agent would.

## Report

For each check, give the outcome and commits read; each verification change and its
reason, either changed code shape or an intended promise change with its evidence;
the rerun result and the break that showed the check can still fail; each bug as
steps, harm and introducing commit; and what remains uncovered, including new code
the check should cover. Say which failures were verification drift and which were
code bugs. If a check passed before the update and fails after, say that the old
pass was on a stale description. Under SDLC, feed results to its evidence records.

Source and local adaptations: [provenance](provenance.json). [MIT license](LICENSE).
