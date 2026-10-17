# Select verification tools

Reuse the target's existing test runner and fixtures. Choose a tool for an actual
surface; installing this source does not enable any tool or server.

| Surface | Smallest suitable capability | Proof |
| --- | --- | --- |
| Browser | Existing Playwright/Cypress suite; available browser tool, Playwright CLI or MCP for exploration | User action, asserted result, relevant console/network observations and screenshot/trace where useful |
| CLI/TUI | Subprocess or isolated PTY harness | Command/input, stdout/stderr, exit status and resulting files/state |
| API | Existing integration client or local HTTP calls | Response contract plus required persistent effects and failure behavior |
| Library | Public caller-facing tests | Observable return values/errors/effects, not internal call choreography |

## Browser construction and repair

[Playwright Test Agents](https://playwright.dev/docs/test-agents) can explore a real
app into a scenario plan and generate executable tests. Use the target's installed
version and fixtures; client definitions stay upstream-owned. Its healer may skip
broken functionality. Required skipped coverage remains failed/blocked under the
existing evidence contract, never passed. Diagnose product versus locator/setup
failure before accepting a repair; preserve the assertion and rerun it.

Use isolated test profiles and task-owned sessions. Prefer visible readiness
assertions and stable locators over fixed sleeps or network-idle assumptions.
Inspect relevant console errors and network outcomes; classify unrelated baseline
warnings separately. Measure performance when the claim or change requires it.
Screenshots complement behavior checks and do not prove persistence by themselves.

[Playwright CLI](https://github.com/microsoft/playwright-cli) and
[Playwright MCP](https://github.com/microsoft/playwright-mcp) are alternatives;
CLI may reduce context overhead, while MCP can suit persistent exploratory sessions.
No relative efficiency was measured here. Chrome DevTools MCP is optional when
profiling/inspection needs exceed the existing tool. Never attach a personal
profile merely for convenience. Tool availability and execution permission are
prerequisites, not granted by these links.

## Before/after claims

For a regression or measurable improvement, state a falsifiable claim and compare
baseline and changed behavior under equivalent inputs/environment. Record artifacts
and confounds. No valid baseline or failed measurement is inconclusive, not success.
For a new capability, derive expected behavior from the requirement instead of
inventing a previously working baseline. See Cursor team's
[verify-this](https://github.com/cursor/plugins/blob/101b274dd991f694e1f7024be2157e5f3adf07de/cursor-team-kit/skills/verify-this/SKILL.md)
as an optional upstream method. Use the destination's existing result vocabulary
and evidence retention; this reference introduces no second gate.
