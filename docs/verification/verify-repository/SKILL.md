---
name: verify-repository
description: Verify this repository's catalog search, usage and source links, and map freshness through the real browser UI and public build CLI.
---

# Verify this repository

Repository maintenance only; this is not a distributed skill package or an account
installation. Read [the feature index](features/README.md). Run from the checkout
root. The catalog is a static local HTML application, so no server, database or
credential is required. Source is loaded directly; no native discovery is claimed.

## Launch and doctor

Prerequisites: Python 3.9+, Node.js and an existing Playwright package with Chromium.
Use the target host's authorized runtime. This helper does not install dependencies.
A local dependency directory may be selected with `NODE_PATH`; an existing browser
may be selected through `VERIFY_BROWSER_CHANNEL` (for example `chrome`) or
`VERIFY_BROWSER_EXECUTABLE`. Values stay local, never in this file.

Run `python3 scripts/build_map.py --check`. Missing/stale output stops verification;
regenerate through `python3 scripts/build_map.py` only when updating the map is in
scope. The helper repeats this check, opens the actual local viewer in an isolated
headless browser and requires its search control and full catalog to be present.
It does not reuse a personal profile or start/stop other applications.

## Drive and evidence

```sh
node docs/verification/verify-repository/scripts/check.cjs --help
mkdir -p .local/verification-runs
node docs/verification/verify-repository/scripts/check.cjs .local/verification-runs/run-001
```

Choose a new evidence directory per run; the helper refuses an existing one.
If Playwright is already available in the repository's local browser environment:

```sh
NODE_PATH=.local/map-browser/node_modules VERIFY_BROWSER_CHANNEL=chrome node docs/verification/verify-repository/scripts/check.cjs .local/verification-runs/run-002
```

The feature recipes own expected behavior. The helper drives their three scenario
IDs, captures screenshots and CLI output, and records source hashes, browser/tool
versions, outcome and cleanup in `result.json`. Read the report and inspect the
screenshots; file existence alone does not establish visual correctness. A missing
dependency/browser or invalid base remains a failed qualification, not a pass.

## Cleanup and coverage

The helper closes its isolated browser in `finally` and retains evidence. It checks
that maintained map files did not change. On failure, inspect the report and fix the
cause before a new run. Do not delete failed evidence or stop unrelated processes.
No fixture restoration is needed: the UI state is session-local and the CLI uses
read-only `--check`.

This pilot covers the catalog and map check, not skill execution, client discovery,
MCP, PDF generation, every viewer control or a complete SDLC run. A complete audit
of this declared subset covers each recipe; expand the index before claiming more.
For maintenance use [maintain-verification-skill](../../../skills/maintain-verification-skill/SKILL.md).
For manual changes pass sanitized screenshots and scenario IDs to
[screenshot-manual](../../../skills/screenshot-manual/SKILL.md); render and inspect
PDF pages separately. Existing [catalog manual](../../manual/catalog.pdf) remains
a general walkthrough; this change does not alter its UI steps.

## Account checks

[Account verification](features/account-verification.md) adds offline/native diagnosis
and an explicitly selected real model scenario, with optional local Paseo. It is
not part of the browser helper: run its CLI recipe separately and preserve the
reported scope and blocked states. The [account guide](../../../account/README.md)
owns invocation, privacy, quota and native trust requirements.
