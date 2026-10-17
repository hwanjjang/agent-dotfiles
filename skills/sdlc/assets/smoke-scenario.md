# Smoke scenario

- ID: stable scenario ID
- Requirement: canonical intent revision and AC IDs
- Required/applicability: required, or justified not-applicable with reason
- Functional path: affected integrated behavior and runtime wiring
- Environment/prerequisites: exact local runtime, dependencies, permissions and fixture setup
- Test data: synthetic or approved fixture references; no credentials or personal data
- Side effects: external systems involved and existing test authorization
- Executable test or procedure: repository test path and exact command, or reproducible manual procedure

| Step | Action | Observable expected result | Explicit failure condition |
| --- | --- | --- | --- |
| 1 | Fill with actual interaction | Fill with meaningful assertion | Fill with failure observation |

- Cleanup: remove only disposable task-owned fixtures/resources when authorized; preserve required evidence and active gate inputs, and verify cleanup outcome
- Coverage rationale: success/error/authorization/boundary conditions; duplicates/retries/concurrency when relevant
- Independence from TDD: explain the additional integrated behavior this smoke exercises

## Execution receipt

- Execution ID and scenario revision:
- Candidate base/head or pre-commit content digest:
- Actual environment and real/mocked integration boundaries:
- Start/end time and command/procedure:
- Exit code and observed behavior:
- Outcome: passed, failed, blocked, not-run, or not-applicable
- Durable sanitized evidence references and content identity:
- Cleanup result:
- Failure/correction and renewed regression-test evidence, if applicable:

Do not complete this section before execution. A startup signal, HTTP status or screenshot alone does not establish the functional assertion. Required environment failures remain blocked/not-run. Submit machine-readable results in the state validator's supported schema.
