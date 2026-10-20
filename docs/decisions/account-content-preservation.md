# Preserve useful account content in maintained source

Reviewed: 2026-10-20. Scope: repository source and an authorized PR; no account
activation, permission change, new connection or merge.

The account audit compared file contents, supporting resources and executable
behavior. Ten portable policies and 22 existing skill packages already matched
the maintained source. The SDLC deployment contained a later optional-isolation
amendment while this repository contained newer intake work. Preserve both through
a selective merge rather than replacing either package wholesale.

## Selected changes and ownership

| Need | Maintained owner | Selection |
| --- | --- | --- |
| Review proceeds without optional isolation proof | SDLC policy, host adapter, receipt template and validator | Default `read_only_required: false`; an explicit true opt-in requires verified evidence. False verified claims, model/effort/independence and action limits remain enforced. |
| Checkable source-heavy research | New `grounded-citations` skill and its ledger helper | Retain retrieved-source IDs, quote matching and numbered-report checks. Require task-local state; remove the Hermes runtime/account-cache dependency. |
| Requirements from documents and meeting notes | `to-spec/references/source-extraction.md`, also consumed by `to-tickets` | Preserve source versions/coordinates, modality, decisions versus proposals and unresolved owners/dates. Existing planning and issue policies retain their jobs. |
| Resolve empirical design uncertainty | `architect/references/feasibility-experiments.md` | Extend existing empirical checks with bounded runnable experiments, risk ordering and evidence-bound validated/partial/invalidated conclusions. |

No additional extraction/spike orchestrator, task schema, tracker, global skill
router or CLI installer is added. Product-owned/Paseo skills retain their existing
manager. Account installation remains a separate action using a committed source
revision; this PR alone does not update existing account snapshots.

## Primary sources and adaptations

Hermes sources are pinned to
[`b0427271e33c8b239985d3d66bd9d4f10f87e25b`](https://github.com/NousResearch/hermes-agent/tree/b0427271e33c8b239985d3d66bd9d4f10f87e25b):

- [grounded-citations](https://github.com/NousResearch/hermes-agent/blob/b0427271e33c8b239985d3d66bd9d4f10f87e25b/skills/research/grounded-citations/SKILL.md)
  and its Python helper: source registration, quote matching and reference checks.
  Local adaptation uses explicit `--ledger`, no client runtime import, bounded
  non-stealing locks and HTTP(S) URLs without embedded credentials. It does not
  fetch sources or prove truth/entailment. Destination chat citation conventions
  remain authoritative; helper verification covers numbered Markdown reports.
- [document-to-action-items](https://github.com/NousResearch/hermes-agent/blob/b0427271e33c8b239985d3d66bd9d4f10f87e25b/skills/productivity/document-to-action-items/SKILL.md)
  and [meeting-action-items](https://github.com/NousResearch/hermes-agent/blob/b0427271e33c8b239985d3d66bd9d4f10f87e25b/skills/productivity/meeting-action-items/SKILL.md):
  content extraction attributed to Ben Barclay and Hermes Agent. The adaptation
  reuses existing spec/ticket and publication owners rather than adding another
  per-record approval flow or assuming particular document/connector tools.
- [spike](https://github.com/NousResearch/hermes-agent/blob/b0427271e33c8b239985d3d66bd9d4f10f87e25b/skills/software-development/spike/SKILL.md):
  Hermes attributes its method to GSD's `/gsd-spike` by Lex Christopherson. The
  reference retains that attribution but does not import GSD packaging, commands
  or runtime. Fixed experiment counts, mandatory confirmation and hardcoding
  advice are omitted. Existing scope, evidence and security policies apply.

Each affected skill records selected revisions, source hashes, dependencies and
adaptations in provenance.json. Upstream MIT notices accompany the adapted
material. No existing pstack or Matt package is upgraded by this change.

The existing pstack-derived architect already owns design and empirical checks;
Matt-derived to-spec/to-tickets already own synthesis and materialization. Preserve
those agreed selections. Hermes supplies the missing narrow mechanics, rather
than replacing the established workflows. The maintainer preference tie-breaker
therefore does not choose between otherwise equivalent whole-skill replacements.

## Community evidence and limits

This is a provisional selection with respect to community effectiveness, not a
popularity ranking or proven improvement in agent performance.

| Source and date | Context and finding | Limit / consequence |
| --- | --- | --- |
| [Hermes issue 91542](https://github.com/NousResearch/hermes-agent/issues/91542), 2026-08-21; replies 2026-08-21 and 2026-09-06 | Reported missing `_hermes_home.py` on a profile-scoped Hub install of grounded-citations in Hermes 0.20.5, revision `fcbd1076a93841fa88855acce810e342a5b78101`. A later reply describes divergent copies across Windows and Linux installs. | Packaging/runtime failure report, not a skill-effectiveness comparison. We independently reproduced the missing-import failure from the selected source before removing the dependency. |
| [Hermes issue 85106](https://github.com/NousResearch/hermes-agent/issues/85106), 2026-08-13; replies 2026-09-13/14 | Developer discussion reports that Desktop removes numbered inline references required by the skill; replies discuss a focused fix and broader citation representation. | No local Desktop reproduction or claim that every current client fails. Keep chat rendering under the host's convention. |
| [Reddit discussion](https://www.reddit.com/r/hermesagent/comments/1w88n0e/what_are_your_favorite_hermes_skills_capabilities/), read 2026-10-20; page displays relative September dates | One positive multi-source sweep description explicitly quotes the poster's agent output; a reply criticizes limited RSS-based Reddit coverage. | Neither establishes independent measured improvement from grounded-citations. No consensus inferred. |
| [oh-my-hermes source register](https://github.com/rlaope/oh-my-hermes/blob/63d0b94120027d487c9a5235b9ec64b696af1b26/docs/SKILL-SOURCES.md), reviewed entries dated 2026-10-13/14 | Maintainer describes selective composition of spike and exploratory QA mechanics into existing owners. | A design/adoption record rather than independent efficacy evidence; reinforces the limited composition approach only. |

Targeted searches did not establish independently corroborated effectiveness for
the specific document/meeting extraction or spike methods. Focused synthetic
application and repository checks establish only the exercised behavior.

## Verification boundary

The regression test reproduced the original isolation rejection before the fix.
CLI tests exercise source registration, task separation, quote mismatch, missing
evidence, unknown IDs, URL mismatch, repeat rendering and lock contention. The
[worked CLI guide](../guides/grounded-citations.md) supplies an additional real
synthetic workflow. Maps, links, metadata and dependency closure are checked.
The PR retains exact candidate/check/review results and any unavailable checks.

The installer discovers committed skill entry points and carries all selected
skill/policy/document files with their relative paths. Verify the committed
snapshot in a disposable destination before claiming distribution. That does
not establish native automatic routing, real-provider research quality, live
tracker writes or an actual account update.
