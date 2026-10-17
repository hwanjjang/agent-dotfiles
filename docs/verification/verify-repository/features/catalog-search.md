# Find a verification capability

Scenario ID: `catalog-search`. A maintainer can find the creation skill and recover
from a query with no matches. Shared setup and command: [verifier](../SKILL.md).

## Sub-features

- Empty query shows the catalog; a nonmatching query shows no feature cards.
- A specific query exposes the intended skill; clearing restores the catalog.

## How to get to it (user POV)

Open `docs/map/index.html` locally and use the search field.

## Driving it with Playwright

Preconditions: current map and a disposable browser session, established by doctor.
Enter `no-such-capability-unique-probe`; expect zero cards. Enter
`create-verification-skill`, open that card and expect usage describing launch.
Capture the selected result as `verification-search.png`. Clear search and expect
all catalog entries again. `result.json` records the scenario outcome.

## Gotchas

Search matches more than titles; do not require exactly one result for a broad
query. Use the observed target card. Screenshots accompany assertions, not replace
them. Close the owned browser to discard the search state.
