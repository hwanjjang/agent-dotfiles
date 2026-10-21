# Prepare, review and export synthetic development cases

Scenario ID: `reviewed-cases`. Surface: `scripts/improvement/cases.py`, with a
Python 3.11+ disposable home and synthetic observations. The
[Store guide](../../../../account/observation/README.md#prepare-and-export-a-reviewed-synthetic-case)
owns request fields, exact review assertions, privacy limits and output rules.
Start after the [task-feedback journey](task-feedback.md); never use a real account
or original session content for this synthetic check.

1. Create one task revision selecting a failed event and its successful counterpart.
   Add weak feedback without a correction and separate explicit correction feedback.
2. Supply the maintained English/Korean positive and adjacent-negative fixtures in
   `tests/fixtures/improvement/cases/development.json`. Prepare using the weak
   feedback: expect `insufficient` / `claim_evidence_missing`, with no case stored.
3. Declare a cause and selected event references. Environment/auth/grader must return
   `blocked` with distinct `triage_*` reasons; unknown stays insufficient. Instruction
   outcome cases require an actual failed tool; success/unknown cannot substitute.
   Prepare using the explicit correction and eligible instruction evidence. Show the exact public payload and recompute
   its digest. Verify the selected revision/feedback stays frozen. Review text,
   fixture files, contracts and counterpart for synthetic-only content.
4. Before review, export must refuse. A changed digest or missing review assertion
   must also refuse. Review the exact digest with both explicit confirmation flags,
   then export to a new absolute path in an existing ordinary directory.
5. Inspect the exported whitelist and hashes. Private task goals, symptoms,
   corrections, event IDs and lineage must be absent; preserve the counterpart and
   `classification: development`. The two maintained positive fixtures' scripts
   should exit2 for reproduction and0 for their successful counterpart. Execute
   only these inspected fixtures, not arbitrary imported case code.
6. Existing destination and parent/leaf symlinks must refuse. Revoke the task grant:
   relative/private-store destinations must also refuse with exact reasons. On revoke,
   private task/case/review records disappear and later show/review/export is blocked.
   Previously detached synthetic exports remain independent local artifacts. Clean
   up the disposable home and exports; no publication or model call is required.

```sh
python3.11 -m unittest discover -s tests -p 'test_improvement_case*.py' -v
python3.11 -m unittest discover -s tests -p 'test_observation*.py' -v
```

The focused tests exercise the CLI flow and negative/privacy/symlink/stale-grant/
changed-hash/review cases. Keep raw command evidence and source hashes ignored.
The [walkthrough](../../../manual/reviewed-cases.pdf) combines a real map capture
with a clearly labeled browser summary of actual synthetic CLI results.

Both generated maps must show reviewed export as available, link the authoritative
Store guide or design, and preserve the limitations: explicit inputs and assertions
are not automatic sanitization; public cases are development material; automatic
diagnosis remains planned, and held-out evaluation remains pending after the completed
bounded development comparison. Native Claude/Codex collection has
separate source-bound consent, trust and platform limits in the native guide.
Caller-declared triage is implemented and is not a verified diagnosis.
