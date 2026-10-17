# Account source and delivery boundaries

This directory supplies account instructions and planning hook source. It does
not install, enable or remove anything. An account installer is not implemented.

Use the [screenshot walkthrough](../docs/manual/account-source.pdf) to find these
sources in the AK SDLC map.

[instructions.md](instructions.md) is the shared entry point; it links to portable
policies rather than copying their rules. Client entry points should refer to one
delivered revision of this bundle, preserving its relative policy/skill paths.
The repository-root AGENTS.md and CLAUDE.md must not be installed account-wide.

## Ownership during replacement

| Content | Treatment |
| --- | --- |
| Shared task policies and development skills | Replace from reviewed source after comparison; retain one owner and record the delivered revision. |
| Paseo skills | Preserve `paseo`, `paseo-advisor`, `paseo-committee`, `paseo-handoff`, `paseo-help` and `paseo-plugin` through their existing manager. They are not vendored here. |
| System skills and app plugins | Preserve under their host manager, including skill authoring/install tools, documents, PDF, spreadsheets, presentations and browser tools. |
| Planning hook registrations | Keep one active route per event; use the [runtime source guide](hooks/README.md) when replacing the old route. |
| Authentication, personal preferences, tool connections and trust state | Remain local. Preserve disabled state as well as enabled state; source import does not enable connections or broaden permissions. |
| Reviewer accounts and task-specific exceptions | Keep private; reconcile them with the [review runtime contract](../skills/sdlc/references/host-adapters.md). Do not convert personal exceptions into public authorization. |
| Installation receipts and backups | Retain locally through verified migration and rollback qualification. Do not commit effective account configuration. |

The previous installer's ownership receipt is migration input, not permission to
delete every path under a client directory. Explicit replacement can retire the
old managed development payload while preserving the categories above. Prevent
the old updater from managing the same files after a verified ownership transfer.

Source changes are reviewed before delivery; installed files are snapshots.
External authoring remains upstream or in a tracked fork, with local patches
recorded. A future installer must resolve selected skill dependencies and shared
policy references, show conflicts and proposed removals, record ownership and
revision, and support recovery. Install selected registry-managed CLI prerequisites
alongside their skills unless excluded; keep project initialization and MCP wiring
explicit. The current tool registry is an inventory, not an installer.

Hermes adapters and additional legacy CLI tools are not selected: their presence
in an old receipt does not establish a current need. This source decision does not
remove installed tools. Account-wide discovery, actual hook execution and MCP connectivity
still require target-client checks; see [verification](../docs/client-verification.md)
and the [migration decision](../docs/decisions/account-source-import.md).
