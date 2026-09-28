# AGENTS.md

Guidance for AI agents (and humans) working in this repository.

## What this repo is

A **marketplace aggregator** for agentic skills and plugins, not an application. It has no
build system, no test suite of its own, and no runtime service. Its "product" is:

1. A set of skill/plugin source trees (four git submodules + first-party `hadrian/`).
2. Python tooling that discovers, installs, validates, and aggregates them into a root
   `marketplace.json` manifest for agentic harnesses (dcode, Claude Code, DeepAgents).

## Repository map

- `marketplace.json` — aggregated root manifest; also mirrored to `.agents/plugins/marketplace.json`. **Generated** by `update_marketplace.py`; prefer regenerating over hand-editing entries.
- Submodules (upstream-owned): `android-skills/`, `scientific-agent-skills/`, `scientific-skills/`, `kotlin-kmp-claude-agent-skills/` — see `.gitmodules`.
- First-party: `hadrian/` (skill), `core/registry.py`, `tools/scaffold_plugin.py`, `tools/validate_plugin.py`, `schema/plugin_schema.json`, and the root-level scripts.

## Hard rules

1. **Never edit submodule contents** expecting them to persist in this repo's history —
   they are pinned commits of upstream projects. Fix upstream (or a fork) instead.
2. **Never commit local state**: `installed_skills/`, `.agents/`, `.hadrian/`,
   `__pycache__/` are gitignored for a reason.
3. **Skill ID = the `name:` field in `SKILL.md` frontmatter** and must be unique across
   the entire tree; duplicates are silently skipped by `install_skills.py` (with a stderr
   warning). Check before adding a skill with an existing name.
4. **Keep tooling stdlib-only.** `install_skills.py`, `generate_metadata.py`,
   `update_marketplace.py`, and `core/registry.py` use only the Python standard library on
   purpose — they must run on a fresh clone without `pip install`. Only
   `tools/validate_plugin.py` has an external dependency (`jsonschema`).
5. **Do not hand-edit generated files** when a generator exists: root `marketplace.json`
   and `.agents/plugins/marketplace.json` come from `update_marketplace.py`; per-skill
   `metadata.json` files come from `generate_metadata.py`.

## Conventions

- A skill is a directory containing a `SKILL.md` with YAML frontmatter. Minimum viable
  frontmatter:

  ```markdown
  ---
  name: my-skill
  description: One or two sentences: what it does and when to use it.
  metadata:
    version: "1.0.0"
  ---
  ```

- The frontmatter parsers are intentionally minimal (flat `key: value`, one level of
  nesting, folded scalars). Avoid exotic YAML (anchors, multi-line lists under a key) in
  first-party skills — it will not parse correctly.
- Plugin manifests (`marketplace.json`) must satisfy `schema/plugin_schema.json`:
  required fields are `name`, `version`, `description`, `harnesses` (enum:
  `deepagents`, `dcode`, `claude-code`, `opencode`, `generic`).

## Common workflows

### Add a first-party skill

1. Create `<skill-name>/SKILL.md` with valid frontmatter at the repo root level.
2. Give the plugin directory a manifest (`python3 tools/scaffold_plugin.py --name ...`)
   or an existing local `marketplace.json`.
3. Validate: `python3 tools/validate_plugin.py <dir>/marketplace.json` (needs `jsonschema`).
4. Regenerate the root manifest: `python3 update_marketplace.py .`

### Add an upstream skill collection

1. `git submodule add <url> <path>` and commit `.gitmodules` + the gitlink.
2. Ensure it has a discoverable manifest (`.claude-plugin/plugin.json`,
   `.codex-plugin/plugin.json`, or local `marketplace.json`) — otherwise
   `update_marketplace.py` will not pick it up.
3. Run `python3 update_marketplace.py .` and commit the regenerated manifests.

### Update submodules to latest upstream

```bash
git submodule update --remote <path>     # move gitlink to upstream HEAD
git add <path> && git commit -m "Bump <name> submodule"
```

## Verification commands

There is no test suite; verify changes by running the tooling:

```bash
python3 install_skills.py list            # discovery still works, no duplicate-ID warnings
python3 update_marketplace.py .           # manifests regenerate cleanly
python3 -m json.tool marketplace.json     # root manifest is valid JSON
python3 tools/validate_plugin.py <manifest>   # per-plugin schema check (needs jsonschema)
git status                                # confirm only intended files changed; no gitignored state staged
```

## Style

- Python: stdlib, `#!/usr/bin/env python3`, argparse CLIs, exit codes for errors. Match
  the existing scripts' tone (plain prints to stdout, warnings/errors to stderr).
- Markdown docs: keep tables and code blocks; no emoji in first-party files.
- Commit messages: imperative mood, one line, e.g. `Add Hadrian L3 goal-loop skill`.
