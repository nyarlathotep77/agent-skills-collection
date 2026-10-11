# Evidence Artifacts — full gate evidence as typed files under `.hadrian/evidence/`

Gate evidence must survive session loss and be auditable or attachable to a PR/MR. A one-line summary in `state.md` is not enough: every Quality Gate run writes its **full evidence** to an artifact file, and the compact state record points at it. Review and rubric verdicts are out of scope — they cite findings, not command output; only `kind=gate` records carry artifacts.

## Path scheme

```
.hadrian/evidence/<cycle>-<gate-id>.md      (or .json)
```

- `<cycle>`: the 1-based cycle number from `.hadrian/state.md`.
- `<gate-id>`: the gate's row id in the contract's Quality Gates table — `G<n>`, matching the `id` of its `VERDICT kind=gate` record. Example: cycle 2, gate row 1 → `.hadrian/evidence/2-G1.md`.
- One file per (cycle, gate) pair. Re-running a gate within the same cycle overwrites that file (idempotent); each cycle writes its own files, so history is preserved across cycles.
- Create the directory on first write (`mkdir -p .hadrian/evidence`). It lives under `.hadrian/`, which stays out of version control via the repo's existing gitignore rule — never commit artifacts.

## Artifact content

Each artifact records: **command** (exactly as run), **exit code**, and a **relevant output excerpt**. Markdown form (default):

```markdown
# Gate evidence — <gate name> (<G<n>>)

- Goal: <objective>
- Cycle: <n>
- Gate: G<n> — <name>
- Source: <spec|kb:<file>|inferred|derived>
- Command: `<exact command as run>`
- Exit code: <int>
- Captured at: <UTC timestamp>

## Output

<relevant output excerpt>
```

JSON form (same fields, for machine consumption):

```json
{"goal": "<objective>", "cycle": 2, "gate": "G1", "name": "<name>", "source": "inferred", "command": "<exact command as run>", "exit_code": 0, "captured_at": "<UTC timestamp>", "output_excerpt": "<relevant output excerpt>"}
```

**Excerpt policy:** full stdout+stderr when small (≤ ~200 lines); otherwise the last 200 lines plus a note `truncated: kept last 200 of <N> lines`. The excerpt must be sufficient to verify the PASS/FAIL without re-running the command.

## Ordering rule — write before verdict (fail-closed)

For every gate in every cycle, in this order:

1. Run the gate command; capture output and exit code.
2. Write the artifact file for this (cycle, gate); verify it exists and is non-empty.
3. Only then append the `VERDICT kind=gate` record to `.hadrian/state.md`. Its `evidence` field carries the one-line summary **plus** the artifact path:

   ```
   VERDICT kind=gate id=G1 status=PASS evidence=".hadrian/evidence/2-G1.md — make lint: 0 errors" source=inferred
   ```

- **Write failure = NOT-RUN.** If the artifact cannot be written (disk error, permissions), record `status=NOT-RUN` with `evidence="artifact write failed: <reason>"`. The gate is never PASS/FAIL without its file.
- A `PASS` or `FAIL` whose referenced artifact does not exist is **invalid** — malformed per the kind=gate rule in references/verdict-contract.md, treated as NOT-RUN on resume/status/stop.
- `NOT-RUN` (missing precondition) and `WAIVED` records need no artifact; their evidence field states why the gate did not run or who waived it.

## State reference

`state.md` stays compact: each cycle entry keeps one line per gate — the summary plus the artifact path inside the VERDICT record's `evidence` field (see above). Nothing else from the output goes into state; the file is the full record.

## Reports

Completion and escalation reports list every evidence artifact path produced for the goal (`.hadrian/evidence/*`) so a human can audit them or attach them to the PR/MR — see references/escalation-report.md.
