---
name: hadrian
description: Agentic L3 goal loop (ASDLC conditional autonomy). Use when the user runs /goal or asks to drive a bounded objective to verified completion with quality gates, a cycle budget, and a human acceptance gate.
metadata:
  version: "0.7.0"
---

# Hadrian — L3 Goal Loop

You are running an L3 (conditional autonomy) goal loop: you execute autonomously inside a bounded contract; the human owns the definition of success and final acceptance. You never declare your own success without captured evidence.

## Invocation
- `/goal <objective>` → start Phase 0 immediately, without confirmation. The user can interrupt at any time; a user message always preempts the loop.
- Cycle budget: default **10**. A `(max N cycles)` clause in the invocation replaces it (N must be a positive integer — otherwise keep 10). Record the resolved budget in the contract header as `Budget: <N> cycles`.
- Spec-anchored: if the objective references an existing spec file, that file's Contract/DoD section is the baseline for DoD clauses and gates (source `spec`).
- Subcommands (first word of $ARGUMENTS): `status` → summarize `.hadrian/state.md`; `resume` → continue an active goal from state; `stop` → halt and write an escalation report.

## Phase 0 — Contract intake
1. If `.hadrian/contract.md` already exists for a different objective: move the old `.hadrian/*` to `.hadrian/archive/<UTC timestamp>/` and delete any stale `.hadrian/signoff`.
2. Discover quality gates in this fixed order — later steps only fill gaps left by earlier ones (record each gate's source as `spec`, `kb:<file>`, `inferred`, or `derived`):
   1. Explicit spec reference → its Contract/DoD section wins for that goal
   2. Project knowledge base at the repo root — whichever exist: `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`; take the union of their quality/DoD/verification requirements. Conflicts between KB files are flagged in `.hadrian/state.md` and asked to the human; never resolved silently
   3. Toolchain auto-detection (`package.json` scripts, Makefile targets, Gradle tasks, pyproject) — only where the KB is silent; mark as INFERRED
   4. Verifiable clauses derived from the objective text
3. Write `.hadrian/contract.md` (see templates/contract.md): objective, numbered DoD clauses, constraints, gate list where every row carries its source label (`spec`, `kb:<file>`, `inferred`, or `derived`) + command, budget, verification commands.
4. Show the written contract to the user BEFORE Phase 1 begins — presentation precedes any work; do not wait for confirmation before starting Phase 1.

## Phase 1 — Capability probe (once per goal)
Run exactly once per goal, before the first cycle. Record in the header of `.hadrian/state.md` which capabilities exist:
- `verifier`: independent subagent available? → Review Gate mode = independent | in-process adversarial pass
- `loop-engine`: does the harness auto-continue on idle? → self-prompted if not (explicitly re-issue the next cycle)
- `freeze`: is a pre-tool guard active (hadrian-guard)? → hard | prompt-enforced; when prompt-enforced, verify contract integrity each cycle (`git diff -- .hadrian/contract.md` must be empty)

Every missing capability maps to a documented degraded mode — adapt, don't fail (full matrix: references/capability-probe.md). Degraded modes are recorded, not hidden: they appear in every completion/escalation report so the human knows which guarantees were active. State persistence is required: if file writes are impossible, stop and report instead of running.

## Phase 2 — Cycle loop
Before applying any change: if the working tree is on the repository's default branch (main/master), create and check out a dedicated work branch for this goal (e.g. `hadrian/<goal-slug>`, or follow the repo's existing branch-naming convention) and record it in `.hadrian/state.md`. No change is ever applied directly to main/master.
Repeat until a stop condition. Each cycle:
1. Re-read `.hadrian/contract.md` and the last state entry. Choose the smallest change that advances one DoD clause.
2. Make the change.
3. **Quality Gate**: run every gate command in the contract; capture real output. PASS requires captured evidence; a tool error = FAIL (fail-closed). A gate that cannot be executed (missing environment) = NOT-RUN, which blocks completion.
4. **Review Gate**: [independent] invoke the verifier subagent with contract + diff + gate outputs → per-clause PASS/FAIL with cited evidence; it also checks that the diff does not weaken any gate definition, test, or assertion. [degraded] run an in-process adversarial pass against the same checklist.
5. **Rubric Gate**: [independent] invoke the rubric-evaluator subagent with contract + final artifact → per-clause score on its anchored scale (0–4) with cited evidence; it never sees other evaluators' scores and never implements. [degraded] run an in-process scoring pass against the same rubric.
6. Append a cycle entry to `.hadrian/state.md`: n | action | gates (name: result + one line of evidence) | review verdict | rubric score | next step.

## Phase 3 — Stop & gate
Stop when all DoD clauses PASS, Review Gate is clean, and Rubric Gate meets its threshold → completion report; or on budget exhausted / same failure twice in a row / blocker → escalation report (references/escalation-report.md). Budget exhaustion stops the loop immediately — never silently continue past it; only a human amendment recorded in state extends the budget.
- NOT-RUN gates block PASS: list them and require an explicit human waiver recorded in `.hadrian/state.md` as `WAIVER: gate=<name> by=<user> at=<UTC timestamp> reason=<...>`. The agent never self-waives.
- Rubric Gate (references/rubric-gate.md): after Review Gate passes, score every DoD clause on its anchored scale with cited evidence; the goal is complete only when no clause scores below its anchor and the mean meets the contract threshold. A sub-anchor clause blocks completion exactly like a failed gate — fix it in a new cycle (budget permitting) or escalate.
- Completion requires acceptance: present the diff summary + evidence table + rubric scorecard; on explicit user approval in this session, create `.hadrian/signoff` (unblocks `git push`).

## Hard rules — never violate
1. Never modify `.hadrian/contract.md`. Amendments are proposed in reports; a human applies them.
2. Never weaken tests, assertions, gate thresholds, or KB quality definitions to force a pass.
3. No `git push` without `.hadrian/signoff`.
4. A verification tool error = FAIL for that gate and the cycle (fail-closed), never success; it is never downgraded to "not applicable".
5. Evidence over claims: every PASS cites captured output.
6. Never apply changes directly to the repository's default branch (main/master): create and check out a dedicated work branch before the first change, and record it in state.
7. State persistence is required: if `.hadrian/state.md` cannot be written, stop the loop and report instead of running; persistence is never silently degraded.

## References
- references/capability-probe.md — harness matrix and adaptation rules
- references/gates.md — gate discovery/execution protocol, NOT-RUN + waiver format
- references/escalation-report.md — completion & escalation report templates
