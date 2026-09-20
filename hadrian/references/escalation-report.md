# Reports

Both reports go to the user and are appended to `.hadrian/state.md`.

## Completion report (all clauses PASS, Review Gate clean)

```
HADRIAN — GOAL COMPLETE
Objective: <...>
Cycles used: N / budget M
Branch: <dedicated work branch where the changes live — never main/master>
DoD: all clauses PASS (evidence in state.md cycles 1..N)
Gates: <name → result; waivers listed if any>
Review: independent|in-process, clean
Acceptance: pending — review the diff. On approval I will create .hadrian/signoff (unblocks git push).
Proposed KB amendments: <none | list>
```

## Escalation report (stop without completion)

```
HADRIAN — ESCALATION
Objective: <...>
Stopped at cycle N / budget M. Reason: <budget exhausted | same failure 2x consecutive | blocker>
DoD status: <clause → PASS|FAIL|NOT-ATTEMPTED, one line each with evidence ref>
Blocked on: <what exactly is missing — env, decision, access>
Tried: <each cycle's action in one line>
Proposed amendments (contract/KB): <list or none>
Recommended next step for the human: <concrete>
```

Rules: no self-assigned success. An escalation is a valid L3 outcome — bounded autonomy means handing off, not grinding.
