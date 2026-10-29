# Goal Contract — <objective>

- Started: <UTC timestamp>
- Budget: <N> cycles (default 10)
- Work branch: <dedicated work branch — never main/master>
- Spec reference: <path or none>
- Knowledge base sources: <AGENTS.md / CLAUDE.md / GEMINI.md / none>
- Ticket: <project_slug#ref or URL | none>

## Definition of Done
1. <clause — verifiable statement>
2. ...

## Quality Gates
| # | Gate | Source | Command | Status |
|---|------|--------|---------|--------|
| 1 | <name> | spec\|kb:<file>\|inferred\|derived | `<command>` | pending |

## Ticket Sync (mandatory when the goal owns a PM ticket)
<!-- Omit this entire section only if no project-management ticket is tied to the objective — then record `Ticket: none` in the header. When present, its clauses and gates are mandatory contract content that block completion exactly like any other DoD clause or gate (references/taiga-sync.md). -->
- PM tool: <taiga | other>
- Story: <project_slug#ref or URL>
- Acting account (`pm_account`): <identity resolved at intake via the tool's identity endpoint — every ticket the goal implements must be assigned to this account before work starts>
- Status roles (resolved from project configuration by role — never hard-coded or invented): initial=<...> in-progress=<...> done=<...>

Mandatory DoD clauses (numbered into Definition of Done) and quality gates (rows added to the Quality Gates table above, source `contract`):
1. **Decomposition before work** — one child task per acceptance criterion / planned work item exists as a child of the story, in the initial status and assigned to the acting account; existing tasks reused idempotently (no duplicates). Gate T1 verifies by re-reading the story's child tasks **before the first cycle that performs real work**; no implementation step happens before T1 passes.
2. **Evidence-backed transitions** — every sub-task moves to in-progress on its first real work step and to done only with captured verification evidence plus an outcome comment; every status move carries a comment naming the triggering activity (no silent moves). The main agent performs all story-level transitions; workers touch only their own assigned task.
3. **Fail-closed story completion** — at stop, the main agent re-reads the story's child tasks and moves the story to the done-role status only when every child task is closed; otherwise it stays in-progress and open children are reported (refs + subjects). Gate T2 verifies by re-reading at stop.

Gate rows added to Quality Gates:
| # | Gate | Source | Command | Status |
|---|------|--------|---------|--------|
| T1 | Ticket decomposition exists before first work cycle (child tasks created/reused, assigned) | contract | <PM tool read of story + child tasks> | pending |
| T2 | All child tasks closed with evidence; story in done-role status (fail-closed re-read at stop) | contract | <PM tool read of story + child tasks at stop> | pending |

## Rubric
Scale per criterion: 0 = none of the substance present; 1 = minimal/partial — recognizable attempt, most substance missing; 2 = mostly present with material gaps; 3 = solid — meets the clause, minor issues only; 4 = full credit. Per-criterion anchor (minimum counting as complete): <default 3>. Mean threshold across all criteria: <default ≥ 3.0>. Frozen after intake; amendments human-only.

| # | Criterion (DoD clause) | Source | Anchored descriptors (4 / 2 / 0) |
|---|------------------------|--------|----------------------------------|
| R1 | C<n> — <criterion text> | spec\|kb:<file>\|inferred\|derived | 4: <...>; 2: <...>; 0: <...> |

<!-- Clause score = minimum of its criterion scores; completion requires no clause below its anchor and mean ≥ threshold (references/rubric-gate.md). -->

## Constraints
- <e.g. no new dependencies, touch only src/foo, ...>

## Verification Commands
- <primary test/build commands used by the Quality Gate>

## Amendments (human-only)
<!-- The agent proposes amendments in reports; a human records them here and updates clauses/gates. -->
