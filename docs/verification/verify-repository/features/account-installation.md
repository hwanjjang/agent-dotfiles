# Account installation

Scenario ID: `account-installation`. Surface: POSIX account installer CLI.
Source: [account guide](../../../../account/README.md). No real account changes,
authentication or external service access are required for the maintained checks.

Run from the repository root with Python 3.11+ and Git:

```sh
python3.11 -m unittest discover -s tests -p 'test_setup_account.py'
```

The tests create committed synthetic source repositories and disposable target
accounts. They verify preview, revision-based install/update, removal/rollback,
conflicts, local drift, interrupted-write recovery and preservation boundaries.
Test names own the individual cases; do not copy their assertions into this recipe.
Use a Python 3.11+ executable available on the test host when its name differs.

When source selection or client adapters change, also exercise the complete
committed candidate using the guide's commands against an isolated `--home`.
Check all selected skill links, clean status, a zero-change update, uninstall and
rollback. Retain source revision, OS/Python/client versions and results locally.
Never override HOME, reuse real account authentication or publish raw plans/backups.

This recipe verifies configuration delivery. Native skill discovery, effective
instruction loading, hook trust/recovery and MCP authentication require separate,
authorized target-client checks. Report untested clients and operating systems;
two directories on one host are not evidence for two platforms.
