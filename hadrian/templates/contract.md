# Goal Contract — <objective>

- Started: <UTC timestamp>
- Budget: <N> cycles (default 10)
- Work branch: <dedicated work branch — never main/master>
- Spec reference: <path or none>
- Knowledge base sources: <AGENTS.md / CLAUDE.md / GEMINI.md / none>

## Definition of Done
1. <clause — verifiable statement>
2. ...

## Quality Gates
| # | Gate | Source | Command | Status |
|---|------|--------|---------|--------|
| 1 | <name> | spec\|kb:<file>\|inferred\|derived | `<command>` | pending |

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
