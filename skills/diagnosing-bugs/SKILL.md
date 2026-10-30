---
name: diagnosing-bugs
description: Diagnose difficult, recurrent or intermittent bugs and performance regressions with a focused reproduction and falsifiable hypotheses. Use when the cause remains uncertain; routine obvious fixes do not need a full diagnosis loop.
---

# Diagnose a difficult bug

Input: observed symptom, intended behavior, environment and relevant source.
Output: supported cause or a bounded unresolved diagnosis, reproduction evidence,
and verified correction when implementation is authorized.

Follow the shared [security](../../policies/security.md) and
[logging](../../policies/logging.md) policies for captured data and temporary probes.
Inspect existing domain terms and decisions where relevant. A diagnosis-only
request ends at findings; it does not authorize implementation or tracker writes.

1. **Build a useful feedback loop.** Prefer an existing failing test, command,
   HTTP reproduction or browser journey that asserts the user's exact symptom.
   Source inspection can help construct it. Record the actual invocation and
   outcome; distinguish setup failure from the reported defect. For intermittent
   failures, report attempts and failure frequency instead of claiming determinism.
2. **Reduce the reproduction.** Remove irrelevant inputs or setup while the same
   failure remains observable. Keep the original scenario for final verification.
   Improve speed and isolation when useful; use scratch state for stress/replay.
3. **Test competing explanations.** For a difficult cause, state plausible
   hypotheses and the observation that would disprove each. Change one variable
   at a time. Use targeted probes or a debugger; measure performance regressions
   against a baseline, following the measured-number recommendation in the
   [evidence policy](../../policies/evidence.md). No fixed hypothesis count is required.
4. **Correct within scope.** If implementation is authorized, pass the supported
   cause, reproduction and intended behavior to [tdd](../tdd/SKILL.md). It owns
   regression/test-first mechanics and practical exceptions; do not maintain a
   second testing procedure here. Rerun the original scenario after the correction.
5. **Clean up and report.** Remove temporary probes and task-created scratch
   artifacts under the logging policy. Preserve sanitized evidence needed for
   handoff. State the cause, checks, correction and remaining uncertainty.

If reproduction needs unavailable data, credentials or production access, stop
the dependent experiment, report attempts and identify the smallest missing input.
Useful read-only analysis may continue, labeled as hypotheses. Do not build an
unbounded harness or alter production instrumentation without task authority.
Use available host interaction for human-only reproduction; no external HITL
script or additional runtime is required by this adaptation.

Source and adaptations: [provenance](provenance.json). License: [MIT](LICENSE).
