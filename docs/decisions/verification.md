# Feature maps and project verification

Adopted: 2026-10-17. The two portable pstack packages fill a concrete gap: creating
and maintaining repeatable project-specific checks. Existing TDD, evidence policy,
SDLC gates and screenshot-manual remain their respective authorities.

## Source and selection

Selected cursor/plugins revision: `101b274dd991f694e1f7024be2157e5f3adf07de`.
[Create](https://github.com/cursor/plugins/tree/101b274dd991f694e1f7024be2157e5f3adf07de/pstack/skills/create-verification-skill)
and [maintain](https://github.com/cursor/plugins/blob/101b274dd991f694e1f7024be2157e5f3adf07de/pstack/skills/maintain-verification-skill/SKILL.md)
provide launch/doctor/drive/evidence/cleanup, user-facing feature recipes and drift
triage. Per-package provenance pins exact files, including the three generator
examples; each package retains the MIT license. Example Notes commands are not a
bundled executable. Adaptations preserve method coverage while using actual host
capabilities, bounded authority and honest partial outcomes.

[Matt wayfinder](https://github.com/mattpocock/skills/blob/49dd158d1076134a641b33efb035946536778336/skills/engineering/wayfinder/SKILL.md)
charts planning decisions; [Addy capability maps](https://github.com/addyosmani/agent-skills/blob/aeac41d4d005999432bb7312f7ff06383a91d59d/skills/spec-driven-development/SKILL.md)
chart decomposition. Neither replaces user-journey verification. LangWatch's
[feature-map](https://github.com/langwatch/langwatch/blob/f2d13c71bf4544640d807728165d743cdf2b99b8/.claude/skills/feature-map/SKILL.md)
connects product capabilities to UI/API/CLI/MCP surfaces; use that idea only where
those surfaces exist, without copying product-specific paths or dual inventories.

Cursor team's verify-this is an optional claim-comparison reference. Superpowers
verification-before-completion and team-kit run-smoke-tests add little beyond this
collection's existing evidence policy and actual project commands, so they are not
additional packages. Browser and claim references are centralized in
[tool selection](../../skills/create-verification-skill/references/verification-tools.md).
Playwright agents/CLI and Chrome DevTools remain optional host capabilities, not
new required MCP configurations. Healer skips never count as passed required coverage.

## Ownership and use

- Shared source: [create-verification-skill](../../skills/create-verification-skill/SKILL.md)
  and [maintain-verification-skill](../../skills/maintain-verification-skill/SKILL.md).
- Each target owns one local verify-<app> source and its feature recipes. Keep
  expected user behavior in those recipes; visual indexes link or derive from them.
- SDLC [routing](../../skills/sdlc/references/skill-routing.md) selects the method
  within an existing stage. TDD still owns implementation; SDLC owns acceptance,
  evidence validation, integrated smoke and review. No new mandatory lifecycle.
- Manual authoring reuses scenario IDs and sanitized captures while separately
  checking PDF content and layout. A screenshot is not proof of persistence.

A generator qualifies at least one real journey and reports untested features.
An explicit full audit covers the whole declared map and reconciles missing
surfaces. Routine edits exercise affected paths rather than forcing a full audit.
Source readers may be parallel when authorized; shared app driving has one owner.
Isolated parallel sessions require separate state, not merely separate worktrees.

Do not import automatic publication, global installation, personal browser access
or unconditional process spawning from upstream. Missing prerequisites stay
blocked/not-run. Document, harness and product defects remain distinct; expected
behavior cannot be rewritten to make a regression pass.

## Repository pilot and limits

The maintenance-only [verify-repository](../verification/verify-repository/SKILL.md)
and [feature index](../verification/verify-repository/features/README.md) cover local
catalog search/recovery, usage/source links and map freshness. They live outside
`skills/` because they maintain this repository and are not distributed defaults.
The executable helper reuses an available Playwright library, creates an isolated
browser, runs actual CLI/UI checks and preserves evidence after cleanup.

The [client verification record](../client-verification.md) distinguishes actual
pilot results from installation, model adherence and MCP execution. Qualify other
targets on their own runtimes. A mocked or substitute environment cannot establish
behavior it does not provide. Skill behavior evaluation is separate from verifying
a product and should include startup gaps, stale recipes, real regressions and
cleanup rather than only checking Markdown metadata.

## Community evidence

Selection is based on source fit and the maintainer's decision, not repository stars.
A [pstack workflow report](https://www.reddit.com/r/cursor/comments/1wrmig0/killer_combo_cursor_projects_pstack_huge/)
is favorable about verification artifacts but does not isolate these two skills.
Direct independent, version-specific evaluations of the pair remain sparse.
[Generic-skill discussion](https://www.reddit.com/r/ClaudeAI/comments/1uhed8x/why_are_all_the_claude_code_skill_files_i_see/)
raises the cost of duplicating standing rules. [Playwright healer discussion](https://www.reddit.com/r/Playwright/comments/1witr6w/playwrights_healer_agent_is_supposed_to_know_the/)
raises false-green and skipped-test concerns. These are anecdotal reports, not a
measured ranking; cross-posts and registry mirrors are not independent validation.

## Related adoption

The [formal verification decision](formal-verification.md) adopts pstack's separate
create/maintain pair for properties checked across every case in a stated scope. It
complements these user-journey recipes and runs only on explicit request.
