---
name: arena
description: Compare independent candidate designs or artifacts, select a base, integrate compatible improvements, and verify the result.
disable-model-invocation: true
---

# Arena

Input: a bounded task, frozen evidence, constraints, candidate budget, and allowed
output locations. Output: one verified artifact and a selection rationale.
Prerequisite: independent workers and a fresh reviewer supported and permitted
by the host. Report an unavailable capability before claiming independent results.
A sequential single-agent exploration is a different method and must be labeled.

1. Define the artifact, acceptance gates, comparison criteria, input revisions,
   and retry/time budget before dispatch. Give every candidate the same brief.
2. Use distinct providers when the decision benefits from different perspectives
   and those providers are available. Honor the requested panel; if a seat is
   unavailable, report the gap and any permitted fallback. Never invent model IDs.
3. Give each candidate its own writable directory or worktree. Candidates do not
   see other candidates' outputs and do not spawn further coordinators.
4. Collect completed artifacts and rationales. Record dropouts. Require genuinely
   different structures when exploring architecture, not cosmetic variants.
5. After outputs are stable, a fresh read-only judge compares them against the
   frozen criteria. The lead also reads each artifact and resolves disagreements
   using evidence or bounded experiments. Model agreement is not proof.
6. Select a base; incorporate only compatible improvements. Record the source and
   reason for each addition, rejected alternatives, and accepted tradeoffs.
7. Verify the synthesized artifact against the acceptance gates. A candidate's
   earlier result does not verify the combination. Reframe within the declared
   budget if the brief was wrong; otherwise report unresolved failure.

The verdict does not authorize implementation, publication, or merging beyond
the requested endpoint. Report actual participants, gaps, selection, and checks.

Source and local adaptations: [provenance](provenance.json). License: [MIT](LICENSE).
