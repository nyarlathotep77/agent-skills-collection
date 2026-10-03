# Rubric Gate — graded evaluation on top of binary gates

Gates are binary (PASS/FAIL, fail-closed). The Rubric adds *graded* measurement on top: a structured scoring instrument whose criteria derive from the DoD clauses, each with a scale and anchored descriptors (what full credit vs partial vs none looks like). It quantifies "how well", not just "whether" — it gives partial-credit visibility when budget runs out, prioritizes remaining work (the lowest-scoring clause is where the next cycle should push), feeds the human acceptance gate with a scorecard instead of raw output dumps, and tracks quality trend across cycles in state.md so regressions surface.

It never overrides gates: a clause that FAILs its gate cannot count as complete regardless of rubric points, and NOT-RUN still blocks completion.

## 1. Derivation (Phase 0)

- Each DoD clause maps to one or more criteria; every criterion records its source (`spec`, `kb:<file>`, `inferred`, `derived`) exactly like gates.
- Default scale is **0–4** with these anchors: 0 = none of the criterion's substance present; 1 = minimal/partial — recognizable attempt, most substance missing; 2 = mostly present with material gaps; 3 = solid — meets the clause, minor issues only; 4 = full credit — fully exemplifies or exceeds.
- Each criterion carries anchored descriptors for at least its top (4), middle (2), and bottom (0) points so scoring is reproducible by a different evaluator.
- Each criterion records an **anchor** (minimum score that counts as complete, default 3); the contract records a **mean threshold** across all criteria (default ≥ 3.0). A clause's score is the minimum of its criterion scores — conservative and fail-closed; with one criterion per clause this reduces to the per-clause score.
- The rubric is written into `.hadrian/contract.md` (`## Rubric` section, see templates/contract.md) and frozen after intake — amendments are human-only, proposed in reports, exactly like gates.

## 2. Capability modes (Phase 1 probe)

Record `rubric=independent|in-process` in the state header:

- **independent** — the harness can spawn a dedicated read-only rubric-evaluator subagent (modeled on `hadrian-verifier`). It scores against the frozen contract rubric with cited evidence; it never implements and never sees other evaluators' scores. A harness only qualifies if it can actually spawn such an evaluator.
- **in-process** — degraded mode: the main agent runs the same scoring pass itself, criterion by criterion, strictly against the frozen descriptors and captured evidence (no new work, no re-scoring after seeing its own implementation notes).

Both modes must exist; adapt, don't fail. The active mode is recorded in every completion/escalation report.

## 3. Execution

- After each cycle's Quality + Review Gates: score every criterion against this cycle's captured evidence and append per-criterion scores with one line of evidence to `.hadrian/state.md` (optional extension field after the review verdict in the cycle entry).
- The rubric runs at minimum on stop conditions (completion/escalation) and whenever the remaining budget is low — a final scorecard must exist before any report.
- Scoring uses only captured evidence from state.md; a criterion with no evidence scores 0–1, never higher (fail-closed).

## 4. Scorecard & completion threshold

- Reports carry a rubric scorecard: criterion → score + one line of evidence (see references/escalation-report.md).
- The goal is complete only when every gate PASSes, the Review Gate is clean, no clause scores below its anchor, and the mean meets the contract threshold. A sub-anchor clause blocks completion exactly like a failed gate — fix it in a new cycle (budget permitting) or escalate.
