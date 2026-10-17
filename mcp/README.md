# MCP connection templates

These are opt-in Claude Code `.mcp.json` fragments, based on the official client
and server documentation checked on 2026-10-17. They are not a universal MCP
configuration schema. Other clients need their own adapters and discovery checks.
No server is enabled by this repository's root configuration.

| Template | Transport and purpose | Requirements |
| --- | --- | --- |
| [GitHub](claude-code/github.json) | Remote HTTP; repository, issue, and PR research with read-only tools | `GITHUB_MCP_TOKEN`, supplied locally with access to the intended repositories. |
| [Context7](claude-code/context7.json) | Remote HTTP; resolve libraries and query documentation | `CONTEXT7_API_KEY`, supplied locally. |
| [Playwright](claude-code/playwright.json) | Local stdio; browser inspection in an isolated headless session | Node.js 18+, npm/npx, and a supported browser available to the server. No secret variable required. |

To adopt a template, merge its selected `mcpServers` entry into the destination
project's `.mcp.json`, preserving other entries. Check for an existing server name
before replacing anything. Export the named variables through the destination's
local environment or credential mechanism; never write their values here. Claude
Code expands `${VAR}` in these files. A missing variable is a configuration error
to resolve before attempting authentication, not a reason to add a real token.

GitHub is deliberately read-only in this starter profile. A task requiring writes
can use the registered authenticated `gh` capability within task authority.
MCP-based writes need an explicitly selected profile and appropriate authority. Context7 queries
are sent to its remote service; send the scoped technical question, not private
source or logs. Playwright uses a fresh profile; authenticated storage and browser
outputs remain local. `--isolated` is session isolation, not a security sandbox.

The Playwright npm package is pinned to `0.0.83`; npm's transitive resolution is
not pinned by this template. For a fully reproducible deployment, install the
selected package with a reviewed lockfile in the destination environment. Do not
replace the version with `latest` during an unreviewed update.

Validation has separate layers:

1. Parse JSON and inspect executable, endpoint, arguments, and variable names.
2. In an authorized target client, verify configuration discovery and authentication.
3. List actual tools and perform one relevant bounded read or isolated browser check.

This repository has checked layer 1 only. Client discovery, remote authentication,
and browser operation through these templates are not claimed to work yet.

Sources:

- [Claude Code MCP configuration and environment expansion](https://code.claude.com/docs/en/mcp#environment-variable-expansion-in-mcp-json)
- [GitHub server configuration](https://github.com/github/github-mcp-server/blob/main/docs/server-configuration.md)
- [Context7 client configuration](https://github.com/upstash/context7/blob/master/docs/resources/all-clients.mdx)
- [Playwright MCP](https://github.com/microsoft/playwright-mcp)

The [tool registry](../tools/registry.json) records upstream projects and selected
versions. Remote endpoints are provider-managed services, not commit-pinned binaries.

See [client verification](../docs/client-verification.md) for scoped adoption
checks and the distinction between discovery, authentication and actual operation.
