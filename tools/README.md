# External tools

[registry.json](registry.json) records selected external capabilities, official
sources, licenses, prerequisites, version choices, and non-mutating version checks.
It is an inventory, not an installer or command executor. No external executable binaries are
vendored and no account settings are changed.

Git and ripgrep support local investigation and worktree isolation. GitHub CLI is
useful when the existing environment already supports authenticated CLI access.
The three optional MCP templates cover GitHub research, library documentation,
and isolated browser verification; see [their configuration guide](../mcp/README.md).
Use an existing equivalent capability when it meets the task rather than adding
a duplicate connection. MCP is optional for the imported skills.

Before enabling a tool in a target environment, check its official installation
instructions, chosen version, access requirements, and a representative operation.
Keep credentials, package caches, browser state, and generated output local.

Required documentation capabilities are bundled: [Archify](../skills/archify/SKILL.md)
for editable diagrams, and [screenshot-manual](../skills/screenshot-manual/SKILL.md)
for screenshot-based PDF manuals. The latter pins ReportLab, pypdf, Pillow, and
PDFium in its requirements file. Install them in an isolated environment. The
source tree includes executable tooling; dependency presence and successful
client operation are checked separately.

The repository-only [account transaction verifier](../docs/verification/verify-account-transactions/SKILL.md)
uses TLA+ tools v1.7.4 (`tla2tools`), pinned by a sha256 recorded at first download
because the release publishes no digest. The jar stays in ignored `.local/tools/`.

[statechart](../skills/statechart/SKILL.md) bundles its TypeScript compiler and
launcher. It finds TLC through `TLA2TOOLS` and `JAVA`; otherwise its first run installs
Java and tla2tools v1.7.4 with mise over the network, so set those variables or
confirm install authority first. Optional SVG rendering installs `pele@1.9.0`.
