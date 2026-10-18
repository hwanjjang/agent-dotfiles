# Bind selected observations and record feedback

Scenario ID: `task-feedback`. Surface: the observation CLI with a disposable home
and synthetic project. Python 3.11+ and a local POSIX filesystem are required.
The [observation guide](../../../../account/observation/README.md#bind-selected-observations-to-a-task)
owns command fields, privacy, limits and purge behavior. Do not activate native
collection or select a real account for this scenario.

1. Create a temporary home/project and grant synthetic collection. Capture or import
   three events across two sessions, retaining their returned local event IDs.
2. Run `task-bind` with one inclusive receipt range and one exact event-ID selection.
   Save its task/revision IDs. Repeat exactly the same request: expect `duplicate`.
   Change that request under the same request ID: expect `request_conflict`.
3. Run `feedback-add --task ID` with a symptom, explicit correction and only selected
   evidence IDs. Expect `reported_correction`, which is a report, not a diagnosis.
   A symptom without correction must remain `insufficient_claim_evidence`.
4. Run `task-show --task ID`. Verify exactly the two selected events are frozen,
   including their separate sessions, and later events do not expand the revision.
   Attempt feedback referencing the unselected third event: expect rejection.
5. Revoke a participating registration. `task-show` must return `disabled`; the
   private task directory and its feedback must be removed. Confirm no installer
   state appeared, then clean up the disposable home.

Run maintained checks from the repository root:

```sh
python3.11 -m unittest discover -s tests -p 'test_observation_feedback*.py' -v
python3.11 -m unittest discover -s tests -p 'test_observation*.py' -v
```

The focused CLI test and Store tests cover the ordered journey and additional
expiry, stale-grant, symlink, retry/conflict and composite-task purge cases. Preserve
actual command outcomes and source hashes outside public source. Selected synthetic
results may be shown in a browser-rendered summary labeled as such; never portray
that summary as a terminal capture or automatic privacy review. The
[walkthrough](../../../manual/task-feedback.pdf) uses this scenario ID.

In both generated maps, open Private observations. Usage must name task-bind,
feedback-add and task-show; sources must reach the maintained guide. The reproduction
node must distinguish implemented task feedback from planned case export. Opt-in Claude/Codex collection exists with the
native guide’s source-bound trust/platform limits; comparative model execution
remains planned.

Correction checks: the focused recovery suite covers corrupt/oversized/missing-lineage/
symlink task cleanup without following external targets, keeping unrelated active
tasks and discarding the index. It also checks resolved 128 KiB row refusal,
128-event acceptance/129-event refusal, malformed revision IDs, overlapping explicit
selections and revocation of a registration added by a later revision. Expiry blocks
reads immediately; run `prune` to verify physical deletion. An event in both feedback
evidence lists remains an explicit mixed observation, not an automatic diagnosis.
