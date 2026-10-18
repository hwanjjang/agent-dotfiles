# Prepare one frozen trial

`trial_dispatch.py prepare` is a pure preparation adapter for the existing
[evaluator](evaluation-accounting.md). It selects one scheduled trial and returns
a supervisor-owned binding plus a minimal executor input. It launches no agent,
command or model; writes no ledger; and accepts no execution receipt. Actual
qualified evidence admission remains a separate prerequisite for issue #26.

## Use

Use Python 3.11 or later from a source checkout. Produce a reviewed detached case
with the [existing Store workflow](../../account/observation/README.md#prepare-and-export-a-reviewed-synthetic-case),
then freeze the complete experiment with `evaluation.py freeze`.

```sh
python3 scripts/improvement/trial_dispatch.py prepare < dispatch-input.json > dispatch.json
```

The input object contains exactly `experiment` (saved freeze output),
`current_spec` (the complete current spec), `trial_id` (one exact scheduled ID),
and `attempt_id` (a supervisor-selected identifier). Keep this whole input and
output outside executor mounts: the frozen experiment includes grading material.
This command does not decide whether that material is safe to disclose.

The adapter reuses the evaluator's canonical freeze, identity and source checks;
it refuses changed spec/budget/runtime/grader identities, tampered inventories
or an absent/ambiguous trial. CLI JSON input is bounded to the evaluator's 16 MiB limit and duplicate keys are
refused. This is a local command, not an arbitrary-input service; there is no
separate dispatch output-size cap.
The same canonical input produces the same dispatch. Pure preparation cannot
detect the same attempt ID reused across separate calls. The existing supervisor
must reserve attempts, retain every attempted outcome and enforce one shared
experiment budget; preparation does not replenish it per trial.

## Ownership and output

The output kind is `development_trial_dispatch`, schema version 1:

- `binding`: experiment digest, exact existing trial, attempt ID, selected-arm
  source digest and the experiment-wide budget digest.
- `executor_input`: only the selected variant's `request` and `files`.
- `requested_runtime`: frozen declared provider/model/client/adapter/reasoning/tools
  and capabilities. These are requested values, never observed execution facts.
- `executor_input_digest` and `dispatch_digest`: canonical content bindings.

The trusted supervisor owns the **whole envelope**. Release only `executor_input`
to the assigned executor. This command does not materialize files or establish
filesystem-safe names: the supervisor must validate paths, aliases, symlinks and
its destination boundary before writing anything. Do not hand it the current spec, frozen experiment,
checks, outcome contracts, expected answers, other-arm identity, counterpart
payload or budget. The adapter excludes these fields structurally; it cannot
detect an answer or private information already embedded in a maintainer-supplied
request/file. Reviewed development fixtures remain public development material,
not unseen holdouts.

No hash or supplied runtime declaration proves who executed a trial. Native mock
receipts cannot become live evidence through this command. A future qualified
supervisor must bind actual model/usage/terminal/artifact provenance and cleanup
to this dispatch, preserve missing/failed/duplicate attempts and keep grading
material with its separate owner. Until then the evaluator's live eligibility
and promotion limits remain unchanged. No new schedule, ledger, grader, auth
framework or hidden-material custody guarantee is introduced.

## Verification and sources

The focused tests cover projection and refusals; the manual records an actual
synthetic Store export -> freeze -> prepare CLI journey in the
[editable walkthrough](../manual/frozen-trial-dispatch.json) and
[PDF](../manual/frozen-trial-dispatch.pdf). These checks establish
preparation behavior, not actual model execution or OS isolation. The existing
[comparison contract](account-improvement-loop.md#comparative-evaluation-contract)
remains authoritative for the experiment and its downstream admission requirements.

[Anthropic's agent-evaluation guidance](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)
distinguishes trials, outcomes and calibrated graders. The
[Codex app-server lifecycle](https://learn.chatgpt.com/docs/app-server) describes
actual turn/terminal observations; requested runtime is not that observation.
Sources were checked 2026-10-18. Community feedback about this exact local adapter
is unavailable, so no popularity or effectiveness claim is made.
