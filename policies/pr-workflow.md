# Reviewable PR workflow

Use when planning, preparing or updating pull requests. This policy adds no
lifecycle stage and requires no issue, stack tool, or parallel agents for local
work. The destination's review requirements and existing task authority apply.

## Choose the merge units before implementation

Give each PR one coherent purpose and a verifiable result on its intended base.
Keep the related tests, documentation, configuration and map changes with the
behavior they describe. Separate unrelated work and substantial mechanical
refactors; do not split by a fixed line, file or time limit. A large generated
diff may need a short explanation rather than artificial fragmentation.

For multi-part work, use [planning-and-task-breakdown](../skills/planning-and-task-breakdown/SKILL.md)
to produce the task graph and PR map. Tasks describe assignable work; PRs describe review and merge units.
Several tasks can share a PR, and a task can span several PRs when acceptance and
remaining work are explicit. Do not assume one ticket means one PR.

Independent PRs start from the destination's integration branch. A dependent PR
targets its parent branch while that parent is unmerged, with the relationship
visible to reviewers. After a parent lands, reconcile the child's base and rerun
affected checks. A single PR needs no separate stack plan.

Every main-merge unit must pass its applicable checks. Test-first failing evidence
is development evidence, not permission to merge a broken intermediate PR.
The planning skill owns wide-refactor decomposition; incomplete internal tasks
must not be presented as independently merge-ready PRs.

## Prepare, update and integrate

Use [make-pr-easy-to-review](../skills/make-pr-easy-to-review/SKILL.md) for author-side
preparation and description writing. If explanation
cannot make the scope coherent, propose a split. Unrelated new work belongs in a
separate PR rather than being appended to an existing reviewed candidate.

One coordinator owns branch/base changes and other shared stack mutations.
Parallel workers own bounded changes, not competing rebases or pushes. Record
the actual head and base behind review and verification evidence. Changed code,
contracts or base invalidate affected evidence; matching patch IDs alone do not
prove compatibility. Preserve review findings and recheck the combined candidate.
Land dependencies before dependents, only within existing merge authority.

Local preparation, external publication, history rewriting and merge are distinct
actions. Reuse authority already supplied, but do not infer a rewrite or force-push
from a generic request to improve reviewability. Preserve unrelated work, human
edits and repository protections. A stale remote head requires reconciliation,
not an overwrite. Draft/ready status follows the actual candidate and destination
conventions; this policy mandates neither all-draft nor all-ready PRs.

[Evidence](evidence.md) owns truthful verification claims;
[issue workflow](issue-workflow.md) owns tracker writes, issue completion and
closing references; [security](security.md) owns disclosure boundaries. A PR
preparation result is not an independent review or a merge authorization.

## Sources and adaptations

Selected 2026-10-17. The [decision record](../docs/decisions/pr-workflow.md) pins
sources and distinguishes community reports from effectiveness claims. This
policy synthesizes pstack's PR planning and verified sequencing, Matt's outcome
slicing, and Addy's focused changes. It omits their full runtimes, numeric size
gates, fixed labels and automatic publication. GitHub stack tooling remains
optional and uninstalled.

### Upstream license notices

MIT License

Copyright (c) 2026 Lauren Tan

Copyright (c) 2026 Matt Pocock

Copyright (c) 2025 Addy Osmani

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
