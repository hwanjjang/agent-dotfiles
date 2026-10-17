# Optional reviewer guidance

Keep the repository's template and required fields. Add only the explanation
needed to understand this change; do not impose a second PR-body template.

- Start with the problem and observable result. Point to the entry file or flow
  where review should begin, then distinguish substantive from generated changes.
- If prose is insufficient, include one small view of the changed relationship
  or behavior. A short sketch or diagram must clarify the diff, not decorate it.
- Link actual verification and its candidate. Before/after evidence is useful
  when available and relevant; never invent an earlier failure. A screenshot
  demonstrates the captured UI state, not every acceptance criterion.
- Explain material compatibility or migration risks, who is affected and whether
  reversal needs more than reverting code. Avoid universal risk categories when
  a plain sentence is clearer. Mark unrun checks and remaining uncertainty.
- Link dependencies and describe the order for reviewing dependent PRs. Use
  issue-closing references only as allowed by the shared issue workflow.

Inspired by Matt Pocock's `pr` guidance at the revision in
[provenance](../provenance.json). Matt credits Dex Horthy / Humanlayer's `show-me`
for its visual explanation approach; see the pinned
[upstream credits](https://github.com/mattpocock/skills/blob/49dd158d1076134a641b33efb035946536778336/skills/engineering/pr/CREDITS.md).
This is a local synthesis, with no copied visual examples or additional skill
dependency.
