# Quality Gates: Discovery & Execution

Gates are project knowledge, not Hadrian configuration. They live in the project's spec or knowledge base; Hadrian only discovers, executes, and records them.

## Discovery order (Phase 0)
Follow this order strictly; later steps only fill gaps left by earlier ones — they never override what an earlier step already established.
1. **Spec reference** — if the goal names a spec file, its Contract/DoD section wins for that goal.
2. **Project knowledge base** — whichever exist at the repo root: `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`. Take the union of their quality / definition-of-done / verification requirements. Conflicts between files → flag in state.md and ask the human; do not pick silently.
3. **Toolchain auto-detection** — when the KB is silent: read `package.json` scripts, Makefile targets, Gradle tasks, pyproject/pytest config to find obvious test/lint/build entry points. Mark these INFERRED in the contract.
4. **Derived clauses** — verifiable requirements stated in the objective text itself.

Record every gate's source in the contract table: `spec`, `kb:<file>`, `inferred`, or `derived`.

## Execution (Quality Gate, each cycle)
- Run each gate command; capture real output. PASS requires captured evidence, recorded as a `VERDICT kind=gate` record in the cycle entry (references/verdict-contract.md) — one line of captured output goes into its evidence field.
- A verification tool erroring = FAIL for that gate and the cycle (fail-closed). Never interpret or downgrade an error to "not applicable".
- A gate whose precondition is missing (no emulator, no service) = NOT-RUN. NOT-RUN blocks completion and requires a human waiver — see below. The agent never self-waives.

## Waiver format (human-only)
When the user explicitly waives a NOT-RUN gate in-session, append to `.hadrian/state.md`:

`WAIVER: gate=<name> by=<user> at=<UTC timestamp> reason=<...>`

A `WAIVER:` line is what makes a `status=WAIVED` verdict record for that gate valid; without it the record is malformed (references/verdict-contract.md).

## Gate-weakening check (Review Gate)
The Review Gate diffs the change against the KB's gate definitions and fails the cycle if any of these appear:
1. A test or assertion edited to force a pass (weakened expectation, deleted case, skipped test)
2. A quality-gate threshold lowered or a required check removed
3. Any edit to quality/DoD sections of `AGENTS.md`, `CLAUDE.md`, or `GEMINI.md`
4. An edit to `.hadrian/contract.md`

Amendments to gates are proposed in the escalation/completion report; a human applies them as a normal commit.

## Declaring gates in your project KB (guidance)
Write each gate as: requirement + explicit command where possible + environment preconditions. Stack-neutral example:

```
Quality gates:
- lint: `make lint` must pass
- tests: `make test` must pass, line coverage >= 80% (`make coverage`)
- ui-checks: requires a running dev server; `scripts/ui-smoke.sh`
```

Prose is fine — the agent resolves commands from your build files. Be explicit about preconditions so NOT-RUN is detected instead of guessed.
