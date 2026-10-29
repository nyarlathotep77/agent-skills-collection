# Ticket Sync — mirror goal-loop work into the PM tool

Mandatory whenever the goal's objective is tied to a project-management ticket (e.g. "Execute Hadrian US#11", or an explicit Taiga URL / `project_slug` + ref). When it applies, ticket sync is **part of the contract**, not an optional side procedure: Phase 0 writes the Ticket Sync section into `.hadrian/contract.md` (templates/contract.md) with its mandatory DoD clauses and quality gates T1/T2, so decomposition, transitions, and fail-closed completion block goal completion exactly like any other clause or gate. A goal with no ticket records `Ticket: none` in the contract header and skips this procedure entirely. The PM tool is **pluggable**; **Taiga** is the reference implementation, accessed through the `taiga_bridge` MCP tools (`whoami_tool`, `get_entity_by_ref_tool`, `create_entity_tool`, `update_entity_by_ref_tool`, `add_comment_by_ref_tool`). Taiga always mirrors reality: every transition corresponds to work actually performed.

## Contract integration — ticket sync is contract content

When a ticket is tied to the goal:
1. **Phase 0** writes the Ticket Sync section into `.hadrian/contract.md` per templates/contract.md: PM tool, story ref, acting account (`pm_account`, resolved via the identity endpoint), and the status roles resolved from project configuration (§0). It numbers the three mandatory clauses (decomposition before work; evidence-backed transitions; fail-closed story completion) into Definition of Done and adds gates **T1** (decomposition exists — verified by re-reading the story's child tasks *before* the first cycle that performs real work) and **T2** (all child tasks closed with evidence, story in done-role status — verified by re-read at stop), both source `contract`.
2. **T1 is a precondition of the first work cycle.** No implementation step happens before decomposition exists and has been read back. If T1 cannot pass (PM tool unreachable, identity unresolvable, no status plays a required role), escalate as a blocker instead of starting untracked work — never implement silently without tickets.
3. **Completion requires T2 PASS** with captured re-read evidence. A goal whose story or child tasks are left open does not complete: it escalates with the open refs + subjects reported, and the story is left in its current state (no speculative transitions).

## 0. Resolve the status vocabulary first (never invent)

Status names differ per project and entity type — never hard-code or guess a name:
1. Read the story first (`get_entity_by_ref_tool`, `include_history=False`) → current status **and** version for optimistic locking.
2. If an update fails with a status error, the error lists the project's valid statuses — retry once using one of those exact names (strict resolution; misses are reported instead of guessed).
3. Map *roles* to the project's configured statuses: initial open / in-progress / done-closed (plus blocked, if it exists). If no status plays a required role, **report and stop** for that transition — never invent or guess a name.

## 1. Claim ownership before work starts (tickets must be assigned to the acting account)

The user stories and sub-tasks a goal implements **must be assigned to the acting account** — the identity whose credentials the loop uses to access the PM tool. Ownership is established *before* any real work on a ticket, so the tool always shows who owns in-flight work:

1. **Resolve the acting identity once.** At the start of ticket sync, call the tool's identity endpoint (Taiga: `whoami_tool`) and record the returned username in `.hadrian/state.md` as `pm_account=<username>`. Every ownership check below is against this identity — never against a human's account or a guess.
2. **Check each owned ticket.** For the containing user story and every child sub-task, read the current assignee (`assigned_to`). Unassigned, or already assigned to the acting account → nothing to do. Assigned to someone else → claim it: reassign to the acting account with a comment recording the handover ("Hadrian taking ownership for goal <objective>; previous assignee: <name>"), using optimistic locking + read-back per §6. Record each handover in `.hadrian/state.md`.
3. **New sub-tasks are born owned.** Decomposition (§2) creates every child task already assigned to the acting account (Taiga: `create_entity_tool` with `assign_to=<acting username>`), so ownership exists at creation — no second write.
4. **Timing.** Ownership is established before the first real work step on a ticket — alongside or ahead of pickup, never after work has started unowned.
5. **Fail-closed.** If identity resolution fails (no identity endpoint, auth error) or an assignment cannot be verified by read-back, do not proceed with implementing that ticket: record the failure in `.hadrian/state.md` and escalate as a blocker. Implementing a ticket the acting account does not own violates this requirement — no silent continuation.

## 2. Decompose before work starts (idempotent)

Before the first cycle that performs real work:
1. Read the story with its existing child tasks (`related.tasks`).
2. For each planned work item / acceptance criterion in the approved execution plan, create **one sub-task per item as a child of the same user story** (`parent_ref` = the story's ref), in the project's initial open status and **already assigned to the acting account** (Taiga: `create_entity_tool` with `assign_to=<acting username>` — ownership exists at creation, no second write; see §1), whose description references its plan step or acceptance criterion (verbatim AC text + story URL).
3. **Idempotency:** existing child tasks covering the same items are reused and reported as `existing`; re-running must never create duplicates. If every item is already covered, report that and proceed without creating anything.
4. Read back each created task to verify (fail-closed): description carries the reference; any mismatch = report failure for that task.

Mechanics follow the `taiga-story-tasks` skill (one task per criterion, idempotency check, read-back verification). The execution plan is already approved by contract presentation in Phase 0 — no second confirmation is needed before creating sub-tasks.

## 3. Sub-task transitions during cycles

Per sub-task, one activity → at most one status change:
- **Pickup** — first real work step on an unstarted sub-task: move it from the initial status to the project's in-progress status ("In Progress"), with a comment stating what was started. Only after actually starting — not at assignment time.
- **Finish (fail-closed)** — move to the project's done/closed status only when the work is complete **and verified** (tests/build pass or equivalent captured evidence), with a comment summarizing the outcome. No sub-task is marked done without verification evidence; if evidence is missing, leave it in progress and report what is missing.
- **Interesting facts** — noteworthy findings during execution (decisions taken, unexpected behavior, environment quirks, captured evidence) are recorded as comments on the corresponding task and/or user story. Every status change also carries a comment naming the activity that caused it — no silent moves.

## 4. Story-level transitions (main agent only)

The containing user story's status is changed **only by the top-level (main) agent**:
- While all child tasks are in their initial open status, the story **stays in its initial status** — no transition to In Progress happens before the first pickup.
- **First pickup:** when any sub-task moves to In Progress, the main agent also moves the story to In Progress with a comment naming the picked-up sub-task (same cycle as the sub-task move).
- **Completion:** after all planned work is done and verified, re-read the story (`related.tasks`) and confirm every child task is in a closed/done state — no open children. Then move the story to Done with a comment summarizing completion. If any child task remains open, the story stays In Progress and the remaining tasks are reported (refs + subjects).

## 5. Authority model

| Actor | May change | Must never change |
|-------|-----------|-------------------|
| **Main agent** — top-level conversation driving the goal | Its sub-tasks **and** the containing user story | Any ticket it is not actively working on |
| **Worker / sub-agent** — spawned to work one assigned sub-task | **Its own assigned task only** (the single task named in its assignment) | The parent user story, any other task, any epic or issue |

A worker's final report ends with one line per transition it performed (entity ref/URL, old → new status, triggering activity); the main agent aggregates and performs all story-level transitions. If your role is ambiguous, act as a worker: touch only the single assigned task and say so in your report. When in doubt about scope, do not write.

## 6. Write discipline & reporting

- Every write uses `update_entity_by_ref_tool` with `status=<exact project status name>`, `expected_version=<version from the read>` (on a 409 conflict: re-read and decide again — never force through a stale version), `comment="<activity that justifies this transition>"`, `read_back=True`.
- Read-back verification after every write (fail-closed): confirm the new state equals the target; for a story marked Done, that all child tasks are closed. Any mismatch = report failure; do not claim success.
- The completion/escalation report carries a ticket-sync section: the acting account (`pm_account`), ownership handovers performed (ticket ref + previous assignee), sub-tasks created/reused (refs), every transition with its triggering activity, the story's final status, and any open children or unresolved status roles reported. On escalation or budget exhaustion the story is left in its current state — no speculative transitions.

## Related skills (same `taiga` plugin)

- `taiga-story-tasks` — decomposition mechanics: one task per acceptance criterion, idempotency check, read-back verification.
- `taiga-status-sync` — transition mechanics: role-based status discovery, comment + optimistic-lock writes, fail-closed verification, authority model. This file defines **when** the goal loop applies them; those skills define **how**.
