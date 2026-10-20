# Improvement experience example: development pilot — 2026-10-19

This is a published, sanitized example of an
[improvement experience](../decisions/account-improvement-loop.md#learn-from-earlier-attempts)
record. It is derived only from the public
[development comparison evidence](native-development-pilot-2026-10-19.md) and
[#27](https://github.com/hwanjjang/agent-dotfiles/issues/27). It adds no new run and
does not change that comparison's **reject** decision. No canonical private record
of this attempt exists; the [store guide](../../account/observation/README.md#record-and-retrieve-improvement-experience)
describes how one would be recorded.

## Edit rows

| Component | Change | Observed difference | Verdict |
| --- | --- | --- | --- |
| `skills/to-tickets/SKILL.md` discovery description | Revised the description only; no other component changed | Natural first-page skill selection: baseline 4/4, candidate 4/4. Derived artifact checks: baseline 3/4, candidate 2/4, with one paired regression. One repetition per case variant. | `confounded` |

The verdict is `confounded`, not `hurt`:

- One repetition carries the artifact difference.
- The public summary does not establish how the description change caused that
  regression in the trajectory.
- Routing shows no observed gain.

## Lesson

`NO_ENTRY`. The rows do not support a transferable lesson. In particular, do not
record "description changes harm artifacts" or "the two descriptions are
equivalent".

## Record context

| Field | Value |
| --- | --- |
| Review status | reviewed in the PR that adds this file |
| Applicability | to-tickets discovery description; EN/KO development cases |
| Exposure | development cases only; no held-out material |
| Authoritative grades | the comparison evidence; this record interprets them and does not replace them |
