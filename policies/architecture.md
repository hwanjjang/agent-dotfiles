# Architecture Policy

Applied at spec time, not after implementation.

- Use the destination project's documented architecture boundaries and invariants
  (for example, its own `AGENTS.md` or architecture documents). Specs must state
  which boundaries a change touches. This collection's maintenance instructions
  do not define another project's system architecture.
- Prefer extending existing patterns over introducing new ones; new patterns
  require an "Alternatives considered" section in the spec.
- Cross-cutting or multi-module changes require a dependency graph in the plan
  and are split into independent tasks with explicit ownership and integration order.

Apply the destination project's concrete system invariants.

Source: AK-authored policy, supplied for public reuse under this repository's
[MIT license](../LICENSE). Adapted for destination-specific ownership and existing
authorization. Private source metadata is retained outside public Git.
