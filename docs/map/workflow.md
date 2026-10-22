# AK SDLC skill map

Open [the AK SDLC map](workflow.html) in a browser. This separate map uses the
same MIT-licensed super-board renderer as the supplied
[pstack](https://erictechpro.github.io/super-board/pstack/) and
[Matt Pocock](https://erictechpro.github.io/super-board/mattpocock/) maps, with
this repository's AK SDLC stages and catalog data. The
[original catalog map](index.html) keeps its layout and shares the updated descriptions.

The generated HTML is self-contained and works offline. GitHub's HTML file view
shows source; open the local HTML file to use the map.

Start SDLC work through `sdlc` with the request, issue or PR and desired endpoint.
The [intake method](../../skills/sdlc/references/intake.md) checks current evidence,
reuses adequate artifacts and starts the earliest unmet prerequisite. Reassess on
consequential scope changes or resumption. The columns show stage relationships;
they do not require repeating completed work or grant authority through a URL.

## Use the map

- Read the 13 stage columns from left to right. Categories group skills within a
  stage; arrows show a method sequence. Open a category to read its numbered
  conditions. Optional methods remain optional. Intent's two interview methods
  are separate alternatives, without an arrow between them.
- The **Anytime** band contains recurring cross-stage methods, policies and tool
  connections. Select a skill for its trigger, purpose, usage, expected result
  and authoritative source. Expand the relevant detail sections, or Expand all.
  All focused skills remain directly usable within their own scope.
- **Search** dims nonmatching nodes, preserving the surrounding map. Clear it to
  restore every node. Use **+ / -**, wheel/pinch zoom and background dragging to
  inspect the wide route; **Fit** shows the whole map. Drag nodes or stage headings
  to rearrange your local view. **Reset layout** restores it. Camera and positions
  are saved locally by the original engine.
- **Full screen** expands the canvas. **Theme** switches light/dark appearance.
  Tab to a node and press Enter or Space to open it; Escape closes its detail
  dialog. Direct skill links use `workflow.html#skill-grill-me`.
- Correction returns to self-verification and PR review. Merge requires explicit
  authority and a main endpoint. The Completion stage details account for the
  separate independent-verification stage used by other explicitly requested
  lifecycle routes. The map never executes a skill or installs a tool.

Like the upstream SDLC maps, canvas mode is always on and group-collapse controls
are hidden. No platform-support filter is shown because this collection does not
claim every mapped item is installed or verified in each client.

See the [screenshot walkthrough](../manual/workflow.pdf) for two user paths.

The Anytime band also includes communication/execution policies and an **Account
setup & runtime** group. Use it for portable install/update/removal, ownership, planning hooks
and reviewer launch diagnostics. Account doctor adds offline/native/model checks;
Paseo is an explicit option, with its own real-model evidence and cleanup. These are supporting sources, not extra SDLC
stages or installed account features. Their dialogs link to the authoritative
guides; the account selection comparison is linked from the account guide.

The **Verification upkeep** group holds two pairs. Use the user-journey
pair when a project lacks repeatable UI, CLI, API or library checks, or when they have
drifted. Use the formal pair only when someone explicitly asks to formally verify,
model-check or formally prove a property, to recheck such a check after its code
changed, or to resync a stale formal model, proof or harness. The two repository verifiers in the group check this checkout only.

## Self-improvement and eval

The Anytime band includes **Self-improvement & eval (1-6)**. Read its numbered
nodes in order: observe, reproduce a case, prepare a candidate, compare through
eval, review promotion evidence, then deploy and observe again. Open the group
header for the cycle and each node for its status, handoff and source. Search
`eval` or bookmark `workflow.html#skill-improvement-eval`.

This is a separate improvement cycle, not six new mandatory stages in the PR
state machine. Synthetic storage, explicit task binding/feedback, opt-in Claude/Codex
collection, offline evaluation accounting, committed-source recommendations, selected same-host receipt verification and the installer
exist. Evidence-bound caller triage and reviewed synthetic case export are available;
reproduction and candidate editing can use existing manual methods. Codex adds four
separately trusted observer definitions; the native guide owns platform proof and
blockers. One bounded live development comparison is
[complete with a reject result](../evidence/native-development-pilot-2026-10-19.md);
automated diagnosis, held-out evaluation and automatic promotion remain pending or planned.
The catalog's **available** status means the linked guide exists, not that every
described runtime is implemented. Node subtitles and details state these limits.

Use the [improvement design](../decisions/account-improvement-loop.md) as the
behavior authority and the [observation guide](../../account/observation/README.md)
for today's runnable synthetic example and task-bind/feedback-add/task-show commands.
The [task-feedback recipe](../verification/verify-repository/features/task-feedback.md)
and [walkthrough](../manual/task-feedback.pdf) cover the explicit selection journey.
Then follow the [reviewed-case recipe](../verification/verify-repository/features/reviewed-cases.md)
and [case walkthrough](../manual/reviewed-cases.pdf) for prepare/show/review/export. An improvement candidate can enter the
ordinary investigation/specification/build/review route when appropriate; eval
adds a behavioral comparison and does not replace project tests or independent
review. Step 5 links the [recommendation contract](../decisions/promotion-recommendations.md)
and [source-backed workflow](../architecture/native-recommendation-workflow.html);
the [actual development comparison](../evidence/native-development-pilot-2026-10-19.md) returned reject, and held-out evidence for a positive recommendation remains pending despite FAKE positive conformance. Collection consent does not authorize inference, publication or deployment.

Account doctor connects to this cycle as setup qualification before eval and an
affected-client check after deployment. Failures can feed reviewed case preparation.
Its successful model scenario is not comparative evidence; the loop design owns
the [reuse boundary](../decisions/account-improvement-loop.md#account-qualification-and-reuse).

## Source and maintenance

[Stage-to-skill routing](../../skills/sdlc/references/skill-routing.md) owns method
selection. [The SDLC state model](../../skills/sdlc/scripts/sdlc_state.py) owns
stage IDs/order. Skill and policy files own their methods and rules.

[workflow.json](workflow.json) contains navigation summaries, item references,
contextual triggers and short canvas labels. [catalog.json](catalog.json) remains
the source of item descriptions, usage, behavior and source paths. The build
adapter converts these into the upstream renderer's stages, categories, Anytime
groups and skill models. No skill body is copied into a second maintained source.

All 26 skills have expanded explanations. Sixteen matching skills use the reference
maps as teaching references; the remaining ten use their adopted upstream or
AK-authored methods directly. Every explanation is checked against the local
`SKILL.md`, with public upstream sources pinned where applicable. Their
details include concrete triggers, steps, expected results, an illustrative
request, a flow, related methods and sources. **AK adaptation** notes distinguish
our behavior from the reference map. A matching name alone does not establish
equivalence: `tdd` uses only our pstack-derived method, not Matt's separate method.
Examples describe intended use; they are not evidence that a skill was executed.

The optional `explanation` object in `catalog.json` owns these examples, flows,
conditional calls, adaptation notes and source links. **Calls these** identifies
methods available within the skill's documented conditions; it does not mandate
every call. The [explanation source manifest](skill-explanations.json) records the
source basis, applicable reference revision and local source fingerprints reviewed
for each entry. AK-authored methods link to public local sources, without private
repository references. When
those sources change, review the explanation and refresh its fingerprint. The
local skill remains authoritative. Regenerate both maps after catalog changes.

```sh
python3 scripts/build_map.py
python3 scripts/build_workflow.py
python3 scripts/build_workflow.py --check
python3 scripts/build_map.py --check
python3 -m unittest discover -s tests -p 'test_build*.py'
```

The workflow generator writes only `workflow.html`; never edit that generated
file. It rejects unknown items, missing triggers/labels, unaccounted or reordered
canonical stages and skills absent from both stage and Anytime navigation.
Semantic routing changes still need a source review; checks do not interpret prose.

The [workflow-map recipe](../verification/verify-repository/features/workflow-map.md)
verifies real browser behavior. Refresh screenshots and the PDF after relevant
UI changes. Keep raw browser evidence in ignored local storage.

## Upstream implementation

The renderer is pinned to super-board revision
`7d848f7555875e0f75768c9216cc3f5efbfc88f1` (inspected 2026-10-17).
The shared CSS, canvas, dialog and shell JavaScript are preserved unchanged.
The renderer's fixed six-stage taxonomy is parameterized for AK SDLC; unused
platform-logo imports are removed. The Anytime header uses the existing group
detail model. Navigation identifies this repository.

The [provenance manifest](vendor/super-board/provenance.json) records exact source
hashes, dependencies and adaptations. The [MIT license](vendor/super-board/LICENSE)
is retained alongside the source and embedded in generated HTML. Selected reference
explanations inform locally verified summaries; the full upstream skill catalog,
comparative rankings, author logos and plugin installation are not included.

The Observe guide also links the implemented bounded delivery snapshots and the
10,000-callback qualification. Capacity/recovery passed the measured synthetic
PostToolUse-only workload; the capacity guide owns the final p95 and its
reference-host limit. SessionStart/Stop boundary probes are outside that timing. Boundary receipt hashes do not
establish exact model exposure. The native-observation recipe owns repeatable
checks, and the capacity guide owns its limits and measurements.
