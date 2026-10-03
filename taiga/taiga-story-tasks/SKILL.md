---
name: taiga-story-tasks
description: Create implementation tasks for a Taiga user story - one task per acceptance criterion, each estimated in story points or man-days. Use when the user asks to break down, decompose, plan, or create tasks for a Taiga user story (by URL or project slug + ref).
metadata:
  version: "1.1.0"
---

# Taiga Story Tasks — one implementation task per Acceptance Criterion

You convert a Taiga user story into its implementation tasks: exactly **one task per acceptance criterion**, each carrying an estimate in **story points or man-days**. You work through the `taiga_bridge` MCP tools (or equivalent Taiga API access): `get_entity_by_ref_tool`, `create_entity_tool`, `list_custom_attributes_tool`, `set_custom_attributes_tool`.

## Input

Accept either:
- a user story URL of the form `https://<host>/project/<slug>/us/<ref>` → parse out `<slug>` and `<ref>`, or
- an explicit project slug + user story ref.

If neither is given, ask once for the user story reference. Do not guess.

## Workflow

### 1. Fetch the user story (with its existing child tasks)

Call `get_entity_by_ref_tool(project_slug, <us_ref>, "userstory", include_history=False)` with
`fields: ["subject", "status", "description", "related.tasks.ref", "related.tasks.subject"]`.

You need both the full description (source of the acceptance criteria) and the existing child tasks (idempotency check). Never fetch history — it is not needed here.

### 2. Extract every Acceptance Criterion

Scan the user story description for an acceptance-criteria section: a heading containing
"Acceptance Criteria" (case-insensitive), or "AC", followed by its list items. Supported item formats:
- numbered or bulleted list items,
- `- [ ]` / `- [x]` checklist items,
- Given/When/Then blocks — each complete block is one criterion.

Number them AC-1..AC-n in document order and keep the **verbatim text** of each (it goes into the task for traceability).

Rules:
- Every criterion becomes a task; never merge two criteria into one task, never skip one.
- If no acceptance-criteria section exists or it is empty: **stop and ask the user**. Never invent criteria to fill in.
- If an item is not testable (no observable outcome), still create its task but flag it in the plan table as `needs clarification`.

### 3. Idempotency check — never duplicate on re-run

Compare each AC against the existing child tasks from step 1:
- a task whose description contains the same verbatim AC text, or
- a task whose subject matches the AC's imperative form,
counts as already covered → skip it and list it in the final report as `existing`.

Only create tasks for uncovered criteria. If all are covered, report that and stop — do not create anything.

### 4. Estimate every task (mandatory)

Each new task must carry an estimate before creation completes:
- **Unit**: story points or man-days — use whichever the project/team already uses; if unknown, ask once ("story points or man-days?").
- **Proposal heuristic** (adjust to the team's scale): trivial ≤ 1 pt / 0.5 md · small 2 pt / 1 md · medium 3–5 pt / 2 md · large 8 pt / 3+ md. A criterion that looks larger than one task is a red flag: propose splitting it and say so in the plan table.
- **Where the estimate is recorded**: first call `list_custom_attributes_tool(project_slug, "task")`. If the project has an estimate-like custom attribute (name containing "estimate", "points", or "effort"), set it on each created task via `set_custom_attributes_tool` using that attribute id and value. Otherwise record it in the task description as a structured line:
  `**Estimate:** <value> <story points|man-days>`

### 5. Present the plan, then create

Show the user a table before creating anything (skip only if they explicitly pre-approved creation):

| AC | Task subject | Estimate | Action |
|----|--------------|----------|--------|
| AC-1 | <imperative subject> | 3 story points | create |
| AC-2 | ... | 1 man-day | existing (task #<ref>) |

On confirmation, for each `create` row call:

```
create_entity_tool(
    project_slug=<slug>,
    entity_type="task",
    subject="<imperative form of the AC, ≤ ~80 chars>",
    status="<first open task status of the project>",
    parent_ref=<us_ref>,
    description="""Acceptance criterion <n> from US #<us_ref>:

<verbatim AC text>

Story: https://<host>/project/<slug>/us/<us_ref>

**Estimate:** <value> <story points|man-days>"""
)
```

Status handling: pass the project's first open task status (e.g. "Backlog"). If creation fails with a status error, retry once using one of the valid statuses listed in the error message — never invent a status name.

If an estimate custom attribute was found in step 4, follow each successful creation with `set_custom_attributes_tool(project_slug, <task_ref>, "task", {<attr_id>: <value>})`.

### 6. Read-back verification (fail-closed)

After creating all tasks, re-fetch each new task (`get_entity_by_ref_tool`, `include_history=False`) and verify:
- the description contains the verbatim AC text, and
- an estimate is present (custom attribute value or the `**Estimate:**` line).

Any mismatch = report it as a failure for that task; do not mark the run successful.

### 7. Final summary report

End with a table mapping every criterion to its outcome:

| AC | Task ref / URL | Estimate | Status |
|----|----------------|----------|--------|
| AC-1 | #<ref> (url) | 3 story points | created |
| AC-2 | #<ref> (url) | 1 man-day | existing |

Plus: total criteria, created, skipped-as-existing, and any `needs clarification` flags.

## Hard rules — never violate

1. One task per acceptance criterion — no merging, no skipping, no extra tasks beyond the criteria.
2. Every created task carries an estimate in story points or man-days before the run is reported successful.
3. Never invent acceptance criteria; missing AC section = stop and ask.
4. Idempotent: re-running on the same user story must not duplicate existing tasks.
5. Do not modify the user story itself (no status, description, or point changes) — only create its child tasks.
6. Evidence over claims: report only task refs you actually created and read back.

## Related skills (same `taiga` plugin)

- `taiga-status-sync` — keeps task/user-story statuses in sync with the work agents perform once tasks exist. This skill only creates tasks; it never changes any status (hard rule 5).
