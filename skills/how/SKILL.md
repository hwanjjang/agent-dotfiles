---
name: how
description: Explain a subsystem's architecture, execution flow, ownership, and boundaries from source evidence before changing it.
disable-model-invocation: true
---

# How

Input: a question, codebase, and relevant revision. Output: a source-backed
explanation, file pointers, and explicit gaps. This is an investigation stage.

For a narrow question, inspect the relevant source directly. For independent
angles across a subsystem, use read-only workers only when the host supports
and permits delegation. Otherwise inspect those angles sequentially. Use the
host's configured models; do not assume a particular provider or tool API.

Frame each angle with [the explorer brief](references/explorer-prompt.md).
Trace triggers, data flow, state ownership, public interfaces, and failure paths.
Separate observed behavior from inferred rationale; use history or primary
sources when the question asks why the design exists.

Synthesize using [the explanation guide](references/explainer-prompt.md).
For a direct investigation, omit the explorer-findings wrapper. Resolve conflicting
findings against source. Include only sections that help answer the question.
Finish when the requested flow is traceable and remaining uncertainties are named.

Source and local adaptations: [provenance](provenance.json). License: [MIT](LICENSE).
