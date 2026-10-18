# Account diagnosis and model verification

Scenario ID: `account-verification`. Surfaces: account CLI, native clients and
optional local Paseo. [The account guide](../../../../account/README.md#diagnose-and-exercise-the-installation)
owns the command/consent/cost contract; this recipe owns the maintained checks.

1. Use Python 3.11+ to run `python3.11 -m unittest discover -s tests -p
   'test_account_doctor.py'`. Disposable accounts cover healthy/drifted/masked or
   competing configuration; protocol fixtures distinguish source-path overrides,
   modified trust and unavailable APIs. Grader fixtures reject plausible replies
   without source reads, incorrect CLI outcomes and invented test execution.
2. Against a selected installed account, run `setup-account.sh doctor --json`.
   Inspect per-check outcomes; offline success never establishes native/model use.
3. With target-client execution authorized, run `doctor --native --client codex`,
   then `--client claude`. Compare discovered sources to the owned bundle. Codex
   hook trust requires `/hooks` review; never force a green result with trust bypass.
4. Select a genuinely available inexpensive model and a new ignored evidence
   directory. Run the guide's `--model-smoke` command for Codex first. Inspect
   source hashes, successful source-read tool output, actual answer, deterministic
   grade and unchanged inputs. Quota/unsupported-model/tool failures remain blocked.
5. With Paseo selected, add `--with-paseo`. Confirm local daemon topology, actual
   provider/model, exact installed-source readback, unchanged inputs and successful
   archival of this run's agent/workspace. Summary logs alone are insufficient.
   Preserve uncertain creation results and owned IDs; do not blindly create again.
6. Use `--scenario routing` separately with each native client. The task must not
   name the desired skills. Verify actual spec/planning source reads or native
   Skill invocation plus exact injected body, correct CLI examples, acceptance
   coverage, ordered dependencies and concrete verification. Structured output
   controls transport shape; it does not replace behavioral grading.
7. Check model identity and per-client activation summaries. Codex's first model
   turn must recover the synthetic plan through its owned SessionStart hook;
   registration/trust alone must not set the activation summary to true.
8. Preserve the report's `account_qualification` evidence kind and `not_run`
   comparison status, including after a successful model run. For improvement
   claims, follow the [comparison contract](../../../decisions/account-improvement-loop.md#account-qualification-and-reuse).
   Run the observation store/CLI tests and installer coexistence test when changing
   these boundaries: doctor and install/update/rollback/uninstall must preserve
   existing observation records and grants without activating collection.

For installation on another OS, run the existing installer tests plus the public
CLI lifecycle against a committed source in disposable accounts: install all
selected skills, update to a different revision, confirm an unchanged update,
then uninstall while preserving synthetic personal settings and host-owned skills.
Record OS/runtime and distinguish container execution from native client behavior.
For opt-in MCP checks, follow [the template validation layers](../../../../mcp/README.md):
use a temporary client configuration, confirm connected discovery, perform a
bounded tool operation on synthetic content, and close the owned browser/session.

Retain source revision, client/model selection, real process outcomes and sanitized
findings. Native state/caches may change, so offline read-only checks and native
process effects are separate. No MCP authentication, Hermes execution, remote Paseo,
all-skill behavioral certification or full SDLC follows from this bounded recipe.
