---
name: tdd
description: Demonstrate a failing behavior check before a bug fix or a test-first feature change, then verify the implementation. Use for requested TDD or a change with a practical focused test path.
---

# Test behavior before the change

This is the collection's single TDD method, adapted from pstack's bug-fix skill.
The feature-change and refactor branches below are local extensions. Use the
target project's test tools and the [behavioral test policy](../../policies/behavioral-tests.md).
Input: intended behavior, affected code and available checks. Output: actual
before/after evidence, the change, and any remaining verification limits.

## Choose the check

Inspect the nearest existing test or executable reproduction. For a bug, target
the reported symptom; for a feature, target its acceptance behavior. Keep expected
results independent of the implementation. Reuse the test harness and interface
already used by callers. Resolve genuinely uncertain behavior with the user;
an established interface does not need another approval round.

For a behavior-preserving refactor, establish passing regression coverage before
editing and rerun it afterwards. Do not break correct code to manufacture Red.
For non-executable content, use relevant content/link checks instead of TDD.

## Execute one behavior at a time

1. Add the smallest check that exposes the missing or broken behavior. Run it
   before changing implementation; confirm it fails for the intended reason.
   A missing dependency or broken test setup is not evidence of the defect.
2. Make the smallest coherent implementation change and run the check again.
   Keep existing contracts and assertions unless the requirement changed.
3. If refactoring helps this change, keep the checks green afterwards. Reuse the
   passing run if no further edits occurred; do not refactor solely for ceremony.
4. Verify affected neighboring behavior and the actual user path as appropriate.
   The calling workflow owns any additional integration or review requirements.

## When test-first is impractical

Avoid broad new infrastructure, brittle mocks or unrelated fixture churn just to
obtain Red. Use the closest useful check: a targeted script, existing integration
test, browser journey, command reproduction or direct observation. Record why
test-first was impractical, what was actually exercised and what remains unknown.
Missing access or a check that cannot observe the promised behavior remains a
verification gap. An alternative check is not a claim that TDD ran.

Within AK SDLC, report this choice through its
[verification receipt contract](../sdlc/references/verification.md#tdd-method-and-alternative-evidence).
That optional integration does not require SDLC for standalone use. Stricter
target-project requirements still apply; an unmet required check stays blocked.

## Completion

Report the failing-before and passing-after commands/results, or the explicit
alternative and its limits. Confirm retained checks are useful beyond this fix.
The [evidence policy](../../policies/evidence.md) governs completion claims.

Source and adaptations: [provenance](provenance.json). License: [MIT](LICENSE).
