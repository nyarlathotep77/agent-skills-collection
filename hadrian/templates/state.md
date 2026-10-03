# Goal State — <objective>

Started: <UTC timestamp>
Budget: <used>/<total> cycles (update after every cycle; budget exhausted = stop + escalation report)
Capability probe: verifier=<independent|in-process> loop-engine=<auto-continue|self-prompted> freeze=<hard|prompt-enforced> rubric=<independent|in-process>
Work branch: <dedicated branch created before the first change — never main/master>
PM account: <acting PM-tool identity from whoami — ticket-tied goals only; n/a otherwise>

## Cycles

Each cycle entry contains exactly these fields: n | action | gates (name: result + one line of evidence) | review verdict | next step, plus an optional rubric scores extension when the Rubric Gate ran (criterion → score + one line of evidence each; clause score = minimum of its criteria). This file is the single source of truth for resuming an active goal across sessions — resume relies only on contract + state, never on session memory.

### Cycle 1
- Action: <what changed, files touched>
- Gates:
  - <gate>: PASS — <one line of captured evidence>
  - <gate>: FAIL — <error excerpt>
  - <gate>: NOT-RUN — <reason, e.g. no emulator>
- Tool error = FAIL for that gate and the cycle (fail-closed); a NOT-RUN gate blocks completion until a human waiver below; the agent never self-waives.
- Review: <PASS|FAIL> — per-clause verdicts with cited evidence (independent or degraded mode), or the single weakening hit that failed the cycle
- Rubric (optional, when the Rubric Gate ran): <criterion → score> — per-criterion scores on the anchored scale with one line of evidence each; clause score = minimum of its criteria
- Next: <next smallest step>

<!-- Waivers (human-only): append exactly this block when a human waives a NOT-RUN gate -->
<!-- WAIVER: gate=<name> by=<user> at=<UTC timestamp> reason=<...> -->
