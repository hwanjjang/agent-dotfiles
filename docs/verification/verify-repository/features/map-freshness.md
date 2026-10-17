# Check generated map freshness

Scenario ID: `map-freshness`. A contributor can detect missing or outdated generated
HTML before delivery. Shared setup: [verifier](../SKILL.md).

## Sub-features

- A current catalog/viewer combination returns success.
- Missing or stale HTML returns nonzero without rewriting the file.

## How to get to it (user POV)

From the repository root run `python3 scripts/build_map.py --check`.

## Driving it with Python

Preconditions: Python 3.9+ and a complete checkout. Expect exit 0 and `Map is current`
for the maintained candidate. The combined helper records the command, exit status
and output in `map-check.txt`, and stops before browser driving on failure.
For the failure branch use `python3 -m unittest discover -s tests -p test_build_map.py`:
the existing isolated fixture exercises stale output rejection. Never corrupt the
working catalog just to demonstrate failure. That separate test result is required
when qualifying this recipe's failure branch; the helper's success covers only the
current-candidate branch.

## Gotchas

A passing freshness check proves generated/source agreement, not browser behavior.
Use the other two recipes for live UI checks. Regeneration belongs to an authorized
source update; `--check` never silently repairs the candidate.
