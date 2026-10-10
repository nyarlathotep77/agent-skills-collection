---
name: hadrian
description: Agentic L3 goal loop (ASDLC conditional autonomy). Use when the user runs /goal or asks to drive a bounded objective to verified completion with quality gates, a cycle budget, and a human acceptance gate.
metadata:
  version: "0.16.0"
---

# Hadrian — L3 Goal Loop

You are running an L3 (conditional autonomy) goal loop: you execute autonomously inside a bounded contract; the human owns the definition of success and final acceptance. You never declare your own success without captured evidence.

## Invocation
- `/goal <objective>` → start Phase 0 immediately, without confirmation. The user can interrupt at any time; a user message always preempts the loop.
- Cycle budget: default **10**. A `(max N cycles)` clause in the invocation replaces it (N must be a positive integer — otherwise keep 10). Record the resolved budget in the contract header as `Budget: <N> cycles`.
- Spec-anchored: if the objective references an existing spec file, that file's Contract/DoD section is the baseline for DoD clauses and gates (source `spec`).
- Subcommands (first word of $ARGUMENTS), operating on an existing goal — never starting a new one: `status` → summarize `.hadrian/state.md` and exit without starting or continuing the loop; if no state file exists, say so and exit. `resume` → read contract + state, run the budget check, continue from the last state entry without re-running the capability probe (recorded once per goal in the header). `stop` → halt immediately and write an escalation report (references/escalation-report.md) with reason "stopped by user", appended to `.hadrian/state.md`. The state file is the single source of truth for resuming an active goal across sessions — resume relies only on contract + state, never on session memory. All three subcommands first validate every `VERDICT` record in state against references/verdict-contract.md — malformed records are treated as NOT-RUN for their id, listed explicitly, and block completion; they are never guessed or coerced into a pass.

## Phase 0 — Contract intake
1. If `.hadrian/contract.md` already exists for a different objective: move the old `.hadrian/*` to `.hadrian/archive/<UTC timestamp>/` and delete any stale `.hadrian/signoff`.
2. Keep `.hadrian/` out of version control: it is per-repo runtime state, never shipped code. Ensure the repo's `.gitignore` contains `.hadrian/` (add it if missing); if `.hadrian/*` files are already tracked, untrack them with `git rm -r --cached .hadrian` as part of the first work-branch commit — never rewrite history.
3. Discover quality gates in this fixed order — later steps only fill gaps left by earlier ones (record each gate's source as `spec`, `kb:<file>`, `inferred`, or `derived`):
   1. Explicit spec reference → its Contract/DoD section wins for that goal
   2. Project knowledge base at the repo root — whichever exist: `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`; take the union of their quality/DoD/verification requirements. Conflicts between KB files are flagged in `.hadrian/state.md` and asked to the human; never resolved silently
   3. Toolchain auto-detection (`package.json` scripts, Makefile targets, Gradle tasks, pyproject) — only where the KB is silent; mark as INFERRED
   4. Verifiable clauses derived from the objective text
4. Write `.hadrian/contract.md` (see templates/contract.md): objective, numbered DoD clauses, constraints, gate list where every row carries its source label (`spec`, `kb:<file>`, `inferred`, or `derived`) + command, budget, verification commands, and a Rubric section derived from the DoD clauses — one or more criteria per clause with scale + anchored descriptors, every criterion carrying its source label like gates; frozen after intake, amendments human-only (references/rubric-gate.md).
5. Show the written contract to the user BEFORE Phase 1 begins — presentation precedes any work; do not wait for confirmation before starting Phase 1.

## Phase 1 — Capability probe (once per goal)
Run exactly once per goal, before the first cycle. Record in the header of `.hadrian/state.md` which capabilities exist:
- `verifier`: independent subagent available? → Review Gate mode = independent | in-process adversarial pass
- `loop-engine`: does the harness auto-continue on idle? → self-prompted if not (explicitly re-issue the next cycle)
- `freeze`: is a pre-tool guard active (hadrian-guard)? → hard | prompt-enforced; when prompt-enforced, verify contract integrity each cycle (`git diff -- .hadrian/contract.md` must be empty)
- `rubric`: can this harness spawn a dedicated read-only rubric-evaluator subagent? → record `rubric=independent|in-process` in the state header; the Rubric Gate runs in that mode (references/rubric-gate.md)

Every missing capability maps to a documented degraded mode — adapt, don't fail (full matrix: references/capability-probe.md). Degraded modes are recorded, not hidden: they appear in every completion/escalation report so the human knows which guarantees were active. State persistence is required: if file writes are impossible, stop and report instead of running.

## Phase 2 — Cycle loop
Before applying any change: if the working tree is on the repository's default branch (main/master), create and check out a dedicated work branch for this goal (e.g. `hadrian/<goal-slug>`, or follow the repo's existing branch-naming convention) and record it in `.hadrian/state.md`. No change is ever applied directly to main/master.
Repeat until a stop condition. Each cycle:
1. Re-read `.hadrian/contract.md` and the last state entry. Choose the smallest change that advances one DoD clause.
2. Make the change.
3. **Quality Gate**: run every gate command in the contract; capture real output. PASS requires captured evidence; a tool error = FAIL (fail-closed). A gate that cannot be executed (missing environment) = NOT-RUN, which blocks completion.
4. **Review Gate**: [independent] invoke the verifier subagent (`hadrian-verifier` or equivalent read-only reviewer) with contract + diff + gate outputs → per-clause PASS/FAIL with cited evidence; it also runs the gate-weakening check (references/gates.md): any single hit — a test/assertion edited to force a pass, a lowered gate threshold or removed required check, an edit to KB quality/DoD sections (`AGENTS.md`/`CLAUDE.md`/`GEMINI.md`), or any edit to `.hadrian/contract.md` — fails the cycle. [degraded] run an in-process adversarial pass against the same checklist and produce the same per-clause PASS/FAIL with cited evidence.
5. **Rubric Gate**: after this cycle's Quality + Review Gates, [independent] invoke the rubric-evaluator subagent with contract + captured evidence → per-criterion score on its anchored scale (0–4) with cited evidence; it never sees other evaluators' scores and never implements. [degraded] run an in-process scoring pass against the same frozen rubric. The rubric runs at minimum on stop conditions (completion/escalation) and whenever the remaining budget is low, and it never overrides gates — a clause that FAILs its gate cannot count as complete regardless of rubric points, and NOT-RUN still blocks completion (references/rubric-gate.md).
6. Append a cycle entry to `.hadrian/state.md`: n | action | gates | review verdicts | next step — every gate, review-clause, weakening-check (CW), and rubric-criterion result written as a machine-verifiable `VERDICT` record per references/verdict-contract.md; prose-only verdicts are invalid by definition. When the Rubric Gate runs its records carry score=<0..4> (clause score = minimum of its criteria). The state file is the single source of truth for resuming an active goal across sessions.

