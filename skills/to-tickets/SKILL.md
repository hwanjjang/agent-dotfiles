---
name: to-tickets
description: Turn a plan, spec or conversation into dependency-linked implementation tickets or local drafts. Reuse an adequate task plan and publish only within existing tracker authority.
---

# Turn a plan into tickets

Input: intended outcomes or an existing plan, source requirements, repository
context and the requested destination. Output: traceable tickets with acceptance
criteria and blockers, or clearly identified local drafts. Ticket creation does
not authorize implementation. This skill works without starting SDLC.

1. Read the source and relevant decisions, including current issue discussion
   when an issue is the input. Resolve the requirements authority and destination
   conventions. Do not require an upstream setup skill, label scheme or tracker.
2. Reuse an adequate task graph. If decomposition is missing or incomplete, use
   [planning-and-task-breakdown](../planning-and-task-breakdown/SKILL.md) to repair
   that same plan. Preserve stable task IDs and agreed granularity. Respect
   requested approval checkpoints without asking again for approved decisions.
3. Use the planning skill's coverage check before materializing. Compare the
   resulting tickets with that checked plan so summarization does not lose
   requirements or connector ownership. Send omissions back to the same plan.
4. Use [issue-writing](../issue-writing/SKILL.md) for body structure and acceptance
   criteria. Add source/parent references and blocking tasks. Link detailed
   execution ownership and PR mapping from the plan instead of copying a second
   spec; retain decision-critical constraints in the ticket handoff.
5. For plan-only work, an unavailable tracker or missing publication authority,
   write one draft per ticket in the task's existing local record directory; in
   a new project use an ignored `.planning/<task-id>/tickets/` directory. Preserve
   existing records and use stable IDs. Report drafts as unposted. Do not silently
   turn a tracker publication failure into completed publication.
6. When publication is authorized, follow the [issue workflow policy](../../policies/issue-workflow.md)
   for all tracker writes and uncertain-result recovery. Publish blockers first
   and retain the task-ID-to-tracker-ID map.
   Use native dependency edges only when supported and authorized; otherwise
   include explicit links. Resume partial runs from IDs verified through that
   policy's reconciliation procedure, preserving the existing tracker vocabulary.

Finish with ticket locations, blockers, the ready frontier, source coverage and
unresolved gaps. If a tracker owns status, local records link to it rather than
maintaining competing statuses. Stop at the requested ticket/draft endpoint.

Source and adaptations: [provenance](provenance.json). License: [MIT](LICENSE).
