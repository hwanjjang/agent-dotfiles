# Statechart skill

Adopted: 2026-10-30. The upstream author announced the skill as stable in pstack
0.15.36 ([post, 2026-10-29](https://x.com/poteto/status/2115880102601101414)); the
repository itself carries no stability label. Provisional with respect to community
validation. The skill fills one gap: a TLA+ model checked by TLC had no readable
result. [Archify](../../skills/archify/SKILL.md) draws an authored lifecycle that the
account verifier checks only against the model's status names. Statechart draws the
states and steps TLC actually explored and marks the shortest path to each broken rule.

## Source and selection

Selected cursor/plugins revision: `1ba91fc25c0977741dd0e267849e6234b037ed0a` (pstack
0.15.36). The skill was added in [#741](https://github.com/cursor/plugins/pull/741),
fixed in [#776](https://github.com/cursor/plugins/pull/776), moved to Pele and a
checksum-pinned mise install in [#791](https://github.com/cursor/plugins/pull/791), and
replaced by the current TypeScript compiler in [#977](https://github.com/cursor/plugins/pull/977)
with [#982](https://github.com/cursor/plugins/pull/982) and #981 on 2026-10-27. #977
removed the earlier chart-to-spec, code-audit and fix-comparison modes.

The compiler reads SANY's XML, the TLC config, TLC's state graph and traces into a
small IR, runs passes for labels, regions, reachability and paths, and writes Mermaid,
a plain-text report and a bounded TLC config. It checks every rule on the config as
written, then reruns without each broken rule; after the first break each run stops at
100,000 distinct states. A full chart is drawn only up to 500 states; above that only
bug paths are drawn, and with no break no chart is written.

The runtime payload is vendored unchanged with its MIT notice and per-file digests in
[provenance](../../skills/statechart/provenance.json). The upstream test directory
(370 files, about 3.6 MB) is not vendored. Upstream `disable-model-invocation: true`
is kept: unlike the formal pair, statechart has no narrower trigger to rely on.

The tie-break did not decide anything: Matt Pocock's skills (`a496f55`) and Addy
Osmani's agent skills (`eb07f19`) contain no statechart, TLA+ or model-check skill.

## Same-revision adoptions

- [create-formal-verification-skill](../../skills/create-formal-verification-skill/SKILL.md)
  takes the one upstream change since `190d287`: a generated verify skill reads TLA+
  results with statechart by name (#794, revised by #977). The local wording adds that
  the chart replaces neither the conformance link nor the scratch-break qualification.
  The maintain skill is unchanged upstream and stays at `190d287`.

## Community evidence and limits

Searches on 2026-10-30 covered the web, Reddit, Hacker News (Algolia API) and GitHub.
No firsthand report of using statechart on a real system was found. X replies could not
be read; likes and reply counts are not evidence.

| Source and date | Context and finding | Limit and consequence |
| --- | --- | --- |
| [Author post](https://x.com/poteto/status/2115880102601101414), 2026-10-29 | Stable at 0.15.36; reports "2 real bugs"; the attached chart is statechart's own run lifecycle in a Pele blueprint theme. | Author claim. The chart marks no broken state, so the two bugs could not be identified. |
| [elderfo/pi-pstack-adapter#23](https://github.com/elderfo/pi-pstack-adapter/pull/23), 2026-10-22 | Independent port certified 0.15.30 with supervised end-to-end runs on Windows and Linux; its security review asked to disclose that the label module runs with full process permissions. | Pre-#977 scripts. The view-module disclosure is kept in provenance. |
| [Samuel-Harris/foundry#33](https://github.com/Samuel-Harris/foundry/pull/33), [chhoumann/t3-pstack#41](https://github.com/chhoumann/t3-pstack/pull/41), [garyj/pstack#5](https://github.com/garyj/pstack/issues/5), pstack-ports | Copies and change summaries. | Distribution, not validation. |
| [Pele on Hacker News](https://news.ycombinator.com/item?id=50132193), 2026-10-17 | Launch discussion (63 comments); its author, kepano, says Pele follows Mermaid syntax, not its layout. | About Pele, not statechart. Pele published 1.10.0 through 1.12.0 between 2026-10-24 and 2026-10-26; the skill pins 1.9.0. |

## Alternatives considered

- Archify lifecycle diagrams: richer presentation, but authored rather than derived from
  TLC. They remain the owner of explanatory pages; a statechart `chart.mmd` can be their
  Mermaid input.
- TLC's own `-dump dot` with Graphviz: the raw graph without reader labels, rule marks
  or shortest paths.
- [tlaplus/AgentSkills](https://github.com/tlaplus/AgentSkills): TLA+ writing procedures
  with no chart; already noted in the [formal verification decision](formal-verification.md).

## Repository pilot and limits

On 2026-10-30 under macOS, Node.js 24.19, OpenJDK 17 and tla2tools v1.7.4 (sha256
matched), the vendored command was run on a copy of the account transaction model
with `MaxKills = 1`, `MaxIOErrors = 0` and `MaxUserChanges = 0`, and a local view that
labels states by operation and journal status.

- The base model drew an 11-state, 15-arrow chart and every rule held, including
  `NoDeadlock`. With `MaxUserChanges = 1` it reached 528 states and wrote no chart; the
  verifier's own bounds reach 9,642 states.
- The `no-rolling-back-mark` variant (86 states, a 9-state chart) broke
  `NoSpuriousRefusal`, and the report gave the 15-step path: rollback is killed before it
  journals `rolling-back`, and a second rollback refuses. The verifier's harness already
  catches the paired code mutation.
- Without I/O errors the chart has no undo states, so it does not replace the Archify
  lifecycle or the verifier's full bounds.

The upstream test suite was not run locally: the session's permission classifier
declined running the downloaded upstream tests. Upstream #982 reports 367 passing
tests with TLC 1.7.4. Bun, Deno, the mise installation, Pele rendering, Linux and
Windows, and model-driven use were not exercised. The pilot's view and configs stay in
ignored `.local/`; the account verifier is unchanged.
