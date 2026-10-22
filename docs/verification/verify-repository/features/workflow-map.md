# Follow AK SDLC in the reference map UI

Scenario ID: `workflow-map`. A reader follows the AK route, opens skill/category
explanations, finds cross-stage methods and navigates the adopted super-board
canvas. Surface: the separate `docs/map/workflow.html` viewer.

## Run

Use the existing Playwright/Chromium prerequisites from
[the repository verifier](../SKILL.md). The dedicated command leaves the original
catalog verifier unchanged:

```sh
node docs/verification/verify-repository/scripts/check-workflow.cjs .local/workflow-evidence-NEW
```

The output directory must not exist. `VERIFY_BROWSER_CHANNEL` or
`VERIFY_BROWSER_EXECUTABLE` selects an already-installed browser. No browser MCP
server or account configuration is installed.

## User paths and expected outcomes

1. Open the viewer. Stage headers match the current canonical route and all
   mapped items have nodes. Intent has two alternative categories, with no arrow
   connecting the two interviews. Open Merge for its authority requirement and
   Correction for its verification/review return.
2. Open Grill Me and expand its details. Its trigger and usage are visible and
   Sources points to `skills/grill-me/SKILL.md`. Matching skills also show an
   illustrative request, internal flow, AK adaptations and pinned reference and
   provenance links. Check Grill With Docs, Architect, To Spec and TDD: the last
   identifies the single pstack-derived method. Search glossary: Domain Modeling
   remains bright and unrelated TDD nodes dim. A nonsense query dims every skill;
   clearing the query restores them. Search preserves layout, rather than removing
   nodes.
   Also inspect Archify, Code Review And Quality, Issue Writing, Planning And Task
   Breakdown, Planning With Files, Screenshot Manual and SDLC. Each has a concrete
   example, flow, scope notes and public provenance; the SDLC explanation preserves
   its pre-merge endpoint and conditional method selection. Create Formal
   Verification and Maintain Formal Verification state that they run only on an explicit
   request, and both link their provenance.
   Inspect Communication, Execution and the Account setup & runtime group too:
   source links must resolve, triggers must explain when to use them, and account
   source/hook entries must state that they do not establish native activation.
   The account transaction verifier names its two properties and links its source.
   Inspect **Self-improvement & eval (1-6)** as a separate numbered cycle:
   observation, reproduction, candidate, eval, review and deployment. Check each
   node's source and capability boundary: synthetic storage, explicit task feedback,
   reviewed synthetic case export, offline evaluation accounting, committed-source recommendations
   and the installer exist; Claude/Codex collection is available with separate
   consent/native-trust boundaries; one bounded live development comparison is
   complete with a reject result, while held-out evaluation and automatic
   promotion remain pending or planned.
   Search `eval` and confirm the comparison node stays visible. These nodes must
   not add mandatory PR state-machine stages.
3. Zoom with +/-, Fit, drag the canvas and drag a node. Camera and node placement
   change; placement survives reload. Reset layout restores positions. Full screen
   opens and exits through the control.
4. Toggle theme and follow `#skill-domain-modeling`. At 390px, the page and skill
   dialog remain inside the viewport. Escape closes the dialog. All interactions
   run offline, without unexpected browser errors or changes to maintained files.

The script records candidate hashes, checks and cleanup in `result.json`, plus
screenshots of desktop, dark, dialog, mobile and mobile-dialog states. It checks
both generated maps and closes its isolated browser. Inspect screenshots for
clipping and readable dialog content; assertions alone do not prove visual quality.

The [screenshot walkthrough](../../../manual/workflow.json) shares this scenario.
Not covered: actual skill execution, installation, MCP connectivity, every browser
or every query. Stage semantics still need review against the authoritative routing.
