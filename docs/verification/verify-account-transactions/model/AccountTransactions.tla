------------------------- MODULE AccountTransactions -------------------------
(***************************************************************************)
(* The account installer's transaction journal, automatic undo and         *)
(* `rollback` in scripts/account_storage.py, for one transaction over a    *)
(* skill directory replaced by a link, a settings file and the receipt, in *)
(* the order setup_account.prepare emits them.                             *)
(*                                                                         *)
(* One step here is one atomic file-system effect in the code; each       *)
(* action names it with an @code reference that run.py checks against the  *)
(* source. Reads under the installer lock (previews, rechecks, post-write  *)
(* checks, backup checks) are folded into the step that acts on them: no   *)
(* other writer runs while the lock is held (docs/decisions/               *)
(* account-installation.md: close clients during apply).                    *)
(*                                                                         *)
(* Kill: the process dies between two steps and the kernel drops the lock.  *)
(* IOError: a write step raises instead of taking effect.                  *)
(* UserChange: between commands, the user edits or deletes one path.       *)
(***************************************************************************)
EXTENDS Naturals, FiniteSets, Sequences

CONSTANTS MaxKills, MaxIOErrors, MaxUserChanges, Variant

Order  == <<"skill", "settings", "receipt">>
\* The journal is stored with sorted keys and rollback walks it in reverse, so its order is by path:
\* .agents/agent-dotfiles/state/installed.json < .agents/skills/tdd < .claude/settings.json.
\* @code scripts/account_storage.py:44 return (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()
\* @code scripts/account_storage.py:459 for name, entry in reversed(list(journal['originals'].items())):
JournalOrder == <<"receipt", "skill", "settings">>
Paths  == {"skill", "settings", "receipt"}
Before == [p \in Paths |-> CASE p = "skill" -> "dir" [] p = "settings" -> "orig" [] OTHER -> "absent"]
After  == [p \in Paths |-> CASE p = "skill" -> "link" [] p = "settings" -> "new" [] OTHER -> "new"]
Values == {"dir", "link", "orig", "new", "absent", "edit"}
\* @code scripts/account_storage.py:427 and journal.get('status') in ('applied', 'pending', 'recovery-required', 'rolling-back'), 'Transaction cannot be rolled back')
Accepts == {"applied", "pending", "recovery-required", "rolling-back"}
Statuses == {"none", "rolled-back"} \cup Accepts
Pcs == {"idle", "i_journal", "i_put", "i_link", "i_repair", "i_applied",
        "u_path", "u_rename", "u_outcome",
        "r_plan", "r_mark", "r_path", "r_rename", "r_done"}

VARIABLES disk, displaced, journal, pc, idx, done, failures, installed,
          kills, ioerrs, userChanges, userChanged, planStatus, wrote,
          clobbered, spurious, dirtyRefusal, refusedEdit, rollbackDone

vars == <<disk, displaced, journal, pc, idx, done, failures, installed,
          kills, ioerrs, userChanges, userChanged, planStatus, wrote,
          clobbered, spurious, dirtyRefusal, refusedEdit, rollbackDone>>

LaterEdit(t) == t \in userChanged /\ disk[t] \notin {Before[t], After[t]}
AnyLaterEdit == \E t \in Paths : LaterEdit(t)
AllBefore == \A t \in Paths : disk[t] = Before[t]

\* The documented exception (account/README.md): while the journal was not `applied` when the
\* rollback started, a missing skill directory is the journaled move gap and the original returns.
GapException(t) == t = "skill" /\ disk[t] = "absent" /\ planStatus # "applied"
Overwrites(t) == LaterEdit(t) /\ ~GapException(t)

Fault == ioerrs < MaxIOErrors /\ ioerrs' = ioerrs + 1
Ghosts == <<clobbered, spurious, dirtyRefusal, refusedEdit, rollbackDone>>
Budgets == <<kills, userChanges, userChanged, installed>>

Init ==
    /\ disk = Before /\ displaced = "empty" /\ journal = "none" /\ pc = "idle"
    /\ idx = 0 /\ done = {} /\ failures = {} /\ installed = FALSE
    /\ kills = 0 /\ ioerrs = 0 /\ userChanges = 0 /\ userChanged = {}
    /\ planStatus = "none" /\ wrote = FALSE
    /\ clobbered = FALSE /\ spurious = FALSE /\ dirtyRefusal = FALSE
    /\ refusedEdit = FALSE /\ rollbackDone = FALSE

-----------------------------------------------------------------------------
(* transact: capture originals, journal `pending`, put each change.        *)

StartInstall ==
    /\ pc = "idle" /\ ~installed
    /\ installed' = TRUE /\ pc' = "i_journal"
    /\ UNCHANGED <<disk, displaced, journal, idx, done, failures, kills, ioerrs,
                   userChanges, userChanged, planStatus, wrote>> /\ UNCHANGED Ghosts

\* @code scripts/account_storage.py:387 write(folder / 'journal.json', encoded(journal))
WriteJournalPending ==
    /\ pc = "i_journal"
    /\ \/ /\ journal' = IF Variant = "no-pending-journal" THEN journal ELSE "pending"
          /\ pc' = "i_put" /\ idx' = 1 /\ UNCHANGED ioerrs
       \/ Fault /\ pc' = "idle" /\ UNCHANGED <<journal, idx>>  \* raised before the try at :389
    /\ UNCHANGED <<disk, displaced, done, failures, planStatus, wrote>> /\ UNCHANGED Budgets /\ UNCHANGED Ghosts

\* @code scripts/account_storage.py:393 done.append(name)
\* @code scripts/account_storage.py:232 os.replace(leaf, displaced.name, src_dir_fd=parent, dst_dir_fd=shelf)
\* @code scripts/account_storage.py:268 os.replace(tmp, leaf, src_dir_fd=parent, dst_dir_fd=parent)
PutStep ==
    /\ pc = "i_put" /\ idx \in 1..3
    /\ LET t == Order[idx] IN
       /\ done' = done \cup {idx}
       /\ \/ /\ t = "skill"   \* the directory moves to its journaled displacement first
             /\ disk' = [disk EXCEPT ![t] = "absent"] /\ displaced' = "dir"
             /\ pc' = "i_link" /\ UNCHANGED <<idx, ioerrs>>
          \/ /\ t # "skill"
             /\ disk' = [disk EXCEPT ![t] = After[t]] /\ UNCHANGED displaced
             /\ idx' = (IF idx = 3 THEN 0 ELSE idx + 1) /\ pc' = IF idx = 3 THEN "i_applied" ELSE "i_put"
             /\ UNCHANGED ioerrs
          \/ Fault /\ pc' = "u_path" /\ idx' = 3 /\ UNCHANGED <<disk, displaced>>
    /\ UNCHANGED <<journal, failures, planStatus, wrote>> /\ UNCHANGED Budgets /\ UNCHANGED Ghosts

\* @code scripts/account_storage.py:237 _put_file_below(parent, leaf, value)
PutLink ==
    /\ pc = "i_link"
    /\ \/ /\ disk' = [disk EXCEPT !["skill"] = "link"] /\ idx' = 2 /\ pc' = "i_put" /\ UNCHANGED ioerrs
       \/ Fault /\ pc' = "i_repair" /\ UNCHANGED <<disk, idx>>
    /\ UNCHANGED <<displaced, journal, done, failures, planStatus, wrote>> /\ UNCHANGED Budgets /\ UNCHANGED Ghosts

\* @code scripts/account_storage.py:242 os.replace(displaced.name, leaf, src_dir_fd=shelf, dst_dir_fd=parent)
PutRepair ==
    /\ pc = "i_repair"
    /\ \/ /\ disk' = [disk EXCEPT !["skill"] = "dir"] /\ displaced' = "empty" /\ UNCHANGED ioerrs
       \/ Fault /\ UNCHANGED <<disk, displaced>>
    /\ pc' = "u_path" /\ idx' = 3
    /\ UNCHANGED <<journal, done, failures, planStatus, wrote>> /\ UNCHANGED Budgets /\ UNCHANGED Ghosts

\* @code scripts/account_storage.py:403 write(folder / 'journal.json', encoded(journal))
WriteJournalApplied ==
    /\ pc = "i_applied"
    /\ \/ /\ journal' = "applied" /\ pc' = "idle" /\ UNCHANGED <<idx, ioerrs>>
       \/ Fault /\ pc' = "u_path" /\ idx' = 3 /\ UNCHANGED journal
    /\ UNCHANGED <<disk, displaced, done, failures, planStatus, wrote>> /\ UNCHANGED Budgets /\ UNCHANGED Ghosts

-----------------------------------------------------------------------------
(* transact's except block: undo `done` in reverse, then journal the outcome. *)

\* @code scripts/account_storage.py:409 if actual == plan['before'][name]:
\* @code scripts/account_storage.py:411 require(actual == plan['after'][name], 'Concurrent change during recovery')
\* @code scripts/account_storage.py:349 require(observed(displaced) == expected, 'Displaced original changed or missing')
\* @code scripts/account_storage.py:350 put(path, None, home=home)
\* @code scripts/account_storage.py:365 put(path, {'data': saved.read_bytes(), 'mode': entry['mode']}, home=home)
\* @code scripts/account_storage.py:367 put(path, {'link': entry['value']} if entry['kind'] == 'link' else None, home=home)
UndoPath ==
    /\ pc = "u_path" /\ idx \in 1..3
    /\ LET t == Order[idx] IN
       IF idx \notin done \/ disk[t] = Before[t]
       THEN /\ idx' = idx - 1 /\ UNCHANGED <<disk, displaced, failures, ioerrs, pc>>
       ELSE IF disk[t] # After[t] \/ (t = "skill" /\ displaced # "dir")
       THEN /\ failures' = failures \cup {t} /\ idx' = idx - 1
            /\ UNCHANGED <<disk, displaced, ioerrs, pc>>
       ELSE \/ /\ t = "skill" /\ disk' = [disk EXCEPT ![t] = "absent"]
               /\ pc' = "u_rename" /\ UNCHANGED <<idx, displaced, failures, ioerrs>>
            \/ /\ t # "skill" /\ disk' = [disk EXCEPT ![t] = Before[t]]
               /\ idx' = idx - 1 /\ UNCHANGED <<displaced, failures, ioerrs, pc>>
            \/ Fault /\ failures' = failures \cup {t} /\ idx' = idx - 1
               /\ UNCHANGED <<disk, displaced, pc>>
    /\ UNCHANGED <<journal, done, planStatus, wrote>> /\ UNCHANGED Budgets /\ UNCHANGED Ghosts

\* @code scripts/account_storage.py:359 os.replace(displaced.name, path.name, src_dir_fd=shelf, dst_dir_fd=parent)
UndoRename ==
    /\ pc = "u_rename"
    /\ \/ /\ disk' = [disk EXCEPT !["skill"] = "dir"] /\ displaced' = "empty"
          /\ UNCHANGED <<failures, ioerrs>>
       \/ Fault /\ failures' = failures \cup {"skill"} /\ UNCHANGED <<disk, displaced>>
    /\ idx' = idx - 1 /\ pc' = "u_path"
    /\ UNCHANGED <<journal, done, planStatus, wrote>> /\ UNCHANGED Budgets /\ UNCHANGED Ghosts

UndoDone ==
    /\ pc = "u_path" /\ idx = 0 /\ pc' = "u_outcome"
    /\ UNCHANGED <<disk, displaced, journal, idx, done, failures, ioerrs, planStatus, wrote>>
    /\ UNCHANGED Budgets /\ UNCHANGED Ghosts

\* @code scripts/account_storage.py:416 journal['status'] = 'recovery-required' if failures else 'rolled-back'
\* @code scripts/account_storage.py:417 write(folder / 'journal.json', encoded(journal))
WriteJournalOutcome ==
    /\ pc = "u_outcome"
    /\ \/ /\ journal' = IF failures = {} THEN "rolled-back" ELSE "recovery-required"
          /\ UNCHANGED ioerrs
       \/ Fault /\ UNCHANGED journal
    /\ pc' = "idle" /\ done' = {} /\ failures' = {}
    /\ UNCHANGED <<disk, displaced, idx, planStatus, wrote>> /\ UNCHANGED Budgets /\ UNCHANGED Ghosts

-----------------------------------------------------------------------------
(* rollback, run by `setup-account.sh rollback --apply` under the lock.      *)

StartRollback ==
    /\ pc = "idle" /\ journal # "none"
    /\ pc' = "r_plan" /\ wrote' = FALSE
    /\ UNCHANGED <<disk, displaced, journal, idx, done, failures, ioerrs, planStatus>>
    /\ UNCHANGED Budgets /\ UNCHANGED Ghosts

\* A refusal raises ValueError; the CLI reports it and the process ends.
Refuse ==
    /\ pc' = "idle"
    /\ spurious' = (spurious \/ (~AnyLaterEdit /\ ~AllBefore))
    /\ dirtyRefusal' = (dirtyRefusal \/ wrote)
    /\ refusedEdit' = (refusedEdit \/ AnyLaterEdit)
    /\ UNCHANGED <<clobbered, rollbackDone>>

States(t) == {Before[t], After[t]} \cup
    (IF t = "skill" /\ displaced = "dir" /\ (journal # "applied" \/ Variant = "gap-after-applied")
     THEN {"absent"} ELSE {})

\* @code scripts/account_storage.py:440 require(displaced == journal['before'][name], 'Displaced original changed')
\* @code scripts/account_storage.py:441 if journal['status'] != 'applied':
\* @code scripts/account_storage.py:444 require(displaced == journal['before'][name], 'Displaced original missing')
\* @code scripts/account_storage.py:445 require(actual in states, f'Rollback would overwrite later changes: {name}')
PlanOK ==
    /\ journal \in Accepts
    /\ disk["skill"] # Before["skill"] => displaced = "dir"
    /\ \/ Variant \in {"no-later-edit-precheck", "no-later-edit-checks"}
       \/ \A t \in Paths : disk[t] \in States(t)

RollbackPlan ==
    /\ pc = "r_plan"
    /\ IF PlanOK
       THEN /\ planStatus' = journal /\ pc' = "r_mark"
            /\ UNCHANGED <<clobbered, spurious, dirtyRefusal, refusedEdit, rollbackDone>>
       ELSE Refuse /\ UNCHANGED planStatus
    /\ UNCHANGED <<disk, displaced, journal, idx, done, failures, ioerrs, wrote>> /\ UNCHANGED Budgets

\* @code scripts/account_storage.py:457 journal['status'] = 'rolling-back'
\* @code scripts/account_storage.py:458 write(folder / 'journal.json', encoded(journal))
WriteJournalRollingBack ==
    /\ pc = "r_mark"
    /\ \/ /\ journal' = IF Variant = "no-rolling-back-mark" THEN journal ELSE "rolling-back"
          /\ wrote' = TRUE /\ pc' = "r_path" /\ idx' = 3 /\ UNCHANGED ioerrs
       \/ Fault /\ pc' = "idle" /\ UNCHANGED <<journal, wrote, idx>>
    /\ UNCHANGED <<disk, displaced, done, failures, planStatus>> /\ UNCHANGED Budgets /\ UNCHANGED Ghosts

\* @code scripts/account_storage.py:462 if actual == journal['before'][name]:
\* @code scripts/account_storage.py:466 require(actual == journal['after'][name] or gap, f'Concurrent rollback change: {name}')
\* @code scripts/account_storage.py:467 restore(path, entry, folder / entry['saved'], journal['before'][name], home=home)
RollbackPath ==
    /\ pc = "r_path" /\ idx \in 1..3
    /\ LET t   == JournalOrder[idx]
           gap == t = "skill" /\ disk[t] = "absent" /\ displaced = "dir"
       IN
       IF disk[t] = Before[t]
       THEN /\ idx' = idx - 1
            /\ UNCHANGED <<disk, displaced, ioerrs, pc, wrote>> /\ UNCHANGED Ghosts
       ELSE IF ~(disk[t] = After[t] \/ gap \/ Variant = "no-later-edit-checks") \/ (t = "skill" /\ displaced # "dir")
       THEN Refuse /\ UNCHANGED <<disk, displaced, idx, ioerrs, wrote>>
       ELSE \/ /\ t = "skill"   \* restore unlinks the path (a no-op on the gap), then renames
               /\ disk' = [disk EXCEPT ![t] = "absent"]
               /\ clobbered' = (clobbered \/ (disk[t] # "absent" /\ Overwrites(t)))
               /\ pc' = "r_rename" /\ wrote' = TRUE
               /\ UNCHANGED <<idx, displaced, ioerrs, spurious, dirtyRefusal, refusedEdit, rollbackDone>>
            \/ /\ t # "skill" /\ disk' = [disk EXCEPT ![t] = Before[t]]
               /\ clobbered' = (clobbered \/ Overwrites(t))
               /\ idx' = idx - 1 /\ wrote' = TRUE
               /\ UNCHANGED <<displaced, ioerrs, pc, spurious, dirtyRefusal, refusedEdit, rollbackDone>>
            \/ Fault /\ pc' = "idle" /\ UNCHANGED <<disk, displaced, idx, wrote>> /\ UNCHANGED Ghosts
    /\ UNCHANGED <<journal, done, failures, planStatus>> /\ UNCHANGED Budgets

\* @code scripts/account_storage.py:359 os.replace(displaced.name, path.name, src_dir_fd=shelf, dst_dir_fd=parent)
RollbackRename ==
    /\ pc = "r_rename"
    /\ \/ /\ disk' = [disk EXCEPT !["skill"] = "dir"] /\ displaced' = "empty"
          /\ clobbered' = (clobbered \/ Overwrites("skill"))
          /\ idx' = idx - 1 /\ pc' = "r_path" /\ UNCHANGED ioerrs
          /\ UNCHANGED <<spurious, dirtyRefusal, refusedEdit, rollbackDone>>
       \/ Fault /\ pc' = "idle" /\ UNCHANGED <<disk, displaced, idx>> /\ UNCHANGED Ghosts
    /\ UNCHANGED <<journal, done, failures, planStatus, wrote>> /\ UNCHANGED Budgets

\* @code scripts/account_storage.py:469 journal['status'] = 'rolled-back'
\* @code scripts/account_storage.py:470 write(folder / 'journal.json', encoded(journal))
WriteJournalRolledBack ==
    /\ pc = "r_path" /\ idx = 0
    /\ \/ /\ journal' = "rolled-back" /\ rollbackDone' = TRUE /\ UNCHANGED ioerrs
       \/ Fault /\ UNCHANGED <<journal, rollbackDone>>
    /\ pc' = "idle"
    /\ UNCHANGED <<disk, displaced, idx, done, failures, planStatus, wrote>> /\ UNCHANGED Budgets
    /\ UNCHANGED <<clobbered, spurious, dirtyRefusal, refusedEdit>>

-----------------------------------------------------------------------------
(* Environment.                                                            *)

\* @code scripts/account_storage.py:325 fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
Kill ==
    /\ pc # "idle" /\ kills < MaxKills
    /\ kills' = kills + 1 /\ pc' = "idle" /\ done' = {} /\ failures' = {}
    /\ UNCHANGED <<disk, displaced, journal, idx, ioerrs, userChanges, userChanged,
                   installed, planStatus, wrote>> /\ UNCHANGED Ghosts

UserChange ==
    /\ pc = "idle" /\ installed /\ userChanges < MaxUserChanges
    /\ \E t \in Paths, v \in {"edit", "absent"} :
          /\ v # disk[t]
          /\ disk' = [disk EXCEPT ![t] = v]
          /\ userChanged' = userChanged \cup {t}
    /\ userChanges' = userChanges + 1
    /\ UNCHANGED <<displaced, journal, pc, idx, done, failures, installed, kills, ioerrs,
                   planStatus, wrote>> /\ UNCHANGED Ghosts

\* Idle between commands; keeps deadlock checking meaningful for steps mid-operation.
Wait == pc = "idle" /\ UNCHANGED vars

Next ==
    \/ StartInstall \/ WriteJournalPending \/ PutStep \/ PutLink \/ PutRepair
    \/ WriteJournalApplied \/ UndoPath \/ UndoRename \/ UndoDone \/ WriteJournalOutcome
    \/ StartRollback \/ RollbackPlan \/ WriteJournalRollingBack \/ RollbackPath
    \/ RollbackRename \/ WriteJournalRolledBack \/ Kill \/ UserChange \/ Wait

Spec == Init /\ [][Next]_vars

-----------------------------------------------------------------------------
(* Properties.                                                             *)

TypeOK ==
    /\ disk \in [Paths -> Values] /\ displaced \in {"empty", "dir"}
    /\ journal \in Statuses /\ pc \in Pcs /\ idx \in 0..3
    /\ done \subseteq 1..3 /\ failures \subseteq Paths

\* P1: whenever a path the user did not touch differs from its original, the journal still
\* accepts a rollback.
ChangesAreJournaled ==
    (\E t \in Paths \ userChanged : disk[t] # Before[t]) => journal \in Accepts

\* P1: a rollback refuses only when a later edit exists or nothing needs restoring.
NoSpuriousRefusal == ~spurious

\* P2: no installer step replaces content the user wrote after the transaction, except the
\* documented gap case.
NoClobber == ~clobbered

\* P2: a refused rollback has changed nothing, its journal included.
RefusalChangesNothing == ~dirtyRefusal

\* Witnesses: each must be reachable (run.py expects TLC to report it violated).
W_PendingGap        == ~(journal = "pending" /\ disk["skill"] = "absent" /\ displaced = "dir")
W_RollingBackGap    == ~(journal = "rolling-back" /\ disk["skill"] = "absent" /\ displaced = "dir")
W_RecoveryRequired  == ~(journal = "recovery-required")
W_RefusedLaterEdit  == ~refusedEdit
W_RollbackAfterKill == ~(rollbackDone /\ kills = MaxKills)
W_UndoRolledBack    == ~(journal = "rolled-back" /\ ~rollbackDone)
W_GapRestored       == ~(rollbackDone /\ "skill" \in userChanged /\ disk["skill"] = "dir")
=============================================================================
