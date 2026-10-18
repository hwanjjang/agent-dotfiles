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

The disposable-delivery scenario connects public CLI preview/apply, committed
baseline and candidate revisions, independent Git component hashes, offline
doctor and installed fixture behavior. A deliberately regressed committed helper
can have clean ownership while its behavior fails; guarded rollback must restore
the prior revision and behavior. A separate disposable home verifies that both
rollback preview and apply refuse an intervening edit without changing content,
journals or observation records. Existing grants/events and unrelated account
settings survive updates, rollback and uninstall. Fixtures are generated in
temporary repositories and labeled mechanics tests; they do not establish an
accepted improvement or native skill/model behavior. Missing client executables
remain blocked offline readiness findings; the scenario does not launch clients.

This mechanics scenario does not establish installer-state access denial for the
applicable task/collector paths. [Issue #55](https://github.com/hwanjjang/agent-dotfiles/issues/55)
owns actual source/profile-bound denial probes through the existing execution
boundary, including the relevant child-process paths. Keep the trusted local
coordinator's access explicit; this does not require whole-account containment or
an external evaluator environment. [Issue #57](https://github.com/hwanjjang/agent-dotfiles/issues/57)
combines this mechanics journey with that scoped installer-state evidence.
Match its exact source/profile identities before reuse; compare its synthetic
installed-receipt and transaction-journal targets with the installer's state
layout. The denied actors are the remote task/result producer and explicit child;
the host installer, controller and scorer retain their authorized access. Changed
executor or protection sources require affected proof renewal. Same-user paths,
successful rollback and mocked write refusals do not satisfy this criterion, and
an earlier passing proof does not qualify changed bytes.

When source selection or client adapters change, also exercise the complete
committed candidate using the guide's commands against an isolated `--home`.
Check all selected skill links, clean status, a zero-change update, uninstall and
rollback. Retain source revision, OS/Python/client versions and results locally.
Never override HOME, reuse real account authentication or publish raw plans/backups.

This recipe verifies configuration delivery. Native skill discovery, effective
instruction loading, hook trust/recovery and MCP authentication require separate,
authorized target-client checks. Report untested clients and operating systems;
two directories on one host are not evidence for two platforms.
