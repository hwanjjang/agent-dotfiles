---
name: make-pr-easy-to-review
description: Prepare an existing PR or local candidate for review by clarifying scope, reviewer entry points and evidence, diagnosing noisy history, and recommending coherent splits when needed.
---

# Make a PR easy to review

Input: an identified PR or local candidate and the requested preparation scope.
Output: reviewer guidance, an accurate description and any needed split proposal,
with applied versus proposed changes explicit. This is author-side preparation;
it does not replace independent review or require SDLC.

1. Read the [PR policy](../../policies/pr-workflow.md). Resolve the actual target,
   repository, head/base repositories and branches, immutable commit IDs, current
   description, commits and diff. Inspect local work before modifying anything;
   preserve unrelated edits. For a fork PR, do not assume `origin` owns its head.
2. Identify mixed intent, mechanical/generated noise, missing verification,
   stale claims and unclear review entry points. Read relevant source and tests;
   diff size alone does not decide whether a split is useful.
3. If the work needs multiple merge units, use the existing
   [planning-and-task-breakdown](../planning-and-task-breakdown/SKILL.md) plan to
   produce or repair its PR map. A split recommendation remains a proposal until
   its concrete operations are authorized under the PR policy.
4. Use the destination's template as the body authority. Read
   [reviewer guidance](references/reviewer-guidance.md) when composing the body
   and review path. Prepare a local body draft when external editing is
   not authorized. Re-read before an authorized metadata update, preserve human
   edits and verify the published result. Reconcile uncertain writes before retry.
5. Keep behavior unchanged during preparation. Metadata-only changes leave the
   candidate tree unchanged. History cleanup or splitting requires the
   [conditional history procedure](references/history-and-splits.md) and existing
   authority for the concrete operation. Do not hide product fixes in cleanup;
   return them to the implementation/testing workflow within authorized scope.
6. Reinspect the final candidate against its recorded base. Check that the title,
   body, review order and evidence describe this candidate, and record what still
   needs review or verification, following the shared evidence policy linked
   from the PR policy.

Complete when a reviewer can identify the purpose, relevant change, verification
and remaining risks, with content preservation checked for any applied cleanup.
Report any split proposal separately from operations actually performed.

Source and adaptations: [provenance](provenance.json). Licenses: [MIT](LICENSE).
