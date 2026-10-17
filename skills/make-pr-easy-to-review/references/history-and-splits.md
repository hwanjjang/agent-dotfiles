# Conditional history cleanup and splits

Read only when history cleanup or a concrete split is requested or approved.
Improving a description alone does not require this procedure. Source authority
remains the [PR policy](../../../policies/pr-workflow.md).

1. Resolve the actual local and remote refs, including fork ownership. Capture
   immutable original head, intended base, merge base and head tree before
   changing refs. Preserve a recoverable local reference to the original head.
   Keep the record outside tracked source. Use a clean isolated worktree when
   local edits or other work make the current checkout unsuitable.
2. Apply the PR policy's scope, merge-unit and authority rules to the concrete
   rewrite/split. Preserve review discussion when replacing commits or PRs.
3. For a pure reorder/squash on the same base, compare the final tree with the
   captured original tree using an equality assertion or a diff whose exit status
   is checked. Printing two hashes is not verification. Investigate every content
   difference before claiming preservation or publishing.
4. For a split, verify each candidate on its intended base and the combined final
   result against the original candidate. Independent PRs must also pass without
   an unmerged sibling. Use the PR map's policy-compliant intended bases.
   Replay the sequence in a disposable integration checkout to check the complete
   outcome. Passing only the last tip does not prove each merge point is sound.
5. If the destination base changed, direct final-tree equality may no longer be
   appropriate. Keep the original baseline, account for base changes separately,
   inspect the effective delta and conflicts, and rerun affected checks on the
   new combined candidate under the PR policy's evidence invalidation rule.
   Unexplained differences block a claim of equivalence and publication of the
   rewritten candidate.
6. Before an authorized push, verify the live remote head still matches the
   captured expected commit. When a force push is necessary and permitted, use
   an explicit expected-old-head lease for the specific destination ref. On any
   mismatch, reconcile concurrent work; do not refresh the expectation merely to
   force the write. Verify the resulting remote head/base after publication and
   reassess affected review/check evidence.

Report original and resulting identities, actual preservation checks, per-unit
checks, base changes and outstanding gaps.
