# Agent-friendly architecture

Apply these minimum principles when designing or changing code. Respect the
destination project's architecture and conventions.

1. **Make relevant code easy to find.** Use names and placement that reveal its
   purpose. Keep related behavior together instead of scattering it unnecessarily.
2. **Keep boundaries and responsibilities clear.** Make public interfaces and
   ownership of mutable state clear, so a change does not depend on knowing the
   internals of several other modules.
3. **Make changes verifiable.** Provide a practical way to check the affected
   behavior. Run checks appropriate to the change; use existing checks when adequate.

Keep a structure that already works. Improve it when repeated difficulty finding,
changing, or verifying code demonstrates a need. This policy sets no fixed folder
layout, file size, layer count, or required tool. Use additional design patterns
and documentation only when they help the task.

## Optional references

- [pstack design red flags](../skills/architect/references/design-red-flags.md):
  examples to consult when boundaries or ownership are causing difficulty.
  The package records its [revision and adaptations](../skills/architect/provenance.json)
  and [MIT license](../skills/architect/LICENSE).
- [Matt's codebase-design](https://github.com/mattpocock/skills/blob/49dd158d1076134a641b33efb035946536778336/skills/engineering/codebase-design/SKILL.md):
  deeper interface-design guidance, available under its
  [MIT license](https://github.com/mattpocock/skills/blob/49dd158d1076134a641b33efb035946536778336/LICENSE).

Source: AK-authored policy, revised locally after source review on 2026-10-17,
under this repository's [MIT license](../LICENSE). The local adaptation keeps
three minimum principles; detailed upstream workflows are optional references.
No additional skill or runtime dependency is required.
