# Qualify native observation delivery

Scenario ID: `native-observation`. Surface: observation CLI, installer and Claude
hooks. [The native guide](../../../../account/observation/native.md) owns setup,
consent, payload and coverage requirements. Use disposable configurations and
synthetic content; do not register the maintainer's real projects implicitly.

1. Run `python3.11 -m unittest discover -s tests -p 'test_observation*.py'` and
   `python3.11 -m unittest discover -s tests -p 'test_setup_account.py'`.
   Confirm opted-out/expired/revoked callbacks do not read input, exact-project
   scope, content exclusion, shared tool-ID deduplication, unknown identities and
   preserved records through installer lifecycle. Run account doctor tests too.
2. Use a committed candidate snapshot, a disposable home and a synthetic project.
   Grant `--client claude`, preview its registration, then apply to that home.
   Verify five observation routes and the unchanged separate planning routes.
   Default install must add no observation route. Keep resolved previews private.
3. Start Claude with the disposable `--settings` file and `--setting-sources ''`;
   this selects test settings while retaining the host's existing authentication.
   Use an explicitly selected available low-cost model, Read-only tool selection,
   no MCP connections, no session persistence and bounded turns/time/budget.
   Ask for one synthetic file read and one intentionally missing file read.
4. Inspect actual native model identity and hook records: session start, two tool
   starts, normal tool end, failure tool end, response end. Check planning recovery
   independently. Do not grade the answer's self-report as event evidence.
5. Verify no fixture contents, file paths, raw tool names, prompts or outputs were
   retained in records. Check the installer receipt has no drift. Direct callback
   tests cover malformed, oversized and revoked inputs with empty output/exit 0.
6. Revoke the test grant, check old-epoch delivery stays disabled, uninstall owned
   configuration, and retain only private test evidence. Repeat on another client
   or host before claiming support there. Never reuse a Claude result for Codex.

Record exact candidate, client/runtime, selected model, event counts, failures and
cleanup. Metadata does not establish task success, model effectiveness, complete
delivery, held-out evaluation or permission to activate real account collection.
