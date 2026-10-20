---
name: to-spec
description: Synthesize requirements from agreed decisions, documents, meeting notes and repository evidence into a concise behavior specification, preserving proposals and gaps, or update an existing spec. Use for spec drafting without starting implementation or ticket publication.
---

# Turn settled requirements into a spec

Input: the request or intent, relevant decisions and available source evidence.
Output: one specification at the requested destination, with source references,
observable acceptance and unresolved decisions. Use directly or within an
orchestrator; no SDLC state, tracker, interview skill or setup command is required.
Follow the shared [evidence](../../policies/evidence.md) and
[security](../../policies/security.md) policies.

## Method

1. Find the existing requirements authority, spec and relevant decisions before
   creating a document. Read the supplied conversation/intent and affected source,
   glossary and ADRs where available. Reuse adequate investigation; distinguish
   inspected behavior from a reported baseline. Missing source access remains a
   stated limit, not a reason to invent how the system works.
   When documents or meeting notes supply requirements, first use
   [source extraction](references/source-extraction.md) to preserve locations,
   modality, decisions versus proposals and unresolved owners/dates.
2. Preserve settled scope, exclusions and constraints. For an existing system,
   record the relevant behavior being retained, changed or added so the spec does
   not turn existing capabilities into new work. Use only distinctions that affect
   this change; do not inventory the whole product.
3. Synthesize using the content contract below. Record existing design choices
   and their rationale; leave consequential unmade choices explicit for design.
   Ask only when missing information changes the promised outcome or makes the
   next handoff unsafe. Do not repeat settled interviews or require a routine
   confirmation of test boundaries. If no answer is available, finish a clearly
   incomplete draft with the affected decision and consequence.
4. Check the spec against the source commitments and applicable policies. Preserve
   existing acceptance IDs and map requirements to them; assign stable IDs only
   where useful and absent. Each required outcome needs a verification approach,
   including retained behavior affected by the change. Prefer existing observable
   interfaces and adequate checks. Proposed tests are a strategy, not execution
   evidence; no universal test-boundary count or new test harness is required.
   Retain verification of authority, transaction safety and capabilities essential
   to the promised outcome. An unavailable required capability leaves a gap;
   narrow the promise only within the agreed scope or report the blocked outcome.
5. Update the existing canonical spec in place when authorized, preserving unrelated
   content. Record material requirement changes and affected downstream references;
   do not rewrite tickets or plans as an incidental sync. Use the caller's artifact
   location and retention rules. With no established location, keep a local draft
   in ignored `.planning/<task-id>/spec.md`; honor an explicit inline/no-write request.
   Report the spec's location or inline status, readiness and remaining decisions.

## Content contract

Use the destination's format. Include only the detail needed for an independent
reader to understand the change and assess its completion:

- Problem, intended outcome, scope, exclusions and decision/source references.
- Observable requirements and acceptance, normal behavior and relevant failure
  behavior; preserve applicable UX and authorization constraints.
- Relevant interfaces and data contracts, including already selected architecture
  or data-model decisions. Link durable ADRs rather than copying them. Material
  alternatives and rejected options need only their decision and rationale.
- Where affected: external effects, retries/fallbacks/concurrency, security/data handling,
  compatibility/migration and observability expectations. Preserve important
  exclusions; omit irrelevant template sections rather than manufacturing work.
- Verification approach, available supporting evidence, assumptions and unresolved
  risks or decisions. Clearly separate requirements from optional suggestions.

User stories are optional; refactors can specify retained contracts and invariants.
Keep execution tasks, file-by-file plans and PR topology with the planning method.
Include a source path or short contract excerpt only when it preserves a necessary
decision more precisely than prose; do not fill the spec with implementation detail.

Complete when the spec faithfully preserves the agreed change and its acceptance,
with enough evidence and explicit uncertainty for the next appropriate handoff.
Do not label unresolved required behavior ready for implementation. Stop at the
spec: ticket creation, implementation and external publication use their respective
workflows under the actual task authority. A spec draft grants none of those actions.

Source and adaptations: [provenance](provenance.json). Licenses: [MIT](LICENSE).
