---
name: issue-writing
description: "Write concise, implementation-ready issues (Jira, GitHub, or any tracker): problem/goal, required changes, and agent-verifiable completion criteria. Use whenever creating, drafting, or rewriting an issue, ticket, or bug report."
user-invocable: true
---

# Issue writing

Write issues that contain only what an implementer needs. A first-time reader must
understand what to do and why without asking follow-up questions.

For creation, body updates, comments, handoff or closure, follow the shared
[issue workflow policy](../../policies/issue-workflow.md). It owns lifecycle,
publication authority and conflict handling; this skill owns body composition.
Keep the linked policy resources available when distributing this skill.

## Structure

```markdown
## Problem / Goal
<What is wrong or what must be achieved, and why it matters. 1–3 sentences.>

## Required changes
- <Concrete change: component, behavior, or file affected>
- ...

## Completion criteria
- [ ] <Objectively checkable condition>
- [ ] ...
```

Add a section such as "Context" or "Reproduction" only when the implementer cannot start
without it (for example, steps to reproduce a bug, error output, or a link to the source
decision).

## Writing rules

- State the problem/goal, the required changes, and the completion criteria explicitly.
- Include background or side information only when implementation directly depends on it.
- Avoid both extremes: sentences so compressed that meaning is lost, and explanations so
  long that the core point is hard to find.
- Use jargon, abbreviations, and internal names only when needed. If the context does not
  make a term clear, add a short explanation.

## Checklist rules

- Include only items required to judge whether the work is done.
- Prefer items an agent can verify directly (a command passes, a file or setting exists,
  an API returns a given response, a link resolves).
- Exclude subjective items or items that need human judgment (e.g. "code is clean",
  "UX feels good").
- Exclude duplicate items and obvious process steps (e.g. "open a PR", "write code").
- Word each item so it is unambiguously done or not done.

## Outcome selection

Use a few observable outcomes, enough to cover the requested behavior, rather than
turning every implementation step or evidence item into a criterion. Group checks
under the outcome they establish; no fixed criterion count is required. Reuse
adequate existing evidence and retain essential authority, transaction-safety and
critical-capability checks. Unsupported capability must be constrained or reported
blocked, not compensated for with unrelated verification.

| Criterion kind | Decision | Meaning |
| --- | --- | --- |
| `outcome` | `KEEP` | A distinct observable user or system result. |
| `process` | `OMIT` | An implementation step; place it in the plan when needed. |
| `duplicate` | `CONSOLIDATE` | Attach its useful evidence to the existing outcome. |

## Final review

Before creating or updating the issue, reread the whole issue and confirm:

1. A person reading it for the first time understands it quickly.
2. An implementer can start without extra explanation.
3. Every checklist item passes the checklist rules above.

Revise until all three hold. Publish or return the finished draft according to
the shared policy's authority and publication rules.
