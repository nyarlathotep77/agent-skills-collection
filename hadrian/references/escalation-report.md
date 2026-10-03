# Reports

Both reports go to the user and are appended to `.hadrian/state.md`.

## Completion report (all clauses PASS, Review Gate clean)

```
HADRIAN — GOAL COMPLETE
Objective: <...>
Cycles used: N / budget M
Branch: <dedicated work branch where the changes live — never main/master>
Capability probe: verifier=<independent|in-process> loop-engine=<auto-continue|self-prompted> freeze=<hard|prompt-enforced>; degraded modes active: <none | list>
DoD: all clauses PASS (evidence in state.md cycles 1..N)
Gates: <name → result; waivers listed if any>
Review: independent|in-process, clean
Acceptance: pending — review the diff. On explicit user approval only, I will create .hadrian/signoff (unblocks git push); no self-assigned success.
PR/MR: <URL of the pull/merge request opened after signoff | exempt — no code changes>
Proposed KB amendments: <none | list>
```

## Escalation report (stop without completion)

```
HADRIAN — ESCALATION
Objective: <...>
Stopped at cycle N / budget M. Reason: <budget exhausted | same failure 2x consecutive | blocker | stopped by user>
Capability probe: verifier=<independent|in-process> loop-engine=<auto-continue|self-prompted> freeze=<hard|prompt-enforced>; degraded modes active: <none | list>
DoD status: <clause → PASS|FAIL|NOT-ATTEMPTED, one line each with evidence ref>
Blocked on: <what exactly is missing — env, decision, access>
Tried: <each cycle's action in one line>
Proposed amendments (contract/KB): <list or none>
Recommended next step for the human: <concrete>
```

Rules: no self-assigned success. `.hadrian/signoff` is created only after explicit user approval; no `git push` without it. Coding-task goals end in an opened PR/MR: when the goal's work modified code in a git repository, after explicit user approval and signoff creation the loop commits on the feature branch, pushes it, opens a pull request (GitHub via `gh`) or merge request (GitLab), and records its URL in the completion report; goals without code changes are exempt. An escalation is a valid L3 outcome — bounded autonomy means handing off, not grinding.
