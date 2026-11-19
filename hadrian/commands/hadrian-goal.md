---
description: Execute an L3 goal loop for a bounded objective (contract intake, automated gates, verified completion)
agent: build
---
# Hadrian L3 Goal Execution

Objective / Command: $ARGUMENTS

You are the implementation engineer executing this Hadrian goal. All mechanics (contract intake, worktree isolation, quality gate verification, evidence generation, verdict recording, and status reporting) are handled deterministically by the Hadrian Engine:
`python3 ~/.agents/skills/hadrian/scripts/engine.py <subcommand>`

## Subcommand Dispatch
If $ARGUMENTS starts with:
- **`status`**: Run `python3 ~/.agents/skills/hadrian/scripts/engine.py status` and report the returned JSON status.
- **`pause`**: Run `python3 ~/.agents/skills/hadrian/scripts/engine.py pause --reason "$ARGUMENTS"` and halt cleanly.
- **`resume`**: Run `python3 ~/.agents/skills/hadrian/scripts/engine.py resume` and continue from the active worktree.
- **`stop`**: Run `python3 ~/.agents/skills/hadrian/scripts/engine.py stop --reason "$ARGUMENTS"` and halt cleanly.
- **`taiga`**: Run `python3 ~/.agents/skills/hadrian/scripts/engine.py taiga-sync --action status` to inspect PM tickets.

---

## Autonomous Goal Protocol (New Objective)

### Phase 0: Intake & Worktree Setup
If no active goal exists in `.hadrian/`:
1. Initialize the goal harness:
   `python3 ~/.agents/skills/hadrian/scripts/engine.py intake "$ARGUMENTS"`
2. Read the returned JSON for your assigned `worktree` path and dedicated `branch`.
3. **Hard Rule (Worktree Isolation):** All file edits and implementations must take place inside `.hadrian/worktrees/<slug>/`. Never modify files in the root checkout.
4. If a ticket ref is associated, verify ownership and decomposition:
   `python3 ~/.agents/skills/hadrian/scripts/engine.py taiga-sync --action status`

### Phase 1: Implementation & Quality Gates
Execute focused cycles:
1. **Implement:** Write or modify the required source code and unit tests inside your assigned worktree.
2. **Execute Gates:** Run the deterministic gate runner:
   `python3 ~/.agents/skills/hadrian/scripts/engine.py run-gates --cycle <cycle_number>`
   - The engine automatically runs Gradle builds, enforces zero compiler warnings, parses test suites, writes `.hadrian/evidence/*.md` artifacts, and records machine-verifiable `VERDICT` lines to `.hadrian/state.md`.
   - **If gates FAIL:** Inspect the failing test names and compiler output returned by `run-gates`. Make the necessary fixes and re-run. Repeat until `status: "PASS"`.
3. **Commit:** When gates pass cleanly, commit your changes:
   `python3 ~/.agents/skills/hadrian/scripts/engine.py commit feat "<concise description of feature>"`

### Phase 2: Knowledge Base & Documentation (if applicable)
If the repository maintains a knowledge base (e.g. OpenWiki):
1. Execute the knowledge base update pass on your work branch.
2. Re-verify gates with `run-gates` and commit docs:
   `python3 ~/.agents/skills/hadrian/scripts/engine.py commit docs "update KB for <objective>"`

### Phase 3: Review Gate & Ticket Completion
1. Retrieve the git diff against the base commit:
   `python3 ~/.agents/skills/hadrian/scripts/engine.py review-diff`
2. Invoke the independent reviewer subagent `@hadrian-verifier` with the contract and diff to verify Definition of Done clauses and ensure no assertions/tests were weakened.
3. If Taiga sync is configured, close all child tasks and transition the story to Done:
   `python3 ~/.agents/skills/hadrian/scripts/engine.py taiga-sync --action finish`
4. Once the Review Gate passes, present the completion report and request user signoff.
