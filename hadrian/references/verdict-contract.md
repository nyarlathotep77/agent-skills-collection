# Verdict Contract — machine-verifiable gate, review & rubric records

Every Quality Gate result, Review Gate verdict, and Rubric criterion score written to `.hadrian/state.md` is a **verdict record**: one strict line per result. Prose-only verdicts are invalid by definition — a cycle entry whose results appear as free text instead of records fails validation exactly like a malformed record (Fail-fast rules below).

## Record grammar

One record per line, fields in exactly this order:

```
VERDICT kind=<kind> id=<id> status=<status>[ score=<score>] evidence="<evidence>" source=<source>
```

- Leading whitespace is ignored; the remainder of the line must match the grammar exactly — no trailing text, no wrapping.
- `evidence` is the only double-quoted field and its value must not contain a double-quote character (rephrase instead). All other values are single tokens: no spaces, no quotes.

Single-line reference regex for validators:

```
^\s*VERDICT kind=(gate|review|rubric) id=(G\d+|C\d+|CW|R\d+) status=(PASS|FAIL|NOT-RUN|WAIVED)( score=[0-4])? evidence="([^"]+)" source=\S+$
```

A line that starts with `VERDICT` but fails this regex — or any per-kind rule below — is **malformed**.

### Fields

| Field | Type / enum | Applies to | Rule |
|---|---|---|---|
| `kind` | `gate` \| `review` \| `rubric` | all | Selects the id and source rules. Any other value = malformed. Must agree with the id prefix (gate→`G`, review→`C`/`CW`, rubric→`R`). |
| `id` | `G<n>` \| `C<n>` \| `CW` \| `R<n>` | all | Must resolve against the frozen contract: gate row n of the Quality Gates table, DoD clause n (plus `CW` for the gate-weakening check), or rubric criterion row n. An id with no matching row/clause = malformed — undeclared ids fail loudly instead of silently passing. |
| `status` | `PASS` \| `FAIL` \| `NOT-RUN` \| `WAIVED`, case-sensitive | all | Per-kind restrictions below; a value outside the enum or disallowed for its kind = malformed. |
| `score` | integer 0–4, decimal, no padding | rubric only | Required for `kind=rubric`, forbidden otherwise. Must be consistent with status: `PASS` iff score ≥ the criterion's anchor (default 3), else `FAIL`. Inconsistency = malformed. |
| `evidence` | non-empty double-quoted string, no embedded quotes | all | One line of captured output from this cycle, or an explicit pointer to where it was captured (file path / command + cycle). Empty or missing = malformed — a PASS with no evidence is impossible by construction. |
| `source` | single token | all | Must match the source recorded in the contract for that id (`spec`, `kb:<file>`, `inferred`, `derived`) for gates and rubric criteria, or the Review Gate mode from the state header (`independent`, `in-process`) for review records. Mismatch = malformed. |

### Per-kind rules

**kind=gate** — one record per row of the contract's Quality Gates table, in every cycle.
- `id=G<n>` where n is the gate's row number in that table.
- All four statuses valid. `WAIVED` additionally requires a matching human waiver line for this gate (format: references/gates.md); without one the record is malformed. The agent never writes WAIVED itself.
- Artifact existence: `PASS` and `FAIL` require their evidence artifact — the `evidence` field must reference `.hadrian/evidence/<cycle>-<G<n>>.{md,json}` for that cycle, and a record whose referenced file does not exist is malformed (treated as NOT-RUN). A verdict without captured evidence is invalid by construction; the artifact is written before the record (references/evidence-artifacts.md). `NOT-RUN`/`WAIVED` records need no artifact — their evidence states why the gate did not run or who waived it.

**kind=review** — one record per DoD clause plus one for the gate-weakening check, in every cycle.
- `id=C<n>` where n is the DoD clause number; `id=CW` for the gate-weakening check (PASS when no hit; FAIL with evidence naming the single hit that failed the cycle).
- Statuses: `PASS`, `FAIL`, or `NOT-RUN` only — `WAIVED` here makes the record malformed.

**kind=rubric** — one record per criterion row of the contract's Rubric table, in every cycle where the Rubric Gate ran.
- `id=R<n>` where n is the criterion's row number.
- Statuses: `PASS` iff score ≥ the criterion's anchor (default 3), else `FAIL`. A criterion with no captured evidence scores 0–1 and FAILs (fail-closed) — it is never NOT-RUN, so `NOT-RUN` and `WAIVED` here make the record malformed.

## Placement in state.md

Records live inside the cycle entry they belong to, under their section bullet:

```
### Cycle 3
- Action: <free text — what changed, files touched>
- Gates:
    VERDICT kind=gate id=G1 status=PASS evidence="make lint: 0 errors" source=inferred
    VERDICT kind=gate id=G2 status=NOT-RUN evidence="no emulator in environment" source=kb:AGENTS.md
- Review:
    VERDICT kind=review id=C1 status=PASS evidence="diff adds retry with backoff; test covers timeout path" source=independent
    VERDICT kind=review id=CW status=PASS evidence="no weakening hits: no test/threshold/KB/contract edits in diff" source=independent
- Rubric (only when the Rubric Gate ran):
    VERDICT kind=rubric id=R1 status=PASS score=3 evidence="retry logic present, minor gap on jitter" source=derived
- Next: <free text — next smallest step>
```

`Action` and `Next` are free text; everything under `Gates`, `Review`, and `Rubric` is records only. A cycle where the Rubric Gate did not run has no `Rubric` section (absence = not run: fine mid-loop, blocks completion — references/rubric-gate.md).

## Malformed examples

Each line below fails validation for the reason noted:

```
VERDICT kind=gate id=G1 status=PASSED evidence="lint ok" source=inferred          # status outside enum
VERDICT kind=rubric id=R1 status=PASS score=5 evidence="great" source=derived     # score out of 0–4 range
VERDICT kind=gate id=G9 status=PASS evidence="ok" source=inferred                 # undeclared gate row
VERDICT kind=rubric id=R1 status=FAIL score=4 evidence="ok" source=derived        # inconsistent with anchor (default 3)
VERDICT kind=review id=C1 status=WAIVED evidence="skipped" source=independent     # WAIVED disallowed for review
VERDICT kind=gate id=G2 status=WAIVED evidence="waived in session" source=inferred# no matching human WAIVER line
VERDICT kind=gate id=G1 status=PASS evidence="" source=inferred                   # empty evidence
```

## Fail-fast validation rules (resume / status / stop)

When `.hadrian/state.md` is read for `status`, `resume`, or `stop`:
1. Validate every line that starts with `VERDICT` against the grammar and per-kind rules above, resolving ids and sources against the frozen contract.
2. Any violation — missing field, status outside the enum (or disallowed for its kind), empty/missing evidence, unknown id, score missing/out of range/inconsistent with status, source mismatch, WAIVED without a matching waiver line — makes that record **malformed**. A malformed record is treated as `NOT-RUN` for its id in its cycle. It is never guessed at, coerced into a pass, or silently rewritten; past state entries are append-only and stay exactly as written.
3. An id with no valid record in the most recent completed cycle also counts as NOT-RUN (fail-closed).
4. `status` lists every malformed record explicitly (cycle, id, reason) alongside its summary.
5. Completion is blocked while any gate/review/rubric id resolves to NOT-RUN: a gate id may be cleared only by a human waiver line; review and rubric ids are cleared only by re-running that evaluator in a new cycle (budget permitting) or escalation.
