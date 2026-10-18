# Intake and readiness

Use inside SDLC on initial intake, consequential new decisions or scope changes,
and resumption. This method selects the next action; [skill routing](skill-routing.md)
owns the stage-to-method mapping. It adds no stage, agent, global router or state
schema. Focused standalone requests retain the entry point's non-PR scope rule.

## Assess the request against current evidence

1. **Outcome and endpoint.** Identify what the user wants now and where the work
   must stop. Preserve established answers and authority from the conversation.
   An issue or PR URL identifies evidence, not permission to implement, publish,
   close or merge. Read the target, relevant discussion, linked work and current
   code/diff. If access fails, record the missing evidence rather than inventing
   its contents or declaring readiness.
2. **Reusable work.** Locate the canonical requirements, plan, implementation,
   review findings and verification. Check their content, revision and applicability
   to this request. A status label, filename or previous completion claim alone
   does not establish readiness. Preserve adequate artifacts and settled decisions.
3. **Missing prerequisites.** Assess clarity, size and startability separately.
   Determine which unknowns can be answered from code, which require research or
   a bounded experiment, and which require a user decision. Do available checks
   resolve the question? Is the scope finishable and reviewable? Are dependencies
   actually available? Do not turn routine source-supported implementation choices
   into another product interview or add optional behavior to fill perceived gaps.
4. **Next action.** Select the earliest unmet prerequisite for the requested work,
   then read the applicable method through [skill routing](skill-routing.md) and
   execute it within authority. A stage name or promised invocation is not a
   handoff. If a required decision or capability is missing, state the concrete
   question/blocker and stopping condition; continue only unaffected useful work.

## Choose proportionately

| Observed need | Next work and boundary |
| --- | --- |
| Required behavior is unresolved | Investigate discoverable facts first; clarify consequential user decisions through the intent method, then synthesize/update the canonical spec. Dependent implementation waits for finishable requirements. Give investigation a bounded question and exit condition. |
| Requirements are clear but too large for a coherent change | Apply the planning method to requirement-covered tasks, dependencies and separate reviewable PR boundaries. A clear spec does not itself make a task small. Ticket publication remains separately authorized. |
| A required dependency is unavailable | Identify its evidence, affected work and release condition. Do not invent a replacement contract to call the task ready. |
| Spec and plan are adequate and dependencies available | Reuse them and proceed to the authorized implementation/verification work. Do not recreate documents or re-interview for already settled decisions. |
| The user requests review | Review actual requirements, diff and evidence. Missing evidence is a finding or review gap; it does not authorize fixes or restarting feature planning. |
| The user requests correction | Carry existing finding IDs into scoped fixes, affected verification and renewed review. Do not equate author verification with independent review completion. |
| Existing implementation may satisfy the request | Verify it against the agreed criteria and assess completion at the authorized endpoint. Do not create duplicate implementation or imply remote closure. |

These observations may coexist: a large request can also be ambiguous or blocked.
Resolve the prerequisite that prevents the next authorized action; do not assign
one permanent classification to the whole issue. Reassess after that action when
its evidence changes the next step.

## Record and resume

Use the existing [triage deliverable](../assets/stage-deliverables.md#triage-reportssdlctasktriagemd)
and stage receipt. For work without persisted lifecycle records, return the same
substance concisely inline; do not initialize state solely to store this assessment.
Record the request/endpoint, observed evidence, reusable artifacts, unresolved
decisions/dependencies, selected next action/method and reason, and stopping
condition. Put material issue updates through the existing
[issue workflow integration](workflow.md#issue-workflow-integration), not a second log.

On resumption, compare the handoff with live issue/PR state where available, the
actual diff, findings and artifact revisions. For a material decision/scope change,
identify which requirements and downstream evidence changed, retain valid work,
and renew affected work under the existing [state contract](state-contract.md).
Preserve task identity, stage history and iteration counters; reassessment does
not reset them or override required dependency invalidation. Reused work still
needs sufficient current evidence at the eventual endpoint.

The assessment is complete when evidence supports a next action that has started,
an explicit consequential question/blocker has been returned, or completion at
the requested endpoint has actually been verified. Record pending publication or
unavailable checks honestly; neither is a successful external update.
