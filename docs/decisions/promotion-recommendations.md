# Evidence-bound recommendation pilot

Status: pure diagnostic rule calculation and fail-closed review recommendation
implemented. Operational eligibility remains unavailable until qualified live
comparison and independent holdout evidence exist. This does not complete the
live eligible-report acceptance criterion. The
[account improvement design](account-improvement-loop.md#source-promotion-and-account-delivery)
remains authoritative for source review, merge and account delivery.

```sh
python3 scripts/improvement/promotion.py recommend < gate-input.json > recommendation.json
```

`gate-input.json` contains exactly `experiment`, `report`, `completions`,
`current_spec`, and `source_diff_digest`. The first four use the
[evaluation accounting contract](evaluation-accounting.md). The last is the
SHA-256 of the source diff to attach to the existing PR review. It is a review
reference, not a claim that this program applied the patch or verified its
resulting tree. The reviewer must confirm the diff and exact tested identities.

The gate recomputes the entire report from its frozen experiment and submitted
completions, comparing canonical JSON bytes for both experiment and report.
Boolean, integer and floating-point substitutions cannot pass as equal values. Rehashing a forged aggregate or flipping `live_eligible` cannot bypass
that comparison. A changed current spec, baseline, candidate, contract, grader,
runner, environment, capability, model or budget invalidates the recommendation.
The caller supplies the current spec; this pure program does not inspect Git or
prove that a self-declared tree hash matches a checkout. A trusted operational
verifier is still required before real eligibility can be supported.

The inherited evaluation contract explicitly identifies its export producer as
an out-of-tree, unmerged PR #35 dependency. This recommendation slice does not
land that producer or complete its integration prerequisite. It consumes supplied
development evidence only; see the linked contract for the pinned source revision
and compatibility limits.

## Predeclared arithmetic rules

Freeze one rule name in the experiment's `promotion_rule` before trials:

- `quality_gain_v1`: candidate has more passes on the declared primary metric;
  each case/counterpart stays within the declared regression margin.
- `equal_quality_lower_tokens_v1`: candidate has at least as many passes, strictly
  lower total tokens, and each case/counterpart stays within the regression margin.

Both rules reject observed critical violations and require complete paired trial
and primary-metric coverage, qualified deterministic graders, known token usage
within the frozen token ceiling, and known aggregate trial latency within the
frozen seconds ceiling. The margin applies per case variant as a proportion of
scheduled repetitions, so improvements elsewhere cannot cancel a local regression.
These are declared small-sample diagnostic rules, not statistical confidence or
non-inferiority tests. Introduce a new versioned rule if their meaning changes.

USD cost is not a default metric. Known tokens and latency satisfy these rules'
resource dimensions without a dollar price. Only an explicit frozen `amount` /
`currency` ceiling requires observed currency usage; absent that ceiling, unknown
currency cost adds no gate reason. The current evaluator does not observe dollar
cost. Request ceilings and actual wall-clock/token enforcement remain the runner's
responsibility. Aggregate recorded latency is a diagnostic quantity, not proof
that runtime enforced a deadline or that parallel elapsed time was measured.

`evaluate_rule(experiment, report)` is a pure arithmetic helper. It assumes the
caller supplies the report and returns `scope: synthetic_rule_diagnostic`. Its
`verdict: eligible` means only that those supplied numbers satisfy the named rule;
`promotion_eligible` remains false. The public CLI does not offer this helper as
an operational eligibility path. Synthetic fixtures exercise its positive branch.
Unrecognized rules remain inconclusive; they cannot silently inherit cost or
benefit requirements from another rule.

## Recommendation and remaining boundary

`recommend(...)` returns `reject` for stale/inconsistent evidence or failed rules,
and `inconclusive` when required evidence is unavailable. Its review packet includes
baseline/candidate, source diff, report and experiment digests. Output also records
the gate's source digest and its own canonical recommendation digest. Treat these
as change-detection references, not signatures or proof of independent authority.

Current reports contain only public development cases, unverified synthetic
observations and no independent holdout custody. Therefore operational
`promotion_eligible`, `merge_authorized`, and `install_authorized` are always false.
The already accepted design requires unseen holdout qualification for actual
promotion; this pilot does not create a new custodian or pretend another folder
satisfies it. A self-described OS receipt, a mock pilot and a rehashed boolean
cannot establish trusted live provenance. No input flag disables this boundary.

Keep original evidence when regrading. A changed evaluator requires a new frozen
identity and a separate report linked to its predecessor. This program only reads
JSON and its own source; it never runs model calls, fixture commands, Git mutations,
installer operations or account changes. Redirect output to a new local artifact
and attach the exact source diff and evidence references to the repository's
existing review workflow. A recommendation does not authorize source integration
or account activation.

[Tests](../../tests/test_improvement_promotion.py) cover positive synthetic rule
calculations, critical failure despite aggregate improvement, per-case regression,
changed identities, rehashed forged summaries, incomplete trials, unknown usage,
explicit-only currency constraints and efficiency rules. Independent review and
qualified live/holdout integration remain separate prerequisites.
