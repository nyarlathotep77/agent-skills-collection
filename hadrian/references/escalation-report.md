# Reports

Both reports go to the user and are appended to `.hadrian/state.md`.

## Completion report (all clauses PASS, Review Gate clean)

```
HADRIAN — GOAL COMPLETE
Objective: <...>
Cycles used: N / budget M
Branch: <dedicated work branch where the changes live — never main/master>
Worktree: <absolute path of the goal's dedicated worktree | degraded — single-checkout branch discipline>; state on stop: <left intact with unmerged work (removal only after merge or explicit user direction) | merged & removed per user direction>
Capability probe: verifier=<independent|in-process> loop-engine=<auto-continue|self-prompted> freeze=<hard|prompt-enforced> rubric=<independent|in-process>; degraded modes active: <none | list>
DoD: all clauses PASS (evidence in state.md cycles 1..N)
Gates: <name → result; waivers listed if any>
Evidence artifacts: <every .hadrian/evidence/<cycle>-<gate>.md path produced for this goal — audit them or attach to the PR/MR>
Review: independent|in-process, clean
Rubric: <independent|in-process> — mean <x.x> vs threshold <t>; no clause below its anchor; per-criterion scorecard (criterion → score + one line of evidence) in state.md cycles 1..N
Acceptance: pending — review the diff. On explicit user approval only, I will create .hadrian/signoff (unblocks git push); no self-assigned success.
PR/MR: <URL of the pull/merge request opened after signoff | exempt — no code changes>
Ticket sync: <none — no ticket tied | pm_account=<...>; sub-tasks created/reused (<refs>); transitions with triggering activity; story final status=<done-role>; open children=<none | refs + subjects>>
Proposed KB amendments: <none | list>
```

## Escalation report (stop without completion)

```
HADRIAN — ESCALATION
Objective: <...>
Stopped at cycle N / budget M. Reason: <budget exhausted | same failure 2x consecutive | blocker | stopped by user>
Worktree: <absolute path of the goal's dedicated worktree | degraded — single-checkout branch discipline> — left intact with unmerged work; removal only after merge or explicit user direction, never silent
Capability probe: verifier=<independent|in-process> loop-engine=<auto-continue|self-prompted> freeze=<hard|prompt-enforced> rubric=<independent|in-process>; degraded modes active: <none | list>
DoD status: <clause → PASS|FAIL|NOT-ATTEMPTED, one line each with evidence ref>
Rubric: <last per-criterion scores, criterion → score; sub-anchor clauses named | not yet run>
Evidence artifacts: <every .hadrian/evidence/<cycle>-<gate>.md path produced for this goal — audit them or attach to the PR/MR>
Blocked on: <what exactly is missing — env, decision, access>
Tried: <each cycle's action in one line>
Ticket sync: <none — no ticket tied | pm_account=<...>; sub-tasks created/reused (<refs>); transitions so far with triggering activity; story current status=<...>; open children=<refs + subjects>>
Proposed amendments (contract/KB): <list or none>
Recommended next step for the human: <concrete>
```

Rules: no self-assigned success. Ticket-tied goals additionally require gate T2 PASS for completion (fail-closed re-read: every child task closed, story in done-role status — references/taiga-sync.md); an open child blocks completion exactly like a failed gate. Malformed verdict records are listed in every report and count as NOT-RUN for their id — they block completion exactly like missing evidence (references/verdict-contract.md). `.hadrian/signoff` is created only after explicit user approval; no `git push` without it. Both reports list every `.hadrian/evidence/` artifact path produced for the goal so a human can audit them or attach them to the PR/MR (references/evidence-artifacts.md). Coding-task goals end in an opened PR/MR: when the goal's work modified code in a git repository, after explicit user approval and signoff creation the loop commits on the feature branch, pushes it, opens a pull request (GitHub via `gh`) or merge request (GitLab), and records its URL in the completion report; goals without code changes are exempt. Soon after completing the goal, all active goal artifacts (`contract.md`, `state.md`, `evidence/`, `signoff`) are archived to `.hadrian/archive/<UTC timestamp>/` (leaving `archive/` and `worktrees/` intact) so that the next new goal will find no leftover artifacts from previous goals. An escalation is a valid L3 outcome — bounded autonomy means handing off, not grinding.
