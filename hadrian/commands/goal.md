---
description: Drive a bounded objective to verified completion with the Hadrian L3 goal loop — contract intake, quality gates, cycle budget, human acceptance. Usage: /goal <objective> [(max N cycles)]
---

# Hadrian L3 Goal Execution

Objective / Command: $ARGUMENTS

## Invocation rules (apply before anything else)

1. **Start immediately.** On a new objective, begin Phase 0 (contract intake) at once — no confirmation prompt, no planning questions. The user can interrupt at any time; any user message preempts the loop and is handled first.
2. **Resolve the cycle budget from $ARGUMENTS:**
   - If it contains `(max N cycles)` with a positive integer N → budget = N.
   - Otherwise (clause absent, or N missing / non-integer / ≤ 0) → budget = 10 (default).
   - Record the resolved value in the contract header as `Budget: <N> cycles`.
3. **Spec reference.** If $ARGUMENTS names a spec file that exists in the repo, read it; its Contract / Definition of Done section becomes the baseline for DoD clauses and quality gates (gate source: `spec`).

## Subcommand dispatch (check first word of arguments)

- **`status`**: Summarize `.hadrian/state.md` and exit.
- **`resume`**: Read `.hadrian/contract.md` and `.hadrian/state.md`, then continue the cycle loop from the last state entry.
- **`stop`**: Halt execution, record the reason in `.hadrian/state.md`, and report what remains.

---

## Autonomous goal protocol (new objectives)

### 1. Phase 0 — Contract intake

1. If `.hadrian/contract.md` already exists for a different goal: move existing `.hadrian/*` to `.hadrian/archive/<timestamp>/` and remove any stale `.hadrian/signoff`.
2. Discover Quality Gates in this fixed order — later steps only fill gaps left by earlier ones (record each gate's source as `spec`, `kb:<file>`, `inferred`, or `derived`):
   - Spec reference → its Contract/DoD section (source `spec`) — the baseline when present.
   - Repository KB (`AGENTS.md`, `CLAUDE.md`, `GEMINI.md`) — union of their quality/DoD/verification requirements; conflicts between KB files are flagged in `.hadrian/state.md` and asked to the human, never resolved silently (source `kb:<file>`).
   - Project toolchain tasks (e.g., `./gradlew test`, `npm test`, `cargo test`, `pytest`) — only where the KB is silent; mark INFERRED (source `inferred`).
   - Verifiable clauses derived from the objective (source `derived`).
3. Create `.hadrian/contract.md` immediately:
   - Header: Started timestamp, Budget (<resolved N> cycles), Spec/KB references.
   - Numbered Definition of Done (DoD) clauses.
    - Quality Gates table (`| # | Gate | Source | Command | Status |`), every row's Source one of `spec`, `kb:<file>`, `inferred`, `derived`.
   - Constraints and Verification Commands.
4. Initialize `.hadrian/state.md` with:
     `Capability probe: verifier=<independent|in-process> loop-engine=<auto-continue|self-prompted> freeze=<hard|prompt-enforced>`
5. Show the written contract to the user BEFORE Phase 1 begins — presentation precedes any work; do not wait for confirmation before starting Phase 1.

### 2. Phase 1 & 2 — Cycle loop (bias for direct action)

**Budget check first:** before starting each cycle, count completed cycles in `.hadrian/state.md`. If the budget is exhausted → stop immediately and write an escalation report with reason `budget exhausted` (format: references/escalation-report.md). Never silently continue past the budget; only a human amendment recorded in state extends it.

**Branch discipline:** before applying any change, record the current git branch in `.hadrian/state.md`. Never apply changes directly to the repository's default (main/master) branch — first create and check out a dedicated work branch for the goal (e.g., `hadrian/<goal-slug>`), then apply all changes on it.

Execute tightly focused cycles until all DoD clauses PASS or a stop condition hits:

1. **Focus**: pick the smallest concrete code change that advances a DoD clause.
2. **Implement**: edit or create files directly with tools.
3. **Execute gates**: run every gate command in the contract via bash (e.g., `./gradlew test`, syntax checks) and capture real terminal output. PASS is only granted with captured output evidence — one line of it goes into state.md. A verification tool erroring = FAIL for that gate and the cycle (fail-closed; never interpreted as "not applicable"). A gate whose precondition is missing (no emulator, no service) = NOT-RUN, which blocks completion until a human waives it.
4. **Adversarial check**: ensure the diff does not weaken tests, delete assertions, or modify `.hadrian/contract.md`.
5. **Record state**: append the cycle result to `.hadrian/state.md` with captured evidence.
6. **Iterate**: proceed immediately to the next cycle without stalling or asking unnecessary questions unless blocked by an unresolvable error — and only while budget remains (see budget check above).

### 3. Execution guardrails (strict anti-entropy)

- **Direct code execution:** never inspect OS processes (`ps`), search for other agents, or stall on existing working-tree diffs. Execute the required changes directly on the codebase.
- **Evidence over claims:** every PASS must cite captured test/build command output.
- **Immutable contract:** never edit `.hadrian/contract.md` after intake.
- **Branch discipline:** record the current git branch in `.hadrian/state.md` before the first change. Never apply changes directly to the repository's default (main/master) branch — create and check out a dedicated work branch for the goal (e.g., `hadrian/<goal-slug>`) before applying any change.
- **No git push:** do not run `git push` without `.hadrian/signoff`.

## Stop conditions & reports

- All DoD clauses PASS + adversarial check clean → completion report; acceptance requires explicit user approval, then create `.hadrian/signoff`.
- NOT-RUN gates block completion: list them in the report and require an explicit human waiver recorded in `.hadrian/state.md` as `WAIVER: gate=<name> by=<user> at=<UTC timestamp> reason=<...>`. The agent never self-waives.
- Budget exhausted / same failure twice in a row / blocker → escalation report (objective, cycles used vs budget, per-clause status with evidence refs, what is blocked, recommended next step). An escalation is a valid outcome — hand off, don't grind.

## Skill reference

Full protocol details live in the Hadrian skill that ships alongside this command: `../SKILL.md` (phases), `../references/gates.md`, `../references/capability-probe.md`, `../references/escalation-report.md`, templates in `../templates/`.
