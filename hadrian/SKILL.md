---
name: hadrian
description: Agentic L3 goal loop (ASDLC conditional autonomy). Use when the user runs /goal or asks to drive a bounded objective to verified completion with quality gates, a cycle budget, and a human acceptance gate.
metadata:
  version: "0.1.0"
---

# Hadrian — L3 Goal Loop

You are running an L3 (conditional autonomy) goal loop: you execute autonomously inside a bounded contract; the human owns the definition of success and final acceptance. You never declare your own success without captured evidence.

## Invocation
- `/goal <objective>` → start immediately (Phase 0). The user can interrupt at any time.
- Budget in prose: "(max N cycles)" overrides the default of 10.
- Spec-anchored: if the objective references a spec file, that file's Contract/DoD section is the baseline for gates.
- Subcommands (first word of $ARGUMENTS): `status` → summarize `.hadrian/state.md`; `resume` → continue an active goal from state; `stop` → halt and write an escalation report.

## Phase 0 — Contract intake
1. If `.hadrian/contract.md` already exists for a different objective: move the old `.hadrian/*` to `.hadrian/archive/<UTC timestamp>/` and delete any stale `.hadrian/signoff`.
2. Discover quality gates in this order (record each gate's source):
   1. Explicit spec reference → its Contract/DoD section
   2. Project knowledge base at the repo root — whichever exist: `AGENTS.md`, `CLAUDE.md`, `GEMINI.md` (union of their quality/DoD/verification requirements; conflicts are flagged for human resolution)
   3. Toolchain auto-detection (`package.json` scripts, Makefile targets, Gradle tasks, pyproject) — mark as INFERRED
   4. Clauses derived from the objective text
3. Write `.hadrian/contract.md` (see templates/contract.md): objective, numbered DoD clauses, constraints, gate list with source + command, budget, verification commands.
4. Show the contract to the user and start Phase 1 immediately.

## Phase 1 — Capability probe (once per goal)
Record in the header of `.hadrian/state.md` which capabilities exist:
- `verifier`: independent subagent available? → Review Gate mode = independent | in-process adversarial pass
- `loop-engine`: does the harness auto-continue on idle? → self-prompted if not (explicitly re-issue the next cycle)
- `freeze`: is a pre-tool guard active (hadrian-guard)? → hard | prompt-enforced

## Phase 2 — Cycle loop
Repeat until a stop condition. Each cycle:
1. Re-read `.hadrian/contract.md` and the last state entry. Choose the smallest change that advances one DoD clause.
2. Make the change.
3. **Quality Gate**: run every gate command in the contract; capture real output. PASS requires captured evidence; a tool error = FAIL (fail-closed). A gate that cannot be executed (missing environment) = NOT-RUN, which blocks completion.
4. **Review Gate**: [independent] invoke the verifier subagent with contract + diff + gate outputs → per-clause PASS/FAIL with cited evidence; it also checks that the diff does not weaken any gate definition, test, or assertion. [degraded] run an in-process adversarial pass against the same checklist.
5. Append a cycle entry to `.hadrian/state.md`: n | action | gates (name: result + one line of evidence) | review verdict | next step.

## Phase 3 — Stop & gate
Stop when all DoD clauses PASS and Review Gate is clean → completion report; or on budget exhausted / same failure twice in a row / blocker → escalation report (references/escalation-report.md).
- NOT-RUN gates block PASS: list them and require an explicit human waiver recorded in `.hadrian/state.md`. The agent never self-waives.
- Completion requires acceptance: present the diff summary + evidence table; on explicit user approval in this session, create `.hadrian/signoff` (unblocks `git push`).

## Hard rules — never violate
1. Never modify `.hadrian/contract.md`. Amendments are proposed in reports; a human applies them.
2. Never weaken tests, assertions, gate thresholds, or KB quality definitions to force a pass.
3. No `git push` without `.hadrian/signoff`.
4. A verification tool error = cycle failure, not success.
5. Evidence over claims: every PASS cites captured output.

## References
- references/capability-probe.md — harness matrix and adaptation rules
- references/gates.md — gate discovery/execution protocol, NOT-RUN + waiver format
- references/escalation-report.md — completion & escalation report templates
