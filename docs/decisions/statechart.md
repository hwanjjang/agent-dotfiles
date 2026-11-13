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
(376 files, about 3.6 MB) is not vendored. Upstream `disable-model-invocation: true`
is kept: unlike the formal pair, statechart has no narrower trigger to rely on.

The tie-break did not decide anything: Matt Pocock's skills (`a496f55`) and Addy
Osmani's agent skills (`eb07f19`) contain no statechart, TLA+ or model-check skill.

## Same-revision adoptions

- [create-formal-verification-skill](../../skills/create-formal-verification-skill/SKILL.md)
  takes the one upstream change since `190d287`: a generated verify skill reads TLA+
  results with statechart by name (#794, revised by #977). The local wording adds that
  the chart replaces neither the conformance link nor the scratch-break qualification.
  The maintain skill is unchanged upstream and stays at `190d287`.
- [arena](../../skills/arena/SKILL.md) takes #986's judge rule without its Cursor model
  slugs: the judge never shares the lead's model family, and with no other family the
  judge is skipped and reported. As upstream, an unknown lead family still gets a judge,
  but never a seat that inherits the lead's model, and the report says the family check
  did not run.
- The [evidence policy](../../policies/evidence.md) takes
  `principle-explain-the-number` as a recommendation, not a gate, and
  [diagnosing-bugs](../../skills/diagnosing-bugs/SKILL.md) links it for performance
  regressions. The upstream benchmark-checklist dependency is not imported. Frozen
  evaluation rules keep precedence. Searches on 2026-10-30 found only directory
  listings of this principle, no firsthand reports.

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
tests with TLC 1.7.4. CI installs Java 17, Node.js 24 and the pinned jar, so the vendored
test's TLC case also runs on Linux there. Bun, Deno, the mise installation, Pele
rendering, Windows and model-driven use were not exercised. The pilot's view and configs stay in
ignored `.local/`; the account verifier is unchanged.

## Known limits from upstream reports

Reviewed on 2026-11-13 against cursor/plugins `ec56937`. No commit has touched
`pstack/` since the vendored revision `1ba91fc`, so the vendored payload still equals
upstream and each report below applies to it. All four reports and the proposed fixes
were open on that date, with no reply from a maintainer. The payload is not patched
here: it stays byte-equal to upstream, and fixes are considered when upstream merges them.

| Limit | Vendored code | Upstream report | Consequence here |
| --- | --- | --- | --- |
| Windows is not supported. Java on Windows ends lines with CRLF, the output is split on `\n` only, and the `$`-anchored TLC message markers then fail to match. Process cleanup also spawns `/bin/sh`. The reporter saw TLC finish and the command exit 1 with no chart or report. | `scripts/run.ts` (`outputLines`, `fileLines`, `killGroup`), `scripts/frontends/dot.ts` (`linesOf`), `scripts/frontends/messages.ts` (`START`, `END`), `scripts/statechart.ts` (the janitor) | [#1170](https://github.com/cursor/plugins/issues/1170), 2026-11-04, Windows 10 with Node.js 22.16; proposed fix [#1147](https://github.com/cursor/plugins/pull/1147) | Use statechart on macOS or Linux. Windows was not exercised here either. |
| Every TLC run uses one worker and no heap flag, so Java's default heap applies. The reporter's 31-million-state model ran about 50 minutes on one core and then failed with `OutOfMemoryError` in the final liveness pass. | `scripts/run.ts` (`PINNED_FLAGS`: `-workers 1 -fp 0 -lncheck final`) | [#1179](https://github.com/cursor/plugins/pull/1179), 2026-11-05 | Expect long runs and possible memory exhaustion on models with millions of states. The account transaction model stays far below that (9,642 states at the verifier's bounds). |
| A strict typecheck of the scripts fails: `exit` in the `common` object is inferred as `number`, not `0 \| 1 \| 2`. | `scripts/run.ts` (`common` and the two results that spread it) | [#1141](https://github.com/cursor/plugins/issues/1141), 2026-10-30, TypeScript 7.0.2 with `@types/node` 26.1.2 | A static-check failure only. The reporter observed no command failure, and the launcher runs the scripts without type checking. Do not add a typecheck gate for this payload without fixing or excluding these lines. |
| The upstream test for a launcher reached through a relative symlink fails on macOS, because the temporary directory sits behind the `/var` symlink. | Not vendored (`scripts/test/cli.test.ts` upstream) | [#1164](https://github.com/cursor/plugins/issues/1164), 2026-11-03; proposed fix [#997](https://github.com/cursor/plugins/pull/997) | A test-fixture failure, not a demonstrated command defect. Expect it when running the upstream suite on macOS. |

The proposed fix for the worker limit is not a drop-in update. It would run the first
check with one worker per CPU and keep a multi-worker trace for a broken `PROPERTY`
above 100,000 states, so that path can differ between runs. Decide on it separately
if upstream merges it.
