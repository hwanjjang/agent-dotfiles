# Offline evaluation accounting

Scenario ID: `evaluation-accounting`.

Run from the repository with Python 3.11+. No credentials, account installation or model service is needed.

1. Run `python3 scripts/improvement/evaluation.py qualify`; expect calibrated closed operators.
2. Run the focused `tests/test_improvement_evaluation.py` checks.
3. Freeze a reviewed development case with its contrary counterpart, both source identities, runtime settings, budgets and repetitions. Retain the resulting inventory.
4. Submit supplied synthetic completions through `report`; inspect each scheduled trial and unknown usage. Missing/duplicate trials must remain visible; changed spec must block them.
5. Verify `live_eligible` is false and promotion remains inconclusive even for positive synthetic evidence.

The [contract](../../../decisions/evaluation-accounting.md) defines exact input fields. Use ignored local files for reports; no trace-supplied commands execute. Browser-check the improvement-eval map entry and inspect the screenshot manual. These checks qualify the offline operator only.