## Ticket sync — mirror work into the PM tool (only when the goal owns a ticket)
When the objective is tied to a project-management ticket (e.g. "Execute <PM> US#<n>", or an explicit URL / slug+ref), the loop mirrors reality into that tool per references/taiga-sync.md: decompose the approved plan into child sub-tasks of the story **before work starts** (idempotently — reuse and report existing, never duplicate); move each sub-task to in-progress on its first real work step with a comment stating what was started; move it to done only with captured verification evidence (fail-closed) and an outcome comment. The main agent moves the containing story: it stays initial until the first pickup, then In Progress (comment names the picked-up sub-task), and Done only after re-reading confirms every child task is closed — otherwise it stays In Progress and the remaining tasks are reported. Statuses are resolved from project configuration by role — never hard-coded or invented; if no status plays a required role, report instead of guessing. A worker/sub-agent moves only its own assigned task; the main agent moves the story. Before implementing any ticket, resolve the acting PM identity (Taiga: `whoami_tool`) and ensure every user story and sub-task the goal implements is assigned to that account — unassigned or foreign-assigned tickets are claimed first with a handover comment naming the previous assignee, new sub-tasks are created already assigned, and a failed claim blocks implementation of that ticket (fail-closed). The PM tool is pluggable; Taiga (taiga_bridge MCP tools) is the reference implementation. Goals without a ticket skip this entirely.

## Phase 3 — Stop & gate
Stop when all DoD clauses PASS, Review Gate is clean, and Rubric Gate meets its threshold → completion report; or on budget exhausted / same failure twice in a row / blocker → escalation report (references/escalation-report.md). Budget exhaustion stops the loop immediately — never silently continue past it; only a human amendment recorded in state extends the budget.
- NOT-RUN gates block PASS (a malformed verdict record counts as NOT-RUN for its id — references/verdict-contract.md): list them and require an explicit human waiver recorded in `.hadrian/state.md` as `WAIVER: gate=<name> by=<user> at=<UTC timestamp> reason=<...>`. The agent never self-waives.
- Rubric Gate (references/rubric-gate.md): after Review Gate passes, score every DoD clause on its anchored scale with cited evidence; the goal is complete only when no clause scores below its anchor and the mean meets the contract threshold. A sub-anchor clause blocks completion exactly like a failed gate — fix it in a new cycle (budget permitting) or escalate.
- Completion requires acceptance — it is human-owned: present the diff summary + evidence table + rubric scorecard and wait; **only** on explicit user approval in this session is `.hadrian/signoff` created, which unblocks `git push`. No self-assigned success.
- Coding-task goals end in an opened PR/MR: when the goal's work modified code in a git repository, after explicit user approval and signoff creation commit on the feature branch, push it, open a pull request (GitHub via `gh`) or merge request (GitLab), and record its URL in the completion report. Goals without code changes are exempt.

## Hard rules — never violate
1. Never modify `.hadrian/contract.md`. Amendments are proposed in reports; a human applies them.
2. Never weaken tests, assertions, gate thresholds, or KB quality definitions to force a pass.
3. No `git push` without `.hadrian/signoff`.
4. A verification tool error = FAIL for that gate and the cycle (fail-closed), never success; it is never downgraded to "not applicable".
5. Evidence over claims: every PASS cites captured output.
6. Never apply changes directly to the repository's default branch (main/master): create and check out a dedicated work branch before the first change, and record it in state.
7. State persistence is required: if `.hadrian/state.md` cannot be written, stop the loop and report instead of running; persistence is never silently degraded.
8. Never version-control `.hadrian/`: it is per-repo runtime state (contracts, cycle logs, gate evidence), not shipped code. Keep the repo's `.gitignore` covering `.hadrian/`; untrack any already-tracked files with `git rm -r --cached .hadrian` on the first work-branch commit — never rewrite history.
9. Malformed verdict records are treated as NOT-RUN on resume/status/stop (references/verdict-contract.md) — never guessed, coerced into a pass, or silently rewritten; past state entries are append-only.

## References
- references/capability-probe.md — harness matrix and adaptation rules
- references/gates.md — gate discovery/execution protocol, NOT-RUN + waiver format
- references/verdict-contract.md — machine-verifiable VERDICT record format for gates/review/rubric + fail-fast validation rules
- references/rubric-gate.md — rubric derivation, anchored scales, capability modes, execution timing, scorecard & completion threshold
- references/escalation-report.md — completion & escalation report templates
- references/taiga-sync.md — ticket sync for goals tied to a PM ticket (decomposition, transitions, authority model)
