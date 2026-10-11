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

## Error classification — transient vs fatal (retry policy)

A verification tool error is classified **before any verdict is recorded**. The class decides whether the gate may be retried within this cycle; it never changes what a completed check's result means, and it never weakens fail-closed semantics — no PASS without a clean run to completion.

- **transient** — infrastructure failure: the tool crashed, timed out, hit a network failure, or lost its binary mid-run. The check **never completed**, so no verdict is possible from that attempt.
- **fatal** — the check ran to completion and reported a real problem: an assertion/test failure, a compile error, or any non-zero exit from a check that ran to completion.

### Retry policy (transient only)

- A transient failure may be retried up to **N times within the same cycle**, with **default N = 1** (one retry after the initial attempt). A goal's contract may declare a different N for specific gates in its Quality Gates table; that value is frozen with the contract and never changed mid-goal.
- Retries happen inside the current cycle and consume **no additional cycle budget** — budget accounting counts cycles, not attempts.
- Every retry is recorded in `.hadrian/state.md` under the cycle entry as a `RETRY` line (format below) carrying UTC timestamp + reason (error class + one-line detail). `RETRY` lines are log lines, not verdict records: they never start with `VERDICT` and are outside references/verdict-contract.md validation.
- **Fatal failures are never retried.** They record `FAIL` immediately on first occurrence — exactly as before this rule existed.
- If the retry budget is exhausted (all N retries still transient), the gate records `NOT-RUN`: by definition the check never completed, so no verdict is possible; the evidence field cites each attempt's timestamp + error class. NOT-RUN blocks completion until a human waives it or fixes the environment — fail-closed preserved. (Any attempt that produced a definitive result — non-zero exit from a run to completion — is fatal by definition and would already have recorded FAIL on first occurrence, so the exhaustion path always ends NOT-RUN.)
- The final attempt's full evidence (command, exit code, output excerpt) is written to `.hadrian/evidence/<cycle>-<G<n>>.{md,json}` exactly as for any gate run; earlier attempts are summarized in the `RETRY` lines and may be appended to the same artifact under an `## Attempts` note.

### RETRY record format (state.md, inside the cycle entry)

```
RETRY gate=G<n> attempt=<k>/<N> at=<UTC timestamp> reason="<transient error class: one-line detail>"
```

`attempt` counts retries only (`1/<N>` = first retry after the initial failed run). One line per retry; no other fields. Example inside a cycle entry:

```
### Cycle 2
- Action: ...
- Gates:
    RETRY gate=G3 attempt=1/1 at=2026-10-11T04:30:00Z reason="timeout: npm registry unreachable (ECONNRESET)"
    VERDICT kind=gate id=G3 status=PASS evidence=".hadrian/evidence/2-G3.md — json.tool rc=0 on retry" source=kb:AGENTS.md
```

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
