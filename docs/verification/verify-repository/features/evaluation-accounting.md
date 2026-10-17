# Offline evaluation accounting

Scenario ID: `evaluation-accounting`.

Run from the repository with Python 3.11+. No credentials, account installation or model service is needed.

1. Run `python3 scripts/improvement/evaluation.py qualify`; expect calibrated closed operators.
2. Run the focused `tests/test_improvement_evaluation.py` checks.
3. Freeze a reviewed development case with its contrary counterpart, both source identities, runtime settings, budgets and repetitions. Retain the resulting inventory.
4. Submit supplied synthetic completions through `report`; inspect each scheduled trial and unknown usage. Missing/duplicate trials must remain visible; changed spec must block them.
5. Verify `live_eligible` is false and promotion remains inconclusive even for positive synthetic evidence.

The [contract](../../../decisions/evaluation-accounting.md) defines exact input fields. Use ignored local files for reports; no trace-supplied commands execute. Browser-check the improvement-eval map entry and inspect the screenshot manual. These checks qualify the offline operator only.

The producer and evaluator are available in the same checkout. Run the real Store
integration checks with `python3 -m unittest discover -s tests -p test_improvement_integration.py`.
Follow the [reviewed case recipe](reviewed-cases.md) to prepare, inspect, review and
export English/Korean development cases. Pass only those exported public files to
`freeze`; review the explicit executable criteria against each prose contract.
The private preview and extra lineage fields must reject as evaluator input.

Inspect `paired_summary`: each scheduled case/variant/repetition has one pair.
Fail→pass is improved, pass→fail regressed, pass/pass both_pass, fail/fail both_fail;
any blocked/inconclusive arm is unresolved. The five counts must sum to
`scheduled_pairs` for overall and every dimension. Inspect the frozen
`primary_metric` dimension separately; outcome success does not imply routing
success. Retain missing, duplicate and failed submissions, and unknown usage.
Changed source identities need a new freeze or explicitly linked regrade.

Earlier pinned-producer/manual runs remain historical. Use the workflow-map
verifier and catalog verifier after status changes. Current integration still
qualifies only offline development accounting, not isolated model execution.
