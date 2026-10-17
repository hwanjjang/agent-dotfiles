# Logging

Scope: adding or reviewing application, service, CLI, or agent-tool diagnostic
logs. Apply during implementation and debugging. Use the destination project's
logger and transport; this policy supplies guidance, not an installed logger.

## Levels

| Level | Use for | Expected response |
| --- | --- | --- |
| `error` | A failed operation or broken invariant that needs investigation. | Investigate the failure; paging depends on the project's alert policy. |
| `warn` | Handled degradation, such as a fallback or a recovered retry. | Check recurring patterns and impact. |
| `info` | Significant business or lifecycle events, such as job completion. | Record the outcome without routine intervention. |
| `debug` | Targeted details that distinguish diagnostic hypotheses. | Enable for diagnosis; disabled in production by default. |

Choose severity by the event's meaning. Keep normal operation out of `error` and
avoid repeated messages that add no diagnostic information. Configure filtering
through the project's logger; do not bypass it with scattered print statements.

## Structured output

- Emit machine-readable JSON records with a stable `event` name and consistent
  field names. Put changing values in fields rather than interpolating them into
  the event name or relying on prose alone.
- Record event time, severity, and the emitting service or component. Include the
  outcome and useful error code or duration when relevant.
- Generate or validate a request/run ID at the boundary and carry it through
  logs and outbound calls for that operation. Preserve tracing context when used.
- When several entry points share a log sink, record the actual `entryPoint`
  where execution starts and propagate it with the correlation ID. Do not infer
  it later from timing or unrelated state.
- Allowlist useful fields. Follow [security.md](security.md) for secret handling;
  exclude passwords, tokens, authorization headers, full request bodies, and
  unredacted personal data from logs and displayed diagnostic output.
- Preserve the destination's output contract. For CLI tools, keep diagnostic
  logs separate from machine-readable command results. For stdio MCP servers,
  ordinary logs go to `stderr`; `stdout` contains only valid MCP messages.
  A diagnostic on `stderr` does not itself mean the operation failed.

Synthetic record (field spelling may follow the destination's existing schema):

```json
{"timestamp":"2026-10-17T09:00:00Z","level":"warn","event":"job_fallback_used","component":"example-worker","requestId":"example-run-42","entryPoint":"cli","outcome":"recovered","errorCode":"DEPENDENCY_TIMEOUT","durationMs":240}
```

## Temporary debug logs

1. State the hypothesis and observation the probe will distinguish. Prefer a
   debugger or focused inspection when available; instrument only the relevant
   boundaries rather than logging everything.
2. Mark every temporary probe with a unique task-specific tag, such as
   `[DEBUG-example-42]`. Keep JSON valid: the tag can be a `debugTag` field or part
   of the message. Use the same tag to locate all probes during cleanup.
3. Inspect only the necessary redacted output. Enabling production diagnostics
   requires existing task authority and a bounded scope and duration; a debugging
   request does not automatically grant production access.
4. Before declaring the fix complete, remove the task's temporary probes and
   search the affected executable source for the tag. Preserve existing permanent
   operational telemetry and other contributors' diagnostics.
5. Re-run the original reproduction and the applicable regression check after
   cleanup. Report any missing reproduction or verification capability explicitly.

## Verification

For an executable logging change, exercise representative normal, recovered, and
failed paths that the change affects. Inspect actual output for correct levels,
valid JSON, stable event names, correlation/entry-point propagation, and sensitive
data exclusion. Check that disabled debug output is absent, cleanup leaves no
task-owned temporary probes, and diagnostics do not corrupt command/protocol
results. Reuse adequate checks and report unexercised paths; writing this policy
alone does not demonstrate runtime compliance.

## Sources and adaptations

Selected and checked on 2026-10-17:

- [Addy Osmani: observability-and-instrumentation](https://github.com/addyosmani/agent-skills/blob/aeac41d4d005999432bb7312f7ff06383a91d59d/skills/observability-and-instrumentation/SKILL.md),
  revision `aeac41d4d005999432bb7312f7ff06383a91d59d`, MIT: adopted severity
  meanings, structured events, correlation and entry-point context, and field
  minimization. Metrics, tracing infrastructure, alerting and runbooks are outside
  this focused policy.
- [Matt Pocock: diagnosing-bugs](https://github.com/mattpocock/skills/blob/49dd158d1076134a641b33efb035946536778336/skills/engineering/diagnosing-bugs/SKILL.md),
  revision `49dd158d1076134a641b33efb035946536778336`, MIT: adopted targeted
  probes, unique temporary debug tags, cleanup and reproduction checks. The full
  diagnosis workflow is not required by this policy.
- [MCP stdio transport](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports#stdio):
  protocol constraint for diagnostic streams, separate from severity selection.

Local adaptations: consolidated the selected rules into one portable policy;
allowed JSON tag fields and destination schema conventions; scoped cleanup to
task-owned probes; retained existing production authority; made CLI/MCP output
boundaries explicit. No upstream skill installation or new runtime dependency is
required. Adoption was selected by the maintainer for this scope; repository stars
and installation counts are not evidence of this individual policy's effectiveness.

## Upstream license notices

MIT License

Copyright (c) 2025 Addy Osmani

Copyright (c) 2026 Matt Pocock

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
