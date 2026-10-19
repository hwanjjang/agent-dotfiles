# Completed bounded development comparison — 2026-10-19

The fixed eight-row development comparison completed with all planned outcomes
retained, verified cleanup and the dedicated VM stopped. The candidate is **not
selected**: its routing score did not improve, and its artifact outcome regressed
in one of four pairs. This completes this development experiment, not general
agent effectiveness, held-out acceptance or account deployment.

The [selected evidence](native-development-pilot-2026-10-19.json) binds the actual
report to reader revision `ef07e0d`, qualified runtime source13, frozen arms and
experiment. The [preregistration](https://github.com/hwanjjang/agent-dotfiles/issues/27#issuecomment-6268482446)
preceded execution: two EN/KO cases, positive and adjacent-negative variants,
both arms, one repetition, seed `20261019`, eight ordered initial turns. The only
candidate change was the `to-tickets` discovery description. Cases, checks,
order and repetitions were not changed after seeing results. No score-driven
retry was performed.

| Dimension | Baseline | Candidate | Paired result |
| --- | --- | --- | --- |
| Natural first-page skill selection | 4/4 pass | 4/4 pass | No observed gain |
| Derived artifact checks | 3/4 pass | 2/4 pass | 2 both pass, 1 both fail, 1 regression |
| Adherence, exposure, MCP | Not assessed | Not assessed | Inconclusive |

All eight attempts completed execution and were admitted through the maintained
source-bound reader; five artifacts passed and three failed deterministic checks.
There were no missing, blocked, duplicate or unassigned rows. The known-good,
seeded-defect, missing-evidence and injection calibration examples matched their
expected verdicts. Calibration is separate from candidate effectiveness.

Each native client selected `gpt-6-luna` with the frozen low-reasoning profile.
This is client-selection evidence, not server-weight attestation. The model's
first-page skill-read signal is not proof of semantic adherence or complete skill
exposure. One repetition and four development pairs cannot establish statistical
superiority, equivalence or a general language effect.

The actual `promotion.py recommend-native` consumer recomputed the report and
verified the complete committed inventories of both arms, returning **reject**:
zero routing gain and two candidate critical outcome violations versus one for
the baseline. Its routing-only `rule_result.arms` counts are 4/4 for both arms;
they must not be mistaken for artifact or overall success. The diagnostic rule
and absent held-out record also prevent positive promotion. The retained reason
`same_host_heldout_unimplemented` is a report-contract label, not a claim that
the optional verifier is absent. No new held-out run is needed to reject this
candidate, and no account installation follows.

## Execution and interruption evidence

The fixed schedule consumed 514,172 observed total tokens and 11,866 output
tokens, with no unknown usage within this schedule. These are client counters,
not billing totals or a hard provider cap. Across retained earlier runs, the
known lower bound is 1,794,719 total and 30,686 output, with five incomplete or
unknown attempts still recorded. Review calls are outside that native-trial
counter.

The separate [actual production-interruption record](production-interruption-2026-10-19.json)
confirms that a bound artifact written before interruption was collected and
owned authentication/resources were removed. Its canonical result remains
`blocked/interrupted`; the test passes because interruption handling worked.
Two preceding `NOT_INJECTED` attempts remain failures, with cleanup verified and
usage unknown. A reviewed bounded checkpoint search then found the required
write and correlated output before injecting interruption. Its partial
8,278/119 usage is a lower bound already included in the cumulative figure.

The coordinator audited each reservation, canonical receipt, artifact admission,
source guards and owned-resource absence before continuing, then verified empty
owned inventory before stopping the VM. The shared VM and ambient Docker context
were preserved. Recommendation ran with network denied and writes denied except
existing admission lock files and `/dev/null`; hashed input/source files were
unchanged. No authentication or raw native event content is published.

The execution preparation passed 68 host-bound offline checks and independent
Claude Opus 5.5 medium review before launch. The reviewed source hashes, rather
than an informational HEAD literal, are the execution guard; root also checked
the clean exact commit at release. The public report receives its own review
and CI before integration. Historical partial pilots and their
[earlier rejection](native-recommendation-2026-10-19.md) are preserved; this fresh
experiment does not rewrite them. Public hashes support audit against retained
private records, not standalone reproduction without those records.
