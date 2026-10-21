# Account installation and ownership

Reviewed: 2026-10-17. The request is reusable installation, update and deletion on
other hosts, with Codex/Claude required and installed Hermes opt-in. This follows
the [source import](account-source-import.md); it does not authorize applying this
checkout to the contributor's real account.

## Compared sources

- [pstack plugin manifest](https://github.com/cursor/plugins/blob/09d06eb4b97a1020ab31e84030e38baf1099c7dc/pstack/.cursor-plugin/plugin.json)
  points at one skill tree. Its setup-pstack skill configures detected Cursor model
  choices; it is not an account uninstall/rollback contract. We keep one source
  bundle without copying its Cursor model overrides.
- [Matt's installation guide](https://github.com/mattpocock/skills/blob/49dd158d1076134a641b33efb035946536778336/README.md)
  distinguishes plugin-managed updates from editable skill installations and warns
  against installing both. We retain one owner, explicit revision updates and no
  concurrent plugin installer for this collection.
- [Addy's guide](https://github.com/addyosmani/agent-skills/blob/aeac41d4d005999432bb7312f7ff06383a91d59d/README.md)
  documents native client adapters and the portability gap when individually copied
  skills refer to shared material. Our committed bundle preserves policy, skill,
  provenance and supporting-document paths rather than copying SKILL.md alone.
- [Vercel's installer](https://github.com/vercel-labs/skills/blob/13e4063a1cf913f5606d57d42ab83a86f5001e04/src/installer.ts)
  provides canonical-directory and symlink/copy modes across many clients. It is a
  useful distribution reference, but does not own this account's instruction/hook
  fragments or migration authority. We do not add a second dependency manager.

The implementation is AK-authored under the repository MIT license, adapting
existing account ownership/transaction patterns. It does not vendor these installers
or change any adopted skill revision. Preference order did not decide the choice:
none of these packaging examples provides this exact migration contract.

## Community evidence

[Vercel issue 886](https://github.com/vercel-labs/skills/issues/886) reports a local
source/canonical-directory overlap deleting SKILL.md before copying it. The report
and linked fix are specific evidence for overlap checks and non-destructive source
handling, not a claim that the current Vercel installer still has that defect.
The [install/bind separation proposal](https://github.com/vercel-labs/skills/issues/1038)
asks for clearer package versus agent-link lifecycle ownership; it is a design
request, not measured effectiveness. Matt's duplicate-install warning is author
guidance. Searches of developer/community discussions did not establish a broad,
independent preference for this custom account transaction design. Its selection
is provisional with respect to community validation and rests on scope fit and tests.

## Contract

- Read a committed local Git snapshot. Never use the contributor's account as a
  template, fetch mutable latest code, execute fetched setup instructions or embed
  credentials/model preferences. Resolve paths/interpreter on the destination host.
- Preview by default; `--apply` performs the selected operation. Conflicting
  selected assets require approval of the exact fingerprinted preview, with all
  inputs rechecked. Source overlap with any affected destination and indirect target paths are rejected.
- Keep one receipt for owned assets and exact configuration fragments. Merge hooks
  and selected MCP entries; preserve other settings and disabled state. Local drift
  blocks destructive replacement. Preserve Paseo/system tools under their owners.
- Serialize this installer's mutations with a local lock. Save private originals,
  write atomically per file, journal directory displacement before the rename and
  retain the original privately for retryable rollback without partial copying.
  This is not a multi-file atomic filesystem transaction; close clients during apply.
  It does not lock other editors, supervise agents or recover arbitrary concurrent edits.
- Take over an earlier manager only through exact receipts. An instruction entry that is
  an in-account link to one regular Markdown file is edited through that file and keeps
  its link, as the earlier manager's own handling did. `--legacy-receipt` may repeat and
  retires only fragments that match exactly once; another owner's planning route is refused
  with its file and event. This is not a universal legacy uninstaller, and leftover files
  of the old manager are never deleted.
- Codex/Claude get shared skills, account pointers and selected planning hooks.
  Hermes opt-in requires an executable and supplies skills/SOUL guidance only.
  No automatic Hermes plugin enablement or unverified lifecycle adapter is introduced.
- Native Windows/custom client profiles are outside this initial adapter. macOS
  and Linux/WSL are the supported POSIX target; record which OS was actually tested.
  Runtime/credential/model installation stays with existing host managers.

Client contracts checked against [Codex skills](https://learn.chatgpt.com/docs/build-skills),
[Codex instructions](https://learn.chatgpt.com/docs/agent-configuration/agents-md),
[Codex hooks](https://learn.chatgpt.com/docs/hooks),
[Claude skills](https://code.claude.com/docs/en/skills),
[Claude memory/imports](https://code.claude.com/docs/en/memory), and
[Hermes skills](https://hermes-agent.nousresearch.com/docs/user-guide/features/skills).
Native discovery, trust, invocation and MCP authentication remain separate from
configuration delivery. The [account guide](../../account/README.md) owns commands
and boundaries; the [verification record](../client-verification.md) owns evidence.
