# Goal State — <objective>

Started: <UTC timestamp>
Budget: <used>/<total> cycles (update after every cycle; budget exhausted = stop + escalation report)
Capability probe: verifier=<independent|in-process> loop-engine=<auto-continue|self-prompted> freeze=<hard|prompt-enforced> rubric=<independent|in-process>
Work branch: <dedicated branch created before the first change — never main/master>
PM account: <acting PM-tool identity from whoami — ticket-tied goals only; n/a otherwise>

## Cycles

Each cycle entry contains exactly these fields: n | action | gates (one VERDICT record per gate row) | review verdicts (one VERDICT record per DoD clause + the weakening check CW) | next step, plus a rubric section of one VERDICT record per criterion when the Rubric Gate ran. Every gate/review/rubric result is a machine-verifiable verdict record per references/verdict-contract.md — prose-only verdicts are invalid by definition. This file is the single source of truth for resuming an active goal across sessions — resume relies only on contract + state, never on session memory.

### Cycle 1
- Action: <what changed, files touched>
- Gates: (one record per row of the contract's Quality Gates table)
    VERDICT kind=gate id=G1 status=<PASS|FAIL|NOT-RUN|WAIVED> evidence="<one line of captured output>" source=<spec|kb:<file>|inferred|derived>
- Review: (one record per DoD clause + CW for the gate-weakening check)
    VERDICT kind=review id=C1 status=<PASS|FAIL|NOT-RUN> evidence="<cited evidence, or the single weakening hit that failed the cycle>" source=<independent|in-process>
    VERDICT kind=review id=CW status=<PASS|FAIL> evidence="<no hits | the single hit that failed the cycle>" source=<independent|in-process>
- Rubric (only when the Rubric Gate ran; one record per criterion row):
    VERDICT kind=rubric id=R1 status=<PASS|FAIL> score=<0..4> evidence="<one line of captured output>" source=<spec|kb:<file>|inferred|derived>
- Next: <next smallest step>

<!-- Malformed verdict records (any line starting with VERDICT that fails references/verdict-contract.md) are treated as NOT-RUN on resume/status/stop and block completion — never guessed or coerced into a pass. -->
<!-- Waivers (human-only, gates only): append exactly this block when a human waives a NOT-RUN gate; it is what makes a status=WAIVED record for that gate valid -->
<!-- WAIVER: gate=<name> by=<user> at=<UTC timestamp> reason=<...> -->
