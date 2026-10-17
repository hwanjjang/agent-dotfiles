# Extract specification synthesis

Adopted 2026-10-17. The maintainer requested standalone stage methods where useful,
then approved extracting Spec first. [to-spec](../../skills/to-spec/SKILL.md) now
owns the method and content contract. The [SDLC routing table](../../skills/sdlc/references/skill-routing.md)
owns when to call it; SDLC retains stage state, input/output revisions, readiness
and authority. No extra lifecycle stage, wrapper family, policy or MCP is added.

## Source choice

The primary upstream is Matt Pocock's
[to-spec](https://github.com/mattpocock/skills/blob/49dd158d1076134a641b33efb035946536778336/skills/engineering/to-spec/SKILL.md),
revision `49dd158d1076134a641b33efb035946536778336`, MIT. It synthesizes conversation
decisions and repository context into a spec, with testing decisions and scope.
Its [companion documentation](https://github.com/mattpocock/skills/blob/49dd158d1076134a641b33efb035946536778336/docs/engineering/to-spec.md)
explains the intended synthesis role and limitations. That documentation is
upstream explanation, not independent evidence of effectiveness.

The existing AK SDLC specification checklist supplies the behavior, interface,
failure, security, compatibility and verification content. Its English template,
workflow summary and normative spec gate now reference the new method instead
of retaining parallel checklists. The historical Korean input remains historical;
the current normative amendment explicitly supersedes its corresponding method.
Per-package provenance records the original local revision and source hashes.

Comparisons confirmed the narrow extraction:

- [pstack poteto-mode](https://github.com/cursor/plugins/blob/101b274dd991f694e1f7024be2157e5f3adf07de/pstack/skills/poteto-mode/SKILL.md)
  composes skills and playbooks. Reuse its separation of coordination and focused
  methods already present here; do not introduce a skill for every state transition.
- [Addy spec-driven-development](https://github.com/addyosmani/agent-skills/blob/aeac41d4d005999432bb7312f7ff06383a91d59d/skills/spec-driven-development/SKILL.md)
  covers specify, plan, tasks and implementation, including capability scoping.
  Importing that whole flow would compete with existing AK orchestration and
  planning. No second workflow is needed for this extraction.
- [Superpowers brainstorming](https://github.com/obra/superpowers/blob/main/skills/brainstorming/SKILL.md)
  distinguishes small work from written designs and feeds a separate planning
  skill. It was inspected as a comparison on 2026-10-17, not copied or pinned as
  an imported dependency. Its interview/review runtime is outside this change.

Matt is selected for method fit, not repository popularity. The pstack > Matt >
Addy preference only resolves otherwise comparable choices.

## Local adaptations and ownership

The spec can be drafted or updated directly without starting SDLC or requiring a
tracker. Preserve a current requirements authority and its stable acceptance IDs;
do not create competing specs. Standalone draft location is a fallback; an SDLC
caller supplies its canonical artifact location and retention contract.

Omit upstream automatic publication, setup dependency, fixed labels, exhaustive
user-story format, one-test-boundary preference and routine reconfirmation.
Use ordinary skill discovery metadata so SDLC can select the method; actual
native selection is a separate client check. Creation of a spec grants no ticket,
implementation or publication authority. Existing issue policy owns any separately
requested external writes.

Preserve agreed decisions and evidence-backed change boundaries. Ask only about
consequential missing decisions, or deliver a qualified incomplete draft; do not
invent choices to make the artifact look ready. Already selected designs belong
in the spec by reference; new architectural choices remain with design. Planning
retains task decomposition and PR topology. This extraction changes no TDD method
or SDLC receipt schema.

## Community evidence

Reviewed 2026-10-17; this is limited, workflow-specific evidence:

- [Matt #966](https://github.com/mattpocock/skills/issues/966), opened 2026-08-26,
  identifies conflicting no-interview and test-boundary confirmation instructions.
  A September 5 fork report removes routine questions. An October 6 user instead
  describes a useful confirmation that exposed a restriction against test
  repositories. These favor distinguishing settled answers from consequential
  gaps, not a blanket always-ask or never-ask rule. The October 7 maintainer-account
  summary is explicitly AI-generated triage, not a separate human endorsement.
- [Matt #843](https://github.com/mattpocock/skills/issues/843), opened 2026-08-12,
  reports an anonymized project where a spec recast existing navigation/catalog
  capabilities as new work. This supports a concise conditional change boundary;
  the report is not independently reproduced here. The October triage is labeled AI.
- [Matt #526](https://github.com/mattpocock/skills/issues/526), opened 2026-07-12,
  reports a useful tracker-search fork without a concrete duplicate-spec incident.
  It was closed as not planned by AI-labeled triage on October 6. Reuse known
  authoritative records; do not add mandatory whole-tracker searches to local
  spec drafting. Existing issue publication policy retains duplicate checks.
- A [Reddit account](https://www.reddit.com/r/SpecDrivenDevelopment/comments/1wqw8wk/mattpococks_skills_users_are_you_seeing_opus_55/)
  reports Opus 5.5 high drafting specs/tickets without reading the named skills,
  then improving them after reading. The observed page showed relative dates and
  an inconsistent crawl age, so no exact publication date is asserted. Replies
  do not establish a controlled comparison or explain model training. This supports
  retaining SDLC's actual-source-read requirement, not claiming metadata enforces it.

No independent version-specific consensus was established. Selection is provisional
with respect to community validation; source fit and the requested extraction are
the basis for adoption. Raw source and feedback records remain local.

## Verification boundary

Validate metadata, licenses, declared resources, routing and links; inspect that
SDLC no longer owns a second content checklist. Exercise an existing-spec update
and a constrained incomplete request, then check the regenerated catalog in the
browser. Record observed outcomes in [client verification](../client-verification.md).
Source presence and simulated method application do not prove native discovery,
authenticated publication or complete SDLC execution.
