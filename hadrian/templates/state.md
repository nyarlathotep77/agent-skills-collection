# Goal State — <objective>

Started: <UTC timestamp>
Capability probe: verifier=<independent|in-process> loop-engine=<harness|self-prompted> freeze=<hard|prompt>

## Cycles

### Cycle 1
- Action: <what changed, files touched>
- Gates:
  - <gate>: PASS — <one line of captured evidence>
  - <gate>: FAIL — <error excerpt>
  - <gate>: NOT-RUN — <reason, e.g. no emulator>
- Review: <PASS|FAIL> — <verdict + cited evidence or weakening found>
- Next: <next smallest step>

<!-- Waivers (human-only): append exactly this block when a human waives a NOT-RUN gate -->
<!-- WAIVER: gate=<name> by=<user> at=<UTC timestamp> reason=<...> -->
