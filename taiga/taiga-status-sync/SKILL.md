---
name: taiga-status-sync
description: Keep Taiga task and user story statuses in sync with the work an agent is actually performing - start, progress, block, and complete transitions via the taiga_bridge MCP tools. Use when an agent begins, advances, blocks on, or finishes a Taiga task or user story it owns; main agents may update tasks and their parent user story, sub-agents only their own assigned task.
metadata:
  version: "1.0.0"
---

# Taiga Status Sync — keep ticket state in step with the work you actually do

You are an agent working on a Taiga project through the `taiga_bridge` MCP tools (or equivalent Taiga API access): `get_entity_by_ref_tool`, `update_entity_by_ref_tool`. This skill governs **when and how** you change the status of the task(s) and user story(ies) you are currently working on, so that Taiga always reflects reality: every transition corresponds to an activity you actually performed, and no agent changes a ticket it does not own.

## Who may change what (authority model)

| Actor | May change | Must never change |
|-------|-----------|-------------------|
| **Main agent** — the top-level conversation driving the objective | Status of its tasks **and** status of the user stories it is working on | Any ticket it is not actively working on |
| **Sub-agent** — spawned via a Task/subagent tool to work one specific task | Status of **its own assigned task only** (the single task named in its assignment prompt) | The parent user story, any other task, any epic or issue |

Determining your role:
- You are the **main agent** if you are the top-level conversation that received the objective (a direct user request, a `/goal` run) and may delegate work to sub-agents.
- You are a **sub-agent** if you were spawned by another agent with a scoped assignment — a Task/subagent invocation whose prompt names one Taiga task ref. Your write surface is exactly that one task, no matter what the parent story's state looks like or how much of it appears finished.
- If your role is ambiguous, act as a sub-agent: touch only the single task explicitly assigned to you and say so in your report. When in doubt about scope, do not write.

## Status vocabulary — discover, never invent

Status names differ per project and entity type. Never hard-code or guess a status name:
1. Read the current state of the entity first (`get_entity_by_ref_tool`, `include_history=False`) — this gives you its current status **and** its version for optimistic locking.
2. If an update fails with a status error, the error lists the project's valid statuses — retry once using one of those exact names (pass `strict=True` so resolution is exact and misses are reported instead of guessed).
3. The mapping below uses *roles*, not literal names: pick the project's status that plays each role.

| Activity performed | Target status role | Notes |
|--------------------|-------------------|-------|
| Work on a task has started (first real step taken) | first open/in-progress status ("In Progress", "Doing") | Only after you actually start — not at assignment time |
| You are blocked and cannot proceed | the project's blocked status, if it exists | Otherwise keep the current status and add a comment describing the blocker + what unblocks it. Never invent a "Blocked" status |
| Task work is done **and verified** (tests/build pass, read-back confirms) | closed/done task status ("Done", "Closed") | Verification evidence must exist before this transition — no "done on faith" |
| All child tasks of a user story are in a closed state (verified by re-reading the story's `related.tasks`) | closed/done user-story status | **Main agent only.** Never mark a story done while any child task is open — if some remain, report them instead |

## Workflow

### 1. Read before you write
Fetch the entity with `get_entity_by_ref_tool(project_slug, <ref>, "task"|"userstory", include_history=False)` and note: current status, version, and (for a user story) its child tasks' refs and statuses. If the entity is already in your target state, **stop — no write, no comment** (idempotent no-op).

### 2. Decide the transition
Map the activity you just performed to the table above. One activity → at most one status change per entity. Do not batch speculative transitions: "will be done soon" is not a reason to move a ticket.

### 3. Write with comment + optimistic lock
Use `update_entity_by_ref_tool` in a single call:
- `status=<exact project status name>`,
- `expected_version=<version from step 1>` — on a 409 conflict, re-read and decide again; never force through a stale version,
- `comment="<what you did that justifies this transition>"` (one or two sentences, e.g. "Implemented AC-2: added retry to sync worker; unit tests green"),
- `read_back=True`.

The comment is mandatory on every status change — Taiga history must show *why* the ticket moved. A write without a corresponding performed activity is forbidden.

### 4. Verify (fail-closed)
`read_back` returns the new state: confirm `state.status` equals the target and, for a user story marked done, that all child tasks are closed. Any mismatch = report failure; do not claim success.

### 5. Report
End with one line per transition: entity ref/URL, old → new status, triggering activity. A sub-agent ends its final message with exactly this (plus any blocker) so the main agent can aggregate — and stops there; the story-level transition is the main agent's job.

## Hard rules — never violate

1. **Sub-agents never change a user story** — not its status, points, description, or anything else. Their write surface is exactly their one assigned task.
2. Only the **main agent** changes user-story status, and only for stories it is actively working on.
3. Never invent or guess status names; use exact project statuses (from a read or from a strict-update error listing).
4. Every status change carries a comment naming the activity that caused it — no silent moves.
5. No transition without a corresponding performed activity: Taiga mirrors reality, not intentions.
6. Read-back verification after every write; report only transitions you actually confirmed.

## Related skills (same `taiga` plugin)

- `taiga-story-tasks` — decomposes a user story into one estimated task per acceptance criterion. The tasks it creates are what this skill keeps in sync. Note: that skill's "do not modify the user story" rule scopes its decomposition workflow; status changes follow this skill instead.
