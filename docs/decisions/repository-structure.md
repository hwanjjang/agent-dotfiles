# Initial repository structure

Status: Adopted for the initial scaffold; revisit as content and distribution
requirements become concrete.

Investigated: 2026-10-17. The links below pin the revisions inspected. This is a
comparison of source organization, not a compatibility or runtime evaluation.

## Decision

Keep reusable source in `policies/`, `skills/`, and `mcp/`. Keep repository
maintenance instructions in root `AGENTS.md`, with `CLAUDE.md` importing it through
`@AGENTS.md`. Record lasting research and decisions under `docs/decisions/`.

Start skills at `skills/<skill-name>/SKILL.md`, with resources beside each skill.
Introduce categories only when the catalog needs them. Add client manifests,
adapters, install scripts, and their checks when an actual distribution route is
selected. These are future extensions, not implemented features.

Keep raw research and task state in ignored `.planning/` or `.local/`. Public
notes contain sanitized conclusions, source links, and the rationale for choices.
README owns the detailed public-versus-local content boundary.

## Compared repositories

Inspected each repository's README and complete Git tree, plus selected manifests
and contributor instructions. Observations describe the pinned source; the last
column is this project's interpretation.

pstack, Matt Pocock, and Addy Osmani are the user's priority references. The
additional projects broaden the comparison; this is not a popularity ranking.

| Source at inspected revision | Observed organization | Implication here |
| --- | --- | --- |
| [pstack](https://github.com/cursor/plugins/tree/ac4e25a0064cd600afdd605208bad72748cb019a/pstack) | `skills/`, `agents/`, `docs/`, portable `plugin.json`, and `.cursor-plugin/` metadata. README describes generated Claude harness artifacts. | Keep source distinct from client packaging; add generation only when a second delivery format requires it. |
| [Matt Pocock](https://github.com/mattpocock/skills/tree/49dd158d1076134a641b33efb035946536778336) | Skills grouped into engineering/productivity and other lifecycle buckets. A manifest explicitly lists the promoted skills; docs mirror promoted categories. | Categories and release selection solve catalog problems. Defer them until there is a catalog to organize. |
| [Addy Osmani](https://github.com/addyosmani/agent-skills/tree/aeac41d4d005999432bb7312f7ff06383a91d59d) | Top-level `skills/`, `agents/`, commands, shared `references/`, `evals/`, and client manifests. AGENTS.md explicitly governs the repository itself. README notes that individual skill installs omit root references. | Keep maintenance instructions separate from payload; colocate required resources so a selected skill remains complete when distributed alone. |
| [Jesse Vincent / Superpowers](https://github.com/obra/superpowers/tree/bb92a77741419a4ab5f06e711a283343f1ada0c3) | Shared `skills/` alongside multiple client plugin directories, `hooks/`, `docs/`, `scripts/`, and `tests/`. The inspected client manifest points at the shared skills. | Prefer a common skill source with explicit client integration boundaries. |
| [Affaan Mustafa / Everything Claude Code](https://github.com/affaan-m/everything-claude-code/tree/76aaa77df6adc5b889e689007bf99b9a4f74af34) | Separate `rules/`, `skills/`, `agents/`, `hooks/`, `mcp-configs/`, and install manifests. Rules include common and language-specific groups. | Policy, workflow, and connection configuration have distinct jobs. Its broader harness structure exceeds the current scope. |
| [Trail of Bits](https://github.com/trailofbits/skills/tree/5c99c03fb8a9ea568432ecbcba5d86e9f4ac2bf0) | A marketplace of `plugins/<name>/skills/` packages. Root `CLAUDE.md` contains only `@AGENTS.md`. | Adopt the instruction import pattern. Use per-plugin trees only if independently installable packages become necessary. |
| [Anthropic](https://github.com/anthropics/skills/tree/dbd4588f9e1033efb41dad4bef2f7947c8993d44) | Top-level `skills/`, `template/`, `spec/`, and marketplace selections. README distinguishes open-source and source-available material. | Colocate skill resources and check each source's redistribution terms before adoption. |
| [William Hobson](https://github.com/wshobson/agents/tree/044b4b21f083948e69ec878a7b07c8d0951a6ffa) | Per-plugin sources, client catalogs, `docs/`, and `tools/`. Contributor guidance describes shared source and client adapters. | Maintain source ownership separately from generated delivery formats and document capability differences. |
| [Vercel Labs](https://github.com/vercel-labs/agent-skills/tree/063bee94c3f4df8453406c830b0a7df0f2860278) | Top-level `skills/` and maintenance tooling. Contributor guidance places scripts and references within each skill. | A flat skill catalog is a viable starting point; keep skill-specific dependencies and resources nearby. |

## Tradeoffs and boundaries

- `policies/` is this repository's name for reusable behavioral defaults. Other
  projects use `rules/` or encode principles as skills. This name does not imply
  automatic discovery by any client.
- `mcp/` groups connection source and documentation. There is no selected shared
  schema, registered server, or generated account configuration yet.
- Top-level source directories make ownership visible with little scaffolding.
  A `plugins/` marketplace becomes useful when multiple packages need independent
  installation or releases; creating it now would impose an undecided packaging
  model.
- Skill category directories can improve navigation later, but introduce paths
  that manifests and tooling must understand. Begin flat and revisit with actual
  content.
- Required skill resources belong inside the skill's package. If shared resources
  are introduced later, define and verify how every installation route includes
  them; do not assume a per-skill install also copies repository-root references.
- An import keeps repository instructions in one file without depending on
  symlink handling. Claude's [documented import syntax](https://code.claude.com/docs/en/memory#import-additional-files)
  supports `@AGENTS.md`; no client startup or instruction-adherence test was run.
- `.gitignore` keeps designated local files out of ordinary staging. It does not
  inspect content or untrack existing files, as described in the
  [Git documentation](https://git-scm.com/docs/gitignore).

The [Agent Skills specification](https://agentskills.io/specification) supports
the chosen per-skill file layout. Client-specific manifests and MCP configuration
must still be checked against their current official documentation when added.

No external skills, policies, scripts, or installers were copied or executed as
part of this investigation. This note records structural choices only.
