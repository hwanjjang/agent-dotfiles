# Account installation

Scenario ID: `account-installation`. Surface: POSIX account installer CLI.
Source: [account guide](../../../../account/README.md). No real account changes,
authentication or external service access are required for the maintained checks.

Run from the repository root with Python 3.11+ and Git:

```sh
python3.11 -m unittest discover -s tests -p 'test_setup_account.py'
python3.11 -m unittest discover -s tests -p 'test_disposable_delivery.py'
```

The tests create committed synthetic source repositories and disposable target
accounts. They verify preview, revision-based install/update, removal/rollback,
conflicts, local drift, interrupted-write recovery and preservation boundaries.
Test names own the individual cases; do not copy their assertions into this recipe.
Use a Python 3.11+ executable available on the test host when its name differs.

The disposable-delivery journey connects committed source identity with installed
behavior and guarded rollback through the public CLI. Its synthetic healthy and
regressed revisions establish mechanics, not candidate benefit or native behavior.
The test source owns individual assertions.

[Issue #57](https://github.com/hwanjjang/agent-dotfiles/issues/57) also consumes the
separate [scoped grading/installer-state evidence](../../scoped-grading-integrity.json).
Reconcile its exact source/profile and the installer's state layout before reuse.
The [native guide](../../../native-trials.md#scoped-grading-integrity) owns tested
actors, trusted-controller access and qualification limits; this installer journey
cannot substitute for that boundary proof or complete accepted-candidate #29.

When source selection or client adapters change, also exercise the complete
committed candidate using the guide's commands against an isolated `--home`.
Check all selected skill links, clean status, a zero-change update, uninstall and
rollback. Retain source revision, OS/Python/client versions and results locally.
Never override HOME, reuse real account authentication or publish raw plans/backups.

This recipe verifies configuration delivery. Native skill discovery, effective
instruction loading, hook trust/recovery and MCP authentication require separate,
authorized target-client checks. Report untested clients and operating systems;
two directories on one host are not evidence for two platforms.
