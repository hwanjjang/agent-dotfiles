# Selective account source import

Reviewed: 2026-10-17. Scope: repository source only; no account installation.

The aim is a better replacement for the selected development setup, not a complete
copy of an older account. Missing content earns inclusion only when it has a
current purpose, an identified owner and a checkable behavior. No comparative
agent benchmark has established that this collection is better overall.

## Comparison with the three reference collections

These are inspected source revisions, not new upgrades of adopted skill packages.

| Source | Observed approach | Decision for this repository |
| --- | --- | --- |
| pstack `technical-writing`, `session-pickup`, `setup-pstack` at `09d06eb4b97a1020ab31e84030e38baf1099c7dc` | Clear technical language, recovery from prior work plus artifact verification, and model choices based on detected host capabilities. | Keep the small existing bilingual writing rules; recover the selected plan and reuse supported reviewer routes. Do not import the entire writing stack, Cursor transcript recovery or Cursor model-rule installer. |
| Matt `handoff`, `writing-for-agents` at `49dd158d1076134a641b33efb035946536778336` | Handoffs reference existing artifacts and suggest relevant skills; agent instructions keep one authoritative definition and remove redundant material. | Add artifact-based handoff guidance to execution policy and retain the already adopted writing-for-agents method. No separate handoff skill or second notebook. |
| Addy `context-engineering`, `using-agent-skills`, `hooks/session-start.sh` at `aeac41d4d005999432bb7312f7ff06383a91d59d` | Restart from persisted scope, task state and verification; separate harness supervision from instructions. The meta-skill hook is reserved for hosts without native routing. | Keep explicit task state and baseline checks. Do not add a global meta-router, automatic session restarts or a second SDLC. |

Pinned primary sources:
[pstack writing](https://github.com/cursor/plugins/blob/09d06eb4b97a1020ab31e84030e38baf1099c7dc/pstack/skills/technical-writing/SKILL.md),
[pickup](https://github.com/cursor/plugins/blob/09d06eb4b97a1020ab31e84030e38baf1099c7dc/pstack/skills/poteto-mode/playbooks/session-pickup.md),
[model setup](https://github.com/cursor/plugins/blob/09d06eb4b97a1020ab31e84030e38baf1099c7dc/pstack/skills/setup-pstack/SKILL.md),
[Matt handoff](https://github.com/mattpocock/skills/blob/49dd158d1076134a641b33efb035946536778336/skills/productivity/handoff/SKILL.md),
[agent writing](https://github.com/mattpocock/skills/blob/49dd158d1076134a641b33efb035946536778336/skills/productivity/writing-for-agents/SKILL.md),
[Addy context](https://github.com/addyosmani/agent-skills/blob/aeac41d4d005999432bb7312f7ff06383a91d59d/skills/context-engineering/SKILL.md),
[routing](https://github.com/addyosmani/agent-skills/blob/aeac41d4d005999432bb7312f7ff06383a91d59d/skills/using-agent-skills/SKILL.md),
[hook](https://github.com/addyosmani/agent-skills/blob/aeac41d4d005999432bb7312f7ff06383a91d59d/hooks/session-start.sh).
These inform the comparison; their complete skills and hooks are not copied.

## Selection

- **Communication policy:** preserve language, clarity and meaning. The existing
  account guidance already fits pstack's clarity goals without imposing every
  document-mode rule, fixed word count or an extra unslop dependency.
- **Execution policy:** retain proportionate routing and plan freshness; link
  evidence, security, issue and SDLC authorities rather than repeat them.
- **Planning runtime:** retain only the POSIX Codex standalone and Claude
  SessionStart dependency closure at the already selected planning-with-files
  pin. It supports the current notebook method. The three preferred collections
  do not replace this exact plan-selection contract. Package discovery alone does
  not install lifecycle hooks. No meta-skill body is injected by the new adapter.
- **Reviewer continuity:** preserve working-route reuse and failure classification
  in the existing host adapter contract, without another policy file. Personal full-access exceptions, account
  identifiers, historical model flags and private evidence stay out of public Git.
- **Not selected:** Hermes integration, Graft, Windows/plugin account launchers,
  generic context-engineering and handoff skills, and an additional skill router.
  They lack a demonstrated need here or duplicate current methods. Existing Paseo
  and host-managed skills remain outside this payload's ownership.

The dispatcher and portable policies are AK-authored material supplied for public
reuse under this repository's MIT license. Private origin evidence stays local.
Upstream runtime assets are unchanged MIT files, pinned and hashed in their
[provenance](../../account/hooks/planning-with-files/provenance.json), with the
upstream license retained. The existing planning skill remains the shared
dependency. No upstream package is upgraded by this import.

## Community evidence and limits

- [Addy issue 569](https://github.com/addyosmani/agent-skills/issues/569), opened
  September 14, 2026: a contributor measured duplicated startup routing with
  Claude Code 2.1.90 and plugin 0.6.9. The author separated injection size from
  real-task effectiveness. Maintainer replies and the September 18 closure confirm
  removal of automatic meta-skill injection. This supports one routing owner;
  it is not a performance ranking of collections.
- [Addy issue 214](https://github.com/addyosmani/agent-skills/issues/214), opened
  May 31, 2026: a Windows/Git Bash report identifies an unquoted plugin path with
  spaces. It informs our quoted paths and disposable space-path tests, without
  claiming Windows support for this account adapter.
- [Matt handoff discussion](https://www.reddit.com/r/ClaudeAI/comments/1tjzqrx/handoffs_are_becoming_a_firstclass_pattern_in/),
  May 21, 2026: discusses artifact references and durable state, while promoting
  the poster's own framework. Treat it as a design anecdote, not independent
  proof of Matt's skill effectiveness. No broad skill-specific consensus for
  pstack technical-writing or a superior account hook replacement was established.

Selection is provisional with respect to community effectiveness. Task fit,
source behavior and focused checks decide this import; repository stars and the
maintainer's preference order are not the deciding evidence.

## Delivery and verification

The [account guide](../../account/README.md) owns replacement boundaries. Source
import does not authorize activation, account deletion, MCP enablement or remote
publication. Native discovery/activation and an old-versus-new task comparison
remain outstanding. The [verification record](../client-verification.md) separates
isolated script checks from client execution. Both maps share the catalog; account
sources appear in Anytime, without adding an SDLC stage.
