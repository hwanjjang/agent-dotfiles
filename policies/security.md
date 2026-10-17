# Security Policy

Applied at spec time, not after implementation.

- No secrets, credentials, or tokens in the repository or in agent artifacts.
- Use task-authorized identities and credential mechanisms; keep credential values local.
- New dependencies require justification in the plan and pass vulnerability review.
- Auth/authorization changes always get a dedicated security review lens.
- Must-follow rules here are candidates for deterministic enforcement (CI checks,
  hooks) — instructions alone are advisory.

Source: AK-authored policy, supplied for public reuse under this repository's
[MIT license](../LICENSE). Adapted for destination-specific ownership and existing
authorization. Private source metadata is retained outside public Git.
